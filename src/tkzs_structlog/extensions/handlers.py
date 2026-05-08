"""tkzs-structlog 处理器模块

C2: 控制台和文件输出处理器。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from tkzs_structlog.exceptions import StructlogHandlerError


def setup_console_handler(
    config: dict[str, Any],
    *,
    stdlib_bridge: bool = False,
    renderer: Any | None = None,
) -> None:
    """设置控制台处理器

    Args:
        config: 控制台配置
        stdlib_bridge: 是否已通过 structlog.stdlib 桥接（使用 ProcessorFormatter）
        renderer: 桥接时的最终渲染器实例（如 ConsoleRenderer）
    """
    if not config.get("enable", True):
        return

    # 获取根日志器
    root_logger = logging.getLogger()

    if stdlib_bridge and renderer is not None:
        from structlog.stdlib import ProcessorFormatter

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ProcessorFormatter(processor=renderer))
    else:
        handler = ColoredConsoleHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)


def setup_file_handler(
    config: dict[str, Any],
    *,
    stdlib_bridge: bool = False,
    renderer: Any | None = None,
) -> None:
    """设置文件处理器

    Args:
        config: 文件配置

    Raises:
        StructlogHandlerError: 文件处理器设置失败
    """
    if not config.get("enable", False):
        return

    file_path = config.get("file_path", "./logs/structlog.log")
    encoding = config.get("encoding", "utf-8")

    try:
        # 创建父目录
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 获取根日志器
        root_logger = logging.getLogger()

        # 创建文件处理器
        handler = logging.FileHandler(
            filename=str(path),
            mode="a",  # 追加模式
            encoding=encoding,
        )

        if stdlib_bridge and renderer is not None:
            from structlog.stdlib import ProcessorFormatter

            handler.setFormatter(ProcessorFormatter(processor=renderer))
        else:
            formatter = logging.Formatter(
                fmt="%(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

        # 添加处理器
        root_logger.addHandler(handler)

    except PermissionError:
        raise StructlogHandlerError(
            handler_name="file",
            reason=f"Permission denied writing to file: {file_path}",
            fix_suggestion="Please check file permissions or use a different path",
        )
    except OSError as e:
        raise StructlogHandlerError(
            handler_name="file",
            reason=f"Failed to create file handler: {str(e)}",
            fix_suggestion="Please check the file path and disk space",
        )


class ColoredConsoleHandler(logging.StreamHandler[Any]):
    """带颜色的控制台处理器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def emit(self, record: logging.LogRecord) -> None:
        """输出日志"""
        try:
            # 添加颜色
            levelname = record.levelname
            color = self.COLORS.get(levelname, "")
            record.levelname = f"{color}{levelname}{self.RESET}"

            msg = self.format(record)
            # 使用 os.linesep 确保跨平台兼容性
            self.stream.write(msg + os.linesep)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_colored_console_handler(config: dict[str, Any]) -> None:
    """设置带颜色的控制台处理器

    Args:
        config: 控制台配置
    """
    if not config.get("enable", True):
        return

    root_logger = logging.getLogger()
    handler = ColoredConsoleHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def setup_output_handlers(config: dict[str, Any]) -> list[str]:
    """设置所有输出处理器

    当 PGSQL 或 Redis 输出失败时，自动降级到文件输出。

    Args:
        config: 完整配置

    Returns:
        错误信息列表（用于记录降级警告）
    """
    errors: list[str] = []

    pgsql_config = config.get("handlers", {}).get("pgsql", {})
    if pgsql_config.get("enable", False):
        try:
            from tkzs_structlog.extensions.pgsql_handler import setup_pgsql_handler

            setup_pgsql_handler(pgsql_config)
        except StructlogHandlerError as e:
            errors.append(f"PGSQL: {e.reason}, fallback to file")
        except Exception:
            errors.append("PGSQL connection failed, fallback to file")

    redis_config = config.get("handlers", {}).get("redis", {})
    if redis_config.get("enable", False):
        try:
            from tkzs_structlog.extensions.redis_handler import setup_redis_handler

            setup_redis_handler(redis_config)
        except StructlogHandlerError as e:
            errors.append(f"Redis: {e.reason}, fallback to file")
        except Exception:
            errors.append("Redis connection failed, fallback to file")

    file_config = config.get("handlers", {}).get("file", {})
    setup_file_handler(file_config)

    return errors
