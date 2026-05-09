# tkzs-structlog 交付阻断文档

> **评审依据**: 开发需求.md (V2.1) / AGENTS.md / 代码审计综述报告  
> **评审方式**: 全量测试 + ruff + mypy + 源码审查  
> **评审日期**: 2026-05-09  
> **检查命令**: `pytest --cov=tkzs_structlog tests/` + `ruff check .` + `mypy src/tkzs_structlog`

---

## 一、总体评估

| 指标 | 需求目标 | 当前状态 | 满足 |
|------|----------|----------|:----:|
| 测试通过率 | 100% | 99.6% (449 passed, 2 failed, 15 skipped) | ❌ |
| 代码覆盖率 | 100% | 99% (rotation.py 2行未覆盖) | ❌ |
| ruff 错误 | 0 | 2 (F401 未使用导入) | ❌ |
| mypy 错误 | 0 | 4 (类库存根缺失) | ❌ |
| V1.0-V2.1 功能完整性 | 100% | ~90% | ❌ |
| V4.0 生态功能 | PGSQL→Redis→ELK→Kafka→Sentry | PGSQL+Redis only | ❌ |

**结论: ❌ 阻断交付 — 存在 9 项阻断级缺陷和多项质量指标不达标**

---

## 二、P0 阻断级缺陷（必须修复后方可交付）

### [BLOCK-01] 测试套件未全量通过（2 failed）

| 属性 | 内容 |
|------|------|
| **涉及文件** | `tests/unit/test_rotation.py:71-105` |
| **失败用例** | `test_lz4_backend_import_error`、`test_zstd_backend_import_error` |
| **根因** | 测试假设 `lz4` 和 `zstandard` 包未安装（期望 `ImportError`），但当前环境已安装这两个包。实际压缩成功返回 `True`，断言 `result is False` 失败。 |
| **需求违反** | 开发需求.md §7.1："测试通过率 100%" |
| **修复方向** | 使用 `unittest.mock.patch` 模拟 `import` 失败，或使用 `@pytest.mark.skipif` 条件跳过已安装场景 |

---

### [BLOCK-02] 代码覆盖率未达 100%（99%）

| 属性 | 内容 |
|------|------|
| **涉及文件** | `src/tkzs_structlog/extensions/rotation.py:150,172` |
| **根因** | 第 150 行 `Lz4Backend.compress()` 的 `except ImportError: return False`、第 172 行 `ZstdBackend.compress()` 的 `except ImportError: return False` 因 lz4/zstd 已安装而无法覆盖。 |
| **需求违反** | 开发需求.md §7.1："覆盖率 100%" |
| **修复方向** | 与 BLOCK-01 关联修复：用 patch 模拟 ImportError 覆盖该分支 |

---

### [BLOCK-03] 控制台处理器未接入初始化流程

| 属性 | 内容 |
|------|------|
| **涉及文件** | `src/tkzs_structlog/core/initializer.py:171-183` |
| **根因** | `initializer._setup_handlers()` 调用 `setup_output_handlers()`，后者仅处理 `pgsql`/`redis`/`file` 三方输出。`setup_console_handler()` 和 `setup_colored_console_handler()` 虽在 `handlers.py:17,168` 定义，但从未在初始化路径中被调用。 |
| **影响** | - `bridge_std_logging=True` 时，`recreate_defaults()` 已执行但根日志器无 console handler，stdout 无日志输出<br>- `bridge_std_logging=False` 时，structlog 内部 ConsoleRenderer 可工作，但彩色处理器 `ColoredConsoleHandler` 从未被使用 |
| **需求违反** | 开发需求.md §2.4："控制台输出：StreamHandler，支持彩色输出"；代码审查报告 P1-04 |
| **修复方向** | 在 `_setup_handlers()` 或 `setup_output_handlers()` 中根据配置调用 `setup_console_handler()` |

---

### [BLOCK-04] V4.0 生态功能严重缺失

| 属性 | 内容 |
|------|------|
| **缺失功能** | ELK 兼容格式输出、Kafka Handler、Sentry Handler |
| **已实现** | PGSQL Handler (pgsql_handler.py)、Redis Handler (redis_handler.py) |
| **需求违反** | 开发需求.md §5.0：PGSQL → Redis → ELK → Kafka → Sentry（按优先级 P0-P4） |
| **影响** | V4.0 配置中 `handlers.kafka`、`extensions.sentry_enable`、`extensions.elk_compatible` 等配置项对应的功能完全不存在，用户配置后静默不生效 |
| **修复方向** | 按优先级依次实现缺失的输出适配器 |

---

### [BLOCK-05] Web 框架适配未实现

| 属性 | 内容 |
|------|------|
| **缺失功能** | FastAPI 中间件、Flask 扩展、Django 中间件 |
| **已实现** | `api/core.py` `bind_context(auto_trace_id=True)` 仅支持手动调用 |
| **需求违反** | 开发需求.md §3.3.3："Web 框架适配（FastAPI/Flask/Django）：请求入口自动绑定，结束自动清除" |
| **影响** | 配置 `extensions.trace_id_bind=true` 时 trace_id 不会自动生成和绑定，需要用户手动调用 `bind_context(auto_trace_id=True)` |
| **修复方向** | 实现三方框架中间件/扩展 |

---

### [BLOCK-06] `__version__` 硬编码与 hatch-vcs 冲突

| 属性 | 内容 |
|------|------|
| **涉及文件** | `src/tkzs_structlog/__init__.py:42`、`src/tkzs_structlog/_version.py` |
| **问题代码** | `__init__.py` 中 `__version__ = "0.1.0"` 硬编码 |
| **根因** | Hatchling vcs versioning 会在 `uv build` 时自动覆盖 `_version.py`，但 `__init__.py` 中的硬编码优先级更高，导致运行时版本号始终为 `"0.1.0"` |
| **需求违反** | 开发需求.md §11.1：CLI version 命令应输出正确版本号 |
| **影响** | CLI `structlog-auto version` 输出固定为 0.1.0，与构建版本号不一致 |
| **修复方向** | 使用 `from importlib.metadata import version` 动态获取，如 `__version__ = version("tkzs-structlog")` |

---

### [BLOCK-07] `py.typed` 标记文件缺失

| 属性 | 内容 |
|------|------|
| **涉及文件** | 无（缺失文件） |
| **需求违反** | 开发需求.md §4.3："发布 py.typed 文件，支持 mypy 检查" |
| **影响** | 包安装后第三方 mypy 检查无法识别类型注解，视作 untyped |
| **修复方向** | 在包目录下创建空文件 `src/tkzs_structlog/py.typed` |

---

## 三、P1 重要缺陷（建议修复后交付）

### [DEFECT-01] ruff 检查 2 处错误未清除

| 位置 | 问题 | 代码 |
|------|------|------|
| `tests/unit/test_pgsql_handler.py:3` | `F401` `threading` imported but unused | `import threading` |
| `tests/unit/test_rotation.py:1023` | `F401` `datetime.timedelta` imported but unused | `from datetime import timedelta` |
| **需求违反** | 开发需求.md §6："ruff 格式化 + 全量校验通过" |

### [DEFECT-02] mypy 4 处类库存根缺失

| 位置 | 错误 |
|------|------|
| `rotation.py:144` | lz4.frame / lz4 — missing library stubs |
| `env_loader.py:110` | psycopg2 — missing library stubs |
| `pgsql_handler.py:106` | psycopg2 — missing library stubs |
| **影响** | 可选依赖的类型信息丢失，mypy strict 模式无法通过 |

### [DEFECT-03] compress 线程池满降级逻辑脆弱

| 属性 | 内容 |
|------|------|
| **涉及文件** | `rotation.py:354-362` |
| **问题** | 当前仅捕获 `RuntimeError` 作为降级触发条件。`concurrent.futures.ThreadPoolExecutor.submit()` 在队列满时默认会阻塞而非抛异常，导致降级逻辑实际上不会触发。 |
| **需求违反** | 开发需求.md §3.2.5 V2.1边界8："异步压缩线程池满：新任务排队，超出队列长度时降级为同步压缩" |

### [DEFECT-04] `TruncateProcessor.set_config` 每次日志事件重复调用

| 属性 | 内容 |
|------|------|
| **涉及文件** | `processors.py:234-244` |
| **问题** | 每次日志事件处理都调用 `_truncator.set_config(...)` 重新配置全局单例，削弱了 `lru_cache` 的类型缓存效果（每次 set_config 不会清除缓存，但高频属性赋值增加开销） |
| **需求违反** | 开发需求.md §3.1.5：处理器应高效执行 |

### [DEFECT-05] `rotate_when=H/D` 实现但无测试覆盖

| 属性 | 内容 |
|------|------|
| **涉及文件** | `rotation.py:276-288` |
| **问题** | 按小时(H)和按天(D)的轮转逻辑已实现，但无对应单元测试。`_should_rotate_by_time` 中 `H` 模式在首次运行时永远不触发（`_last_rotate_time > 0` 检查导致首次调用跳过）。 |

---

## 四、P2 建议性缺陷

| 编号 | 问题 | 位置 | 说明 |
|------|------|------|------|
| SUG-01 | `repr_iter` 参数 `method` 未使用 | `processors.py:117` | 死参数，增加困惑 |
| SUG-02 | `exceptions/__init__.py` 异常类名 `__name__` 比较脆弱 | `loader.py:111` | `type(e).__name__ == "Json5EOF"` 应改用 `isinstance` |
| SUG-03 | `pyproject.toml` ruff target-version 未同步 | `pyproject.toml:127` | `target-version = "py310"` ✅（已修复） |
| SUG-04 | docs/config_spec.md 是否覆盖 V4.0 | 待确认 | 需要检查配置规范文档完整性 |
| SUG-05 | `LoggerFactory._logger` 属性从未使用 | `logger_factory.py` | 死代码 |

---

## 五、与开发需求的差距矩阵

| 版本 | 功能点 | 需求状态 | 实际状态 | 差距 |
|------|--------|:--------:|:--------:|:----:|
| **V1.0** | 标准 logging 桥接 | 桥梁接+recreate_defaults | ✅ 已修复 | — |
| **V1.0** | 控制台彩色输出 | ColoredConsoleHandler 生效 | ❌ 未接入 | 见 BLOCK-03 |
| **V2.0** | Web 框架适配 | FastAPI/Flask/Django 中间件 | ❌ 未实现 | 见 BLOCK-05 |
| **V2.1** | 压缩线程池满降级 | 队列满→同步压缩 | ⚠️ 脆弱 | 见 DEFECT-03 |
| **V3.0** | py.typed 文件 | 发布类型标记 | ❌ 缺失 | 见 BLOCK-07 |
| **V3.0** | 版本管理 | hatch-vcs 统一管理 | ❌ 硬编码 | 见 BLOCK-06 |
| **V4.0** | ELK 兼容输出 | 实现 elk_compatible 配置 | ❌ 未实现 | 见 BLOCK-04 |
| **V4.0** | Kafka 输出 | 实现 handlers.kafka | ❌ 未实现 | 见 BLOCK-04 |
| **V4.0** | Sentry 集成 | 实现 sentry_enable 配置 | ❌ 未实现 | 见 BLOCK-04 |
| **全版本** | 测试通过率 100% | 全量 100% | ❌ 99.6% | 见 BLOCK-01 |
| **全版本** | 覆盖率 100% | 全量 100% | ❌ 99% | 见 BLOCK-02 |
| **全版本** | ruff 0错误 | 0 | ❌ 2 | 见 DEFECT-01 |
| **全版本** | mypy 0错误 | 0 | ❌ 4 | 见 DEFECT-02 |

---

## 六、修复优先级建议

```
第1优先级（阻断级，必须修复后才能交付）
├── BLOCK-01  测试通过率 → 100%        [预估 0.5h]
├── BLOCK-02  覆盖率 → 100%            [预估 0.5h] (与BLOCK-01关联)
├── BLOCK-03  控制台处理器接入初始化      [预估 1h]
├── BLOCK-06  版本管理统一              [预估 0.5h]
├── BLOCK-07  py.typed 文件创建         [预估 0.1h]

第2优先级（重要级，建议修复后交付）
├── BLOCK-04  V4.0 生态缺失 (Kafka/ELK/Sentry) [预估 16h+]
├── BLOCK-05  Web框架适配               [预估 8h+]
├── DEFECT-01 ruff 2处错误              [预估 0.1h]
├── DEFECT-02 mypy 4处存根缺失          [预估 0.3h]
├── DEFECT-03 线程池降级逻辑加固         [预估 1h]
├── DEFECT-04 TruncateProcessor性能优化  [预估 0.5h]

第3优先级（建议级）
├── DEFECT-05 rotate_when H/D 测试补充   [预估 1h]
├── SUG-01~05 代码清理                  [预估 0.5h]
```

---

## 七、交付前检查清单

- [ ] BLOCK-01: 修复 lz4/zstd 测试（patch ImportError）
- [ ] BLOCK-02: 覆盖率回升 100%（与BLOCK-01关联）
- [ ] BLOCK-03: `_setup_handlers` 接入 `setup_console_handler`
- [ ] BLOCK-06: `__version__` 改为 `importlib.metadata.version`
- [ ] BLOCK-07: 创建 `py.typed` 标记文件
- [ ] DEFECT-01: 清理测试代码 ruff 错误
- [ ] DEFECT-02: 安装可选依赖类型存根或添加 `# type: ignore`
- [ ] 全量测试 `pytest --cov=tkzs_structlog tests/` 通过（0 failed）
- [ ] `ruff check .` 0 error
- [ ] `mypy src/tkzs_structlog` 0 error
- [ ] `uv build` 验证包构建
- [ ] BLOCK-04/BLOCK-05 需在交付路线图中标注为 V4.1/V4.2

---

*文档生成: 2026-05-09 | 评审工具: pytest / ruff / mypy / 源码审查*
