"""集成测试

测试配置加载 -> 初始化 -> 日志输出的全链路。
"""

import json
import tempfile
from pathlib import Path

from tkzs_structlog import (
    bind_context,
    clear_context,
    get_logger,
    init_structlog,
    is_initialized,
    reset_structlog,
    unbind_context,
)


class TestBasicIntegration:
    """基础集成测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_init_default_config(self):
        """测试使用默认配置初始化"""
        init_structlog()
        assert is_initialized()

    def test_init_custom_config(self):
        """测试使用自定义配置初始化"""
        config = {
            "version": "1.0",
            "logger_name": "custom_logger",
            "min_level": "DEBUG",
            "handlers": {
                "console": {"enable": True},
            },
        }
        init_structlog(config=config)
        assert is_initialized()

    def test_get_logger_after_init(self):
        """测试初始化后获取日志器"""
        init_structlog()
        logger = get_logger()
        assert logger is not None

    def test_log_output(self):
        """测试日志输出（不抛出异常即可）"""
        init_structlog()
        logger = get_logger()
        # 不应该抛出异常
        logger.info("test message", key="value")

    def test_context_binding(self):
        """测试上下文绑定"""
        init_structlog()
        bind_context(request_id="12345", user_id=100)
        logger = get_logger()
        logger.info("test with context")

    def test_unbind_context(self):
        """测试解绑上下文"""
        init_structlog()
        bind_context(a=1, b=2)
        unbind_context("a")
        logger = get_logger()
        logger.info("test after unbind")

    def test_clear_context(self):
        """测试清空上下文"""
        init_structlog()
        bind_context(a=1, b=2)
        clear_context()
        logger = get_logger()
        logger.info("test after clear")


class TestFileHandlerIntegration:
    """文件处理器集成测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_file_handler_creation(self):
        """测试文件处理器创建"""
        import gc
        import time

        gc.collect()  # 确保之前的文件句柄被释放
        time.sleep(0.1)  # 给系统一点时间释放文件句柄

        tmpdir = tempfile.mkdtemp()
        try:
            log_file = Path(tmpdir) / "test.log"
            config = {
                "version": "1.0",
                "logger_name": "test",
                "handlers": {
                    "console": {"enable": False},
                    "file": {
                        "enable": True,
                        "file_path": str(log_file),
                        "encoding": "utf-8",
                    },
                },
            }
            init_structlog(config=config)
            logger = get_logger()
            logger.info("test message")

            # 检查文件是否创建
            assert log_file.exists()

            # 显式关闭文件处理器
            reset_structlog()
        finally:
            # 清理 - 忽略可能的文件句柄问题
            gc.collect()
            try:
                import shutil

                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass


class TestTruncateIntegration:
    """截断功能集成测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_truncate_long_string(self):
        """测试截断长字符串"""
        config = {
            "version": "2.0",
            "handlers": {"console": {"enable": False}},
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 50,
                }
            },
        }
        init_structlog(config=config)
        logger = get_logger()

        # 不应该抛出异常
        logger.info("long_message", data="x" * 500)


class TestSensitiveDataIntegration:
    """敏感数据脱敏集成测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_sensitive_data_masking(self):
        """测试敏感数据脱敏"""
        config = {
            "version": "2.0",
            "handlers": {"console": {"enable": False}},
            "extensions": {
                "sensitive_fields": ["password", "phone"],
            },
        }
        init_structlog(config=config)
        logger = get_logger()

        # 不应该抛出异常
        logger.info(
            "login",
            username="john",
            password="secret123",
            phone="13812345678",
        )


class TestConfigFromFile:
    """从文件加载配置集成测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_load_config_from_file(self):
        """测试从文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "version": "1.0",
                    "logger_name": "file_config",
                    "min_level": "INFO",
                    "handlers": {"console": {"enable": True}},
                },
                f,
            )
            f.flush()
            config_path = f.name

        try:
            init_structlog(config_path=config_path)
            assert is_initialized()
            logger = get_logger()
            logger.info("test from file config")
        finally:
            Path(config_path).unlink()


class TestMultipleInitReset:
    """多次初始化/重置测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_structlog()

    def teardown_method(self):
        """每个测试后重置"""
        reset_structlog()

    def test_reinit_after_reset(self):
        """测试重置后重新初始化"""
        init_structlog()
        assert is_initialized()

        reset_structlog()
        assert not is_initialized()

        init_structlog()
        assert is_initialized()

    def test_reinit_with_different_config(self):
        """测试使用不同配置重新初始化"""
        init_structlog(config={"version": "1.0", "logger_name": "first"})
        logger1 = get_logger()
        assert logger1 is not None

        reset_structlog()

        init_structlog(config={"version": "1.0", "logger_name": "second"})
        logger2 = get_logger()
        assert logger2 is not None
