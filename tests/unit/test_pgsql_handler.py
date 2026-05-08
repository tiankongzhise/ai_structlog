"""PGSQL 处理器模块测试（完整覆盖）"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from tkzs_structlog.exceptions import StructlogHandlerError
from tkzs_structlog.extensions.pgsql_handler import _validate_table_name


class TestPGSQLHandlerInit:
    """测试 PGSQLHandler 初始化"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        config = {"enable": True}
        handler = PGSQLHandler(config)

        assert handler.config == config
        assert handler._pool is None
        assert handler._running is False
        assert handler._batch == []

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        config = {
            "enable": True,
            "table_name": "custom_logs",
            "batch_size": 50,
            "flush_interval": 10,
            "pool_size": 3,
        }
        handler = PGSQLHandler(config)

        assert handler.config["table_name"] == "custom_logs"
        assert handler.config["batch_size"] == 50
        assert handler.config["flush_interval"] == 10
        assert handler.config["pool_size"] == 3


class TestPGSQLHandlerSingleton:
    """测试 PGSQLHandler 单例模式"""

    def test_get_instance_first_call(self):
        """测试首次获取实例"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": True}

        handler = PGSQLHandler.get_instance(config)

        assert handler is not None
        assert isinstance(handler, PGSQLHandler)

    def test_get_instance_subsequent_call(self):
        """测试后续获取实例"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": True}

        handler1 = PGSQLHandler.get_instance(config)
        handler2 = PGSQLHandler.get_instance()

        assert handler1 is handler2

    def test_get_instance_without_init(self):
        """测试未初始化时获取实例"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()

        with pytest.raises(Exception):
            PGSQLHandler.get_instance()

    def test_reset_instance(self):
        """测试重置实例"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": True}

        handler1 = PGSQLHandler.get_instance(config)
        PGSQLHandler.reset_instance()

        handler2 = PGSQLHandler.get_instance(config)
        assert handler1 is not handler2


class TestPGSQLHandlerInitialize:
    """测试 PGSQLHandler 初始化"""

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    @patch("tkzs_structlog.extensions.pgsql_handler.get_pgsql_config")
    def test_initialize_not_enabled(self, mock_config, mock_available):
        """测试未启用时不初始化"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": False}

        handler = PGSQLHandler(config)
        handler.initialize()

        mock_available.assert_not_called()

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    def test_initialize_psycopg2_not_available(self, mock_available):
        """测试依赖缺失时抛出异常"""
        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        mock_available.return_value = False
        config = {"enable": True}

        handler = PGSQLHandler(config)

        with pytest.raises(StructlogHandlerError) as exc_info:
            handler.initialize()

        assert "not installed" in str(exc_info.value.reason)

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    @patch("tkzs_structlog.extensions.pgsql_handler.get_pgsql_config")
    def test_initialize_connection_error(self, mock_config, mock_available):
        """测试连接失败时抛出异常"""
        from tkzs_structlog.exceptions import StructlogHandlerError
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "invalid_host",
            "port": 5432,
            "user": "test",
            "password": "test",
            "db": "test",
        }

        config = {"enable": True, "pool_size": 1}

        handler = PGSQLHandler(config)

        with pytest.raises(StructlogHandlerError):
            handler.initialize()


class TestPGSQLHandlerEmit:
    """测试 PGSQLHandler 日志写入"""

    def test_emit_not_running(self):
        """测试未运行时写入"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": False}

        handler = PGSQLHandler(config)

        log_entry = {"level": "INFO", "message": "test"}
        handler.emit(log_entry)

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    @patch("tkzs_structlog.extensions.pgsql_handler.get_pgsql_config")
    def test_emit_success(self, mock_config, mock_available):
        """测试成功写入"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 5432,
            "user": "test",
            "password": "test",
            "db": "test",
        }

        config = {"enable": True, "pool_size": 1}
        handler = PGSQLHandler(config)
        handler._running = True
        handler._queue = queue.Queue(maxsize=10000)

        log_entry = {"level": "INFO", "message": "test", "logger": "test"}
        handler.emit(log_entry)

        assert handler._queue.qsize() == 1


class TestPGSQLHandlerShutdown:
    """测试 PGSQLHandler 关闭"""

    def test_shutdown_not_started(self):
        """测试未启动时关闭"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        config = {"enable": False}

        handler = PGSQLHandler(config)
        handler.shutdown()

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    @patch("tkzs_structlog.extensions.pgsql_handler.get_pgsql_config")
    def test_shutdown_started(self, mock_config, mock_available):
        """测试正常关闭"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 5432,
            "user": "test",
            "password": "test",
            "db": "test",
        }

        config = {"enable": True, "pool_size": 1}
        handler = PGSQLHandler(config)
        handler._running = True

        handler.shutdown()

        assert handler._running is False


class TestSetupPgsqlHandler:
    """测试 setup_pgsql_handler 函数"""

    def test_setup_disabled(self):
        """测试禁用时返回 None"""
        from tkzs_structlog.extensions.pgsql_handler import setup_pgsql_handler

        config = {"enable": False}
        result = setup_pgsql_handler(config)

        assert result is None

    @patch("tkzs_structlog.extensions.pgsql_handler.PGSQLHandler")
    def test_setup_enabled(self, mock_handler_class):
        """测试启用时返回 handler"""
        from tkzs_structlog.extensions.pgsql_handler import setup_pgsql_handler

        mock_handler = MagicMock()
        mock_handler_class.get_instance.return_value = mock_handler

        config = {"enable": True}
        result = setup_pgsql_handler(config)

        assert result is mock_handler
        mock_handler.initialize.assert_called_once()


class TestValidateTableName:
    """测试表名验证（完整覆盖）"""

    def test_valid_table_name(self):
        """测试合法表名"""

        assert _validate_table_name("structlog_logs") == "structlog_logs"
        assert _validate_table_name("_test") == "_test"
        assert _validate_table_name("a1") == "a1"

    def test_invalid_table_name_starts_with_number(self):
        """测试以数字开头的表名"""

        with pytest.raises(StructlogHandlerError):
            _validate_table_name("123table")

    def test_invalid_table_name_special_chars(self):
        """测试包含特殊字符的表名"""

        with pytest.raises(StructlogHandlerError):
            _validate_table_name("table;DROP TABLE users")
        with pytest.raises(StructlogHandlerError):
            _validate_table_name("table name")
        with pytest.raises(StructlogHandlerError):
            _validate_table_name("table-name")


class TestPGSQLHandlerInitializePostPool:
    """测试 initialize() 中 pool 创建后的逻辑 (行 119-126)"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    @patch("tkzs_structlog.extensions.pgsql_handler.is_pgsql_available")
    @patch("tkzs_structlog.extensions.pgsql_handler.get_pgsql_config")
    @patch("tkzs_structlog.extensions.pgsql_handler.threading.Thread")
    def test_initialize_sets_running_and_starts_thread(self, mock_thread, mock_config, mock_available):
        """测试初始化后 _running=True 且启动了 daemon 线程"""
        from unittest.mock import MagicMock

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        PGSQLHandler.reset_instance()
        mock_available.return_value = True
        mock_config.return_value = {
            "host": "localhost",
            "port": 5432,
            "user": "test",
            "password": "test",
            "db": "test",
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool):
            with patch.object(PGSQLHandler, "_test_connection"):
                with patch.object(PGSQLHandler, "_create_table"):
                    config = {"enable": True, "pool_size": 1}
                    handler = PGSQLHandler(config)
                    handler.initialize()

                    assert handler._running is True
                    mock_thread.assert_called_once()
                    call_kwargs = mock_thread.call_args[1]
                    assert call_kwargs["daemon"] is True
                    assert call_kwargs["target"] == handler._worker


class TestPGSQLHandlerTestConnection:
    """测试连接测试（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_test_connection_success(self):
        """测试连接成功"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        handler._test_connection()  # 应该不抛出异常

        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()
        handler._pool.putconn.assert_called_once_with(mock_conn)

    def test_test_connection_exception(self):
        """测试连接异常"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Connection failed")
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        with pytest.raises(Exception):
            handler._test_connection()


class TestPGSQLHandlerCreateTable:
    """测试表创建（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_create_table_already_created(self):
        """测试表已创建时直接返回"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._table_created = True

        handler._create_table()  # 应该直接返回，不执行任何操作

        assert handler._table_created is True

    def test_create_table_success(self):
        """测试成功创建表"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        handler._create_table()

        assert handler._table_created is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        handler._pool.putconn.assert_called_once_with(mock_conn)

    def test_create_table_exception(self, caplog):
        """测试创建表异常"""
        import logging

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Table creation failed")
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        with caplog.at_level(logging.WARNING, logger="tkzs_structlog.extensions.pgsql_handler"):
            handler._create_table()

        assert handler._table_created is False
        mock_conn.rollback.assert_called_once()


class TestPGSQLHandlerWorker:
    """测试工作线程（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_worker_not_running(self):
        """测试 _running 为 False 时 worker 退出"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 0.1})
        handler._running = False

        handler._worker()

    def test_worker_exits_after_one_iteration(self):
        """测试 worker 在单次迭代后退出（通过设置 _running=False）"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 0.01, "batch_size": 1000})
        handler._running = True
        handler._queue = queue.Queue()
        handler._queue.put({"level": "INFO", "message": "test", "logger": "test", "extra": {}})

        handler._running = False
        handler._worker()

        assert handler._running is False

    def test_worker_empty_queue_exception_then_flushes(self):
        """测试 queue.Empty 时如果有 batch 则刷新 (行 191-193)"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 1})
        handler._running = True
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]

        raised_empty = False
        def raise_empty(*args, **kwargs):
            nonlocal raised_empty
            if raised_empty:
                handler._running = False
                raise queue.Empty()
            raised_empty = True
            raise queue.Empty()

        with patch.object(handler, "_queue") as mock_queue:
            mock_queue.get = raise_empty
            with patch.object(handler, "_flush_batch") as mock_flush:
                handler._worker()

                assert mock_flush.called

    def test_worker_unexpected_exception_swallowed(self):
        """测试 worker 捕获意外异常不中断循环 (行 194-195)"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 1})
        handler._running = True
        handler._batch = []

        raised_error = False
        def raise_error(*args, **kwargs):
            nonlocal raised_error
            if raised_error:
                handler._running = False
                raise queue.Empty()
            raised_error = True
            raise RuntimeError("Unexpected")

        with patch.object(handler, "_queue") as mock_queue:
            mock_queue.get = raise_error
            with patch.object(handler, "_flush_batch"):
                handler._worker()

        assert handler._running is False

    def test_worker_batch_full_triggers_flush(self):
        """测试 batch 达到 batch_size 时调用 _flush_batch (行 185-189)"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 60, "batch_size": 2})
        handler._running = True
        handler._batch = []

        call_count = 0
        def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"level": "INFO", "message": "test1", "logger": "test", "extra": {}}
            elif call_count == 2:
                return {"level": "INFO", "message": "test2", "logger": "test", "extra": {}}
            else:
                handler._running = False
                raise queue.Empty()

        with patch.object(handler, "_queue") as mock_queue:
            mock_queue.get = get_side_effect
            with patch.object(handler, "_flush_batch") as mock_flush:
                handler._worker()

                assert mock_flush.call_count >= 1
                flush_calls = [c for c in mock_flush.call_args_list if c]
                assert len(flush_calls) >= 1

    def test_worker_timeout_flush_triggers_flush(self):
        """测试超时后调用 _flush_batch (行 187-189)"""
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True, "flush_interval": 60, "batch_size": 100})
        handler._running = True
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]
        handler._last_flush = time.time() - 100

        def get_side_effect(*args, **kwargs):
            handler._running = False
            raise queue.Empty()

        with patch.object(handler, "_queue") as mock_queue:
            mock_queue.get = get_side_effect
            with patch.object(handler, "_flush_batch") as mock_flush:
                handler._worker()

                assert mock_flush.called


class TestPGSQLHandlerFlushBatch:
    """测试批量写入（使用 mock）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_flush_batch_empty(self):
        """测试空 batch 不写入"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._batch = []
        handler._pool = None

        handler._flush_batch()  # 应该直接返回

        assert len(handler._batch) == 0

    def test_flush_batch_pool_none(self):
        """测试 pool 为 None 时不写入"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]
        handler._pool = None

        handler._flush_batch()  # 应该直接返回

        assert len(handler._batch) == 1  # batch 没被清空

    def test_flush_batch_success(self):
        """测试成功写入"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._batch = [
            {"log_time": "2025-01-01 00:00:00", "level": "INFO", "logger": "test", "message": "test1", "extra": {}},
        ]
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        handler._flush_batch()

        assert len(handler._batch) == 0
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        handler._pool.putconn.assert_called_once_with(mock_conn)

    def test_flush_batch_exception(self, caplog):
        """测试写入异常"""
        import logging

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Insert failed")
        mock_conn.cursor.return_value = mock_cursor

        handler = PGSQLHandler({"enable": True})
        handler._batch = [{"level": "INFO", "message": "test", "logger": "test", "extra": {}}]
        handler._pool = MagicMock()
        handler._pool.getconn.return_value = mock_conn

        with caplog.at_level(logging.ERROR, logger="tkzs_structlog.extensions.pgsql_handler"):
            handler._flush_batch()

        assert len(handler._batch) == 0  # batch 应该被清空（即使出错）
        mock_conn.rollback.assert_called_once()


class TestPGSQLHandlerEmitEdgeCases:
    """测试日志写入队列（边界情况）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_emit_queue_full(self, caplog):
        """测试队列满时丢弃日志"""
        import logging
        import queue

        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._running = True
        handler._queue = MagicMock()
        handler._queue.put_nowait.side_effect = queue.Full("Queue full")

        with caplog.at_level(logging.WARNING, logger="tkzs_structlog.extensions.pgsql_handler"):
            log_entry = {"level": "INFO", "message": "test"}
            handler.emit(log_entry)

        assert "queue full" in caplog.text.lower()


class TestPGSQLHandlerShutdownEdgeCases:
    """测试关闭流程（边界情况）"""

    def teardown_method(self):
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        PGSQLHandler.reset_instance()

    def test_shutdown_with_thread(self):
        """测试有关联线程时的关闭"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._running = True
        handler._worker_thread = MagicMock()
        handler._pool = MagicMock()

        handler.shutdown()

        assert handler._running is False
        handler._worker_thread.join.assert_called_once_with(timeout=5)
        handler._pool.closeall.assert_called_once()

    def test_shutdown_no_thread(self):
        """测试无关联线程时的关闭"""
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler

        handler = PGSQLHandler({"enable": True})
        handler._running = True
        handler._worker_thread = None
        handler._pool = None

        handler.shutdown()  # 应该不抛出异常

        assert handler._running is False
