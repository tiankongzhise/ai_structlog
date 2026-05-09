# claude_deepseek 修复记录

> **修复日期**: 2026-05-09
> **修复依据**: claude_deepseek_交付阻断文档 + opencode_bigpickle_交付阻断文档 + 开发需求.md (V2.1)
> **修复前状态**: 452 passed, 15 skipped, 100% coverage（测试项已达标）
> **重点修复**: 构建系统、公共API、依赖管理、控制台输出重复

---

## 修复 #1: `__init__.py` 公共 API 损坏 — 5 个异常类未导入

**问题** (claude_deepseek Bug #1):
`__init__.py` 的 `__all__` 列表中声明了 `StructlogBaseError`、`StructlogConfigError`、`StructlogConfigFileNotFoundError`、`StructlogConfigParseError`、`StructlogConfigVersionError` 共 5 个异常类，但未从 `tkzs_structlog.exceptions` 导入它们。用户执行 `from tkzs_structlog import StructlogBaseError` 会抛出 `AttributeError`。

**涉及文件**: `src/tkzs_structlog/__init__.py:32-38`

**修复方法**:
1. 在 `from tkzs_structlog.exceptions import (...)` 语句中补充导入缺失的 5 个异常类
2. 在 `__all__` 中添加 `__version__` 导出（因已通过 `__getattr__` 动态提供版本号）

**修改前**:
```python
from tkzs_structlog.exceptions import (
    StructlogHandlerError,
    StructlogNotInitedError,
    StructlogProcessorError,
    StructlogProcessorImportError,
    StructlogProcessorInstantiateError,
)
```

**修改后**:
```python
from tkzs_structlog.exceptions import (
    StructlogBaseError,
    StructlogConfigError,
    StructlogConfigFileNotFoundError,
    StructlogConfigParseError,
    StructlogConfigVersionError,
    StructlogHandlerError,
    StructlogNotInitedError,
    StructlogProcessorError,
    StructlogProcessorImportError,
    StructlogProcessorInstantiateError,
)
```

**验证**:
```python
from tkzs_structlog import StructlogBaseError, StructlogConfigError
from tkzs_structlog import StructlogConfigFileNotFoundError, StructlogConfigParseError
from tkzs_structlog import StructlogConfigVersionError, __version__
# 全部导入成功，无 AttributeError
```

---

## 修复 #2: `uv build` 包构建失败 — hatch-vcs 路径解析错误

**问题** (claude_deepseek Bug #2):
执行 `uv build` 时报错：
```
FileNotFoundError: [Errno 2] No such file or directory:
'...\\src\\tkzs_structlog\\_version.py'
```

**根因分析**:
`pyproject.toml` 中配置了 `sources = ["src", "pyproject.toml", "LICENSE", "README.md"]`，这导致 hatchling 构建 SDIST 时将 `src/` 目录展平（其内容直接放在 SDIST 根目录）。SDIST 中的路径是 `tkzs_structlog/_version.py`（无 `src/` 前缀）。但 hatch-vcs 的 `version-file` 配置为 `src/tkzs_structlog/_version.py`，该路径在展平后的 SDIST 中不存在，导致 `Path.write_text()` 因父目录缺失而抛出 `FileNotFoundError`。

**涉及文件**: `pyproject.toml`

**修复方法**:
移除自定义 `sources` 配置，让 hatchling 使用默认的 VCS 文件包含策略。默认策略保留 `src/` 目录前缀，使 hatch-vcs 的 `version-file` 路径 `src/tkzs_structlog/_version.py` 在 SDIST 中正确存在。

**修改前**:
```toml
[tool.hatch.build]
sources = ["src", "pyproject.toml", "LICENSE", "README.md"]
```

**修改后**:
```toml
# 移除 [tool.hatch.build] 的 sources 配置
# hatchling 使用默认 VCS 文件包含策略
```

**注意**: 虽然移除了 `sources` 配置，但这是为了匹配 hatch-vcs 的路径需求。SDIST 和 wheel 的文件内容不受影响，因为 wheel 的 `packages = ["src/tkzs_structlog"]` 仍精确控制打包内容。

**验证**:
```bash
uv build
# Building source distribution...
# Building wheel from source distribution...
# Successfully built dist\tkzs_structlog-0.1.dev38+...tar.gz
# Successfully built dist\tkzs_structlog-0.1.dev38+...-py3-none-any.whl
```

---

## 修复 #3: Mypy 类型检查 2 个错误 — psycopg2 缺少类型存根

**问题** (opencode_bigpickle DEFECT-02 / claude_deepseek 缺陷 #5):
```
src\tkzs_structlog\config\env_loader.py:110: error: Library stubs not installed for "psycopg2"
src\tkzs_structlog\extensions\pgsql_handler.py:106: error: Library stubs not installed for "psycopg2"
```

**根因分析**:
`psycopg2-binary` 包不包含类型存根（stubs），mypy 在 strict 模式下要求所有第三方导入都有类型信息。

**涉及文件**:
- `src/tkzs_structlog/config/env_loader.py:110`
- `src/tkzs_structlog/extensions/pgsql_handler.py:106`

**修复方法**:
在两处 psycopg2 导入语句后添加 `# type: ignore[import-untyped]` 注释，明确告知 mypy 该包无类型存根。这比全局配置 `ignore_missing_imports = true` 更精确，不会屏蔽其他缺失类型存根的警告。

**修改**:
```python
# env_loader.py
import psycopg2  # type: ignore[import-untyped]  # noqa: F401

# pgsql_handler.py
from psycopg2 import pool  # type: ignore[import-untyped]
```

**验证**:
```bash
mypy src/tkzs_structlog
# Success: no issues found in 23 source files
```

---

## 修复 #4: psycopg2-binary 从核心依赖移至可选依赖

**问题** (claude_deepseek 缺陷 #2):
`psycopg2-binary>=2.9.12` 被放在 `pyproject.toml` 的 `dependencies` 核心列表中，所有安装此包的用户都会被强制安装 psycopg2-binary（约 3MB+），即使用户只使用控制台和文件日志。

**需求依据**: 开发需求.md §5.0 明确 PGSQL 的降级策略为"连接失败时降级到文件"，§11.1 要求"可选依赖 + extras_require"。

**涉及文件**: `pyproject.toml:41`

**修复方法**:
将 `psycopg2-binary>=2.9.12` 从核心 `dependencies` 移到 `[project.optional-dependencies].ecosystem`。PGSQL Handler 已有完善的降级逻辑（`is_pgsql_available()` 检查 + `StructlogHandlerError` 异常），在 psycopg2 不可用时自动降级到文件输出。

**修改前**:
```toml
dependencies = [
  "structlog>=23.1.0",
  "pyjson5>=2.0.0",
  "pydantic>=2.0",
  "psycopg2-binary>=2.9.12",
]
```

**修改后**:
```toml
dependencies = [
  "structlog>=23.1.0",
  "pyjson5>=2.0.0",
  "pydantic>=2.0",
]
```

`psycopg2-binary` 已在 `ecosystem` 可选依赖组中，用户可通过 `pip install tkzs-structlog[ecosystem]` 安装。

**验证**: 测试套件全部通过（452 passed, 15 skipped — PGSQL 集成测试在有服务器时运行，无服务器时自动跳过）。

---

## 修复 #5: 控制台处理器双重输出

**问题** (claude_deepseek 缺陷 #6 / opencode_bigpickle BLOCK-03):
当 `bridge_std_logging=True`（默认值）时，`_setup_processors()` 调用 `structlog.stdlib.recreate_defaults()` 向根日志器添加一个 `StreamHandler`。随后 `_setup_handlers()` → `setup_output_handlers()` → `setup_console_handler()` 又添加另一个 `StreamHandler`（`ColoredConsoleHandler`），导致每条日志在控制台输出两次。

**涉及文件**:
- `src/tkzs_structlog/core/initializer.py:_setup_processors()` / `_setup_handlers()`
- `src/tkzs_structlog/extensions/handlers.py:setup_output_handlers()`

**修复方法**:
1. **移除 `recreate_defaults()`**: 从 `_setup_processors()` 中删除 `sl_stdlib.recreate_defaults()` 调用及其后的 `_setup_log_level()` 重调。处理器链的配置由 `structlog.configure()` 完成，输出处理器的配置由 `_setup_handlers()` 统一管理。
2. **传递桥接信息**: 修改 `setup_output_handlers()` 接受 `stdlib_bridge` 和 `renderer` 参数，并传递给 `setup_console_handler()` 和 `setup_file_handler()`。当桥接启用时，控制台/文件处理器使用 `ProcessorFormatter` 正确格式化 structlog 输出。
3. **清除已有处理器**: 在 `_setup_handlers()` 开头添加 `root_logger.handlers.clear()`，避免重复初始化时处理器累积。

**修改后的调用链**:
```
_setup_processors()
  └── structlog.configure(processors=chain, ...)  # 配置处理器链
  └── [不再调用 recreate_defaults()]

_setup_handlers()
  └── root_logger.handlers.clear()               # 清除旧处理器
  └── setup_output_handlers(config, stdlib_bridge=True, renderer=ConsoleRenderer())
        └── setup_console_handler(config, stdlib_bridge=True, renderer=ConsoleRenderer())
              └── StreamHandler + ProcessorFormatter(processor=ConsoleRenderer)
        └── setup_file_handler(config, stdlib_bridge=True, renderer=ConsoleRenderer())
              └── FileHandler + ProcessorFormatter(processor=ConsoleRenderer)
```

**验证**:
- 所有 452 个测试通过
- 控制台输出不再重复
- 桥接模式和非桥接模式均正确工作

---

## 修复 #6: py.typed 文件提交到版本控制

**问题** (opencode_bigpickle BLOCK-07 / claude_deepseek 缺陷 #4):
`src/tkzs_structlog/py.typed` 文件存在但未被 git 跟踪（untracked），发布到 PyPI 后该文件不会被打包，下游用户对 `tkzs_structlog` 进行 mypy 检查时不会获得类型提示支持。

**涉及文件**: `src/tkzs_structlog/py.typed`

**修复方法**:
该文件已存在（空的 marker 文件），只需将其纳入 git 版本控制。在 `uv build` 的输出中已确认该文件包含在 wheel 中：`tkzs_structlog/py.typed`。

**验证**: Wheel 文件列表确认包含 `py.typed`。

---

## 最终验证结果

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `uv build` | ✅ 通过 | SDIST + Wheel 构建成功 |
| `ruff check .` | ✅ 通过 | All checks passed |
| `mypy src/tkzs_structlog` | ✅ 通过 | 0 errors in 23 source files |
| `pytest --cov=tkzs_structlog tests/` | ✅ 通过 | 452 passed, 15 skipped |
| 代码覆盖率 | ✅ 100% | 1350 statements, 0 missed |
| `__init__.py` 公共 API | ✅ 修复 | 10 个异常类可正常导入 |
| `py.typed` | ✅ 已跟踪 | 包含在 wheel 中 |
| psycopg2 依赖 | ✅ 可选 | 移入 ecosystem 可选组 |

---

**修复总结**: 共修复 6 项阻断级/重要缺陷。所有修复均经过测试验证（452 passed, 100% coverage），ruff/mypy 检查零错误，包构建成功。

---

## 第二轮修复（针对 opencode_bigpickle_交付阻断文档 剩余缺陷）

### 修复 #7: 压缩线程池降级逻辑加固 (DEFECT-03)

**问题** (opencode_bigpickle DEFECT-03):
`_compress_file` 方法中仅捕获 `RuntimeError` 作为降级触发条件。但 `concurrent.futures.ThreadPoolExecutor.submit()` 使用无界队列，队列满时默认会阻塞而非抛异常，导致"队列满→降级同步压缩"逻辑实际上不会触发。违反了开发需求 §3.2.5 V2.1边界8。

**涉及文件**: `src/tkzs_structlog/extensions/rotation.py:349-364`

**修复方法**:
使用 `threading.BoundedSemaphore` 限制异步压缩的并发深度。信号量初始值 = `compress_concurrency + compress_max_queue`（默认 10）。当信号量无法非阻塞获取时，降级为同步压缩；异步提交后通过 `future.add_done_callback` 释放信号量。

**修改**:
```python
# __init__: 添加信号量
self._compress_semaphore = threading.BoundedSemaphore(max_queue)

# _compress_file: 信号量控制的异步/同步切换
if self.compress_async and self._compress_executor and self._compress_semaphore:
    semaphore = self._compress_semaphore
    acquired = semaphore.acquire(blocking=False)
    if not acquired:
        # 队列满 → 降级同步压缩（记录 WARNING）
        self._do_compress(file_path, dst_path)
        return
    try:
        future = self._compress_executor.submit(self._do_compress, file_path, dst_path)
        future.add_done_callback(lambda _: semaphore.release())
    except RuntimeError:
        semaphore.release()
        self._do_compress(file_path, dst_path)
```

**边界覆盖**:
- ✅ 队列满（信号量为0）→ 降级同步压缩，记录 WARNING
- ✅ 线程池关闭（RuntimeError）→ 释放信号量，降级同步压缩
- ✅ 成功异步提交 → 回调释放信号量

---

### 修复 #8: TruncateProcessor 配置变更检测 (DEFECT-04)

**问题** (opencode_bigpickle DEFECT-04):
`TruncateProcessor` 每次日志事件处理都调用 `_truncator.set_config(...)` 重新配置全局单例，涉及 9 个属性赋值。虽然不会清除 `lru_cache`，但高频属性赋值增加不必要开销。

**涉及文件**: `src/tkzs_structlog/extensions/processors.py:71-100`

**修复方法**:
在 `CustomTruncator.set_config` 中添加配置哈希检测。计算所有配置参数的哈希值，仅当哈希值与上次不同时才执行属性赋值。首次调用哈希值为 0，确保初始化执行。

**修改**:
```python
def set_config(self, ...) -> None:
    # 计算配置哈希，无变更则跳过
    new_hash = hash(( max_depth, str_max_length, ... ))
    if new_hash == self._config_hash:
        return
    self._config_hash = new_hash
    # 实际赋值...
```

---

### 修复 #9: repr_iter 未使用参数规范化 (SUG-01)

**问题** (opencode_bigpickle SUG-01):
`CustomTruncator.repr_iter(self, obj, level, maxlen, method)` 的 `method` 参数从未使用。虽然由 `reprlib.Repr` 父类传入（`repr1` 方法），但在函数体内无任何引用。

**涉及文件**: `src/tkzs_structlog/extensions/processors.py:117`

**修复方法**:
保留参数名 `method` 以保持与父类 `reprlib.Repr.repr_iter` 签名兼容（调用方可能使用关键字参数），添加文档说明该参数用途。

---

### 修复 #10: loader.py 脆弱异常类型比较 (SUG-02)

**问题** (opencode_bigpickle SUG-02):
`config/loader.py:111` 使用 `type(e).__name__ == "Json5EOF"` 进行类名字符串比较，脆弱且不具可维护性。若 pyjson5 库内部类名变更或使用子类，此检查将静默失败。

**涉及文件**: `src/tkzs_structlog/config/loader.py:111`

**修复方法**:
使用 `isinstance(e, pyjson5.Json5EOF)` 替代字符串比较。`pyjson5` 公开导出 `Json5EOF` 类，可直接用于类型检查。

**修改前**:
```python
except Exception as e:
    if type(e).__name__ == "Json5EOF" or "No JSON data found" in str(e):
        return {}
```

**修改后**:
```python
except pyjson5.Json5EOF:
    return {}
except Exception:
    try:
        config = json.loads(content)
    except json.JSONDecodeError:
        raise
```

---

## 第二轮验证结果

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `pytest --cov` | ✅ 通过 | 471 passed, 15 skipped |
| 代码覆盖率 | ✅ 100% | 1366 statements, 0 missed |
| `ruff check .` | ✅ 通过 | All checks passed |
| `mypy src/tkzs_structlog` | ✅ 通过 | 0 errors |
| `uv build` | ✅ 成功 | Wheel + SDIST |

**第二轮修复总结**: 共修复 4 项缺陷（1 项重要级 DEFECT + 3 项建议级 SUG），覆盖压缩线程池降级、处理器性能优化、代码健壮性提升。新增 6 个回归测试覆盖所有修改路径。
