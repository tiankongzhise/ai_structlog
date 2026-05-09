# tkzs-structlog 配置规范

## 顶层字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `version` | `string` | 否 | `"2.1"` | 配置版本：`1.0` / `2.0` / `2.1` / `3.0` / `4.0` |
| `logger_name` | `string` | 否 | `"structlog_auto"` | 日志器名称 |
| `min_level` | `string` | 否 | `"INFO"` | `DEBUG` / `INFO` / `WARN` / `ERROR`（`WARN` 归一为 WARNING） |
| `bridge_std_logging` | `bool` | 否 | `true` | 为 true 时桥接标准库 `logging` |
| `context_bind` | `bool` | 否 | `false` | 是否启用上下文绑定 |
| `processors` | `string[]` | 否 | 见默认值 | 处理器类路径列表 |
| `handlers` | `object` | 否 | 见默认值 | 输出处理器配置 |
| `extensions` | `object` | 否 | 见默认值 | 扩展功能配置 |

## 加载优先级

1. `init_structlog(config_path=...)` 指定文件
2. 环境配置：`STRUCTLOG_ENV=prod` → `structlog_config.prod.json`
3. 工作目录 / 项目根目录下的 `structlog_config.json`
4. 内置默认 + `merge_config` 合并

## handlers 配置

### console

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `true` | 是否启用控制台输出 |

### file

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `false` | 是否启用文件输出 |
| `file_path` | `string` | `"./logs/structlog.log"` | 日志文件路径 |
| `encoding` | `string` | `"utf-8"` | 文件编码 |
| `custom_rotate` | `object` | - | 自定义轮转配置 |

### file.custom_rotate

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `false` | 是否启用轮转 |
| `max_bytes` | `int` | `10485760` | 单文件最大字节数（10MB） |
| `backup_count` | `int` | `10` | 最大保留文件数（0=不限制） |
| `retain_days` | `int` | `7` | 最大保留天数（0=不限制） |
| `rotate_when` | `string` | `"MIDNIGHT"` | 时间轮转：`H`/`D`/`MIDNIGHT`/`W0`-`W6` |
| `interval` | `int` | `1` | 时间间隔 |
| `compress` | `bool` | `false` | 是否启用压缩 |
| `compress_method` | `string` | `"gzip"` | 压缩方法：`gzip`/`lz4`/`zstd` |
| `compress_concurrency` | `int` | `2` | 异步压缩并发数（1-10） |
| `compress_async` | `bool` | `true` | 是否异步压缩 |

### pgsql

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `false` | 是否启用 PGSQL 输出 |
| `table_name` | `string` | `"structlog_logs"` | 表名 |
| `batch_size` | `int` | `100` | 批量写入条数（1-1000） |
| `flush_interval` | `int` | `5` | 刷新间隔秒数（1-60） |
| `pool_size` | `int` | `5` | 连接池大小（1-20） |

### redis

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `false` | 是否启用 Redis 输出 |
| `key_prefix` | `string` | `"structlog:"` | Redis key 前缀 |
| `batch_size` | `int` | `100` | 批量写入条数（1-1000） |
| `flush_interval` | `int` | `5` | 刷新间隔秒数（1-60） |

## extensions 配置

### log_truncate

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | `bool` | `false` | 是否启用日志截断 |
| `max_depth` | `int` | `3` | 递归截断层数 |
| `str_max_length` | `int` | `256` | 字符串最大长度 |
| `seq_max_elements` | `int` | `50` | 序列最大元素数 |
| `dict_max_pairs` | `int` | `30` | 字典最大键值对 |
| `ignore_types` | `string[]` | `[]` | 不截断的类名列表 |
| `ignore_fields` | `string[]` | `[]` | 不截断的字段名（精确匹配） |
| `ignore_fields_pattern` | `string[]` | `[]` | 不截断的字段名（通配符，如 `*_id`） |
| `ignore_fields_regex` | `string \| null` | `null` | 不截断的字段名（正则，如 `^session.*`） |
| `depth_warning` | `bool` | `true` | 超限时添加 `[MAX_DEPTH=N]` 警告 |

### sensitive_fields

类型：`string[]`
默认值：`["password", "phone", "id_card", "bank_card"]`
说明：敏感信息脱敏字段列表。内置脱敏规则见下表。

| 字段 | 脱敏规则 | 示例 |
|------|----------|------|
| `password` | 全隐藏 | `"******"` |
| `phone` | 保留前3后4 | `"138****5678"` |
| `id_card` | 保留前6后4 | `"110101******1234"` |
| `bank_card` | 保留前4后4 | `"6222******1234"` |

### 其他扩展字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `trace_id_bind` | `bool` | `false` | 是否启用 trace_id 自动绑定 |
| `filter_rules` | `object` | `{}` | 日志过滤规则（`exclude`/`include`） |
| `config_hot_reload` | `bool` | `false` | 是否启用配置热重载 |
| `elk_compatible` | `bool` | `false` | 是否启用 ELK 兼容格式 |
| `sentry_enable` | `bool` | `false` | 是否启用 Sentry 集成 |
| `sentry_dsn` | `string \| null` | `null` | Sentry DSN |

## 内置默认配置

详见 `src/tkzs_structlog/config/defaults.py` 中的 `get_default_config()`。

## 兼容性说明

- V4.0 工具可加载 V1.0 ~ V4.0 配置文件
- 缺失字段自动使用对应版本的默认值
- 废弃字段先标记 `deprecated`，保留一个版本周期后移除

## 更多文档

- [用户手册](user-guide.md) - 功能详解与使用示例
- [API 参考](api-reference.md) - API 签名与用法
- [CLI 指南](cli-guide.md) - 命令行工具
- [生产最佳实践](best-practices.md) - 部署与优化建议
