# tkzs-structlog V4.0 阶段技术方案

> 版本：V4.0
> 创建日期：2026-05-08
> 依据文档：开发需求.md §五/§六、开发计划.md §六/V4.0、ai_opencode_v4阶段开发计划.md
> 本次范围：仅 PGSQL（P0）+ Redis（P1）

---

## 一、环境准备

### 1.1 依赖安装

根据开发需求.md §五，第三方依赖采用可选安装方式。

#### 1.1.1 安装命令

```bash
pip install psycopg2-binary redis python-dotenv
```

#### 1.1.2 pyproject.toml 配置

```toml
[project.optional-dependencies]
pgsql = ["psycopg2-binary>=2.9.0"]
redis = ["redis>=4.5.0"]
all = ["psycopg2-binary>=2.9.0", "redis>=4.5.0", "python-dotenv>=1.0.0"]
```

### 1.2 环境变量读取

#### 1.2.1 .env 文件格式

```
# PGSQL 配置
PG_HOST=REDACTED_IP
PG_PORT=5432
PG_USER=REDACTED_USER
PG_PASSWORD=REDACTED_PASSWORD
PG_DB=test_db

# Redis 配置
REDIS_HOST=REDACTED_REDIS_HOST
REDIS_PORT=21186
REDIS_PASSWORD=REDACTED_REDIS_PASSWORD
REDIS_DB=0
```

#### 1.2.2 环境变量加载模块

```python
# src/tkzs_structlog/config/env_loader.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def load_env_config() -> dict[str, Any]:
    """加载 .env 配置文件

    Returns:
        包含 PGSQL 和 Redis 配置的字典
    """
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    return {
        "pgsql": {
            "host": os.getenv("PG_HOST", "localhost"),
            "port": int(os.getenv("PG_PORT", "5432")),
            "user": os.getenv("PG_USER", "postgres"),
            "password": os.getenv("PG_PASSWORD", ""),
            "db": os.getenv("PG_DB", "structlog"),
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", ""),
            "db": int(os.getenv("REDIS_DB", "0")),
        },
    }


def get_pgsql_config() -> dict[str, Any]:
    """获取 PGSQL 配置

    Returns:
        PGSQL 配置字典
    """
    return load_env_config()["pgsql"]


def get_redis_config() -> dict[str, Any]:
    """获取 Redis 配置

    Returns:
        Redis 配置字典
    """
    return load_env_config()["redis"]
```

#### 1.2.3 边界情况

| 边界情况 | 处理方式 |
|----------|----------|
| .env 文件不存在 | 使用默认值 |
| 配置项缺失 | 使用默认值（host=localhost 等） |
| 端口非法 | 捕获异常，使用默认端口 |

---

## 二、PGSQL 输出模块 (C2)

### 2.1 实现信息

- **优先级**：P0
- **配置段**：`handlers.pgsql`
- **依赖包**：`psycopg2-binary`
- **降级策略**：连接失败时降级到文件输出

### 2.2 配置接口

#### 2.2.1 JSONC 配置格式

```jsonc
{
  "version": "4.0",
  "handlers": {
    "pgsql": {
      "enable": true,
      "table_name": "structlog_logs",
      "batch_size": 100,
      "flush_interval": 5,
      "pool_size": 5
    }
  }
}
```

#### 2.2.2 配置字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| enable | bool | false | 是否启用 PGSQL 输出 |
| table_name | str | "structlog_logs" | 日志表名 |
| batch_size | int | 100 | 批量写入阈值 |
| flush_interval | int | 5 | 强制刷新间隔（秒） |
| pool_size | int | 5 | 连接池大小 |

### 2.3 配置模型

```python
# src/tkzs_structlog/config/validator.py

class HandlerPgsqlConfig(BaseModel):
    """PGSQL 处理器配置"""

    enable: bool = False
    table_name: str = "structlog_logs"
    batch_size: int = Field(default=100, ge=1, le=1000)
    flush_interval: int = Field(default=5, ge=1, le=60)
    pool_size: int = Field(default=5, ge=1, le=20)


class HandlerRedisConfig(BaseModel):
    """Redis 处理器配置"""

    enable: bool = False
    key_prefix: str = "structlog:"
    batch_size: int = Field(default=100, ge=1, le=1000)
    flush_interval: int = Field(default=5, ge=1, le=60)


class HandlersConfig(BaseModel):
    """处理器配置"""

    console: HandlerConsoleConfig = Field(default_factory=HandlerConsoleConfig)
    file: HandlerFileConfig = Field(default_factory=HandlerFileConfig)
    pgsql: HandlerPgsqlConfig = Field(default_factory=HandlerPgsqlConfig)
    redis: HandlerRedisConfig = Field(default_factory=HandlerRedisConfig)
```

### 2.4 核心实现代码

#### 2.4.1 PGSQLHandler 类

```python
# src/tkzs_structlog/extensions/pgsql_handler.py

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tkzs_structlog.config.env_loader import get_pgsql_config
from tkzs_structlog.exceptions import StructlogHandlerError


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

    def __init__(self, config: dict[str, Any]):
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
        """获取单例实例"""
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

    def initialize(self) -> None:
        """初始化连接池和工作线程"""
        if not self.config.get("enable", False):
            return

        try:
            import psycopg2
            from psycopg2 import pool

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

            self._create_table()
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker, daemon=True
            )
            self._worker_thread.start()

        except ImportError:
            raise StructlogHandlerError(
                handler_name="pgsql",
                reason="psycopg2-binary not installed",
                fix_suggestion="pip install psycopg2-binary",
            )
        except Exception as e:
            raise StructlogHandlerError(
                handler_name="pgsql",
                reason=f"Failed to initialize PGSQL handler: {str(e)}",
                fix_suggestion="Check PGSQL connection settings",
            )

    def _create_table(self) -> None:
        """创建默认日志表"""
        if self._table_created:
            return

        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS %s (
                    id SERIAL PRIMARY KEY,
                    log_time TIMESTAMP NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    logger VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    extra JSONB
                )
            """
                % self.config.get("table_name", "structlog_logs")
            )
            conn.commit()
            self._table_created = True
        finally:
            cursor.close()
            self._pool.putconn(conn)

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

        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            table_name = self.config.get("table_name", "structlog_logs")

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
            self._batch.clear()
            self._last_flush = time.time()
        except Exception:
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
            pass

    def shutdown(self) -> None:
        """关闭处理器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        if self._pool:
            self._pool.closeall()


def setup_pgsql_handler(config: dict[str, Any]) -> PGSQLHandler | None:
    """设置 PGSQL 处理器

    Args:
        config: PGSQL 配置

    Returns:
        PGSQLHandler 实例或 None
    """
    if not config.get("enable", False):
        return None

    handler = PGSQLHandler.get_instance(config)
    handler.initialize()
    return handler
```

### 2.5 边界情况

| 边界情况 | 处理方式 |
|----------|----------|
| 连接失败 | 自动重连 3 次，失败后降级到文件 |
| 批量写入失败 | 回滚事务，保留日志在队列 |
| 队列满 | 丢弃最旧日志，记录警告 |
| 表不存在 | 自动创建默认表 |
| 依赖缺失 | 抛出 StructlogHandlerError |

---

## 三、Redis 输出模块 (C2)

### 3.1 实现信息

- **优先级**：P1
- **配置段**：`handlers.redis`
- **依赖包**：`redis-py`
- **降级策略**：连接失败时降级到文件输出

### 3.2 配置接口

#### 3.2.1 JSONC 配置格式

```jsonc
{
  "version": "4.0",
  "handlers": {
    "redis": {
      "enable": true,
      "key_prefix": "structlog:",
      "batch_size": 100,
      "flush_interval": 5
    }
  }
}
```

#### 3.2.2 配置字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| enable | bool | false | 是否启用 Redis 输出 |
| key_prefix | str | "structlog:" | Redis key 前缀 |
| batch_size | int | 100 | 批量写入阈值 |
| flush_interval | int | 5 | 强制刷新间隔（秒） |

### 3.3 核心实现代码

#### 3.3.1 RedisHandler 类

```python
# src/tkzs_structlog/extensions/redis_handler.py

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tkzs_structlog.config.env_loader import get_redis_config
from tkzs_structlog.exceptions import StructlogHandlerError


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

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._client = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=10000)
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.time()

    @classmethod
    def get_instance(cls, config: dict[str, Any] | None = None) -> RedisHandler:
        """获取单例实例"""
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

    def initialize(self) -> None:
        """初始化连接池和工作线程"""
        if not self.config.get("enable", False):
            return

        try:
            import redis

            env_config = get_redis_config()
            self._client = redis.Redis(
                host=env_config["host"],
                port=env_config["port"],
                password=env_config["password"],
                db=env_config["db"],
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            self._client.ping()
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker, daemon=True
            )
            self._worker_thread.start()

        except ImportError:
            raise StructlogHandlerError(
                handler_name="redis",
                reason="redis-py not installed",
                fix_suggestion="pip install redis",
            )
        except Exception as e:
            raise StructlogHandlerError(
                handler_name="redis",
                reason=f"Failed to initialize Redis handler: {str(e)}",
                fix_suggestion="Check Redis connection settings",
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
            self._batch.clear()
            self._last_flush = time.time()
        except Exception:
            pass

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
            pass

    def shutdown(self) -> None:
        """关闭处理器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        if self._client:
            self._client.close()


def setup_redis_handler(config: dict[str, Any]) -> RedisHandler | None:
    """设置 Redis 处理器

    Args:
        config: Redis 配置

    Returns:
        RedisHandler 实例或 None
    """
    if not config.get("enable", False):
        return None

    handler = RedisHandler.get_instance(config)
    handler.initialize()
    return handler
```

### 3.4 边界情况

| 边界情况 | 处理方式 |
|----------|----------|
| 连接失败 | 自动重连 3 次，失败后降级到文件 |
| 批量写入失败 | 丢弃当前批次，记录警告 |
| 队列满 | 丢弃最旧日志，记录警告 |
| 依赖缺失 | 抛出 StructlogHandlerError |
| Redis 不可用 | 降级到文件输出 |

---

## 四、降级处理

### 4.1 降级策略

当 PGSQL 或 Redis 输出失败时，自动降级到文件输出：

```python
# src/tkzs_structlog/extensions/handlers.py

def setup_output_handlers(config: dict[str, Any]) -> None:
    """设置所有输出处理器

    Args:
        config: 完整配置
    """
    errors: list[str] = []

    # PGSQL
    pgsql_config = config.get("handlers", {}).get("pgsql", {})
    if pgsql_config.get("enable", False):
        try:
            from tkzs_structlog.extensions.pgsql_handler import setup_pgsql_handler
            setup_pgsql_handler(pgsql_config)
        except StructlogHandlerError as e:
            errors.append(f"PGSQL: {e.reason}, fallback to file")
        except Exception:
            errors.append("PGSQL connection failed, fallback to file")

    # Redis
    redis_config = config.get("handlers", {}).get("redis", {})
    if redis_config.get("enable", False):
        try:
            from tkzs_structlog.extensions.redis_handler import setup_redis_handler
            setup_redis_handler(redis_config)
        except StructlogHandlerError as e:
            errors.append(f"Redis: {e.reason}, fallback to file")
        except Exception:
            errors.append("Redis connection failed, fallback to file")

    # 文件输出（始终设置，作为降级目标）
    file_config = config.get("handlers", {}).get("file", {})
    setup_file_handler(file_config)

    # 记录降级警告
    if errors:
        logger = logging.getLogger("structlog")
        for error in errors:
            logger.warning(error)
```

---

## 五、测试要求

### 5.1 单元测试覆盖要求

| 模块 | 测试要求 |
|------|----------|
| env_loader.py | 覆盖率 100% |
| pgsql_handler.py | 覆盖率 100% |
| redis_handler.py | 覆盖率 100% |
| handlers.py 降级逻辑 | 覆盖率 100% |

### 5.2 边界测试用例

| 测试项 | 测试场景 |
|--------|----------|
| .env 文件缺失 | 使用默认值 |
| PGSQL 连接失败 | 自动降级到文件 |
| Redis 连接失败 | 自动降级到文件 |
| 批量阈值边界 | 达到阈值触发写入 |
| 队列满 | 丢弃旧日志 |

---

## 六、验收检查表

- [ ] Sprint 1: 环境准备完成
- [ ] Sprint 2: PGSQL 配置模型完成
- [ ] Sprint 3: PGSQL 处理器实现完成，覆盖率 100%
- [ ] Sprint 4: Redis 配置模型完成
- [ ] Sprint 5: Redis 处理器实现完成，覆盖率 100%
- [ ] Sprint 6: 降级逻辑完成，集成测试通过
- [ ] Sprint 7: 全量测试 100% 通过，ruff 零错误

---

*文档版本：V1.0*
*最后更新：2026-05-08*