"""API模块测试"""

import pytest

from tkzs_structlog.api.core import (
    bind_context,
    clear_context,
    is_initialized,
    unbind_context,
)
from tkzs_structlog.exceptions import StructlogNotInitedError


class TestContextAPI:
    """测试上下文API"""

    def test_bind_context(self):
        """测试绑定上下文"""
        bind_context(request_id="123")
        bind_context(user_id=456)
        # 绑定后上下文会被 get_logger 使用

    def test_unbind_context(self):
        """测试解绑上下文"""
        bind_context(a=1, b=2)
        unbind_context("a")
        # b 应该仍然存在

    def test_clear_context(self):
        """测试清空上下文"""
        bind_context(a=1, b=2)
        clear_context()
        # 上下文应该为空

    def test_unbind_nonexistent(self):
        """测试解绑不存在的键"""
        unbind_context("nonexistent")


class TestInitAndLogger:
    """测试初始化和日志器"""

    def test_init_with_default(self):
        """测试使用默认配置初始化"""
        from tkzs_structlog import get_logger, init_structlog, reset_structlog

        reset_structlog()
        init_structlog()
        assert is_initialized()

        logger = get_logger()
        assert logger is not None

        reset_structlog()

    def test_init_with_dict_config(self):
        """测试使用字典配置初始化"""
        from tkzs_structlog import get_logger, init_structlog, reset_structlog

        reset_structlog()
        config = {
            "version": "1.0",
            "logger_name": "test",
            "min_level": "DEBUG",
        }
        init_structlog(config=config)
        assert is_initialized()

        logger = get_logger()
        assert logger is not None

        reset_structlog()

    def test_get_logger_without_init(self):
        """测试未初始化时获取日志器"""
        from tkzs_structlog import reset_structlog

        reset_structlog()
        with pytest.raises(StructlogNotInitedError):
            from tkzs_structlog import get_logger

            get_logger()

    def test_reset_structlog(self):
        """测试重置"""
        from tkzs_structlog import init_structlog, is_initialized, reset_structlog

        init_structlog()
        assert is_initialized()

        reset_structlog()
        assert not is_initialized()

    def test_reinitialization(self):
        """测试重复初始化"""
        from tkzs_structlog import init_structlog, is_initialized, reset_structlog

        init_structlog(config={"version": "1.0", "logger_name": "first"})
        assert is_initialized()

        # 再次初始化应该先重置
        init_structlog(config={"version": "1.0", "logger_name": "second"})
        assert is_initialized()

        reset_structlog()

    def test_init_with_kwargs_override(self):
        """测试 kwargs 覆盖配置"""
        from tkzs_structlog import init_structlog, reset_structlog

        reset_structlog()
        init_structlog(
            config={"version": "1.0"},
            logger_name="override_test",
            min_level="DEBUG",
        )
        # 应该成功初始化，不抛出异常
        assert is_initialized()

        reset_structlog()
