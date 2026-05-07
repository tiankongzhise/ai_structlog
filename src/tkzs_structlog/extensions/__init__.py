"""tkzs-structlog 扩展层模块

C1: 自定义处理器模块（截断、脱敏、过滤）
C2: 输出源扩展模块（文件轮转、第三方输出）
C3: 热更新模块（配置监听）
"""

from tkzs_structlog.extensions.handlers import (
    setup_console_handler,
    setup_file_handler,
)
from tkzs_structlog.extensions.processors import (
    FilterProcessor,
    SensitiveDataProcessor,
    TruncateProcessor,
)

__all__ = [
    "setup_console_handler",
    "setup_file_handler",
    "TruncateProcessor",
    "SensitiveDataProcessor",
    "FilterProcessor",
]
