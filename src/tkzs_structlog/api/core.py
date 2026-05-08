"""tkzs-structlog 核心API模块

B1: 提供 init_structlog、get_logger、bind_context 等核心API。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from tkzs_structlog.core.initializer import get_initializer, reset_initializer
from tkzs_structlog.core.logger_factory import get_logger_factory
from tkzs_structlog.exceptions import StructlogNotInitedError
from tkzs_structlog.extensions.hotreload import WATCHDOG_AVAILABLE, ConfigHotReloader
from tkzs_structlog.extensions.processors import set_global_config

if TYPE_CHECKING:
    from structlog.typing import WrappedLogger


# 全局上下文存储
_context_store: dict[str, Any] = {}

# 全局热重载器
_hotreloader: ConfigHotReloader | None = None


def init_structlog(
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    enable_hotreload: bool = False,
    enable_trace_id: bool | None = None,
    **kwargs: Any,
) -> None:
    """初始化 structlog

    Args:
        config_path: 配置文件路径
        config: 配置字典（直接传入）
        enable_hotreload: 是否启用配置热重载
        enable_trace_id: 是否自动绑定 trace_id（True 时自动生成 UUID）
                         若为 None，则从配置 extensions.trace_id_bind 读取
        **kwargs: 其他配置参数

    Example:
        >>> import tkzs_structlog
        >>> tkzs_structlog.init_structlog()
        >>> logger = tkzs_structlog.get_logger()
        >>> logger.info("hello", name="world")
    """
    # 获取初始化器
    initializer = get_initializer()

    # 执行初始化
    initializer.init(
        config_path=str(config_path) if config_path else None,
        config=config,
        **kwargs,
    )

    # 设置全局配置（供处理器使用）
    set_global_config(initializer.config)

    # trace_id 自动绑定
    if enable_trace_id is None:
        enable_trace_id = initializer.config.get("extensions", {}).get("trace_id_bind", False)

    if enable_trace_id:
        bind_context(auto_trace_id=True)

    # 启用热重载
    if enable_hotreload and WATCHDOG_AVAILABLE:
        _setup_hotreload(initializer.config)


def _setup_hotreload(config: dict[str, Any]) -> None:
    """设置热重载"""
    global _hotreloader

    hot_reload_enabled = config.get("extensions", {}).get("config_hot_reload", False)
    if not hot_reload_enabled:
        return

    # 获取配置文件路径
    from tkzs_structlog.config import get_default_config_path

    config_path = get_default_config_path()

    def on_reload(new_config: dict[str, Any]) -> None:
        """配置重新加载回调"""
        global _context_store
        # 更新全局配置
        set_global_config(new_config)
        # 重新初始化
        initializer = get_initializer()
        initializer.reset()
        initializer.init(config=new_config)

    try:
        _hotreloader = ConfigHotReloader(config_path, on_reload)
        _hotreloader.start()
    except ImportError:
        pass


def get_logger(name: str | None = None, **kwargs: Any) -> WrappedLogger:
    """获取日志器

    Args:
        name: 日志器名称（可选）
        **kwargs: 额外参数

    Returns:
        structlog 日志器

    Raises:
        StructlogNotInitedError: 未初始化

    Example:
        >>> logger = tkzs_structlog.get_logger()
        >>> logger.info("message", key="value")
    """
    initializer = get_initializer()
    if not initializer.is_initialized:
        raise StructlogNotInitedError()

    factory = get_logger_factory()
    logger = factory.get_logger(name, **kwargs)

    # 绑定全局上下文
    if _context_store:
        logger = logger.bind(**_context_store)

    return logger


def bind_context(auto_trace_id: bool = False, **kwargs: Any) -> None:
    """绑定全局上下文

    Args:
        auto_trace_id: 是否自动生成 trace_id（UUID）
        **kwargs: 上下文键值对

    Example:
        >>> tkzs_structlog.bind_context(request_id="12345", user_id=100)
        >>> logger = tkzs_structlog.get_logger()
        >>> logger.info("message")  # 会自动包含 request_id 和 user_id
        >>> tkzs_structlog.bind_context(auto_trace_id=True)  # 自动生成 trace_id
    """
    global _context_store
    if auto_trace_id and "trace_id" not in kwargs:
        import uuid

        kwargs["trace_id"] = str(uuid.uuid4())
    if kwargs:
        _context_store.update(kwargs)


def unbind_context(*keys: str) -> None:
    """解绑全局上下文

    Args:
        *keys: 要解绑的键

    Example:
        >>> tkzs_structlog.unbind_context("request_id")
    """
    global _context_store
    for key in keys:
        _context_store.pop(key, None)


def clear_context() -> None:
    """清空全局上下文

    Example:
        >>> tkzs_structlog.clear_context()
    """
    global _context_store
    _context_store.clear()


def reset_structlog() -> None:
    """重置 structlog

    停止热重载，清除全局状态。
    """
    global _hotreloader, _context_store

    # 停止热重载
    if _hotreloader:
        _hotreloader.stop()
        _hotreloader = None

    # 清除上下文
    _context_store.clear()

    # 重置初始化器
    reset_initializer()

    # 重置 structlog
    structlog.reset_defaults()


def is_initialized() -> bool:
    """检查是否已初始化

    Returns:
        是否已初始化
    """
    initializer = get_initializer()
    return initializer.is_initialized
