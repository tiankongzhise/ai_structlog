"""tkzs-structlog 文件轮转模块

C2: 自定义复合轮转处理器，支持日期+大小轮转、压缩、清理。
"""

from __future__ import annotations

import concurrent.futures
import gzip
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

# ==================== 压缩后端抽象 ====================


class CompressBackend(ABC):
    """压缩后端抽象类"""

    @abstractmethod
    def compress(self, src_path: Path, dst_path: Path) -> bool:
        """压缩文件

        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径

        Returns:
            是否成功
        """
        ...  # pragma: no cover

    @property
    @abstractmethod
    def extension(self) -> str:
        """压缩文件扩展名"""
        ...  # pragma: no cover


class GzipBackend(CompressBackend):
    """Gzip 压缩后端"""

    @property
    def extension(self) -> str:
        return ".gz"

    def compress(self, src_path: Path, dst_path: Path) -> bool:
        """Gzip 压缩"""
        try:
            with open(src_path, "rb") as f_in, gzip.open(dst_path, "wb") as f_out:
                f_out.writelines(f_in)
            return True
        except Exception:
            return False


class Lz4Backend(CompressBackend):
    """Lz4 压缩后端"""

    @property
    def extension(self) -> str:
        return ".lz4"

    def compress(self, src_path: Path, dst_path: Path) -> bool:
        """Lz4 压缩"""
        try:
            import lz4.frame

            with open(src_path, "rb") as f_in, lz4.frame.open(dst_path, "wb") as f_out:
                f_out.write(f_in.read())
            return True
        except ImportError:
            return False
        except Exception:
            return False


class ZstdBackend(CompressBackend):
    """Zstd 压缩后端"""

    @property
    def extension(self) -> str:
        return ".zst"

    def compress(self, src_path: Path, dst_path: Path) -> bool:
        """Zstd 压缩"""
        try:
            import zstandard as zstd

            with open(src_path, "rb") as f_in, open(dst_path, "wb") as f_out:
                cctx = zstd.ZstdCompressor()
                cctx.copy_stream(f_in, f_out)
            return True
        except ImportError:
            return False
        except Exception:
            return False


def get_compress_backend(method: str) -> CompressBackend:
    """获取压缩后端

    Args:
        method: 压缩方法（gzip/lz4/zstd）

    Returns:
        压缩后端实例
    """
    backends: dict[str, type[CompressBackend]] = {
        "gzip": GzipBackend,
        "lz4": Lz4Backend,
        "zstd": ZstdBackend,
    }
    backend_cls = backends.get(method.lower(), GzipBackend)
    return backend_cls()


# ==================== 自定义轮转处理器 ====================


class CustomRotatingFileHandler:
    """自定义复合轮转文件处理器

    支持：
    - 大小轮转 (max_bytes)
    - 日期轮转 (rotate_when)
    - 自动压缩
    - 按数量/天数清理
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.file_path = Path(config["file_path"])
        self.encoding = config.get("encoding", "utf-8")

        rotate_config = config.get("custom_rotate", {})
        self.enable_rotate = rotate_config.get("enable", False)
        self.max_bytes = rotate_config.get("max_bytes", 10485760)
        self.backup_count = rotate_config.get("backup_count", 10)
        self.retain_days = rotate_config.get("retain_days", 7)
        self.rotate_when = rotate_config.get("rotate_when", "MIDNIGHT")
        self.interval = rotate_config.get("interval", 1)
        self.compress = rotate_config.get("compress", False)
        self.compress_method = rotate_config.get("compress_method", "gzip")
        self.compress_concurrency = rotate_config.get("compress_concurrency", 2)
        self.compress_async = rotate_config.get("compress_async", True)

        # 状态
        self._file_lock = threading.Lock()
        self._last_rotate_time: float = 0
        self._compress_backend = get_compress_backend(self.compress_method)

        # 异步压缩线程池
        self._compress_executor: concurrent.futures.ThreadPoolExecutor | None = None
        if self.compress_async and self.compress:
            self._compress_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.compress_concurrency,
                thread_name_prefix="log_compress",
            )

    def _should_rotate_by_size(self) -> bool:
        """检查是否应该按大小轮转"""
        if not self.enable_rotate or self.max_bytes <= 0:
            return False

        if not self.file_path.exists():
            return False

        return self.file_path.stat().st_size >= self.max_bytes

    def _should_rotate_by_time(self) -> bool:
        """检查是否应该按时间轮转"""
        if not self.enable_rotate:
            return False

        if self.rotate_when == "MIDNIGHT":
            # 每天零点轮转
            now = datetime.now()
            if now.hour == 0 and now.minute == 0:
                return True
            # 检查是否跨天
            if self._last_rotate_time > 0:
                last_time = datetime.fromtimestamp(self._last_rotate_time)
                if last_time.date() != now.date():
                    return True

        return False

    def rotate(self) -> None:
        """执行轮转"""
        with self._file_lock:
            if not self.file_path.exists():
                return

            # 生成轮转文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotate_path = self.file_path.with_name(f"{self.file_path.stem}.{timestamp}{self.file_path.suffix}")

            # 原子重命名（失败重试 3 次，仍失败则记录 ERROR 并跳过轮转以保证写入不中断）
            max_retries = 3
            replaced = False
            for attempt in range(max_retries):
                try:
                    os.replace(self.file_path, rotate_path)
                    self._last_rotate_time = time.time()
                    replaced = True
                    break
                except OSError as e:
                    if attempt == max_retries - 1:
                        logging.getLogger(__name__).error(
                            "Failed to rotate log file after %s attempts: %s",
                            max_retries,
                            e,
                        )
                        return
                    time.sleep(0.1 * (attempt + 1))

            if not replaced:  # pragma: no cover
                return

            # 执行压缩
            if self.compress:
                self._compress_file(rotate_path)

            # 执行清理
            self.cleanup()

    def _compress_file(self, file_path: Path) -> None:
        """压缩文件"""
        compress_ext = self._compress_backend.extension
        dst_path = file_path.with_suffix(file_path.suffix + compress_ext)

        if self.compress_async and self._compress_executor:
            try:
                self._compress_executor.submit(self._do_compress, file_path, dst_path)
            except RuntimeError:
                logging.getLogger(__name__).warning(
                    "Compress thread pool unavailable, falling back to synchronous compress for %s",
                    file_path,
                )
                self._do_compress(file_path, dst_path)
        else:
            self._do_compress(file_path, dst_path)

    def _do_compress(self, src_path: Path, dst_path: Path) -> None:
        """执行压缩"""
        try:
            success = self._compress_backend.compress(src_path, dst_path)
            if success:
                os.remove(src_path)
            # 压缩失败保留原文件
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Compress failed for %s -> %s: %s",
                src_path,
                dst_path,
                e,
                exc_info=True,
            )

    def cleanup(self) -> None:
        """清理旧日志文件"""
        if not self.file_path.parent.exists():
            return

        # 获取所有日志文件（包括压缩文件）
        pattern = f"{self.file_path.stem}.*"
        files: list[tuple[Path, float, int]] = []

        for f in self.file_path.parent.glob(pattern):
            if f.name == self.file_path.name:
                continue
            files.append((f, f.stat().st_mtime, int(f.stat().st_size)))

        # 按修改时间排序（从旧到新）
        files.sort(key=lambda x: x[1])

        # 按数量清理
        if self.backup_count > 0 and len(files) > self.backup_count:
            to_delete = files[: len(files) - self.backup_count]
            for f, _, _ in to_delete:
                try:
                    f.unlink()
                except OSError:
                    pass
            files = files[len(files) - self.backup_count :]

        # 按天数清理
        if self.retain_days > 0:
            now = time.time()
            cutoff = now - (self.retain_days * 86400)
            to_delete = [f for f, mtime, _ in files if mtime < cutoff]
            for f in to_delete:
                try:
                    f.unlink()
                except OSError:
                    pass

    def check_and_rotate(self) -> None:
        """检查并执行轮转"""
        if self._should_rotate_by_size() or self._should_rotate_by_time():
            self.rotate()

    def close(self) -> None:
        """关闭处理器"""
        if self._compress_executor:
            self._compress_executor.shutdown(wait=True)

    def __del__(self) -> None:
        """析构"""
        self.close()
