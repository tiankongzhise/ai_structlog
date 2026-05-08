"""tkzs-structlog Structlog初始化模块

D1: 负责初始化 structlog 配置，包括处理器链、日志级别、标准 logging 桥接。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import structlog

from tkzs_structlog.config import (
    get_extension_config,
    get_processor_names,
    load_config,
)
from tkzs_structlog.core.logger_factory import get_logger_factory, reset_logger_factory
from tkzs_structlog.core.processor_builder import get_processor_builder, reset_processor_builder
from tkzs_structlog.extensions.handlers import (
    setup_output_handlers,
)

if TYPE_CHECKING:
    from pathlib import Path


# 日志级别映射
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class StructlogInitializer:
    """Structlog 初始化器

    负责配置和初始化 structlog。
    """

    def __init__(self) -> None:
        self._is_initialized = False
        self._config: dict[str, Any] = {}
        self._use_stdlib_bridge = False
        self._bridge_renderer: Any | None = None

    def init(
        self,
        config_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 structlog

        Args:
            config_path: 配置文件路径
            config: 配置字典（直接传入）
            **kwargs: 其他配置参数
        """
        if self._is_initialized:
            self.reset()

        # 加载配置
        if config is not None:
            self._config = config
        else:
            self._config = load_config(str(config_path) if config_path else None)

        # 应用 kwargs 覆盖
        self._config.update(kwargs)

        # 1. 设置日志级别
        self._setup_log_level()

        # 2. 构建处理器链
        self._setup_processors()

        # 3. 设置输出处理器
        self._setup_handlers()

        # 4. 初始化日志工厂
        self._setup_logger_factory()

        self._is_initialized = True

    def _setup_log_level(self) -> None:
        """设置全局日志级别"""
        min_level = self._config.get("min_level", "INFO")
        numeric_level = LEVEL_MAP.get(min_level.upper(), logging.INFO)

        # 配置根日志器级别
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

    def _setup_processors(self) -> None:
        """构建处理器链"""
        import structlog.stdlib as sl_stdlib

        from tkzs_structlog.extensions.processors import (
            FilterProcessor,
            SensitiveDataProcessor,
            TruncateProcessor,
        )

        builder = get_processor_builder()
        processor_specs = get_processor_names(self._config)

        # 过滤掉渲染器，只保留处理器
        renderer_classes = (
            "structlog.dev.ConsoleRenderer",
            "structlog.processors.JSONRenderer",
            "structlog.processors.Renderer",
        )
        processor_specs_only = [s for s in processor_specs if s not in renderer_classes]

        # 构建基础处理器
        processors = builder.build(processor_specs_only)

        # 添加扩展处理器
        truncate_config = get_extension_config(self._config, "log_truncate")
        if truncate_config and truncate_config.get("enable"):
            processors.append(TruncateProcessor)

        sensitive_config = get_extension_config(self._config, "sensitive_fields")
        if sensitive_config:
            processors.append(SensitiveDataProcessor)

        filter_rules = get_extension_config(self._config, "filter_rules")
        if filter_rules and (filter_rules.get("exclude") or filter_rules.get("include")):
            processors.append(FilterProcessor)

        bridge = self._config.get("bridge_std_logging", True)
        renderer = structlog.dev.ConsoleRenderer()

        # 标准 logging 桥接：stdlib LoggerFactory + ProcessorFormatter + recreate_defaults
        if bridge:
            self._use_stdlib_bridge = True
            self._bridge_renderer = renderer
            chain = [
                sl_stdlib.filter_by_level,
                sl_stdlib.add_logger_name,
                sl_stdlib.add_log_level,
                sl_stdlib.PositionalArgumentsFormatter(),
                *processors,
                sl_stdlib.ProcessorFormatter.wrap_for_formatter,
            ]
            structlog.configure(
                processors=chain,
                wrapper_class=sl_stdlib.BoundLogger,
                logger_factory=sl_stdlib.LoggerFactory(),
                context_class=dict,
                cache_logger_on_first_use=True,
            )
            sl_stdlib.recreate_defaults()
        else:
            self._use_stdlib_bridge = False
            self._bridge_renderer = None
            processors.append(renderer)
            structlog.configure(
                processors=processors,
                context_class=dict,
                cache_logger_on_first_use=True,
            )

    def _setup_handlers(self) -> None:
        """设置输出处理器

        包括控制台、文件、PGSQL、Redis 处理器。
        当 PGSQL 或 Redis 失败时，自动降级到文件输出。
        """
        errors = setup_output_handlers(self._config)

        if errors:
            logger = logging.getLogger("structlog")
            for error in errors:
                logger.warning(error)

    def _setup_logger_factory(self) -> None:
        """设置日志工厂"""
        logger_factory = get_logger_factory()
        logger_name = self._config.get("logger_name", "structlog_auto")
        logger_factory.initialize(logger_name)

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._is_initialized

    @property
    def config(self) -> dict[str, Any]:
        """当前配置"""
        return self._config.copy()

    def reset(self) -> None:
        """重置初始化状态"""
        self._is_initialized = False
        self._config = {}
        self._use_stdlib_bridge = False
        self._bridge_renderer = None

        # 重置全局状态
        reset_processor_builder()
        reset_logger_factory()

        # 恢复默认 structlog 配置
        structlog.reset_defaults()


# 全局初始化器实例
_initializer: StructlogInitializer | None = None


def get_initializer() -> StructlogInitializer:
    """获取全局初始化器"""
    global _initializer
    if _initializer is None:
        _initializer = StructlogInitializer()
    return _initializer


def reset_initializer() -> None:
    """重置全局初始化器"""
    global _initializer
    if _initializer is not None:
        _initializer.reset()
    _initializer = None
