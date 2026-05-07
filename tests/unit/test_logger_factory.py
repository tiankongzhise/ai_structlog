"""日志工厂模块测试"""

import pytest

from tkzs_structlog.core.logger_factory import (
    LoggerFactory,
    get_logger_factory,
    reset_logger_factory,
)
from tkzs_structlog.exceptions import StructlogNotInitedError


class TestLoggerFactory:
    """测试日志工厂"""

    def setup_method(self):
        """每个测试前重置"""
        reset_logger_factory()

    def teardown_method(self):
        """每个测试后重置"""
        reset_logger_factory()

    def test_initialize(self):
        """测试初始化"""
        factory = LoggerFactory()
        assert not factory.is_initialized

        factory.initialize("test_logger")
        assert factory.is_initialized
        assert factory.logger_name == "test_logger"

    def test_get_logger_without_init(self):
        """测试未初始化时获取日志器"""
        factory = LoggerFactory()
        with pytest.raises(StructlogNotInitedError):
            factory.get_logger()

    def test_get_logger_after_init(self):
        """测试初始化后获取日志器"""
        factory = LoggerFactory()
        factory.initialize("test_logger")
        logger = factory.get_logger()
        assert logger is not None

    def test_get_logger_with_name(self):
        """测试带名称获取日志器"""
        factory = LoggerFactory()
        factory.initialize("test_logger")
        logger = factory.get_logger(name="custom_name")
        assert logger is not None

    def test_reset(self):
        """测试重置"""
        factory = LoggerFactory()
        factory.initialize("test_logger")
        assert factory.is_initialized

        factory.reset()
        assert not factory.is_initialized

    def test_get_global_factory(self):
        """测试获取全局工厂"""
        factory1 = get_logger_factory()
        factory2 = get_logger_factory()
        assert factory1 is factory2
