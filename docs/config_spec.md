# tkzs-structlog 配置规范（摘要）

详细设计与边界说明以仓库根目录《开发需求.md》为准。此处列出顶层配置结构与加载优先级。

## 顶层字段（节选）

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 配置版本：`1.0` / `2.0` / `2.1` / `3.0` / `4.0` |
| `logger_name` | string | structlog 日志器名称 |
| `min_level` | string | `DEBUG` / `INFO` / `WARN` / `ERROR`（`WARN` 归一为 WARNING） |
| `bridge_std_logging` | bool | 为 true 时使用 stdlib `LoggerFactory` + `ProcessorFormatter` 桥接标准库 `logging` |
| `processors` | string[] | 处理器类路径列表（渲染器类名会被单独处理） |
| `handlers` | object | `console` / `file` 等输出配置 |
| `extensions` | object | 截断、脱敏、过滤、热重载等扩展（随版本递增） |

内置默认值见 `src/tkzs_structlog/config/defaults.py` 中的 `get_default_config()`。

## 加载优先级

1. `init_structlog(config_path=...)` 指定文件  
2. 环境配置：`STRUCTLOG_ENV` → `structlog_config.{env}.json`  
3. 工作目录 / 项目根目录下的 `structlog_config.json`  
4. 内置默认 + `merge_config` 合并  

空文件或仅注释且无 JSON 值的文件视为 `{}`，再与内置默认合并。
