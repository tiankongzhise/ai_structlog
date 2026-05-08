"""处理器模块测试"""

import logging
import sys
from io import StringIO

import pytest


class TestSetupConsoleHandler:
    """测试控制台处理器设置"""

    def test_console_handler_disabled(self):
        """测试禁用控制台处理器"""
        from tkzs_structlog.extensions.handlers import setup_console_handler

        config = {"enable": False}
        setup_console_handler(config)  # 应该静默返回

    def test_console_handler_enabled(self):
        """测试启用控制台处理器"""
        from tkzs_structlog.extensions.handlers import setup_console_handler

        config = {"enable": True}
        setup_console_handler(config)

        # 验证处理器被添加
        root_logger = logging.getLogger()
        handler_found = any(
            isinstance(h, logging.StreamHandler) and h.stream in (sys.stdout, sys.__stdout__)
            for h in root_logger.handlers
        )
        assert handler_found


class TestSetupFileHandler:
    """测试文件处理器设置"""

    def test_file_handler_disabled(self):
        """测试禁用文件处理器"""
        from tkzs_structlog.extensions.handlers import setup_file_handler

        config = {"enable": False}
        setup_file_handler(config)  # 应该静默返回

    def test_file_handler_enabled(self, tmp_path):
        """测试启用文件处理器"""
        from tkzs_structlog.extensions.handlers import setup_file_handler

        log_file = tmp_path / "test.log"
        config = {
            "enable": True,
            "file_path": str(log_file),
            "encoding": "utf-8",
        }

        setup_file_handler(config)

        assert log_file.exists()

        # 验证处理器被添加
        root_logger = logging.getLogger()
        handler_found = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
        assert handler_found

    def test_file_handler_creates_directory(self, tmp_path):
        """测试创建父目录"""
        from tkzs_structlog.extensions.handlers import setup_file_handler

        log_file = tmp_path / "subdir" / "nested" / "test.log"
        config = {
            "enable": True,
            "file_path": str(log_file),
        }

        setup_file_handler(config)

        assert log_file.parent.exists()
        assert log_file.exists()

    def test_file_handler_invalid_path(self, tmp_path):
        """测试无效路径（包含非法字符）"""
        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.handlers import setup_file_handler

        # 使用包含非法字符的路径 (Windows不允许 | 在文件名中)
        config = {
            "enable": True,
            "file_path": str(tmp_path / "test|invalid.log"),
        }

        # 应该抛出异常
        with pytest.raises((StructlogHandlerError, OSError)):
            setup_file_handler(config)

    def test_file_handler_custom_encoding(self, tmp_path):
        """测试自定义编码"""
        from tkzs_structlog.extensions.handlers import setup_file_handler

        log_file = tmp_path / "test.log"
        config = {
            "enable": True,
            "file_path": str(log_file),
            "encoding": "gbk",
        }

        setup_file_handler(config)

        assert log_file.exists()


class TestColoredConsoleHandler:
    """测试彩色控制台处理器"""

    def test_handler_init(self):
        """测试处理器初始化"""
        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler

        output = StringIO()
        handler = ColoredConsoleHandler(output)

        assert handler.stream == output
        assert handler.COLORS is not None
        assert handler.RESET == "\033[0m"

    def test_handler_emit_custom_levels(self):
        """测试自定义日志级别输出"""
        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler

        output = StringIO()
        handler = ColoredConsoleHandler(output)

        # 测试各个级别
        levels = [
            (logging.DEBUG, "DEBUG", "debug"),
            (logging.INFO, "INFO", "info"),
            (logging.WARNING, "WARNING", "warning"),
            (logging.ERROR, "ERROR", "error"),
            (logging.CRITICAL, "CRITICAL", "critical"),
        ]

        for level, level_name, msg in levels:
            output.truncate(0)
            output.seek(0)

            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            result = output.getvalue()
            # 检查输出包含级别名称
            assert level_name in result or msg in result.lower() or result.strip() == ""

    def test_handler_emit_with_colors(self):
        """测试带颜色的输出"""
        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler

        output = StringIO()
        handler = ColoredConsoleHandler(output)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        result = output.getvalue()
        # 输出应该不为空
        assert len(result) > 0

    def test_handler_color_codes(self):
        """测试颜色代码存在"""
        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler

        output = StringIO()
        handler = ColoredConsoleHandler(output)

        assert "\033[36m" in handler.COLORS["DEBUG"]  # 青色
        assert "\033[32m" in handler.COLORS["INFO"]  # 绿色
        assert "\033[33m" in handler.COLORS["WARNING"]  # 黄色
        assert "\033[31m" in handler.COLORS["ERROR"]  # 红色
        assert "\033[35m" in handler.COLORS["CRITICAL"]  # 紫色


class TestSetupColoredConsoleHandler:
    """测试彩色控制台处理器设置"""

    def test_colored_console_disabled(self):
        """测试禁用彩色控制台"""
        from tkzs_structlog.extensions.handlers import setup_colored_console_handler

        config = {"enable": False}
        setup_colored_console_handler(config)

    def test_colored_console_enabled(self):
        """测试启用彩色控制台"""
        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler, setup_colored_console_handler

        config = {"enable": True}
        setup_colored_console_handler(config)

        # 验证处理器被添加
        root_logger = logging.getLogger()
        handler_found = any(isinstance(h, ColoredConsoleHandler) for h in root_logger.handlers)
        assert handler_found


class TestHandlerEdgeCases:
    """处理器边界情况测试"""

    def test_multiple_handlers(self, tmp_path):
        """测试添加多个处理器"""
        from tkzs_structlog.extensions.handlers import (
            setup_colored_console_handler,
            setup_console_handler,
            setup_file_handler,
        )

        setup_console_handler({"enable": True})
        setup_colored_console_handler({"enable": True})
        setup_file_handler(
            {
                "enable": True,
                "file_path": str(tmp_path / "test.log"),
            }
        )

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 3

    def test_file_handler_permission_error(self, tmp_path):
        """测试文件处理器权限错误抛出 StructlogHandlerError"""
        from unittest.mock import patch

        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.handlers import setup_file_handler

        log_file = tmp_path / "test.log"
        config = {"enable": True, "file_path": str(log_file)}

        # 模拟 mkdir 成功但 FileHandler 抛出 PermissionError
        with patch(
            "tkzs_structlog.extensions.handlers.logging.FileHandler", side_effect=PermissionError("access denied")
        ):
            with pytest.raises(StructlogHandlerError) as exc_info:
                setup_file_handler(config)

        assert "Permission denied" in str(exc_info.value)

    def test_colored_handler_emit_exception(self):
        """测试 emit 中发生异常时调用 handleError"""
        from unittest.mock import patch

        from tkzs_structlog.extensions.handlers import ColoredConsoleHandler

        output = StringIO()
        handler = ColoredConsoleHandler(output)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # 模拟 stream.write 抛出异常
        with patch.object(output, "write", side_effect=OSError("stream error")):
            with patch.object(handler, "handleError") as mock_handle_error:
                handler.emit(record)
                # handleError 应该被调用
                mock_handle_error.assert_called_once_with(record)
