"""tkzs-structlog API层模块

B1: 核心API模块
B2: CLI模块
"""

from tkzs_structlog.api.core import (
    bind_context,
    clear_context,
    get_logger,
    init_structlog,
    is_initialized,
    reset_structlog,
    unbind_context,
)
from tkzs_structlog.extensions.processors import set_global_config

__all__ = [
    "init_structlog",
    "get_logger",
    "bind_context",
    "unbind_context",
    "clear_context",
    "reset_structlog",
    "is_initialized",
    "set_global_config",
]
