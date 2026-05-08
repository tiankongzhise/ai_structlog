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


import time


class TestRedisHandlerWorker:
    """测试工作线程（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        RedisHandler.reset_instance()

    def test_worker_not_running(self):
        """测试 _running 为 False 时 worker 退出"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 0.1})
        handler._running = False

        handler._worker()  # 应该立即退出

    def test_worker_timeout_flush(self):
        """测试超时后刷新"""
        import queue
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 0.1, "batch_size": 1000})
        handler._running = True
        handler._queue = queue.Queue()
        handler._queue.put({"level": "INFO", "message": "test", "logger": "test", "extra": {}})

        # 等待超时
        time.sleep(0.2)
        handler._running = False
        handler._worker()

        assert len(handler._batch) == 0

    def test_worker_batch_size_flush(self):
        """测试达到 batch_size 时刷新"""
        import queue
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 60, "batch_size": 2})
        handler._running = True
        handler._queue = queue.Queue()
        handler._queue.put({"level": "INFO", "message": "test1", "logger": "test", "extra": {}})
        handler._queue.put({"level": "INFO", "message": "test2", "logger": "test", "extra": {}})

        # worker 应该立即刷新
        handler._running = False
        handler._worker()

        assert len(handler._batch) == 0


class TestRedisHandlerFlushBatch:
    """测试批量写入（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        RedisHandler.reset_instance()

    def test_flush_batch_empty(self):
        """测试空 batch 不写入"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._batch = []
        handler._client = None

        handler._flush_batch("test_key")  # 应该直接返回

        assert len(handler._batch) == 0

    def test_flush_batch_client_none(self):
        """测试 client 为 None 时不写入"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]
        handler._client = None

        handler._flush_batch("test_key")  # 应该直接返回

        assert len(handler._batch) == 1  # batch 没被清空

    def test_flush_batch_success(self):
        """测试成功写入"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline

        handler = RedisHandler({"enable": True})
        handler._batch = [
            {"log_time": "2025-01-01T00:00:00", "level": "INFO", "logger": "test", "message": "test1", "extra": {}},
        ]
        handler._client = mock_client

        handler._flush_batch("test_key")

        assert len(handler._batch) == 0
        mock_pipeline.rpush.assert_called_once()
        mock_pipeline.execute.assert_called_once()
        assert handler._last_flush > 0

    def test_flush_batch_exception(self, caplog):
        """测试写入异常"""
        import logging
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.rpush.side_effect = Exception("Redis error")
        mock_client.pipeline.return_value = mock_pipeline

        handler = RedisHandler({"enable": True})
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]
        handler._client = mock_client

        with caplog.at_level(logging.ERROR, logger="tkzs_structlog.extensions.redis_handler"):
            handler._flush_batch("test_key")

        assert len(handler._batch) == 1  # batch 没被清空（当前实现）
        assert "Failed to flush batch" in caplog.text


class TestRedisHandlerEmitEdgeCases:
    """测试日志写入队列（边界情况）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        RedisHandler.reset_instance()

    def test_emit_queue_full(self, caplog):
        """测试队列满时丢弃日志"""
        import logging
        import queue
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._running = True
        handler._queue = MagicMock()
        handler._queue.put_nowait.side_effect = queue.Full("Queue full")

        with caplog.at_level(logging.WARNING, logger="tkzs_structlog.extensions.redis_handler"):
            log_entry = {"level": "INFO", "message": "test"}
            handler.emit(log_entry)

        assert "queue full" in caplog.text.lower()


class TestRedisHandlerShutdownEdgeCases:
    """测试关闭流程（边界情况）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler
        RedisHandler.reset_instance()

    def test_shutdown_with_thread(self):
        """测试有关联线程时的关闭"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._running = True
        handler._worker_thread = MagicMock()
        handler._client = MagicMock()

        handler.shutdown()

        assert handler._running is False
        handler._worker_thread.join.assert_called_once_with(timeout=5)
        handler._client.close.assert_called_once()

    def test_shutdown_no_thread(self):
        """测试无关联线程时的关闭"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._running = True
        handler._worker_thread = None
        handler._client = None

        handler.shutdown()  # 应该不抛出异常

        assert handler._running is False

    def test_shutdown_no_client(self):
        """测试无 client 时的关闭"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True})
        handler._running = True
        handler._worker_thread = MagicMock()
        handler._client = None

        handler.shutdown()  # 应该不抛出异常

        assert handler._running is False
        handler._worker_thread.join.assert_called_once_with(timeout=5)
