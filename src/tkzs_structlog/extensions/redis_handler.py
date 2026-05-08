"""tkzs-structlog Redis 输出处理器

C2: Redis 日志输出，支持连接池、异步队列、List 结构存储。
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from datetime import datetime
from typing import Any

from tkzs_structlog.config.env_loader import get_redis_config, is_redis_available
from tkzs_structlog.exceptions import StructlogHandlerError

logger = logging.getLogger(__name__)


class RedisHandler:
    """Redis 日志处理器

    特性：
    - 连接池管理
    - 异步队列缓冲
    - List 结构存储
    - 自动降级
    """

    _instance: RedisHandler | None = None
    _lock = threading.Lock()

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=10000)
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.time()

    @classmethod
    def get_instance(cls, config: dict[str, Any] | None = None) -> RedisHandler:
        """获取单例实例

        Args:
            config: Redis 配置，仅首次调用时需要

        Returns:
            RedisHandler 实例

        Raises:
            StructlogHandlerError: 未初始化时调用
        """
        with cls._lock:
            if cls._instance is None:
                if config is None:
                    raise StructlogHandlerError(
                        handler_name="redis",
                        reason="Redis handler not initialized",
                        fix_suggestion="Call setup_redis_handler first",
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

        if not is_redis_available():
            raise StructlogHandlerError(
                handler_name="redis",
                reason="redis-py not installed",
                fix_suggestion="pip install redis or install with tkzs-structlog[ecosystem]",
            )

        try:
            import redis  # type: ignore[import-not-found]

            env_config = get_redis_config()
            self._client = redis.Redis(
                host=env_config["host"],
                port=env_config["port"],
                password=env_config["password"] if env_config["password"] else None,
                db=env_config["db"],
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            self._client.ping()  # type: ignore[attr-defined]
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker, daemon=True
            )
            self._worker_thread.start()
            logger.info("Redis handler initialized successfully")

        except Exception as e:
            raise StructlogHandlerError(
                handler_name="redis",
                reason=f"Failed to initialize Redis handler: {str(e)}",
                fix_suggestion="Check Redis connection settings in .env file",
            )

    def _worker(self) -> None:
        """工作线程：批量写入日志"""
        key_prefix = self.config.get("key_prefix", "structlog:")
        key = f"{key_prefix}logs"

        while self._running:
            try:
                timeout = self.config.get("flush_interval", 5)
                log_entry = self._queue.get(timeout=timeout)
                self._batch.append(log_entry)

                batch_size = self.config.get("batch_size", 100)
                if len(self._batch) >= batch_size or (
                    time.time() - self._last_flush > timeout
                ):
                    self._flush_batch(key)

            except queue.Empty:
                if self._batch:
                    self._flush_batch(key)
            except Exception:
                pass

    def _flush_batch(self, key: str) -> None:
        """批量写入 Redis"""
        if not self._batch:
            return

        if self._client is None:
            return

        try:
            pipe = self._client.pipeline()
            for entry in self._batch:
                message = json.dumps(
                    {
                        "log_time": entry.get("log_time", datetime.now().isoformat()),
                        "level": entry.get("level", "INFO"),
                        "logger": entry.get("logger", "structlog"),
                        "message": entry.get("message", ""),
                        "extra": entry.get("extra", {}),
                    },
                    ensure_ascii=False,
                )
                pipe.rpush(key, message)

            pipe.execute()
            batch_size = len(self._batch)
            self._batch.clear()
            self._last_flush = time.time()
            logger.debug(f"Flushed {batch_size} log entries to Redis")
        except Exception as e:
            logger.error(f"Failed to flush batch to Redis: {e}")

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
            logger.warning("Redis queue full, dropping log entry")

    def shutdown(self) -> None:
        """关闭处理器"""
        self._running = False
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5)
        if self._client is not None:
            self._client.close()
        logger.info("Redis handler shutdown")


def setup_redis_handler(config: dict[str, Any]) -> RedisHandler | None:
    """设置 Redis 处理器

    Args:
        config: Redis 配置

    Returns:
        RedisHandler 实例或 None（未启用时）
    """
    if not config.get("enable", False):
        return None

    handler = RedisHandler.get_instance(config)
    handler.initialize()
    return handler
