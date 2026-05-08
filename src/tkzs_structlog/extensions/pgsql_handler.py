"""tkzs-structlog PGSQL 输出处理器

C2: PGSQL 日志输出，支持连接池、异步队列、批量写入。
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from datetime import datetime
from typing import Any

from tkzs_structlog.config.env_loader import get_pgsql_config, is_pgsql_available
from tkzs_structlog.exceptions import StructlogHandlerError

logger = logging.getLogger(__name__)

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_table_name(table_name: str) -> str:
    if not TABLE_NAME_PATTERN.match(table_name):
        raise StructlogHandlerError(
            handler_name="pgsql",
            reason=f"Invalid table name: '{table_name}'. Table names must start with a letter or underscore and contain only letters, numbers, and underscores.",
            fix_suggestion="Use a valid table name (e.g., 'structlog_logs', 'app_logs')",
        )
    return table_name


class PGSQLHandler:
    """PGSQL 日志处理器

    特性：
    - 连接池管理
    - 异步队列缓冲
    - 批量写入
    - 自动降级
    """

    _instance: PGSQLHandler | None = None
    _lock = threading.Lock()

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._pool = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=10000)
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.time()
        self._table_created = False

    @classmethod
    def get_instance(cls, config: dict[str, Any] | None = None) -> PGSQLHandler:
        """获取单例实例

        Args:
            config: PGSQL 配置，仅首次调用时需要

        Returns:
            PGSQLHandler 实例

        Raises:
            StructlogHandlerError: 未初始化时调用
        """
        with cls._lock:
            if cls._instance is None:
                if config is None:
                    raise StructlogHandlerError(
                        handler_name="pgsql",
                        reason="PGSQL handler not initialized",
                        fix_suggestion="Call setup_pgsql_handler first",
                    )
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None

    def initialize(self) -> None:
        """初始化连接池和工作线程

        Raises:
            StructlogHandlerError: 依赖缺失或连接失败
        """
        if not self.config.get("enable", False):
            return

        if not is_pgsql_available():
            raise StructlogHandlerError(
                handler_name="pgsql",
                reason="psycopg2-binary not installed",
                fix_suggestion="pip install psycopg2-binary or install with tkzs-structlog[ecosystem]",
            )

        try:
            from psycopg2 import pool  # type: ignore[import-untyped]

            env_config = get_pgsql_config()
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.get("pool_size", 5),
                host=env_config["host"],
                port=env_config["port"],
                user=env_config["user"],
                password=env_config["password"],
                database=env_config["db"],
            )

            self._test_connection()
            self._create_table()
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker, daemon=True
            )
            self._worker_thread.start()
            logger.info("PGSQL handler initialized successfully")

        except Exception as e:
            raise StructlogHandlerError(
                handler_name="pgsql",
                reason=f"Failed to initialize PGSQL handler: {str(e)}",
                fix_suggestion="Check PGSQL connection settings in .env file",
            )

    def _test_connection(self) -> None:
        """测试连接是否可用"""
        conn = self._pool.getconn()  # type: ignore[attr-defined]
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()
            self._pool.putconn(conn)  # type: ignore[attr-defined]

    def _create_table(self) -> None:
        """创建默认日志表"""
        if self._table_created:
            return

        conn = self._pool.getconn()  # type: ignore[attr-defined]
        try:
            cursor = conn.cursor()
            table_name = _validate_table_name(self.config.get("table_name", "structlog_logs"))
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    log_time TIMESTAMP NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    logger VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    extra JSONB
                )
            """
            )
            conn.commit()
            self._table_created = True
            logger.debug(f"Table {table_name} created or already exists")
        except Exception as e:
            logger.warning(f"Failed to create table: {e}")
            conn.rollback()
        finally:
            cursor.close()
            self._pool.putconn(conn)  # type: ignore[attr-defined]

    def _worker(self) -> None:
        """工作线程：批量写入日志"""
        while self._running:
            try:
                timeout = self.config.get("flush_interval", 5)
                log_entry = self._queue.get(timeout=timeout)
                self._batch.append(log_entry)

                batch_size = self.config.get("batch_size", 100)
                if len(self._batch) >= batch_size or (
                    time.time() - self._last_flush > timeout
                ):
                    self._flush_batch()

            except queue.Empty:
                if self._batch:
                    self._flush_batch()
            except Exception:
                pass

    def _flush_batch(self) -> None:
        """批量写入数据库"""
        if not self._batch:
            return

        if self._pool is None:
            return

        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            table_name = _validate_table_name(self.config.get("table_name", "structlog_logs"))

            for entry in self._batch:
                cursor.execute(
                    f"INSERT INTO {table_name} (log_time, level, logger, message, extra) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        entry.get("log_time", datetime.now()),
                        entry.get("level", "INFO"),
                        entry.get("logger", "structlog"),
                        entry.get("message", ""),
                        entry.get("extra", {}),
                    ),
                )

            conn.commit()
            batch_size = len(self._batch)
            self._batch.clear()
            self._last_flush = time.time()
            logger.debug(f"Flushed {batch_size} log entries to PGSQL")
        except Exception as e:
            logger.error(f"Failed to flush batch to PGSQL: {e}")
            conn.rollback()
        finally:
            cursor.close()
            self._pool.putconn(conn)

    def emit(self, log_entry: dict[str, Any]) -> None:
        """写入日志到队列

        Args:
            log_entry: 日志条目
        """
        if not self._running:
            return
        try:
            self._queue.put_nowait(log_entry)
        except queue.Full:
            logger.warning("PGSQL queue full, dropping log entry")

    def shutdown(self) -> None:
        """关闭处理器"""
        self._running = False
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5)
        if self._pool is not None:
            self._pool.closeall()
        logger.info("PGSQL handler shutdown")


def setup_pgsql_handler(config: dict[str, Any]) -> PGSQLHandler | None:
    """设置 PGSQL 处理器

    Args:
        config: PGSQL 配置

    Returns:
        PGSQLHandler 实例或 None（未启用时）
    """
    if not config.get("enable", False):
        return None

    handler = PGSQLHandler.get_instance(config)
    handler.initialize()
    return handler
