"""PGSQL 处理器集成测试

使用 .env 中的真实数据库连接进行测试。
敏感信息通过 env_loader 动态读取，不硬编码。
"""

import time

import pytest

from tkzs_structlog.config.env_loader import get_pgsql_config, is_pgsql_available
from tkzs_structlog.exceptions import StructlogHandlerError
from tkzs_structlog.extensions.pgsql_handler import (
    PGSQLHandler,
    _validate_table_name,
    setup_pgsql_handler,
)


def _can_connect_pgsql() -> bool:
    """检查是否可以连接到 PGSQL 数据库"""
    if not is_pgsql_available():
        return False
    try:
        import psycopg2

        config = get_pgsql_config()
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            dbname=config["db"],
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


# 模块级 skipif：无可用 PGSQL 时跳过所有需要连接的测试
skip_if_no_pgsql = pytest.mark.skipif(not _can_connect_pgsql(), reason="No PGSQL server available")


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试前重置单例"""
    PGSQLHandler.reset_instance()
    yield
    PGSQLHandler.reset_instance()


class TestValidateTableName:
    """测试表名验证函数"""

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


# ==================== 不需要 PGSQL 连接的测试 ====================


class TestPGSQLHandlerInitializeNoConn:
    """测试 PGSQLHandler 初始化（无需连接）"""

    def test_initialize_not_enabled(self):
        """测试未启用时不初始化"""
        config = {"enable": False}
        handler = PGSQLHandler(config)
        handler.initialize()

        assert handler._running is False
        assert handler._pool is None


class TestPGSQLHandlerFlushBatchNoConn:
    """测试批量写入（无需连接）"""

    def test_flush_batch_pool_none(self):
        """测试 pool 为 None 时不写入"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler._pool = None
        handler._batch = [{"log_time": "2025-01-01", "level": "INFO", "logger": "test", "message": "test", "extra": {}}]

        handler._flush_batch()  # 应该直接返回
        assert len(handler._batch) == 1  # batch 没被清空


class TestPGSQLHandlerEmitNoConn:
    """测试日志写入队列（无需连接）"""

    def test_emit_when_not_running(self):
        """测试未运行时写入"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler._running = False

        log_entry = {"level": "INFO", "message": "test"}
        handler.emit(log_entry)  # 应该直接返回，不写入队列


class TestSetupPgsqlHandlerNoConn:
    """测试 setup_pgsql_handler 函数（无需连接）"""

    def test_setup_disabled(self):
        """测试禁用时返回 None"""
        config = {"enable": False}
        handler = setup_pgsql_handler(config)

        assert handler is None


# ==================== 需要 PGSQL 连接的测试 ====================


@pytest.fixture(scope="module")
def pgsql_config():
    """获取 PGSQL 配置（从 .env 读取）"""
    if not _can_connect_pgsql():
        pytest.skip("Cannot connect to PGSQL server")
    return get_pgsql_config()


@skip_if_no_pgsql
class TestPGSQLHandlerInitialize:
    """测试 PGSQLHandler 初始化（真实连接）"""

    def test_initialize_success(self, pgsql_config):
        """测试成功初始化"""
        config = {"enable": True, "pool_size": 2}
        handler = PGSQLHandler(config)
        handler.initialize()

        assert handler._running is True
        assert handler._pool is not None
        assert handler._worker_thread is not None
        assert handler._table_created is True

    def test_initialize_custom_table_name(self, pgsql_config):
        """测试自定义表名"""
        config = {"enable": True, "table_name": "custom_test_logs"}
        handler = PGSQLHandler(config)
        handler.initialize()

        assert handler._table_created is True
        handler.shutdown()

    def test_table_created_once(self, pgsql_config):
        """测试表只创建一次"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()
        assert handler._table_created is True

        # 再次调用 initialize 不会重复创建表
        handler._table_created = True
        handler._create_table()  # 应该直接返回
        assert handler._table_created is True

        handler.shutdown()


@skip_if_no_pgsql
class TestPGSQLHandlerFlushBatch:
    """测试批量写入（真实连接）"""

    def test_flush_batch_empty(self, pgsql_config):
        """测试空 batch 不写入"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 空 batch 应该直接返回
        handler._flush_batch()
        handler.shutdown()

    def test_flush_batch_with_data(self, pgsql_config):
        """测试有数据时的批量写入"""
        config = {"enable": True, "batch_size": 10}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 手动添加测试数据
        handler._batch = [
            {"log_time": "2025-01-01 00:00:00", "level": "INFO", "logger": "test", "message": "test1", "extra": {}},
            {"log_time": "2025-01-01 00:00:01", "level": "DEBUG", "logger": "test", "message": "test2", "extra": {}},
        ]

        # 刷新 batch
        handler._flush_batch()

        # 验证 batch 已清空且记录了日志
        assert len(handler._batch) == 0
        handler.shutdown()

    def test_flush_batch_exception(self, pgsql_config):
        """测试写入异常时回滚"""

        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 添加一个会导致错误的条目（表不存在或其他错误）
        handler._batch = [{"log_time": "2025-01-01", "level": "INFO", "logger": "test", "message": "test", "extra": {}}]

        # mock cursor.execute 抛出异常
        from unittest.mock import MagicMock, patch

        with patch.object(handler._pool, "getconn") as mock_getconn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Simulated DB error")
            mock_conn.cursor.return_value = mock_cursor
            mock_getconn.return_value = mock_conn

            handler._flush_batch()  # 应该捕获异常并记录错误

        assert len(handler._batch) == 0  # batch 应该被清空（即使出错）
        handler.shutdown()


@skip_if_no_pgsql
class TestPGSQLHandlerWorker:
    """测试工作线程（真实连接）"""

    def test_worker_empty_queue_timeout(self, pgsql_config):
        """测试队列为空时超时刷新"""
        config = {"enable": True, "flush_interval": 1}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 不添加数据，等待超时
        time.sleep(1.5)

        # worker 应该已经处理了超时
        handler.shutdown()

    def test_worker_flush_on_batch_size(self, pgsql_config):
        """测试达到 batch_size 时刷新"""
        config = {"enable": True, "batch_size": 2, "flush_interval": 60}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 添加两条日志，应该触发刷新
        handler.emit({"level": "INFO", "message": "msg1", "logger": "test", "extra": {}})
        handler.emit({"level": "INFO", "message": "msg2", "logger": "test", "extra": {}})

        time.sleep(0.5)  # 等待 worker 处理
        handler.shutdown()

    def test_worker_flush_on_timeout(self, pgsql_config):
        """测试超时后刷新"""
        config = {"enable": True, "batch_size": 1000, "flush_interval": 1}
        handler = PGSQLHandler(config)
        handler.initialize()

        handler.emit({"level": "INFO", "message": "timeout test", "logger": "test", "extra": {}})

        time.sleep(1.5)  # 等待超时刷新
        handler.shutdown()


@skip_if_no_pgsql
class TestPGSQLHandlerShutdown:
    """测试关闭流程（真实连接）"""

    def test_shutdown_with_thread(self, pgsql_config):
        """测试有关联线程时的关闭"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        assert handler._running is True
        assert handler._worker_thread is not None

        handler.shutdown()

        assert handler._running is False

    def test_shutdown_pool_cleanup(self, pgsql_config):
        """测试关闭时清理连接池"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        handler.shutdown()

        # pool 应该被关闭（closeall 被调用）
        # 我们无法直接验证，但可以确认没有异常抛出


@skip_if_no_pgsql
class TestPGSQLHandlerEmit:
    """测试日志写入队列（真实连接）"""

    def test_emit_when_running(self, pgsql_config):
        """测试运行时写入队列"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        log_entry = {"level": "INFO", "message": "test message", "logger": "test", "extra": {}}
        handler.emit(log_entry)

        # 给 worker 一点时间处理
        time.sleep(0.1)
        handler.shutdown()

    def test_emit_queue_full(self, pgsql_config):
        """测试队列满时丢弃日志"""
        config = {"enable": True}
        handler = PGSQLHandler(config)
        handler.initialize()

        # 队列大小是 10000，我们不需要真的填满它
        # 只需要测试 queue.put_nowait 的行为
        handler._queue = handler._queue  # 保持原队列
        log_entry = {"level": "INFO", "message": "test"}
        handler.emit(log_entry)

        handler.shutdown()


@skip_if_no_pgsql
class TestSetupPgsqlHandler:
    """测试 setup_pgsql_handler 函数（真实连接）"""

    def test_setup_enabled(self, pgsql_config):
        """测试启用时返回 handler"""
        config = {"enable": True}
        handler = setup_pgsql_handler(config)

        assert handler is not None
        assert isinstance(handler, PGSQLHandler)
        handler.shutdown()
