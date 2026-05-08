"""PGSQL 处理器模块测试"""

from unittest.mock import MagicMock, patch

import pytest


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
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        from tkzs_structlog.exceptions import StructlogHandlerError

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
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        from tkzs_structlog.exceptions import StructlogHandlerError

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
        from tkzs_structlog.extensions.pgsql_handler import PGSQLHandler
        import queue

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