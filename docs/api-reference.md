# tkzs-structlog API 参考

## 核心 API

### `init_structlog(config_path=None, config=None, enable_hotreload=False, enable_trace_id=None, **kwargs)`

初始化 structlog 全局配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config_path` | `str \| Path \| None` | `None` | 配置文件路径，自动搜索项目根目录 |
| `config` | `dict \| None` | `None` | 直接传入配置字典（优先级高于文件加载） |
| `enable_hotreload` | `bool` | `False` | 启用配置热重载（需安装 watchdog） |
| `enable_trace_id` | `bool \| None` | `None` | 自动绑定 trace_id；为 None 时从配置读取 |
| `**kwargs` | `Any` | - | 额外配置，会覆盖配置文件中的对应字段 |

**异常：**
- `StructlogConfigError`：配置错误
- `StructlogConfigFileNotFoundError`：配置文件不存在
- `StructlogConfigParseError`：配置文件解析失败
- `StructlogConfigVersionError`：不支持的配置版本
- `StructlogProcessorError`：处理器相关错误

**示例：**

```python
import tkzs_structlog

# 自动加载配置
tkzs_structlog.init_structlog()

# 指定配置文件
tkzs_structlog.init_structlog(config_path="./config/prod.json")

# 直接传配置
tkzs_structlog.init_structlog(config={"version": "2.1", "min_level": "DEBUG"})

# 启用热重载和 trace_id
tkzs_structlog.init_structlog(enable_hotreload=True, enable_trace_id=True)
```

---

### `get_logger(name=None, **kwargs)`

获取 structlog 日志器。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str \| None` | `None` | 日志器名称，不传则使用配置中的 `logger_name` |
| `**kwargs` | `Any` | - | 额外的日志上下文 |

**返回值：** `structlog.types.BoundLogger`

**异常：**
- `StructlogNotInitedError`：未调用 `init_structlog()` 时抛出

**示例：**

```python
logger = tkzs_structlog.get_logger()
logger.info("event_name", key="value")

logger = tkzs_structlog.get_logger("my_module")
logger.warning("deprecated_api", endpoint="/v1/old")
```

---

### `bind_context(auto_trace_id=False, **kwargs)`

绑定全局日志上下文。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `auto_trace_id` | `bool` | `False` | 自动生成 UUID trace_id |
| `**kwargs` | `Any` | - | 上下文键值对 |

**示例：**

```python
tkzs_structlog.bind_context(request_id="abc123", user_id=100)
tkzs_structlog.bind_context(auto_trace_id=True)

logger = tkzs_structlog.get_logger()
logger.info("order_placed")  # 自动包含 request_id, user_id, trace_id
```

---

### `unbind_context(*keys)`

解绑全局上下文中的指定字段。

| 参数 | 类型 | 说明 |
|------|------|------|
| `*keys` | `str` | 要解绑的字段名 |

```python
tkzs_structlog.unbind_context("request_id")
```

---

### `clear_context()`

清空所有全局上下文。

```python
tkzs_structlog.clear_context()
```

---

### `is_initialized()`

检查 structlog 是否已初始化。

**返回值：** `bool`

```python
if tkzs_structlog.is_initialized():
    logger = tkzs_structlog.get_logger()
```

---

### `reset_structlog()`

重置 structlog 到未初始化状态。停止热重载，清除全局上下文。

```python
tkzs_structlog.reset_structlog()
```

---

## 配置 API

### `load_config(config_path=None, use_env=True, use_default=True)`

加载配置（支持多级降级）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config_path` | `str \| Path \| None` | `None` | 配置文件路径 |
| `use_env` | `bool` | `True` | 是否使用环境特定配置 |
| `use_default` | `bool` | `True` | 是否使用内置默认配置 |

**返回值：** `dict[str, Any]`

---

### `validate_config(config)`

校验配置字典。

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `dict[str, Any]` | 配置字典 |

**返回值：** `StructlogV1Config`（Pydantic 模型实例）

**异常：**
- `StructlogConfigVersionError`：不支持的配置版本
- `pydantic.ValidationError`：字段校验失败

---

### `get_default_config(version=None)`

获取指定版本的默认配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `version` | `str \| None` | `None` | 配置版本，None 返回最新版 |

**返回值：** `dict[str, Any]`

---

## 异常层次

```
Exception
  └── StructlogBaseError
        ├── StructlogConfigError
        │     ├── StructlogConfigFileNotFoundError
        │     ├── StructlogConfigParseError
        │     └── StructlogConfigVersionError
        ├── StructlogProcessorError
        │     ├── StructlogProcessorImportError
        │     └── StructlogProcessorInstantiateError
        ├── StructlogNotInitedError
        └── StructlogHandlerError
```

每个异常实例包含：

| 属性 | 类型 | 说明 |
|------|------|------|
| `error_type` | `str` | 错误类型 |
| `error_field` | `str \| None` | 错误字段 |
| `reason` | `str \| None` | 错误原因 |
| `fix_suggestion` | `str \| None` | 修复建议 |

---

## 模块结构

```
tkzs_structlog/
  __init__.py              # 公开 API 入口
  config/
    __init__.py
    defaults.py            # 内置默认配置
    loader.py              # 配置加载
    parser.py              # 配置解析
    validator.py           # Pydantic 配置校验
    env_loader.py          # 环境变量加载
  core/
    __init__.py
    initializer.py         # Structlog 初始化
    processor_builder.py   # 处理器链构建
    logger_factory.py      # 日志工厂
  extensions/
    __init__.py
    processors.py          # 截断/脱敏/过滤处理器
    handlers.py            # 控制台/文件处理器
    rotation.py            # 复合轮转处理器
    pgsql_handler.py       # PGSQL 输出
    redis_handler.py       # Redis 输出
    hotreload.py           # 配置热重载
  api/
    __init__.py
    core.py                # 核心 API 实现
    cli.py                 # CLI 实现
  exceptions/
    __init__.py            # 自定义异常
```
