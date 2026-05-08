"""tkzs-structlog 日志工厂模块

D3: 负责创建和管理 structlog 日志器实例。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from structlog.typing import WrappedLogger


class LoggerFactory:
    """日志工厂

    封装 structlog 的日志器创建逻辑。
    """

    def __init__(self) -> None:
        self._is_initialized = False
        self._logger_name: str = "structlog_auto"

    def initialize(self, logger_name: str) -> None:
        """初始化日志工厂

        Args:
            logger_name: 日志器名称
        """
        self._is_initialized = True
        self._logger_name = logger_name

    def get_logger(
        self,
        name: str | None = None,
        **kwargs: Any,
    ) -> WrappedLogger:
        """获取日志器

        Args:
            name: 日志器名称（可选）
            **kwargs: 额外参数

        Returns:
            structlog 日志器

        Raises:
            StructlogNotInitedError: 未初始化
        """
        if not self._is_initialized:
            from tkzs_structlog.exceptions import StructlogNotInitedError

            raise StructlogNotInitedError()

        # 使用 structlog.get_logger
        if name:
            logger = structlog.get_logger(name, **kwargs)
        else:
            logger = structlog.get_logger(**kwargs)

        return logger

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._is_initialized

    @property
    def logger_name(self) -> str:
        """日志器名称"""
        return self._logger_name

    def reset(self) -> None:
        """重置日志工厂"""
        self._is_initialized = False


# 全局日志工厂实例
_logger_factory: LoggerFactory | None = None


def get_logger_factory() -> LoggerFactory:
    """获取全局日志工厂

    Returns:
        LoggerFactory 实例
    """
    global _logger_factory
    if _logger_factory is None:
        _logger_factory = LoggerFactory()
    return _logger_factory


def reset_logger_factory() -> None:
    """重置全局日志工厂"""
    global _logger_factory
    if _logger_factory is not None:
        _logger_factory.reset()
    _logger_factory = None
