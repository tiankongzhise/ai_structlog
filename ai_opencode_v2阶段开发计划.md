# tkzs-structlog V2.0 增强版开发计划

> 创建日期：2026-05-08
> 依据文档：`开发需求.md` §三（V2.0/V2.1）、`开发计划.md` §三（V2.0 增强版）
> 前置条件：V1.0 基础版已验收通过（284 passed, 覆盖率 100%, ruff 通过）

---

## 一、V2.0 整体目标

在 V1.0 基础日志能力之上，完成生产级核心能力：**日志截断、复合轮转、多环境、脱敏、上下文**。

### 当前完成情况（代码审查结论）

| V2.0 功能 | 状态 | 备注 |
|-----------|------|------|
| 日志截断（CustomTruncator + TruncateProcessor） | ✅ 已完成 | 含 V2.1 类型缓存、深度警告、通配符/正则 |
| 自定义复合轮转（CustomRotatingFileHandler） | ✅ 已完成 | 含 V2.1 异步压缩、原子重命名、可插拔后端 |
| 多环境配置加载（STRUCTLOG_ENV） | ✅ 已完成 | get_env_config_path |
| 敏感信息脱敏（SensitiveDataProcessor） | ✅ 已完成 | 内置4种规则+自定义 |
| 日志过滤（FilterProcessor） | ✅ 已完成 | exclude/include 规则 |
| API 扩展（unbind_context, clear_context） | ✅ 已完成 | |
| 统一异常体系（StructlogBaseError） | ✅ 已完成 | 含 error_type/error_field/reason/fix_suggestion |
| **请求上下文绑定 - trace_id 自动生成** | ❌ 未实现 | 需开发 |
| **Web 框架适配** | ❌ 未实现 | 开发计划中列为中期目标 |
| **Windows 进程锁** | ❌ 未实现 | 目前仅 threading.Lock |

### 代码质量待改进项

| 编号 | 问题 | 级别 | 对应修复 |
|------|------|------|----------|
| Q1 | `ruff format` 4个文件未格式化 | P1 | 运行 `ruff format .` |
| Q2 | `_global_config` 非线程安全 | P2 | 使用 `threading.RLock` |
| Q3 | `rotate_when` 仅实现 MIDNIGHT | P2 | 补充 H/D/W0-W6 策略 |
| Q4 | LoggerFactory 死代码 `_logger` | P2 | 清理 |
| Q5 | Python 版本文档不一致（3.8+ vs 3.10+） | P2 | 对齐 pyproject.toml 与 README |

---

## 二、开发排期

### Sprint 1：格式化清理与基础修复（0.5h）

| 任务 | 工作内容 | 工时 | 验收标准 |
|------|----------|------|----------|
| 格式化修复 | 运行 `ruff format .`，修复 4 个文件 | 0.3h | `ruff format . --check` 全部通过 |
| ruff 验证 | `ruff check .` 零错误 | 0.2h | CI 门禁通过 |

---

### Sprint 2：trace_id 自动生成（3h）

**依据**：开发计划.md §3.5、开发需求.md §3.3.3

| 任务 | 工作内容 | 工时 | 验收标准 |
|------|----------|------|----------|
| bind_context 扩展 | 新增 `auto_trace_id` 参数，`True` 时自动生成 UUID | 1h | 调用 `bind_context(auto_trace_id=True)` 后 get_logger 返回的日志器包含 `trace_id` 字段 |
| trace_id 去重 | 已传入 `trace_id` 时不覆盖 | 0.5h | `bind_context(auto_trace_id=True, trace_id="custom")` 保留自定义值 |
| 配置开关 | `extensions.trace_id_bind=true` 时 init_structlog 自动启用 | 1h | 配置控制自动绑定行为 |
| 单元测试 | 覆盖 auto_trace_id、配置开关、去重逻辑 | 0.5h | 覆盖率 100% |

---

### Sprint 3：Windows 进程锁 + 轮转增强（3h）

**依据**：代码审查报告 P0-03（Windows 进程锁缺失）、P2-02（rotate_when 仅 MIDNIGHT）

| 任务 | 工作内容 | 工时 | 验收标准 |
|------|----------|------|----------|
| Windows 进程锁 | `rotation.py` 中添加跨平台进程锁，Windows 用 `msvcrt.locking` | 1.5h | 多进程轮转安全，Windows/Linux 均通过 |
| rotate_when 扩展 | 实现 `_should_rotate_by_time` 对 H/D/W0-W6 的支持 | 1h | 配置 `rotate_when="H"` 按小时轮转 |
| 单元测试 | 覆盖进程锁异常场景、各轮转模式 | 0.5h | 覆盖率 100% |

---

### Sprint 4：代码质量改进（2h）

**依据**：代码审查报告 P2-03（_global_config 线程安全）、P2-04（LoggerFactory 死代码）

| 任务 | 工作内容 | 工时 | 验收标准 |
|------|----------|------|----------|
| _global_config 线程安全 | 使用 `threading.RLock` 保护 `set_global_config` 和处理器中的读取 | 1h | 并发调用不产生竞态 |
| LoggerFactory 死代码清理 | 移除 `_logger` 未使用属性，简化 reset 逻辑 | 0.5h | 代码无 dead code |
| Python 版本文档对齐 | pyproject.toml、README、开发需求.md 统一为 `>=3.10` | 0.5h | 文档一致 |

---

### Sprint 5：V2.0 集成测试与验收（2h）

| 任务 | 工作内容 | 工时 | 验收标准 |
|------|----------|------|----------|
| 集成测试补充 | trace_id 全链路测试、进程锁多进程测试 | 1h | 全部通过 |
| 全量测试 | `pytest --cov` 覆盖率 100%，通过率 100% | 0.5h | 无遗漏 |
| ruff 最终验证 | `ruff format . --check` + `ruff check .` | 0.5h | 零错误零警告 |

---

## 三、V2.0 里程碑验收

- [ ] `ruff format . --check` 全部通过
- [ ] trace_id UUID 自动生成功能正常
- [ ] `extensions.trace_id_bind` 配置开关生效
- [ ] Windows 进程锁实现，多进程轮转安全
- [ ] rotate_when 支持 H/D/MIDNIGHT/W0-W6
- [ ] `_global_config` 线程安全
- [ ] 单元测试覆盖率 100%，通过率 100%
- [ ] Python 版本文档统一

---

## 四、暂不纳入 V2.0 范围

以下功能来自开发需求但当前阶段不做：

| 功能 | 原因 | 计划阶段 |
|------|------|----------|
| FastAPI/Flask/Django 中间件 | V2.0 核心功能（截断/轮转/脱敏/过滤/上下文）已全部实现；框架适配属于独立集成工作，可安排在 V3.0 或单独迭代 | V3.0+ |
| V2.1 性能测试（类型缓存命中率 ≥90%） | 缓存机制已实现，性能基准测试需专用环境 | V2.1 专项 |
| docs/config_spec.md | 不影响功能交付，文档工作单独排期 | 文档专项 |

---

## 五、风险与技术应对

| 风险 | 应对 |
|------|------|
| Windows 进程锁兼容性 | `msvcrt.locking` 与 `fcntl.flock` 双实现，平台自动选择 |
| trace_id 覆盖已有字段 | 去重逻辑：已传入 trace_id 时不自动生成 |
| 线程安全回归 | 使用 `threading.RLock` 可重入锁，配合现有 `threading.Lock` |
| rotate_when 扩展破坏现有行为 | 保持 MIDNIGHT 为默认值，新增模式不影响已有配置 |

---

*文档版本：V1.0*
*最后更新：2026-05-08*