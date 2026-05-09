# tkzs-structlog V2.0 阶段技术方案

> 版本：V2.0  
> 创建日期：2026-05-08  
> 依据文档：开发需求.md §二/§三、开发计划.md §三/V2.1

---

## 一、Sprint 1：格式化清理与基础修复

### 1.1 任务说明

修复 ruff format 问题，确保代码符合规范。

### 1.2 实现方案

```bash
# 直接运行 ruff format 修复格式问题
ruff format .
```

### 1.3 验收标准

- `ruff format . --check` 无输出（即全部通过）
- `ruff check .` 零错误

### 1.4 测试验证

```bash
ruff format . --check
ruff check .
```

---

## 二、Sprint 2：trace_id 自动生成

### 2.1 功能需求

根据开发需求.md §3.3.3 和开发计划.md §3.5：

1. **扩展 bind_context**，支持 `auto_trace_id` 参数，为 `True` 时自动生成 UUID
2. **trace_id 去重**：已传入 `trace_id` 时不覆盖
3. **配置开关**：`extensions.trace_id_bind=true` 时 init_structlog 自动启用自动绑定

### 2.2 技术方案

#### 2.2.1 API 扩展（api/core.py）

```python
def bind_context(auto_trace_id: bool = False, **kwargs: Any) -> None:
    """绑定全局上下文

    Args:
        auto_trace_id: 是否自动生成 trace_id（UUID）
        **kwargs: 上下文键值对

    Example:
        >>> tkzs_structlog.bind_context(request_id="12345")
        >>> tkzs_structlog.bind_context(auto_trace_id=True)  # 自动生成 trace_id
    """
    global _context_store
    if auto_trace_id and "trace_id" not in kwargs:
        import uuid
        kwargs["trace_id"] = str(uuid.uuid4())
    if kwargs:
        _context_store.update(kwargs)
```

#### 2.2.2 配置开关（init_structlog）

在 `init_structlog` 完成后，检查 `config["extensions"]["trace_id_bind"]`：

```python
def init_structlog(..., enable_trace_id: bool = None, **kwargs):
    # 现有初始化逻辑...
    
    # trace_id 自动绑定逻辑
    if enable_trace_id is None:
        enable_trace_id = config.get("extensions", {}).get("trace_id_bind", False)
    
    if enable_trace_id:
        bind_context(auto_trace_id=True)
```

### 2.3 边界情况

| 边界 | 处理逻辑 |
|------|----------|
| `auto_trace_id=True` 且已传入 `trace_id` | 不覆盖已存在的 `trace_id` |
| `auto_trace_id=True` 且 `trace_id=None` | 生成新的 UUID |
| `extensions.trace_id_bind=true` 且上下文已绑定 | 不重复绑定 |
| 配置中 `trace_id_bind=false` 或未配置 | 不自动绑定 |

### 2.4 测试用例

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_bind_context_auto_trace_id_generated | 验证 auto_trace_id=True 生成 UUID |
| test_bind_context_auto_trace_id_no_override | 验证已有 trace_id 不被覆盖 |
| test_bind_context_auto_trace_id_false | 验证 auto_trace_id=False 不生成 |
| test_init_structlog_auto_trace_id_from_config | 验证配置开关生效 |
| test_init_structlog_auto_trace_id_disabled | 验证配置为 false 时不自动绑定 |
| test_trace_id_format_valid_uuid | 验证生成的 trace_id 是有效 UUID 格式 |

### 2.5 验收标准

- `ruff check .` 零错误
- 测试覆盖率 100%（api/core.py）
- 边界情况全部覆盖

---

## 三、Sprint 3：Windows 进程锁 + 轮转增强

### 3.1 Windows 进程锁

#### 3.1.1 功能需求

实现跨平台进程锁，确保多进程轮转安全。代码审查报告 P0-03 指出 Windows 环境无进程锁保护。

#### 3.1.2 技术方案

```python
import sys

def _get_process_lock(file_path: Path) -> tuple[Any, bool]:
    """获取跨进程文件锁

    Returns:
        (lock_file, is_locked) - 锁文件对象和是否成功获取锁
    """
    lock_path = file_path.with_suffix(file_path.suffix + ".lock")
    
    if sys.platform == "win32":
        import msvcrt
        try:
            lock_file = open(lock_path, "w")
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            return lock_file, True
        except (OSError, IOError):
            if 'lock_file' in locals():
                lock_file.close()
            return None, False
    else:
        import fcntl
        try:
            lock_file = open(lock_path, "w")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file, True
        except (OSError, IOError):
            if 'lock_file' in locals():
                lock_file.close()
            return None, False

def _release_process_lock(lock_file: Any) -> None:
    """释放进程锁"""
    if lock_file is None:
        return
    
    if sys.platform == "win32":
        import msvcrt
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        except:
            pass
    else:
        import fcntl
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except:
            pass
    
    try:
        lock_file.close()
    except:
        pass
```

#### 3.1.3 边界情况

| 边界 | 处理逻辑 |
|------|----------|
| Windows 平台 | 使用 `msvcrt.locking` 非阻塞锁 |
| Linux/macOS 平台 | 使用 `fcntl.flock` 非阻塞锁 |
| 锁文件不存在 | 自动创建 |
| 锁被占用 | 返回 `False`，调用方跳过轮转 |
| 锁释放失败 | 使用 try/except 忽略错误 |

### 3.2 rotate_when 扩展

#### 3.2.1 功能需求

实现 `rotate_when` 支持 "H"（按小时）、"D"（按天）、"MIDNIGHT"（每天零点）、"W0-W6"（按周）模式。

#### 3.2.2 技术方案

```python
def _should_rotate_by_time(self) -> bool:
    """检查是否应该按时间轮转"""
    if not self.enable_rotate:
        return False

    now = datetime.now()
    rotate_when = self.rotate_when.upper()

    if rotate_when == "MIDNIGHT":
        if now.hour == 0 and now.minute == 0:
            return True
        if self._last_rotate_time > 0:
            last_time = datetime.fromtimestamp(self._last_rotate_time)
            if last_time.date() != now.date():
                return True
    
    elif rotate_when == "H":  # 按小时
        if self._last_rotate_time > 0:
            last_time = datetime.fromtimestamp(self._last_rotate_time)
            if now.hour != last_time.hour:
                return True
    
    elif rotate_when == "D":  # 按天（每天固定时间，例如 00:00）
        if self._last_rotate_time > 0:
            last_time = datetime.fromtimestamp(self._last_rotate_time)
            if last_time.date() != now.date():
                return True
    
    elif rotate_when.startswith("W") and len(rotate_when) == 2:  # 按周
        try:
            weekday = int(rotate_when[1])
            if 0 <= weekday <= 6 and now.weekday() == weekday:
                if self._last_rotate_time > 0:
                    last_time = datetime.fromtimestamp(self._last_rotate_time)
                    if last_time.isocalendar()[1] != now.isocalendar()[1]:
                        return True
                else:
                    return True
        except ValueError:
            pass

    return False
```

#### 3.2.3 边界情况

| 边界 | 处理逻辑 |
|------|----------|
| `rotate_when="H"` 且当前小时与上次不同 | 触发轮转 |
| `rotate_when="D"` 且日期变化 | 触发轮转 |
| `rotate_when="W0-W6"` 且星期匹配且周数变化 | 触发轮转 |
| `rotate_when` 为无效值 | 默认不触发，按 MIDNIGHT 逻辑处理 |
| `_last_rotate_time=0`（首次运行） | MIDNIGHT 和 D 模式下检查日期差异，H/W 模式下不触发 |

### 3.3 测试用例

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_process_lock_windows | Windows 平台锁获取成功 |
| test_process_lock_windows_locked | Windows 平台锁被占用返回 False |
| test_process_lock_unix | Linux/macOS 平台锁获取成功 |
| test_process_lock_release | 锁释放成功 |
| test_should_rotate_by_time_hourly | 按小时轮转模式正确 |
| test_should_rotate_by_time_daily | 按天轮转模式正确 |
| test_should_rotate_by_time_weekly | 按周轮转模式正确 |
| test_should_rotate_by_time_invalid | 无效 rotate_when 不触发 |
| test_should_rotate_by_time_first_run | 首次运行正确处理 |

### 3.4 验收标准

- `ruff check .` 零错误
- 测试覆盖率 100%（extensions/rotation.py）
- 边界情况全部覆盖

---

## 四、Sprint 4：代码质量改进

### 4.1 _global_config 线程安全

#### 4.1.1 功能需求

当前 `_global_config` 为模块级全局变量，多线程调用 `set_global_config()` 可能存在竞态。

#### 4.1.2 技术方案

使用 `threading.RLock` 保护全局配置读写：

```python
import threading

_global_config: dict[str, Any] = {}
_config_lock = threading.RLock()

def set_global_config(config: dict[str, Any]) -> None:
    """设置全局配置（线程安全）"""
    global _global_config
    with _config_lock:
        _global_config = config

def get_global_config() -> dict[str, Any]:
    """获取全局配置（线程安全）"""
    with _config_lock:
        return _global_config.copy()
```

#### 4.1.3 边界情况

| 边界 | 处理逻辑 |
|------|----------|
| 多线程同时调用 set_global_config | RLock 互斥，后到的线程等待 |
| 读取时写入 | RLock 保证读写互斥 |
| RLock 初始化失败 | 降级为非线程安全实现 |

### 4.2 LoggerFactory 死代码清理

#### 4.2.1 功能需求

移除 `LoggerFactory` 中未使用的 `_logger` 属性。

#### 4.2.2 技术方案

删除 `logger_factory.py` 中以下代码：

```python
# 删除以下行：
self._logger: WrappedLogger | None = None  # 删除
self._logger = None  # 在 initialize 中删除
self._logger = None  # 在 reset 中删除
```

### 4.3 Python 版本文档对齐

将 `开发需求.md` 中 Python 版本要求统一为 `>=3.10`（与 `pyproject.toml` 一致）。

### 4.4 测试验证

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_set_global_config_thread_safe | 多线程同时设置配置 |
| test_get_global_config_thread_safe | 多线程同时读取配置 |
| test_config_lock_reentrant | RLock 可重入（同一线程多次获取） |

### 4.5 验收标准

- `ruff check .` 零错误
- 测试覆盖率 100%
- 无 dead code

---

## 五、Sprint 5：V2.0 集成测试与验收

### 5.1 集成测试补充

1. **trace_id 全链路测试**：
   - 配置启用 `trace_id_bind=true` → init_structlog → get_logger → 验证日志含 trace_id
   - 手动绑定 `trace_id` → 配置启用 → 验证不覆盖

2. **进程锁多进程测试**（跨平台）：
   - 父进程创建锁文件
   - 子进程尝试获取同一锁
   - 验证只有一个进程成功

### 5.2 全量测试

```bash
pytest tests/ --cov=tkzs_structlog --cov-report=term-missing
```

验收标准：覆盖率 100%，通过率 100%

### 5.3 最终验证

```bash
ruff format . --check
ruff check .
```

---

## 六、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/tkzs_structlog/api/core.py` | 修改 | 添加 `auto_trace_id` 参数，添加 `get_global_config` |
| `src/tkzs_structlog/extensions/processors.py` | 修改 | 使用线程安全的全局配置访问 |
| `src/tkzs_structlog/extensions/rotation.py` | 修改 | 添加 Windows 进程锁，扩展 rotate_when |
| `src/tkzs_structlog/core/logger_factory.py` | 修改 | 移除死代码 |
| `tests/unit/test_api.py` | 修改 | 添加 trace_id 测试 |
| `tests/unit/test_processors.py` | 修改 | 添加线程安全测试 |
| `tests/unit/test_rotation.py` | 修改 | 添加进程锁和 rotate_when 测试 |
| `docs/config_spec.md` | 新建（如需要） | 配置规范文档 |

---

## 七、验收检查表

- [ ] Sprint 1: ruff format 通过
- [ ] Sprint 2: trace_id 功能完成，测试 100%
- [ ] Sprint 3: 进程锁 + rotate_when 完成，测试 100%
- [ ] Sprint 4: 线程安全 + 死代码清理完成，测试 100%
- [ ] Sprint 5: 全量测试 100% 覆盖，100% 通过
- [ ] ruff check 零错误

---

*文档版本：V1.0*
*最后更新：2026-05-08*