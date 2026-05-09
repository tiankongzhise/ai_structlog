# tkzs-structlog CLI 指南

CLI 工具需要安装可选依赖：

```bash
pip install "tkzs-structlog[cli]"
```

## 命令概览

| 命令 | 功能 |
|------|------|
| `tkzs-structlog validate` | 校验配置文件合法性 |
| `tkzs-structlog generate` | 生成默认配置文件（含注释） |
| `tkzs-structlog version` | 显示版本信息 |

也可以使用别名 `structlog-auto`：

```bash
structlog-auto validate
structlog-auto generate
structlog-auto version
```

---

## validate — 校验配置文件

```bash
tkzs-structlog validate --config-path ./structlog_config.json
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--config-path` | `-c` | `structlog_config.json` | 配置文件路径 |

**退出码：**
- `0`：配置合法
- `1`：配置非法（输出错误详情）

**示例：**

```bash
# 校验成功
$ tkzs-structlog validate
Validating config: structlog_config.json
✓ Config is valid

# 校验失败
$ tkzs-structlog validate -c ./bad_config.json
Validating config: ./bad_config.json
✗ Config is invalid
  - [ConfigVersionError] Field: version | Reason: Unsupported config version: 5.0 | Fix: Supported versions: 1.0, 2.0, 2.1, 3.0, 4.0
```

---

## generate — 生成默认配置文件

```bash
tkzs-structlog generate --output ./structlog_config.json
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--output` | `-o` | `None`（输出到 stdout） | 输出文件路径 |
| `--env` | `-e` | `None` | 环境名称 |
| `--version` | `-v` | `2.1` | 配置版本 |

**示例：**

```bash
# 生成并输出到 stdout
tkzs-structlog generate

# 生成到文件
tkzs-structlog generate --output structlog_config.json

# 生成指定版本的配置
tkzs-structlog generate --version 1.0 --output config_v1.json

# 生成环境配置
tkzs-structlog generate --env prod --output structlog_config.prod.json
```

生成的文件包含注释头部：

```
# tkzs-structlog 配置文件 (版本 2.1)
# 自动生成于 2026-05-09 12:00:00
# 环境: prod

{
  "version": "2.1",
  "logger_name": "structlog_auto",
  ...
}
```

---

## version — 显示版本信息

```bash
tkzs-structlog version
```

**输出示例：**

```
tkzs-structlog: 4.0.0
Supported config versions: 1.0, 2.0, 2.1, 3.0, 4.0
```

---

## 在代码中使用 CLI 功能

CLI 底层实现函数也可直接在代码中调用：

```python
from tkzs_structlog.api.cli import _validate_config_impl, _generate_config_impl

# 校验配置
success, errors = _validate_config_impl("./structlog_config.json")
if success:
    print("Config is valid")

# 生成配置
content = _generate_config_impl(output_path="./output.json", env="prod", version="2.1")
```
