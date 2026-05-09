# 文档与代码一致性修复 TODO

基于审计报告 `docs/archive/代码审计综述报告.md` 发现的问题。

## 严重 (CRITICAL)

- [ ] **FIX-01**: 修正 user-guide.md §12.1 PGSQL 环境变量名 — 文档写 `PGSQL_HOST/PORT/USER/PASSWORD/DB`，代码用 `PG_HOST/PORT/USER/PASSWORD/DB`。需将文档改为实际代码使用的 `PG_*` 前缀。

## 重大 (MAJOR)

- [ ] **FIX-02**: 从用户文档中移除 Kafka 集成声明 — README、user-guide、best-practices 声称 Kafka 已实现，但代码中无 `kafka_handler.py`、无任何 Kafka 逻辑、无测试。将 Kafka 标记为"计划中"或直接移除。
- [ ] **FIX-03**: 从用户文档中移除 Sentry 集成声明 — 虽有配置字段但无 `sentry_handler.py` 实现。将 Sentry 标记为"计划中"或直接移除。
- [ ] **FIX-04**: `get_default_config()` 补充 V3.0/V4.0 支持 — `defaults.py` 的 `version_map` 只含 1.0/2.0/2.1，缺少 3.0/4.0。需添加对应的默认配置。
- [ ] **FIX-05**: 修正 cli-guide.md 中 CLI version 示例输出 — 文档显示 `4.0.0`，实际为 `0.1.dev44+g0b7310855`。改为通用的 `x.y.z` 占位符。

## 中等 (MODERATE)

- [ ] **FIX-06**: 修正 `rotate_when` 校验器 W1-W5 缺失 — `validator.py` 的 `Literal` 只有 `W0, W6`，缺少 `W1-W5`。补充完整的 `W0`-`W6`。
- [ ] **FIX-07**: 修正 README V4.0 特性清单 — 将 Kafka/Sentry 从已实现特性中移除，或标注为计划中。

## 轻微 (MINOR)

- [ ] **FIX-08**: 修正 AGENTS.md `init_structlog` 签名简化过度 — 补充 `enable_hotreload` 和 `enable_trace_id` 参数。
- [ ] **FIX-09**: 修正 CLAUDE.md config 层架构描述 — 补充 `env_loader.py`。
