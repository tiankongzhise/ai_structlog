# tkzs-structlog 生产最佳实践

## 目录

1. [配置管理](#1-配置管理)
2. [性能优化](#2-性能优化)
3. [安全实践](#3-安全实践)
4. [部署建议](#4-部署建议)
5. [多环境策略](#5-多环境策略)
6. [监控与排障](#6-监控与排障)

---

## 1. 配置管理

### 1.1 配置文件版本化

始终为配置文件指定 `version` 字段，确保高版本工具能正确解析：

```jsonc
{
  "version": "2.1"
}
```

### 1.2 日志级别策略

| 环境 | 建议级别 | 说明 |
|------|----------|------|
| 开发 | `DEBUG` | 捕获详细信息 |
| 测试 | `INFO` | 减少噪声 |
| 生产 | `INFO` 或 `WARN` | 仅关注关键信息 |

### 1.3 文件输出配置

```jsonc
{
  "handlers": {
    "file": {
      "enable": true,
      "file_path": "/var/log/myapp/app.log",
      "custom_rotate": {
        "enable": true,
        "max_bytes": 104857600,    // 100MB
        "backup_count": 30,
        "retain_days": 30,
        "compress": true,
        "compress_async": true
      }
    }
  }
}
```

建议：
- 生产环境始终启用轮转和压缩
- `backup_count` 和 `retain_days` 根据磁盘空间调整
- 日志路径使用绝对路径，避免工作目录变更导致日志丢失

---

## 2. 性能优化

### 2.1 日志截断配置

高并发场景下，合理配置截断参数可显著降低序列化开销：

```jsonc
{
  "extensions": {
    "log_truncate": {
      "enable": true,
      "str_max_length": 512,       // 根据业务字段长度调整
      "seq_max_elements": 20,      // 容器截断数量
      "dict_max_pairs": 10,
      "ignore_fields_pattern": ["*_id", "trace_*"]  // 通配符降低配置成本
    }
  }
}
```

### 2.2 处理器顺序

处理器链顺序影响性能。将轻量处理器放在前面，尽早过滤不需要的日志：

```jsonc
{
  "processors": [
    "structlog.stdlib.filter_by_level",
    "structlog.stdlib.add_log_level",
    "structlog.stdlib.add_logger_name",
    "structlog.processors.TimeStamper",
    "structlog.dev.ConsoleRenderer"
  ]
}
```

### 2.3 异步压缩

```jsonc
{
  "custom_rotate": {
    "compress_async": true,
    "compress_concurrency": 2,
    "compress_method": "lz4"       // lz4 压缩速度比 gzip 快 2-3 倍
  }
}
```

- lz4：压缩速度快，适合高频轮转
- zstd：压缩比高，适合低频轮转
- gzip：兼容性最好

### 2.4 缓存机制

tkzs-structlog 内置了以下缓存以提升性能：
- **类型判定缓存**：`lru_cache(maxsize=1024)` 缓存对象类型名称
- **处理器类缓存**：`lru_cache(maxsize=256)` 缓存处理器导入路径
- **截断配置哈希**：配置未变化时跳过属性赋值

---

## 3. 安全实践

### 3.1 敏感信息脱敏

```jsonc
{
  "extensions": {
    "sensitive_fields": [
      "password", "phone", "id_card", "bank_card",
      "token", "secret_key", "api_key", "refresh_token"
    ]
  }
}
```

不要在日志中记录：
- 明文密码
- 完整身份证号
- CVV / PIN 码
- 数据库连接字符串
- 私钥内容

### 3.2 日志过滤

```jsonc
{
  "extensions": {
    "filter_rules": {
      "exclude": [
        "credit_card_no",
        "cvv",
        "pin",
        "auth_token"
      ]
    }
  }
}
```

### 3.3 生产安全 checklist

- [ ] 敏感字段全部加入 `sensitive_fields`
- [ ] 不在日志中记录完整个人身份信息（PII）
- [ ] 日志文件权限设为 640 或更严格
- [ ] 日志目录不与 Web 静态目录重叠
- [ ] 定期轮转和压缩日志文件
- [ ] 配置 `retain_days` 满足合规要求

---

## 4. 部署建议

### 4.1 Docker 部署

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install "tkzs-structlog[all]"

# 复制配置
COPY structlog_config.json .

# 确保日志目录存在
RUN mkdir -p /var/log/myapp

CMD ["python", "-m", "myapp"]
```

### 4.2 Kubernetes 部署

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: structlog-config
data:
  structlog_config.json: |
    {
      "version": "2.1",
      "min_level": "INFO",
      "handlers": {
        "console": {"enable": true},
        "file": {
          "enable": true,
          "file_path": "/var/log/app/app.log",
          "custom_rotate": {
            "enable": true,
            "max_bytes": 52428800,
            "backup_count": 10,
            "compress": true
          }
        }
      }
    }
```

### 4.3 Supervisor / systemd

日志重定向配置：

```ini
[program:myapp]
command=python -m myapp
stdout_logfile=/var/log/myapp/stdout.log
stderr_logfile=/var/log/myapp/stderr.log
environment=STRUCTLOG_ENV="prod"
```

---

## 5. 多环境策略

### 5.1 文件命名约定

```
project/
  structlog_config.json          # 开发环境（默认）
  structlog_config.prod.json     # 生产环境
  structlog_config.staging.json  # 预发布环境
```

### 5.2 环境特定配置建议

| 配置项 | 开发 | 测试 | 生产 |
|--------|------|------|------|
| `min_level` | DEBUG | INFO | WARN |
| `console.enable` | true | true | false |
| `file.enable` | false | true | true |
| `file.custom_rotate.compress` | false | true | true |
| `sentry_enable` | false | false | true |

### 5.3 环境变量

```bash
# Linux/macOS
export STRUCTLOG_ENV=prod

# Windows PowerShell
$env:STRUCTLOG_ENV = "prod"
```

---

## 6. 监控与排障

### 6.1 常见问题

| 问题 | 排查方法 |
|------|----------|
| 日志不输出 | 检查 `min_level` 是否太高 |
| 配置文件未生效 | 使用 `validate` 命令校验 |
| 轮转不触发 | 检查 `enable: true` 和 `max_bytes` 配置 |
| 压缩不生效 | 检查可选依赖是否安装 |
| 热重载不工作 | 确认安装了 `watchdog` |

### 6.2 配置校验

```bash
# 部署前校验配置
tkzs-structlog validate --config-path ./structlog_config.prod.json
```

### 6.3 降级日志

当第三方输出（PGSQL/Redis）不可用时，tkzs-structlog 自动降级到文件输出并记录警告日志。监控这些警告可以及时发现下游服务问题：

```python
import logging

# 监听 structlog 内部日志
structlog_logger = logging.getLogger("structlog")
structlog_logger.addHandler(logging.StreamHandler())
```
