"""tkzs-structlog 环境变量加载模块

从 .env 文件加载敏感配置信息。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

load_dotenv: Any = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_env_config() -> dict[str, Any]:
    """加载 .env 配置文件

    Returns:
        包含 PGSQL 和 Redis 配置的字典

    Example:
        .env 文件格式::

            PG_HOST=your_host
            PG_PORT=5432
            PG_USER=your_user
            PG_PASSWORD=your_password
            PG_DB=your_db

            REDIS_HOST=your_host
            REDIS_PORT=6379
            REDIS_PASSWORD=your_password
            REDIS_DB=0
    """
    if load_dotenv is not None:
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug(f"Loaded environment from {env_path}")
        else:
            logger.debug(".env file not found, using default values")
    else:
        logger.warning("python-dotenv not installed, using default values")

    return {
        "pgsql": {
            "host": os.getenv("PG_HOST", "localhost"),
            "port": _parse_port(os.getenv("PG_PORT", "5432")),
            "user": os.getenv("PG_USER", "postgres"),
            "password": os.getenv("PG_PASSWORD", ""),
            "db": os.getenv("PG_DB", "structlog"),
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": _parse_port(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", ""),
            "db": _parse_port(os.getenv("REDIS_DB", "0")),
        },
    }


def _parse_port(value: str) -> int:
    """解析端口号

    Args:
        value: 端口号字符串

    Returns:
        端口号整数，解析失败返回 0
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def get_pgsql_config() -> dict[str, Any]:
    """获取 PGSQL 配置

    Returns:
        PGSQL 配置字典
    """
    return load_env_config()["pgsql"]  # type: ignore[no-any-return]


def get_redis_config() -> dict[str, Any]:
    """获取 Redis 配置

    Returns:
        Redis 配置字典
    """
    return load_env_config()["redis"]  # type: ignore[no-any-return]


def is_pgsql_available() -> bool:
    """检查 PGSQL 依赖是否可用

    Returns:
        是否可用
    """
    try:
        import psycopg2  # type: ignore[import-untyped]  # noqa: F401

        return True
    except ImportError:
        return False


def is_redis_available() -> bool:
    """检查 Redis 依赖是否可用

    Returns:
        是否可用
    """
    try:
        import redis  # noqa: F401

        return True
    except ImportError:
        return False
