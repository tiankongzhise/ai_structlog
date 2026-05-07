# tkzs-structlog

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Structlog Version](https://img.shields.io/badge/structlog-23.1.0+-green.svg)](https://www.structlog.org/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-ff69b4.svg)](https://docs.astral.sh/ruff/)
[![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://pytest-cov.readthedocs.io/)

tkzs-structlog 是一款**配置驱动、无代码侵入**的 Structlog 自动化配置工具，支持日志截断、复合轮转、多环境适配、敏感信息脱敏等生产级能力，全程遵循向下兼容、异常明确、默认降级的设计原则，可快速集成到任意 Python 项目中。

## 核心特性

| 版本 | 核心能力 | 关键特性 |
|------|----------|----------|
| V1.0（基础版） | 基础日志配置与输出 | 配置加载/校验、控制台/文件输出、标准 logging 桥接 |
| V2.0（增强版） | 生产级核心能力 | 日志智能截断、自定义复合轮转（日期+大小+保留+压缩）、多环境、脱敏、上下文绑定 |
| V2.1（优化版） | 性能/稳健性增强 | 截断类型缓存、深度警告、通配符/正则排除字段；异步压缩、原子重命名、可插拔压缩后端 |
| V3.0（扩展版） | 易用性提升 | 配置热重载、CLI 工具、完整类型提示 |
| V4.0（生态版） | 第三方输出适配 | PGSQL/Redis/ELK/Kafka/Sentry 集成 |

### 核心优势
1. **配置驱动**：通过 JSONC 配置文件定义所有日志行为，无需修改业务代码
2. **向下兼容**：高版本工具兼容低版本配置，缺失字段自动填充默认值
3. **异常友好**：所有异常包含错误字段+修复建议，快速定位问题
4. **默认降级**：配置非法/缺失时自动降级到内置默认配置，避免服务不可用
5. **性能优化**：类型缓存、异步压缩、原子操作，适配高并发场景

## 快速开始

### 安装
```bash
pip install tkzs-structlog
```

### 基础使用

#### 1. 创建配置文件
在项目根目录创建 `structlog_config.json`（支持 JSONC 注释）：
```jsonc
{
  "version": "2.1",
  "logger_name": "my_project",
  "min_level": "INFO",
  "handlers": {
    "console": {"enable": true},
    "file": {
      "enable": true,
      "file_path": "./logs/app.log",
      "custom_rotate": {
        "enable": true,
        "max_bytes": 10485760,  // 10MB
        "backup_count": 10,
        "retain_days": 7,
        "compress": true,
        "compress_async": true
      }
    }
  },
  "extensions": {
    "log_truncate": {
      "enable": true,
      "max_depth": 3,
      "str_max_length": 256,
      "ignore_fields_pattern": ["*_id", "session_*"]
    },
    "sensitive_fields": ["password", "phone", "id_card"]
  }
}
```

#### 2. 初始化并使用日志
```python
import tkzs_structlog

# 初始化（自动加载根目录配置文件）
tkzs_structlog.init_structlog()

# 获取日志器
logger = tkzs_structlog.get_logger()

# 输出日志
logger.info("user_login", user_id=123, phone="13812345678", password="123456")
# 输出示例（自动脱敏+截断）：
# {"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "event": "user_login", "user_id": 123, "phone": "138****5678", "password": "******"}
```

### 自定义配置路径
```python
# 加载指定路径的配置文件
tkzs_structlog.init_structlog(config_path="/opt/config/structlog_config.json")
```

## 核心功能详解

### 1. 日志智能截断
自动截断超长字符串、大容器（列表/字典/集合），支持：
- 递归深度控制（避免嵌套对象过度展开）
- 类型级忽略（指定类不截断）
- 字段级忽略（精确匹配/通配符/正则）
- 深度警告（超限字段标注警告信息）

**配置示例**：
```jsonc
{
  "extensions": {
    "log_truncate": {
      "enable": true,
      "max_depth": 3,
      "str_max_length": 256,
      "seq_max_elements": 50,
      "dict_max_pairs": 30,
      "ignore_types": ["UserToken"],
      "ignore_fields": ["trace_id"],
      "ignore_fields_pattern": ["*_id"],
      "ignore_fields_regex": "^session.*",
      "depth_warning": true
    }
  }
}
```

### 2. 自定义复合轮转
支持多维度日志轮转策略，保障日志文件可控：
- **触发条件**：文件大小超限 / 到达指定时间（如每天零点）
- **清理规则**：按文件数量 / 保留天数清理旧日志
- **压缩优化**：异步压缩、可插拔后端（gzip/lz4/zstd）、原子重命名

**配置示例**：
```jsonc
{
  "handlers": {
    "file": {
      "enable": true,
      "file_path": "./logs/app.log",
      "custom_rotate": {
        "enable": true,
        "max_bytes": 10485760,      // 10MB
        "backup_count": 10,         // 最多保留10个文件
        "retain_days": 7,           // 最多保留7天
        "rotate_when": "MIDNIGHT",  // 按天轮转
        "compress": true,
        "compress_method": "gzip",  // 支持 gzip/lz4/zstd
        "compress_concurrency": 2,  // 异步压缩并发数
        "compress_async": true      // 开启异步压缩
      }
    }
  }
}
```

### 3. 敏感信息脱敏
自动脱敏常见敏感字段，支持自定义脱敏规则：
- 内置字段：`password`（全隐藏）、`phone`（保留前3后4）、`id_card`（保留前6后4）
- 自定义字段：通过 `extensions.sensitive_fields` 扩展

### 4. 多环境配置
通过环境变量 `STRUCTLOG_ENV` 加载对应环境配置：
```bash
# 加载 structlog_config.prod.json
export STRUCTLOG_ENV=prod
```

配置加载优先级：`structlog_config.{env}.json` → `structlog_config.json` → 内置默认配置

## CLI 工具（V3.0+）
```bash
# 校验配置文件合法性
tkzs-structlog validate --config-path ./structlog_config.json

# 生成默认配置文件（含注释）
tkzs-structlog generate --output ./structlog_config.json

# 查看版本信息
tkzs-structlog version
```

## 配置全参考
完整的配置字段说明请参考：[配置规范文档](docs/config_spec.md)

## 生态集成（V4.0+）
支持将日志输出到第三方服务，配置示例：
```jsonc
{
  "handlers": {
    "redis": {
      "enable": true,
      "host": "127.0.0.1",
      "port": 6379,
      "db": 0,
      "key": "app_logs"
    },
    "kafka": {
      "enable": true,
      "bootstrap_servers": ["127.0.0.1:9092"],
      "topic": "app_logs"
    }
  },
  "extensions": {
    "sentry_enable": true,
    "sentry_dsn": "https://xxx@sentry.io/xxx"
  }
}
```

## 测试与兼容性
- **Python 版本**：3.8+
- **Structlog 版本**：23.1.0+
- **测试覆盖率**：100% 单元测试覆盖，100% 集成测试通过率
- **兼容性**：全版本配置向下兼容，低版本配置可直接在高版本工具中使用

## 异常处理
所有自定义异常均继承 `StructlogBaseError`，包含以下属性便于排查：
- `error_type`：错误类型（如 ConfigError/ProcessorError）
- `error_field`：错误字段（若有）
- `reason`：错误原因
- `fix_suggestion`：修复建议

## 开发与贡献
### 代码规范
项目使用 `ruff` 进行代码格式化和校验：
```bash
# 格式化代码
ruff format .

# 校验并自动修复
ruff check . --fix
```

### 测试
```bash
# 运行单元测试（含覆盖率报告）
pytest --cov=tkzs_structlog tests/

# 运行集成测试
pytest tests/integration/
```

## 许可证

本项目基于 **GNU Lesser General Public License v2.1 (LGPL v2.1)** 许可证发布。

详细条款请参考：
- [LICENSE](LICENSE)
- [GNU LGPL v2.1 官方文档](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

### 关于 LGPL v2.1
- 你可以**自由使用、修改、分发本项目**
- 若对本项目**源码进行修改**，修改后的源码**必须同样以 LGPL v2.1 开源**
- 允许**作为库被闭源商业项目引用/链接使用**，无需开源闭源部分
- 需保留原始版权声明与许可证文本

## 交付物清单
- 📦 Python 包：`tkzs-structlog`（PyPI 发布）
- 📝 文档：用户手册、配置规范、API 文档、CLI 使用文档
- 🧪 测试：单元测试（100% 覆盖率）、集成测试、性能测试、兼容性测试
- 📊 报告：测试报告、性能数据、兼容性验证结果