"""轮转模块测试"""

import gzip
import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCompressBackends:
    """测试压缩后端"""

    def test_gzip_backend_compress(self, tmp_path):
        """测试Gzip压缩"""
        from tkzs_structlog.extensions.rotation import GzipBackend

        backend = GzipBackend()

        # 创建测试文件
        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test log content" * 100)

        dst_file = tmp_path / "test.log.gz"

        result = backend.compress(src_file, dst_file)

        assert result is True
        assert dst_file.exists()
        assert dst_file.stat().st_size < src_file.stat().st_size

    def test_gzip_backend_extension(self):
        """测试Gzip扩展名"""
        from tkzs_structlog.extensions.rotation import GzipBackend

        backend = GzipBackend()
        assert backend.extension == ".gz"

    def test_gzip_backend_decompress_verify(self, tmp_path):
        """测试Gzip压缩后内容正确"""
        from tkzs_structlog.extensions.rotation import GzipBackend

        backend = GzipBackend()

        original_content = b"Hello, World!" * 100
        src_file = tmp_path / "test.log"
        src_file.write_bytes(original_content)

        dst_file = tmp_path / "test.log.gz"
        backend.compress(src_file, dst_file)

        # 解压验证
        with gzip.open(dst_file, "rb") as f:
            decompressed = f.read()

        assert decompressed == original_content

    def test_gzip_backend_nonexistent_file(self, tmp_path):
        """测试压缩不存在的文件"""
        from tkzs_structlog.extensions.rotation import GzipBackend

        backend = GzipBackend()

        src_file = tmp_path / "nonexistent.log"
        dst_file = tmp_path / "test.log.gz"

        result = backend.compress(src_file, dst_file)
        assert result is False

    def test_lz4_backend_import_error(self, tmp_path):
        """测试lz4不可用时"""
        from tkzs_structlog.extensions.rotation import Lz4Backend

        backend = Lz4Backend()

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test")

        dst_file = tmp_path / "test.log.lz4"

        # lz4 未安装时应该返回 False
        result = backend.compress(src_file, dst_file)
        assert result is False

    def test_lz4_backend_extension(self):
        """测试lz4扩展名"""
        from tkzs_structlog.extensions.rotation import Lz4Backend

        backend = Lz4Backend()
        assert backend.extension == ".lz4"

    def test_zstd_backend_import_error(self, tmp_path):
        """测试zstd不可用时"""
        from tkzs_structlog.extensions.rotation import ZstdBackend

        backend = ZstdBackend()

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test")

        dst_file = tmp_path / "test.log.zst"

        result = backend.compress(src_file, dst_file)
        assert result is False

    def test_zstd_backend_extension(self):
        """测试zstd扩展名"""
        from tkzs_structlog.extensions.rotation import ZstdBackend

        backend = ZstdBackend()
        assert backend.extension == ".zst"


class TestGetCompressBackend:
    """测试获取压缩后端"""

    def test_get_gzip_backend(self):
        """测试获取gzip后端"""
        from tkzs_structlog.extensions.rotation import GzipBackend, get_compress_backend

        backend = get_compress_backend("gzip")
        assert isinstance(backend, GzipBackend)

    def test_get_lz4_backend(self):
        """测试获取lz4后端"""
        from tkzs_structlog.extensions.rotation import Lz4Backend, get_compress_backend

        backend = get_compress_backend("lz4")
        assert isinstance(backend, Lz4Backend)

    def test_get_zstd_backend(self):
        """测试获取zstd后端"""
        from tkzs_structlog.extensions.rotation import ZstdBackend, get_compress_backend

        backend = get_compress_backend("zstd")
        assert isinstance(backend, ZstdBackend)

    def test_get_unknown_backend_defaults_to_gzip(self):
        """测试未知后端默认为gzip"""
        from tkzs_structlog.extensions.rotation import GzipBackend, get_compress_backend

        backend = get_compress_backend("unknown")
        assert isinstance(backend, GzipBackend)

    def test_get_backend_case_insensitive(self):
        """测试后端名称大小写不敏感"""
        from tkzs_structlog.extensions.rotation import GzipBackend, get_compress_backend

        backend = get_compress_backend("GZIP")
        assert isinstance(backend, GzipBackend)


class TestCustomRotatingFileHandler:
    """测试自定义轮转处理器"""

    def test_handler_init_defaults(self, tmp_path):
        """测试处理器默认初始化"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
        }

        handler = CustomRotatingFileHandler(config)

        assert handler.enable_rotate is False
        assert handler.max_bytes == 10485760  # 10MB
        assert handler.backup_count == 10
        assert handler.retain_days == 7

    def test_handler_init_custom_config(self, tmp_path):
        """测试处理器自定义配置"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "encoding": "gbk",
            "custom_rotate": {
                "enable": True,
                "max_bytes": 1024 * 1024,  # 1MB
                "backup_count": 5,
                "retain_days": 14,
                "compress": True,
                "compress_method": "gzip",
                "compress_async": False,
            },
        }

        handler = CustomRotatingFileHandler(config)

        assert handler.enable_rotate is True
        assert handler.max_bytes == 1024 * 1024
        assert handler.backup_count == 5
        assert handler.retain_days == 14
        assert handler.compress is True
        assert handler.compress_method == "gzip"
        assert handler.compress_async is False

    def test_should_rotate_by_size_disabled(self, tmp_path):
        """测试禁用大小时不轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": False},
        }

        handler = CustomRotatingFileHandler(config)

        assert handler._should_rotate_by_size() is False

    def test_should_rotate_by_size_file_not_exists(self, tmp_path):
        """测试文件不存在时不轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "nonexistent.log"),
            "custom_rotate": {"enable": True, "max_bytes": 100},
        }

        handler = CustomRotatingFileHandler(config)

        assert handler._should_rotate_by_size() is False

    def test_should_rotate_by_size_under_limit(self, tmp_path):
        """测试文件小于限制时不轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"small content")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "max_bytes": 1000000},
        }

        handler = CustomRotatingFileHandler(config)

        assert handler._should_rotate_by_size() is False

    def test_should_rotate_by_size_over_limit(self, tmp_path):
        """测试文件超过限制时轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        # 创建大于1MB的文件
        log_file.write_bytes(b"x" * (1024 * 1024 + 1))

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "max_bytes": 1024 * 1024},
        }

        handler = CustomRotatingFileHandler(config)

        assert handler._should_rotate_by_size() is True

    def test_should_rotate_by_time_disabled(self, tmp_path):
        """测试禁用时间轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": False},
        }

        handler = CustomRotatingFileHandler(config)

        assert handler._should_rotate_by_time() is False

    def test_should_rotate_by_time_not_midnight(self, tmp_path):
        """测试非零点时不轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": True, "rotate_when": "MIDNIGHT"},
        }

        handler = CustomRotatingFileHandler(config)

        # 设置最后轮转时间为当前时间
        handler._last_rotate_time = time.time()

        # 除非正好是零点，否则不应该轮转
        now = datetime.now()
        if now.hour != 0 or now.minute != 0:
            assert handler._should_rotate_by_time() is False

    def test_rotate_nonexistent_file(self, tmp_path):
        """测试轮转不存在的文件"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "nonexistent.log"),
            "custom_rotate": {"enable": True},
        }

        handler = CustomRotatingFileHandler(config)
        handler.rotate()  # 应该静默失败

    def test_rotate_existing_file(self, tmp_path):
        """测试轮转存在的文件"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test log content")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True},
        }

        handler = CustomRotatingFileHandler(config)
        handler.rotate()

        # 原文件应该不存在了
        assert not log_file.exists()

        # 应该创建了轮转文件
        rotated_files = list(tmp_path.glob("test.*"))
        assert len(rotated_files) == 1

    def test_rotate_with_compress(self, tmp_path):
        """测试轮转并压缩"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test log content")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "compress": True,
                "compress_async": False,
            },
        }

        handler = CustomRotatingFileHandler(config)
        handler.rotate()

        # 等待压缩完成
        time.sleep(0.5)

        # 应该存在压缩文件
        compressed_files = list(tmp_path.glob("test.*.gz"))
        assert len(compressed_files) == 1

    def test_cleanup_by_count(self, tmp_path):
        """测试按数量清理"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"current")

        # 创建多个轮转文件
        for i in range(15):
            f = tmp_path / f"test.{i}.log"
            f.write_bytes(b"old log")
            # 设置不同的修改时间
            old_time = time.time() - (i * 86400)
            os.utime(f, (old_time, old_time))

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 5,
                "retain_days": 0,
            },
        }

        handler = CustomRotatingFileHandler(config)
        handler.cleanup()

        # 应该只剩下5个文件
        rotated_files = list(tmp_path.glob("test.*"))
        assert len(rotated_files) == 5

    def test_cleanup_by_days(self, tmp_path):
        """测试按天数清理"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"current")

        # 创建一个旧文件
        old_file = tmp_path / "test.old.log"
        old_file.write_bytes(b"old log")

        # 修改文件时间为10天前
        old_time = time.time() - (10 * 86400)
        os.utime(old_file, (old_time, old_time))

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 0,
                "retain_days": 7,
            },
        }

        handler = CustomRotatingFileHandler(config)
        handler.cleanup()

        # 旧文件应该被删除
        assert not old_file.exists()

    def test_cleanup_nonexistent_directory(self):
        """测试清理不存在的目录"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": "/nonexistent/dir/test.log",
            "custom_rotate": {"enable": True, "retain_days": 7},
        }

        handler = CustomRotatingFileHandler(config)
        handler.cleanup()  # 应该静默失败

    def test_check_and_rotate_no_rotate(self, tmp_path):
        """测试不需要轮转时"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"small")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "max_bytes": 1000000},
        }

        handler = CustomRotatingFileHandler(config)
        handler.check_and_rotate()

        # 文件不应该被轮转
        assert log_file.exists()

    def test_close_handler(self, tmp_path):
        """测试关闭处理器"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {
                "enable": True,
                "compress": True,
                "compress_async": True,
            },
        }

        handler = CustomRotatingFileHandler(config)
        handler.close()

        # 应该等待线程池关闭
        assert handler._compress_executor is None or handler._compress_executor._shutdown

    def test_handler_destructor(self, tmp_path):
        """测试处理器析构"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {
                "enable": True,
                "compress": True,
                "compress_async": True,
            },
        }

        handler = CustomRotatingFileHandler(config)
        del handler  # 触发 __del__


class TestRotationEdgeCases:
    """轮转边界情况测试"""

    def test_compress_file_sync(self, tmp_path):
        """测试同步压缩"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test content")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "compress": True,
                "compress_async": False,
            },
        }

        handler = CustomRotatingFileHandler(config)
        handler._compress_file(log_file)

        # 等待压缩
        time.sleep(0.1)

        # 应该有压缩文件
        compressed = list(tmp_path.glob("*.gz"))
        assert len(compressed) >= 1

    def test_do_compress_exception(self, tmp_path):
        """测试压缩异常处理"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(tmp_path / "main.log"),
            "custom_rotate": {"enable": True},
        }

        handler = CustomRotatingFileHandler(config)

        # 模拟压缩失败
        handler._do_compress(log_file, Path("/invalid/path"))

        # 文件应该仍然存在
        assert log_file.exists()

    def test_cleanup_permission_error(self, tmp_path):
        """测试清理权限错误"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        # 创建一个只读文件
        read_only_file = tmp_path / "test.readonly.log"
        read_only_file.write_bytes(b"readonly")
        read_only_file.chmod(0o444)

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 0,
                "retain_days": 0,
            },
        }

        handler = CustomRotatingFileHandler(config)

        # 手动添加只读文件到文件列表进行清理测试
        try:
            handler.cleanup()
        except Exception:
            pass  # 可能抛出权限错误

        # 恢复权限以便清理
        read_only_file.chmod(0o644)
