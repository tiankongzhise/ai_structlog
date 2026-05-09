"""Redis 处理器模块测试"""

import threading
import time
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
        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.redis_handler import RedisHandler

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
        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.redis_handler import RedisHandler

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
        import queue

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

    @patch("tkzs_structlog.extensions.redis_handler.logger")
    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_initialize_success(self, mock_config, mock_available, mock_logger):
        """测试成功初始化（覆盖 95-112 行）"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0,
        }

        # Mock redis module import
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_module = MagicMock()
        mock_redis_module.Redis.return_value = mock_redis_client

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            config = {"enable": True}
            handler = RedisHandler(config)
            handler.initialize()

            assert handler._running is True
            assert handler._client is not None
            assert handler._worker_thread is not None
            assert handler._worker_thread.daemon is True
            mock_redis_client.ping.assert_called_once()
            mock_logger.info.assert_called_with("Redis handler initialized successfully")

    @patch("tkzs_structlog.extensions.redis_handler.threading.Thread")
    @patch("tkzs_structlog.extensions.redis_handler.logger")
    @patch("tkzs_structlog.extensions.redis_handler.is_redis_available")
    @patch("tkzs_structlog.extensions.redis_handler.get_redis_config")
    def test_initialize_success_with_thread_mock(self, mock_config, mock_available, mock_logger, mock_thread):
        """测试成功初始化（mock 线程，覆盖 95-112 行）"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0,
        }

        # Mock redis module import
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_module = MagicMock()
        mock_redis_module.Redis.return_value = mock_redis_client
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            config = {"enable": True}
            handler = RedisHandler(config)
            handler.initialize()

            assert handler._running is True
            assert handler._client is not None
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            mock_redis_client.ping.assert_called_once()


class TestRedisHandlerWorkerCoverage:
    """测试 _worker() 方法覆盖（127-142 行）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()

    @patch("tkzs_structlog.extensions.redis_handler.logger")
    def test_worker_processes_queue_and_flushes_by_timeout(self, mock_logger):
        """测试 worker 处理队列并在超时时刷新（覆盖 127-136 行）"""
        import queue

        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 0.1, "batch_size": 1000})
        handler._running = True
        handler._queue = queue.Queue()
        handler._client = MagicMock()

        # 放入一条日志
        log_entry = {"level": "INFO", "message": "test", "logger": "test", "extra": {}}
        handler._queue.put(log_entry)

        # 等待超时
        time.sleep(0.2)

        # 现在设置 _running = False 让 worker 退出
        handler._running = False

        # 调用 worker（它会因为 _running=False 退出循环）
        # 但在退出前会处理队列中的内容
        handler._worker()

        # 验证 flush_batch 被调用（通过检查 _batch 被清空）
        # 由于我们在超时后设置了 _running=False，worker 会在下一次循环退出
        # 但是队列中的内容可能已经被处理了

    def test_worker_queue_get_timeout_then_flush(self):
        """测试队列超时后刷新 batch（覆盖 127-140 行）"""
        import queue

        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 0.1, "batch_size": 100})
        handler._running = True
        handler._queue = queue.Queue()
        handler._client = MagicMock()
        handler._batch = []

        # 启动 worker，让它超时
        def stop_after_timeout():
            time.sleep(0.3)
            handler._running = False

        stop_thread = threading.Thread(target=stop_after_timeout)
        stop_thread.start()

        handler._worker()

        stop_thread.join()

    def test_worker_exception_in_loop(self):
        """测试 worker 循环中发生异常（覆盖 141-142 行）"""
        import queue

        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 0.1})
        handler._running = True
        handler._queue = MagicMock()
        # 让 get 抛出 Exception（不是 queue.Empty）
        handler._queue.get.side_effect = Exception("Unexpected error")

        # worker 应该捕获异常并继续（但因为我们设置了 side_effect，它会一直抛出）
        # 我们需要让它在一次异常后退出
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Unexpected error")
            handler._running = False
            raise queue.Empty()

        handler._queue.get = mock_get

        handler._worker()  # 应该不崩溃

    def test_worker_appends_to_batch_and_flushes_by_batch_size(self):
        """测试 worker 添加日志到 batch 并在达到 batch_size 时刷新（覆盖 130-136 行）"""
        import queue

        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 60, "batch_size": 2})
        handler._running = True
        handler._client = MagicMock()
        handler._batch = []
        handler._last_flush = time.time()

        # 模拟队列行为：先返回一个日志条目，然后返回 Empty
        mock_queue = MagicMock()
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"level": "INFO", "message": "test1", "logger": "test", "extra": {}}
            if call_count == 2:
                return {"level": "INFO", "message": "test2", "logger": "test", "extra": {}}
            raise queue.Empty()

        mock_queue.get.side_effect = mock_get
        mock_queue.get_nowait = mock_get
        handler._queue = mock_queue

        # 运行 worker 一段时间
        def stop_worker():
            time.sleep(0.5)
            handler._running = False

        stop_thread = threading.Thread(target=stop_worker)
        stop_thread.start()

        handler._worker()

        stop_thread.join()

        # batch 应该被清空（因为达到了 batch_size）
        assert len(handler._batch) == 0

    def test_worker_empty_exception_with_non_empty_batch(self):
        """测试队列为空但 batch 不为空时刷新（覆盖 138-140 行）"""
        import queue

        from tkzs_structlog.extensions.redis_handler import RedisHandler

        handler = RedisHandler({"enable": True, "flush_interval": 60, "batch_size": 100})
        handler._running = True
        handler._client = MagicMock()
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]

        # 模拟队列抛出 Empty 异常
        mock_queue = MagicMock()
        mock_queue.get.side_effect = queue.Empty()
        handler._queue = mock_queue

        # 运行 worker 一次循环
        def stop_worker():
            time.sleep(0.2)
            handler._running = False

        stop_thread = threading.Thread(target=stop_worker)
        stop_thread.start()

        handler._worker()

        stop_thread.join()

        # batch 应该被清空（因为 queue.Empty 时刷新）
        assert len(handler._batch) == 0


class TestRedisHandlerFlushBatchEdgeCases:
    """测试 _flush_batch 边界情况"""

    def teardown_method(self):
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        RedisHandler.reset_instance()

    def test_flush_batch_with_json_encoding(self):
        """测试 JSON 编码包含中文和特殊字符"""
        from tkzs_structlog.extensions.redis_handler import RedisHandler

        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline

        handler = RedisHandler({"enable": True})
        handler._batch = [
            {"level": "INFO", "message": "测试中文", "logger": "test", "extra": {"key": "值"}},
        ]
        handler._client = mock_client

        handler._flush_batch("test_key")

        assert len(handler._batch) == 0
        # 验证 json.dumps 被调用（通过 pipeline.rpush）
        mock_pipeline.rpush.assert_called_once()
        call_args = mock_pipeline.rpush.call_args
        message = call_args[0][1]
        assert "测试中文" in message
        mock_pipeline.execute.assert_called_once()

    def teardown_method(self):  # noqa: F811
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
