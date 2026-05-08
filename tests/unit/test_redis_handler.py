"""Redis 处理器模块测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestRedisHandlerInit:
    """测试 RedisHandler 初始化"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        config = {"enable": True}
        handler = RedisHandler(config)

        assert handler.config == config
        assert handler._client is None
        assert handler._running is False
        assert handler._batch == []

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        config = {
            "enable": True,
            "key_prefix": "myapp:",
            "batch_size": 50,
            "flush_interval": 10,
        }
        handler = RedisHandler(config)

        assert handler.config["key_prefix"] == "myapp:"
        assert handler.config["batch_size"] == 50
        assert handler.config["flush_interval"] == 10


class TestRedisHandlerSingleton:
    """测试 RedisHandler 单例模式"""

    def test_get_instance_first_call(self):
        """测试首次获取实例"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": True}

        handler = RedisHandler.get_instance(config)

        assert handler is not None
        assert isinstance(handler, RedisHandler)

    def test_get_instance_subsequent_call(self):
        """测试后续获取实例"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": True}

        handler1 = RedisHandler.get_instance(config)
        handler2 = RedisHandler.get_instance()

        assert handler1 is handler2

    def test_get_instance_without_init(self):
        """测试未初始化时获取实例"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()

        with pytest.raises(Exception):
            RedisHandler.get_instance()

    def test_reset_instance(self):
        """测试重置实例"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": True}

        handler1 = RedisHandler.get_instance(config)
        RedisHandler.reset_instance()

        handler2 = RedisHandler.get_instance(config)
        assert handler1 is not handler2


class TestRedisHandlerInitialize:
    """测试 RedisHandler 初始化"""

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_initialize_not_enabled(self, mock_config, mock_available):
        """测试未启用时不初始化"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": False}

        handler = RedisHandler(config)
        handler.initialize()

        mock_available.assert_not_called()

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    def test_initialize_redis_not_available(self, mock_available):
        """测试依赖缺失时抛出异常"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        from tkzs_structlog.exceptions import StructlogHandlerError

        RedisHandler.reset_instance()
        mock_available.return_value = False
        config = {"enable": True}

        handler = RedisHandler(config)

        with pytest.raises(StructlogHandlerError) as exc_info:
            handler.initialize()

        assert "not installed" in str(exc_info.value.reason)

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_initialize_connection_error(self, mock_config, mock_available):
        """测试连接失败时抛出异常"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        from tkzs_structlog.exceptions import StructlogHandlerError

        RedisHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "invalid_host",
            "port": 6379,
            "password": "invalid",
            "db": 0,
        }

        config = {"enable": True}

        handler = RedisHandler(config)

        with pytest.raises(StructlogHandlerError):
            handler.initialize()

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_initialize_not_redis_available(self, mock_config, mock_available):
        """测试依赖不可用时抛出异常"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        mock_available.return_value = False

        config = {"enable": True}
        handler = RedisHandler(config)

        from tkzs_structlog.exceptions import StructlogHandlerError

        with pytest.raises(StructlogHandlerError) as exc_info:
            handler.initialize()

        assert "not installed" in str(exc_info.value.reason)


class TestRedisHandlerEmit:
    """测试 RedisHandler 日志写入"""

    def test_emit_not_running(self):
        """测试未运行时写入"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": False}

        handler = RedisHandler(config)

        log_entry = {"level": "INFO", "message": "test"}
        handler.emit(log_entry)

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_emit_success(self, mock_config, mock_available):
        """测试成功写入"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        import queue

        RedisHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0,
        }

        config = {"enable": True}
        handler = RedisHandler(config)
        handler._running = True
        handler._queue = queue.Queue(maxsize=10000)

        log_entry = {"level": "INFO", "message": "test", "logger": "test"}
        handler.emit(log_entry)

        assert handler._queue.qsize() == 1


class TestRedisHandlerShutdown:
    """测试 RedisHandler 关闭"""

    def test_shutdown_not_started(self):
        """测试未启动时关闭"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        config = {"enable": False}

        handler = RedisHandler(config)
        handler.shutdown()

    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_shutdown_started(self, mock_config, mock_available):
        """测试正常关闭"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0,
        }

        config = {"enable": True}
        handler = RedisHandler(config)
        handler._running = True
        handler._client = MagicMock()

        handler.shutdown()

        assert handler._running is False


class TestSetupRedisHandler:
    """测试 setup_redis_handler 函数"""

    def test_setup_disabled(self):
        """测试禁用时返回 None"""
        from tkzs_structlog.extensions.redis_handler import setup_redis_handler

        config = {"enable": False}
        result = setup_redis_handler(config)

        assert result is None

    @patch("tkzs_structlog.extensions.redis_handler.RedisHandler")
    def test_setup_enabled(self, mock_handler_class):
        """测试启用时返回 handler"""
        from tkzs_structlog.extensions.redis_handler import setup_redis_handler

        mock_handler = MagicMock()
        mock_handler_class.get_instance.return_value = mock_handler

        config = {"enable": True}
        result = setup_redis_handler(config)

        assert result is mock_handler
        mock_handler.initialize.assert_called_once()