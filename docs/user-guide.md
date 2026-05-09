# tkzs-structlog 用户手册

## 目录

1. [概述](#1-概述)
2. [安装](#2-安装)
3. [快速开始](#3-快速开始)
4. [配置文件](#4-配置文件)
5. [日志截断](#5-日志截断)
6. [自定义复合轮转](#6-自定义复合轮转)
7. [敏感信息脱敏](#7-敏感信息脱敏)
8. [多环境配置](#8-多环境配置)
9. [上下文绑定](#9-上下文绑定)
10. [日志过滤](#10-日志过滤)
11. [配置热重载](#11-配置热重载)
12. [生态集成 (V4.0)](#12-生态集成-v40)
13. [异常处理](#13-异常处理)

---

## 1. 概述

tkzs-structlog 是一个配置驱动的 Structlog 自动化配置工具。它通过 JSONC 配置文件定义所有日志行为，无需在业务代码中编写日志配置逻辑。

支持 Python 3.10+，完整的类型注解，100% 测试覆盖率。

## 2. 安装

### 基础安装

```bash
pip install tkzs-structlog
```

### 完整安装（含所有可选依赖）

```bash
pip install "tkzs-structlog[all]"
```

### 按需安装

```bash
# CLI 工具 + 热重载
pip install "tkzs-structlog[cli]"

# 第三方输出（PGSQL/Redis）
pip install "tkzs-structlog[ecosystem]"

# 扩展压缩后端（lz4/zstd）
pip install "tkzs-structlog[compress]"
```

## 3. 快速开始

### 3.1 最小化使用

```python
import tkzs_structlog

# 自动加载项目根目录的 structlog_config.json
# 若配置文件不存在，自动使用内置默认配置
tkzs_structlog.init_structlog()

logger = tkzs_structlog.get_logger()
logger.info("app_started", version="1.0.0")
```

### 3.2 自定义配置路径

```python
tkzs_structlog.init_structlog(config_path="/etc/myapp/structlog_config.json")
```

### 3.3 直接传入配置字典

```python
config = {
    "version": "2.1",
    "logger_name": "myapp",
    "min_level": "DEBUG",
    "handlers": {
        "console": {"enable": True},
        "file": {"enable": True, "file_path": "./logs/app.log"},
    },
}
tkzs_structlog.init_structlog(config=config)
```

### 3.4 获取命名日志器

```python
logger = tkzs_structlog.get_logger("my_module")
logger.info("module_loaded")
```

## 4. 配置文件

配置文件使用 JSONC 格式（支持 `//` 注释），默认从项目根目录加载。

### 4.1 最小配置

```jsonc
{
  "version": "2.1",
  "logger_name": "myapp",
  "min_level": "INFO",
  "handlers": {
    "console": {"enable": true}
  }
}
```

### 4.2 完整配置结构

```jsonc
{
  "version": "2.1",               // 配置版本：1.0 / 2.0 / 2.1 / 3.0 / 4.0
  "logger_name": "structlog_auto", // 日志器名称
  "min_level": "INFO",            // 日志级别：DEBUG / INFO / WARN / ERROR
  "bridge_std_logging": true,     // 桥接标准 logging 模块
  "context_bind": false,          // 是否启用上下文绑定

  "processors": [                 // 处理器链（按顺序执行）
    "structlog.processors.TimeStamper",
    "structlog.dev.ConsoleRenderer"
  ],

  "handlers": {
    "console": {
      "enable": true              // 控制台输出
    },
    "file": {
      "enable": false,
      "file_path": "./logs/structlog.log",
      "encoding": "utf-8",
      "custom_rotate": {          // 自定义复合轮转
        "enable": false,
        "max_bytes": 10485760,    // 10MB
        "backup_count": 10,
        "retain_days": 7,
        "rotate_when": "MIDNIGHT",
        "interval": 1,
        "compress": false,
        "compress_method": "gzip",
        "compress_concurrency": 2,
        "compress_async": true
      }
    }
  },

  "extensions": {
    "log_truncate": {             // 日志截断
      "enable": false,
      "max_depth": 3,
      "str_max_length": 256,
      "seq_max_elements": 50,
      "dict_max_pairs": 30,
      "ignore_types": [],
      "ignore_fields": [],
      "ignore_fields_pattern": [],
      "ignore_fields_regex": null,
      "depth_warning": true
    },
    "sensitive_fields": [         // 敏感信息脱敏字段
      "password", "phone", "id_card", "bank_card"
    ],
    "trace_id_bind": false,       // 自动绑定 trace_id
    "filter_rules": {             // 日志过滤规则
      "exclude": [],
      "include": []
    },
    "config_hot_reload": false,   // 配置热重载
    "elk_compatible": false,
    "sentry_enable": false,
    "sentry_dsn": null
  }
}
```

### 4.3 加载优先级

1. `init_structlog(config_path=...)` 指定路径
2. 环境配置：`STRUCTLOG_ENV=prod` → `structlog_config.prod.json`
3. 项目根目录 `structlog_config.json`
4. 内置默认配置（最终降级）

详细字段说明请参考 [配置规范文档](config_spec.md)。

## 5. 日志截断

自动截断超长字符串和大容量容器，避免日志输出过大。

### 5.1 配置

```jsonc
{
  "extensions": {
    "log_truncate": {
      "enable": true,
      "max_depth": 3,              // 递归深度（嵌套对象截断层数）
      "str_max_length": 256,       // 字符串最大长度
      "seq_max_elements": 50,      // list/tuple/set 最大元素数
      "dict_max_pairs": 30,        // 字典最大键值对
      "ignore_types": ["UserToken"],          // 不截断的类名
      "ignore_fields": ["trace_id"],          // 不截断的字段名
      "ignore_fields_pattern": ["*_id"],       // 通配符匹配
      "ignore_fields_regex": "^session.*",    // 正则匹配
      "depth_warning": true                    // 超限时标注警告
    }
  }
}
```

### 5.2 截断规则

| 类型 | 截断方式 |
|------|----------|
| `str` | 对称截断（前 N/2 + ... + 后 N/2） |
| `list` / `tuple` / `set` | 对称截断元素 |
| `dict` | 对称截断键值对 |
| 可迭代对象 | 按元素截断 |
| 不可迭代对象 | 对 `repr()` 截断 |
| `int` / `float` / `bool` / `None` | 不截断 |
| `@truncate_ignore` 标记类 | 不截断 |

### 5.3 字段排除优先级

1. 精确匹配 (`ignore_fields`)
2. 通配符匹配 (`ignore_fields_pattern`)
3. 正则匹配 (`ignore_fields_regex`)

## 6. 自定义复合轮转

支持多维度日志轮转策略。

### 6.1 触发条件

- **大小轮转**：日志文件 ≥ `max_bytes`
- **日期轮转**：到达指定时间（MIDNIGHT / H / D / W0-W6）

### 6.2 清理规则

满足任一条件即清理：
- 日志文件数 > `backup_count`（保留最新 N 个）
- 日志文件时间 > `retain_days`（保留 N 天内）

### 6.3 压缩

```jsonc
{
  "handlers": {
    "file": {
      "custom_rotate": {
        "compress": true,
        "compress_method": "gzip",  // gzip / lz4 / zstd
        "compress_concurrency": 2,  // 异步压缩并发数
        "compress_async": true      // 开启异步压缩
      }
    }
  }
}
```

### 6.4 轮转安全保证

- **原子重命名**：`os.replace()` 跨平台原子操作，重试 3 次
- **进程锁**：跨平台文件锁，多进程不冲突
- **异步压缩**：线程池 + 信号量限流，队列满时自动降级同步压缩
- **降级策略**：压缩后端缺失时降级 gzip，压缩失败保留原文件

详细实现见 `tkzs_structlog/extensions/rotation.py`。

## 7. 敏感信息脱敏

### 7.1 内置脱敏规则

| 字段 | 规则 | 示例 |
|------|------|------|
| `password` | 全替换 | `"******"` |
| `phone` | 保留前3后4 | `"138****5678"` |
| `id_card` | 保留前6后4 | `"110101******1234"` |
| `bank_card` | 保留前4后4 | `"6222******1234"` |

### 7.2 自定义脱敏字段

```jsonc
{
  "extensions": {
    "sensitive_fields": ["token", "secret_key", "api_key"]
  }
}
```

自定义字段默认全隐藏（`******`）。

## 8. 多环境配置

通过环境变量 `STRUCTLOG_ENV` 加载对应环境的配置文件。

```bash
# 加载 structlog_config.prod.json
export STRUCTLOG_ENV=prod

# 加载 structlog_config.dev.json
export STRUCTLOG_ENV=dev
```

加载优先级：`structlog_config.{env}.json` → `structlog_config.json` → 内置默认。

## 9. 上下文绑定

### 9.1 全局上下文

```python
import tkzs_structlog

tkzs_structlog.init_structlog()

# 绑定全局上下文
tkzs_structlog.bind_context(request_id="abc123", user_id=100)

# 所有日志自动包含这些字段
logger = tkzs_structlog.get_logger()
logger.info("order_created", order_id=5001)

# 解绑特定字段
tkzs_structlog.unbind_context("request_id")

# 清空所有上下文
tkzs_structlog.clear_context()
```

### 9.2 自动 trace_id

```jsonc
{
  "extensions": {
    "trace_id_bind": true
  }
}
```

```python
tkzs_structlog.init_structlog()
# 自动绑定 trace_id（UUID）
tkzs_structlog.bind_context(auto_trace_id=True)
```

或通过 API 参数启用：

```python
tkzs_structlog.init_structlog(enable_trace_id=True)
```

## 10. 日志过滤

```jsonc
{
  "extensions": {
    "filter_rules": {
      "exclude": ["debug_info", "internal_data"],
      "include": ["timestamp", "level", "event", "user_id"]
    }
  }
}
```

- `include`：白名单模式，只保留指定字段
- `exclude`：黑名单模式，过滤指定字段
- `include` 优先级高于 `exclude`

## 11. 配置热重载

需要安装 `watchdog`：

```bash
pip install tkzs-structlog[cli]
```

### 11.1 配置文件启用

```jsonc
{
  "extensions": {
    "config_hot_reload": true
  }
}
```

### 11.2 API 参数启用

```python
tkzs_structlog.init_structlog(enable_hotreload=True)
```

配置文件变更后自动重新加载，热重载时加全局锁保证线程安全。

## 12. 生态集成 (V4.0)

### 12.1 PGSQL

```jsonc
{
  "handlers": {
    "pgsql": {
      "enable": true,
      "table_name": "structlog_logs",
      "batch_size": 100,
      "flush_interval": 5,
      "pool_size": 5
    }
  }
}
```

连接信息从 `.env` 文件读取：

```
PG_HOST=127.0.0.1
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=secret
PG_DB=logs
```

### 12.2 Redis

```jsonc
{
  "handlers": {
    "redis": {
      "enable": true,
      "key_prefix": "structlog:",
      "batch_size": 100,
      "flush_interval": 5
    }
  }
}
```

连接信息从 `.env` 文件读取：

```
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### 12.3 Sentry

```jsonc
{
  "extensions": {
    "sentry_enable": true,
    "sentry_dsn": "https://xxx@sentry.io/xxx"
  }
}
```

仅 ERROR/CRITICAL 级别发送，Sentry 不可用不影响主流程。

### 12.4 降级策略

| 输出源 | 降级行为 |
|--------|----------|
| PGSQL | 连接失败 → 文件输出 |
| Redis | 连接失败 → 文件输出 |
| Sentry | 仅 ERROR/CRITICAL 发送，不可用跳过 |

## 13. 异常处理

所有自定义异常继承 `StructlogBaseError`，示例：

```python
from tkzs_structlog import StructlogConfigError

try:
    tkzs_structlog.init_structlog()
except StructlogConfigError as e:
    print(e.error_type)      # "ConfigError"
    print(e.error_field)     # "version"
    print(e.reason)          # "Unsupported config version: 5.0"
    print(e.fix_suggestion)  # "Supported versions: 1.0, 2.0, 2.1, 3.0, 4.0"
```

### 异常类型

| 异常类 | 触发场景 |
|--------|----------|
| `StructlogConfigError` | 配置错误基类 |
| `StructlogConfigFileNotFoundError` | 配置文件不存在 |
| `StructlogConfigParseError` | 配置文件语法错误 |
| `StructlogConfigVersionError` | 不支持的配置版本 |
| `StructlogProcessorImportError` | 处理器导入失败 |
| `StructlogProcessorInstantiateError` | 处理器实例化失败 |
| `StructlogNotInitedError` | 未初始化时调用 get_logger |
| `StructlogHandlerError` | 输出处理器错误 |
