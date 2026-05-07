"""标准 logging 与 structlog 桥接集成测试"""

import logging

import pytest

from tkzs_structlog import init_structlog, reset_structlog


class TestStdlibBridge:
    """bridge_std_logging=True 时 logging 模块输出可被捕获"""

    def setup_method(self) -> None:
        reset_structlog()

    def teardown_method(self) -> None:
        reset_structlog()

    def test_stdlib_logging_emits_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        init_structlog(
            config={
                "version": "1.0",
                "logger_name": "test",
                "min_level": "INFO",
                "bridge_std_logging": True,
                "handlers": {
                    "console": {"enable": True},
                    "file": {"enable": False},
                },
            }
        )
        logging.getLogger("stdlib_bridge").info("bridge_ok")
        captured = capsys.readouterr()
        assert "bridge_ok" in captured.out

    def test_bridge_disabled_skips_stdlib_formatter_path(self) -> None:
        """关闭桥接时使用非 stdlib 处理器链（不应抛错）"""
        init_structlog(
            config={
                "version": "1.0",
                "logger_name": "test",
                "min_level": "INFO",
                "bridge_std_logging": False,
                "handlers": {
                    "console": {"enable": True},
                    "file": {"enable": False},
                },
            }
        )
        assert logging.getLogger().handlers
