# tkzs-structlog

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Structlog Version](https://img.shields.io/badge/structlog-23.1.0+-green.svg)](https://www.structlog.org/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-ff69b4.svg)](https://docs.astral.sh/ruff/)
[![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://pytest-cov.readthedocs.io/)
[![License](https://img.shields.io/badge/license-LGPL%20v2.1-blue.svg)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

**配置驱动、零代码侵入**的 Structlog 自动化配置工具，支持日志截断、复合轮转、多环境适配、敏感信息脱敏、热重载、CLI 工具及第三方输出集成（PGSQL/Redis/Kafka/Sentry）。

## 特性一览

| 版本 | 核心能力 | 文档 |
|------|----------|------|
| V1.0 | 配置加载/校验、控制台/文件输出、标准 logging 桥接 | [用户手册](docs/user-guide.md) |
| V2.0 | 日志智能截断、自定义复合轮转、多环境、脱敏、上下文绑定 | [用户手册](docs/user-guide.md) |
| V2.1 | 截断类型缓存、通配符/正则排除、深度警告；异步压缩、原子重命名、可插拔压缩后端 | [用户手册](docs/user-guide.md) |
| V3.0 | 配置热重载、CLI 工具、完整类型提示 | [CLI 指南](docs/cli-guide.md) |
| V4.0 | PGSQL/Redis/Kafka/Sentry 集成 | [生态集成](docs/user-guide.md#生态集成-v40) |

## 快速开始

```bash
pip install tkzs-structlog
```

```python
import tkzs_structlog

tkzs_structlog.init_structlog()
logger = tkzs_structlog.get_logger()
logger.info("user_login", user_id=123, phone="13812345678", password="secret")
```

配置文件 `structlog_config.json` 自动从项目根目录加载，详见 [配置规范](docs/config_spec.md)。

## 文档

| 文档 | 说明 |
|------|------|
| [用户手册](docs/user-guide.md) | 安装、配置、功能详解、生产实践 |
| [API 参考](docs/api-reference.md) | 所有公开 API 签名与用法 |
| [CLI 指南](docs/cli-guide.md) | validate/generate/version 命令 |
| [配置规范](docs/config_spec.md) | JSONC 全字段说明 |
| [生产最佳实践](docs/best-practices.md) | 部署、性能、安全建议 |

## 核心设计原则

- **配置驱动**：所有日志行为通过 JSONC 定义，无需修改业务代码
- **向下兼容**：高版本工具兼容低版本配置，缺失字段自动填充默认值
- **异常友好**：所有异常包含错误类型 + 错误字段 + 原因 + 修复建议
- **默认降级**：配置缺失/非法时降级到内置默认配置，避免服务不可用

## 开发

```bash
uv sync --all-extras
ruff check . --fix && ruff format .
mypy src/tkzs_structlog
pytest --cov=tkzs_structlog tests/
```

## 许可证

[GNU Lesser General Public License v2.1](LICENSE)
