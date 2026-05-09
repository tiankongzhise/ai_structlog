# 文档与代码一致性修复 TODO

基于审计报告 `docs/archive/代码审计综述报告.md` 发现的问题。

## 严重 (CRITICAL)

- [x] **FIX-01**: 修正 user-guide.md §12.1 PGSQL 环境变量名 — 文档写 `PGSQL_HOST/PORT/USER/PASSWORD/DB`，代码用 `PG_HOST/PORT/USER/PASSWORD/DB`。(commit 8721d67)

## 重大 (MAJOR)

- [x] **FIX-02**: 从用户文档中移除 Kafka 集成声明 — README、user-guide、best-practices 声称 Kafka 已实现，但代码中无 `kafka_handler.py`。(commit eb2627f)
- [x] **FIX-03**: Sentry 标记为计划中 — 虽有配置字段但无 `sentry_handler.py` 实现。(commit c88070b)
- [x] **FIX-04**: `get_default_config()` 补充 V3.0/V4.0 支持 — `defaults.py` 的 `version_map` 只含 1.0/2.0/2.1。(commit 3079057)
- [x] **FIX-05**: 修正 cli-guide.md 中 CLI version 示例输出 — 文档显示 `4.0.0`，实际为 `0.1.dev44`。(commit cd5b9c7)

## 中等 (MODERATE)

- [x] **FIX-06**: 修正 `rotate_when` 校验器 W1-W5 缺失 — `validator.py` 的 `Literal` 只有 `W0, W6`。(commit 8d17c84)
- [x] **FIX-07**: 修正 README V4.0 特性清单 — 已在 FIX-02 中一并完成。(commit eb2627f)

## 轻微 (MINOR)

- [x] **FIX-08**: 修正 AGENTS.md `init_structlog` 签名简化过度 — 补充完整参数。(commit d76ad75)
- [x] **FIX-09**: 修正 CLAUDE.md config 层架构描述 — 补充 `env_loader.py`。(commit a9b55d3)
