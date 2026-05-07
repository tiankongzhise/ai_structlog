"""tkzs-structlog

Structlog 自动化配置工具，支持配置驱动的日志截断、复合轮转、多环境适配、敏感信息脱敏等生产级能力。
"""

from __future__ import annotations

from tkzs_structlog.api import (
    bind_context,
    clear_context,
    get_logger,
    init_structlog,
    is_initialized,
    reset_structlog,
    unbind_context,
)
from tkzs_structlog.config import (
    DEFAULT_CONFIG,
    SUPPORTED_VERSIONS,
    get_default_config,
    load_config,
    validate_config,
)
from tkzs_structlog.core import (
    LoggerFactory,
    ProcessorBuilder,
    StructlogInitializer,
)
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

__version__ = "0.1.0"

__all__ = [
    # API
    "init_structlog",
    "get_logger",
    "bind_context",
    "unbind_context",
    "clear_context",
    "reset_structlog",
    "is_initialized",
    # Config
    "DEFAULT_CONFIG",
    "SUPPORTED_VERSIONS",
    "get_default_config",
    "load_config",
    "validate_config",
    # Core
    "StructlogInitializer",
    "ProcessorBuilder",
    "LoggerFactory",
    # Exceptions
    "StructlogBaseError",
    "StructlogConfigError",
    "StructlogConfigFileNotFoundError",
    "StructlogConfigParseError",
    "StructlogConfigVersionError",
    "StructlogProcessorError",
    "StructlogProcessorImportError",
    "StructlogProcessorInstantiateError",
    "StructlogNotInitedError",
    "StructlogHandlerError",
]
