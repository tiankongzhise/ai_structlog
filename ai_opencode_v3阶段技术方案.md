# tkzs-structlog V3.0 阶段技术方案

> 版本：V3.0  
> 创建日期：2026-05-08  
> 依据文档：开发需求.md §四/§五、开发计划.md §五/V3.0、ai_opencode_v3阶段开发计划.md

---

## 一、Sprint 1：V2.1 遗留问题修复

### 1.1 测试失败修复

#### 1.1.1 问题分析

测试 `test_should_rotate_by_time_hourly_same_hour` 失败，断言 `assert result is False` 但实际返回 `True`。

问题原因：轮转逻辑中同一小时内判断条件有误。

#### 1.1.2 技术方案

检查 `_should_rotate_by_time` 方法中的小时轮转逻辑：

```python
def _should_rotate_by_time(self) -> bool:
    """检查是否应该按时间轮转"""
    if not self.enable_rotate:
        return False

    now = datetime.now()
    rotate_when = self.rotate_when.upper()

    if rotate_when == "H":  # 按小时
        if self._last_rotate_time > 0:
            last_time = datetime.fromtimestamp(self._last_rotate_time)
            # 问题：当前逻辑只检查小时不同就返回True
            # 修复：应该只在当前小时 > 上次小时时触发轮转
            if now.hour != last_time.hour:
                return True
    
    return False
```

修复方案：当 `now.hour == last_time.hour` 时应返回 `False`。

#### 1.1.3 验收标准

- 测试 `test_should_rotate_by_time_hourly_same_hour` 通过
- 相关测试全部通过

### 1.2 覆盖率提升

#### 1.2.1 未覆盖代码分析

rotation.py 模块覆盖率 85%，未覆盖代码行：

- 行 42-47: 进程锁相关
- 行 45-46, 49-61: 压缩后端相关
- 行 73-88: 压缩相关
- 行 277-303: 清理相关

#### 1.2.2 补充测试用例

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_process_lock_acquire_release | 进程锁获取和释放 |
| test_compress_backend_gzip | Gzip 压缩后端 |
| test_compress_backend_lz4_fallback | LZ4 降级处理 |
| test_cleanup_by_days | 按天数清理 |
| test_cleanup_by_count | 按数量清理 |

#### 1.2.3 验收标准

- rotation.py 覆盖率 100%

---

## 二、Sprint 2：配置热重载完善

### 2.1 功能需求

根据开发需求.md §4.1：

- 使用 `watchdog` 监听配置文件变化
- 配置 `extensions.config_hot_reload=true` 时启用
- 热重载时加锁（`threading.Lock`），避免并发修改
- 自定义处理器热加载：通过 `importlib.reload` 重新导入

### 2.2 当前实现状态

- `hotreload.py`: 已实现 `ConfigHotReloader` 和 `ConfigFileHandler`
- `core.py`: 已集成热重载到 `init_structlog`
- 测试覆盖：test_hotreload.py 有 263 行测试代码

### 2.3 补充测试用例

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_config_hot_reload_enabled | 配置启用热重载 |
| test_config_hot_reload_disabled | 配置禁用热重载 |
| test_hotreload_concurrent_safety | 并发安全 |
| test_hotreload_watchdog_unavailable | watchdog 不可用降级 |

### 2.4 验收标准

- 端到端热重载测试通过
- 边界测试覆盖率 100%

---

## 三、Sprint 3：CLI 命令行工具完善

### 3.1 功能需求

根据开发需求.md §4.2：

基于 `click` 框架实现以下命令：

| 命令 | 功能 | 参数 |
|------|------|------|
| `structlog-auto validate` | 校验配置文件合法性 | `--config-path`, `--env` |
| `structlog-auto generate` | 生成默认配置文件（含注释） | `--output`, `--env` |
| `structlog-auto version` | 输出工具版本及支持的配置版本 | 无 |

### 3.2 当前实现状态

- `cli.py`: 已实现 validate/generate/version 命令
- 测试覆盖：test_cli.py 有 276 行测试代码
- 入口点：已在 pyproject.toml 配置

### 3.3 补充测试用例

| 测试名称 | 覆盖边界 |
|----------|----------|
| test_validate_with_env | 环境变量配置校验 |
| test_generate_with_nested_path | 嵌套路径生成 |
| test_version_output_format | 版本输出格式 |

### 3.4 验收标准

- CLI 命令行工具测试通过率 100%
- 边界测试覆盖率 100%

---

## 四、Sprint 4：类型提示完善

### 4.1 功能需求

根据开发需求.md §4.3：

- 所有函数/类添加类型注解（使用 `typing` 模块）
- 发布 `py.typed` 文件，支持 `mypy` 检查
- 使用 `ruff` 格式化
- 核心模块添加 Google 风格文档字符串

### 4.2 当前实现状态

- 核心模块已添加类型注解
- mypy 配置已在 pyproject.toml 中设置

### 4.3 补充工作

| 工作内容 | 说明 |
|----------|------|
| mypy 检查 | 运行 `mypy src/tkzs_structlog` |
| py.typed 文件 | 创建空标记文件 |

### 4.4 验收标准

- mypy strict 检查通过
- ruff 零错误

---

## 五、Sprint 5：最终验收

### 5.1 全量测试

```bash
pytest tests/ --cov=tkzs_structlog --cov-report=term-missing
```

验收标准：
- 覆盖率 100%（排除 `__main__` / `__init__`）
- 通过率 100%

### 5.2 代码质量

```bash
ruff format . --check
ruff check .
```

验收标准：
- ruff format 通过
- ruff check 零错误

### 5.3 类型检查

```bash
mypy src/tkzs_structlog
```

验收标准：
- mypy 零错误

---

## 六、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/tkzs_structlog/extensions/rotation.py` | 修改 | 修复轮转逻辑边界 |
| `tests/unit/test_rotation.py` | 修改 | 补充测试用例 |
| `src/tkzs_structlog/py.typed` | 新建 | mypy 类型标记文件 |
| `tests/integration/test_integration.py` | 修改（如需要） | 补充集成测试 |

---

## 七、验收检查表

- [ ] Sprint 1: V2.1 遗留问题修复完成，测试通过
- [ ] Sprint 2: 热重载测试通过，边界覆盖 100%
- [ ] Sprint 3: CLI 测试通过，边界覆盖 100%
- [ ] Sprint 4: mypy 零错误
- [ ] Sprint 5: 全量测试 100% 通过，100% 覆盖
- [ ] ruff format/check 零错误

---

*文档版本：V1.0*  
*最后更新：2026-05-08*
