"""tkzs-structlog 处理器模块

C2: 控制台和文件输出处理器。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from tkzs_structlog.exceptions import StructlogHandlerError


def setup_console_handler(config: dict[str, Any]) -> None:
    """设置控制台处理器

    Args:
        config: 控制台配置
    """
    if not config.get("enable", True):
        return

    # 获取根日志器
    root_logger = logging.getLogger()

    # 创建控制台处理器
    handler = logging.StreamHandler(sys.stdout)

    # 设置格式
    formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # 添加处理器
    root_logger.addHandler(handler)

    # 配置 structlog 控制台渲染器
    if "ConsoleRenderer" not in str(config):
        # 使用 structlog 的 ConsoleRenderer
        pass


def setup_file_handler(config: dict[str, Any]) -> None:
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

        # 设置格式
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


class ColoredConsoleHandler(logging.StreamHandler):
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
            self.stream.write(msg + self.stream.sep)
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
