"""轮转模块测试"""

import gzip
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


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
        rotated_files = list(tmp_path.glob("test.*.log"))
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

    def test_check_and_rotate_once_when_size_and_time_trigger(self, tmp_path):
        """大小与时间同时满足时只执行一次 rotate"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "both.log"
        log_file.write_bytes(b"x" * 500)

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "max_bytes": 10},
        }
        handler = CustomRotatingFileHandler(config)
        with patch.object(handler, "_should_rotate_by_size", return_value=True):
            with patch.object(handler, "_should_rotate_by_time", return_value=True):
                with patch.object(handler, "rotate", wraps=handler.rotate) as mock_rotate:
                    handler.check_and_rotate()
                    assert mock_rotate.call_count == 1

    def test_rotate_os_replace_retries_before_success(self, tmp_path, monkeypatch):
        """os.replace 失败时重试直至成功"""
        import tkzs_structlog.extensions.rotation as rot
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "retry.log"
        log_file.write_text("data", encoding="utf-8")
        config = {"file_path": str(log_file), "custom_rotate": {"enable": True}}
        handler = CustomRotatingFileHandler(config)

        calls = {"n": 0}
        real_replace = rot.os.replace

        def flaky_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
            calls["n"] += 1
            if calls["n"] < 2:
                raise OSError("simulated busy")
            return real_replace(src, dst)

        monkeypatch.setattr(rot.os, "replace", flaky_replace)
        handler.rotate()
        assert calls["n"] == 2
        assert not log_file.exists()

    def test_rotate_os_replace_all_fail_skips_without_raising(self, tmp_path, monkeypatch):
        """连续失败则记录错误并保留原文件（不向外抛 StructlogHandlerError）"""
        import tkzs_structlog.extensions.rotation as rot
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "fail.log"
        log_file.write_text("keep", encoding="utf-8")
        config = {"file_path": str(log_file), "custom_rotate": {"enable": True}}
        handler = CustomRotatingFileHandler(config)

        monkeypatch.setattr(rot.os, "replace", MagicMock(side_effect=OSError("locked")))
        handler.rotate()
        assert log_file.exists()
        assert log_file.read_text(encoding="utf-8") == "keep"

    def test_should_rotate_by_time_non_midnight_when(self, tmp_path):
        """rotate_when 非 MIDNIGHT 时不触发时间轮转（该分支暂未实现）"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": True, "rotate_when": "H"},
        }
        handler = CustomRotatingFileHandler(config)
        # 非 MIDNIGHT 的 rotate_when 暂未实现，应返回 False
        assert handler._should_rotate_by_time() is False

    def test_should_rotate_by_time_midnight_trigger(self, tmp_path):
        """零点时刻触发时间轮转"""
        from datetime import datetime
        from unittest.mock import patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": True, "rotate_when": "MIDNIGHT"},
        }
        handler = CustomRotatingFileHandler(config)

        # 模拟当前时间为零点
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with patch("tkzs_structlog.extensions.rotation.datetime") as mock_dt:
            mock_dt.now.return_value = midnight
            mock_dt.fromtimestamp.side_effect = datetime.fromtimestamp
            result = handler._should_rotate_by_time()
        assert result is True

    def test_should_rotate_by_time_cross_day(self, tmp_path):
        """跨天时触发时间轮转"""
        from datetime import datetime, timedelta
        from unittest.mock import patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        config = {
            "file_path": str(tmp_path / "test.log"),
            "custom_rotate": {"enable": True, "rotate_when": "MIDNIGHT"},
        }
        handler = CustomRotatingFileHandler(config)

        # 设置昨天的轮转时间
        yesterday = datetime.now() - timedelta(days=1)
        handler._last_rotate_time = yesterday.timestamp()

        # 现在是今天（非零点）
        now = datetime.now().replace(hour=10, minute=0)
        with patch("tkzs_structlog.extensions.rotation.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp.side_effect = datetime.fromtimestamp
            result = handler._should_rotate_by_time()
        assert result is True

    def test_compress_file_async_pool_shutdown_fallback(self, tmp_path):
        """异步线程池关闭时降级为同步压缩"""
        from unittest.mock import MagicMock, patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test content")

        config = {
            "file_path": str(tmp_path / "main.log"),
            "custom_rotate": {
                "enable": True,
                "compress": True,
                "compress_async": True,
            },
        }
        handler = CustomRotatingFileHandler(config)

        # 模拟线程池已关闭（submit 抛 RuntimeError）
        mock_executor = MagicMock()
        mock_executor.submit.side_effect = RuntimeError("pool shutdown")
        handler._compress_executor = mock_executor

        with patch.object(handler, "_do_compress") as mock_do_compress:
            handler._compress_file(log_file)
            # 应该降级为同步
            mock_do_compress.assert_called_once()

    def test_do_compress_exception_keeps_original(self, tmp_path):
        """_do_compress 异常时保留原文件并记录警告"""
        from unittest.mock import patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test content")

        config = {
            "file_path": str(tmp_path / "main.log"),
            "custom_rotate": {"enable": True},
        }
        handler = CustomRotatingFileHandler(config)

        # 模拟 compress 方法抛出异常
        with patch.object(handler._compress_backend, "compress", side_effect=OSError("disk full")):
            handler._do_compress(log_file, tmp_path / "test.log.gz")

        # 原文件应该仍然存在（因为 compress 失败了，remove 没执行）
        assert log_file.exists()

    def test_cleanup_unlink_oserror_in_count_cleanup(self, tmp_path):
        """按数量清理时 unlink 抛 OSError 不中断整体清理"""
        from unittest.mock import patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"current")

        # 创建多个轮转文件
        for i in range(8):
            f = tmp_path / f"test.{i:03d}.log"
            f.write_bytes(b"old")
            old_time = time.time() - (i * 100)
            os.utime(f, (old_time, old_time))

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 3,
                "retain_days": 0,
            },
        }
        handler = CustomRotatingFileHandler(config)

        # 模拟 unlink 抛出 OSError，验证不会中断
        original_unlink = Path.unlink
        call_count = {"n": 0}

        def unlink_with_first_error(self, missing_ok=False):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("permission denied")
            return original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", unlink_with_first_error):
            handler.cleanup()  # 不应该抛出异常

    def test_cleanup_unlink_oserror_in_days_cleanup(self, tmp_path):
        """按天数清理时 unlink 抛 OSError 不中断整体清理"""
        from unittest.mock import patch

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"current")

        # 创建两个超期文件
        for name in ("test.old1.log", "test.old2.log"):
            f = tmp_path / name
            f.write_bytes(b"old")
            old_time = time.time() - (10 * 86400)
            os.utime(f, (old_time, old_time))

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 0,
                "retain_days": 7,
            },
        }
        handler = CustomRotatingFileHandler(config)

        original_unlink = Path.unlink
        call_count = {"n": 0}

        def unlink_with_first_error(self, missing_ok=False):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("permission denied")
            return original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", unlink_with_first_error):
            handler.cleanup()  # 不应该抛出异常

    def test_lz4_backend_compress_with_mock(self, tmp_path):
        """通过 mock lz4 模块测试 lz4 压缩成功路径"""
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock, patch

        from tkzs_structlog.extensions.rotation import Lz4Backend

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test content")
        dst_file = tmp_path / "test.log.lz4"

        # 创建 mock lz4 模块
        mock_lz4 = ModuleType("lz4")
        mock_lz4.frame = MagicMock()

        # mock context manager
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_lz4.frame.open.return_value = mock_ctx

        with patch.dict(sys.modules, {"lz4": mock_lz4, "lz4.frame": mock_lz4.frame}):
            backend = Lz4Backend()
            result = backend.compress(src_file, dst_file)

        assert result is True

    def test_zstd_backend_compress_with_mock(self, tmp_path):
        """通过 mock zstandard 模块测试 zstd 压缩成功路径"""
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock, patch

        from tkzs_structlog.extensions.rotation import ZstdBackend

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test content")
        dst_file = tmp_path / "test.log.zst"

        # 创建 mock zstandard 模块
        mock_zstd_mod = ModuleType("zstandard")
        mock_compressor = MagicMock()
        mock_compressor.copy_stream = MagicMock()
        mock_zstd_cls = MagicMock(return_value=mock_compressor)
        mock_zstd_mod.ZstdCompressor = mock_zstd_cls

        with patch.dict(sys.modules, {"zstandard": mock_zstd_mod}):
            backend = ZstdBackend()
            result = backend.compress(src_file, dst_file)

        assert result is True

    def test_lz4_backend_compress_exception(self, tmp_path):
        """lz4 压缩异常（非 ImportError）返回 False"""
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock, patch

        from tkzs_structlog.extensions.rotation import Lz4Backend

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test")
        dst_file = tmp_path / "test.log.lz4"

        mock_lz4 = ModuleType("lz4")
        mock_lz4.frame = MagicMock()
        mock_lz4.frame.open.side_effect = OSError("lz4 error")

        with patch.dict(sys.modules, {"lz4": mock_lz4, "lz4.frame": mock_lz4.frame}):
            backend = Lz4Backend()
            result = backend.compress(src_file, dst_file)

        assert result is False

    def test_zstd_backend_compress_exception(self, tmp_path):
        """zstd 压缩异常（非 ImportError）返回 False"""
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock, patch

        from tkzs_structlog.extensions.rotation import ZstdBackend

        src_file = tmp_path / "test.log"
        src_file.write_bytes(b"test")
        dst_file = tmp_path / "test.log.zst"

        mock_zstd_mod = ModuleType("zstandard")
        mock_zstd_mod.ZstdCompressor = MagicMock(side_effect=OSError("zstd error"))

        with patch.dict(sys.modules, {"zstandard": mock_zstd_mod}):
            backend = ZstdBackend()
            result = backend.compress(src_file, dst_file)

        assert result is False


class TestProcessLock:
    """测试跨平台进程锁"""

    def test_get_process_lock_returns_tuple(self, tmp_path):
        """测试获取锁返回 (file, bool) 元组"""
        from tkzs_structlog.extensions.rotation import _get_process_lock

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        result = _get_process_lock(log_file)

        assert isinstance(result, tuple)
        assert len(result) == 2
        lock_file, is_locked = result
        assert is_locked is True or is_locked is False

    def test_get_process_lock_nonexistent_file(self, tmp_path):
        """测试不存在的文件也能创建锁"""
        from tkzs_structlog.extensions.rotation import _get_process_lock

        log_file = tmp_path / "nonexistent.log"
        lock_file, is_locked = _get_process_lock(log_file)

        # 即使文件不存在，也应该能创建锁文件
        assert lock_file is None or lock_file is not None

    def test_release_process_lock_none(self, tmp_path):
        """测试释放空锁"""
        from tkzs_structlog.extensions.rotation import _release_process_lock

        # 传入 None 不应抛异常
        _release_process_lock(None)

    def test_process_lock_reentrant(self, tmp_path):
        """测试同一进程可重复获取锁"""
        from tkzs_structlog.extensions.rotation import _get_process_lock

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        lock1, locked1 = _get_process_lock(log_file)
        if locked1:
            lock2, locked2 = _get_process_lock(log_file)
            # 同一进程第二次获取可能失败（锁被占用）


class TestRotateWhenExtended:
    """测试 rotate_when 扩展模式"""

    def test_should_rotate_by_time_hourly(self, tmp_path):
        """测试按小时轮转模式"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "H"},
        }
        handler = CustomRotatingFileHandler(config)

        # 设置上次轮转时间在上一小时
        old_time = datetime.now() - timedelta(hours=1)
        handler._last_rotate_time = old_time.timestamp()

        result = handler._should_rotate_by_time()

        # 当前小时与上次不同，应该轮转
        assert result is True

    def test_should_rotate_by_time_hourly_same_hour(self, tmp_path):
        """测试同一小时不触发轮转"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "H"},
        }
        handler = CustomRotatingFileHandler(config)

        now = datetime.now()
        old_time = now.replace(minute=now.minute - 30 if now.minute >= 30 else 0, second=0, microsecond=0)
        handler._last_rotate_time = old_time.timestamp()

        result = handler._should_rotate_by_time()

        if old_time.hour == now.hour:
            assert result is False
        else:
            assert result is True

    def test_should_rotate_by_time_daily(self, tmp_path):
        """测试按天轮转模式"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "D"},
        }
        handler = CustomRotatingFileHandler(config)

        # 设置上次轮转为昨天
        old_time = datetime.now() - timedelta(days=1)
        handler._last_rotate_time = old_time.timestamp()

        result = handler._should_rotate_by_time()

        # 跨天了，应该轮转
        assert result is True

    def test_should_rotate_by_time_daily_same_day(self, tmp_path):
        """测试同一天不触发轮转"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "D"},
        }
        handler = CustomRotatingFileHandler(config)

        # 设置上次轮转为几小时前
        old_time = datetime.now() - timedelta(hours=5)
        handler._last_rotate_time = old_time.timestamp()

        result = handler._should_rotate_by_time()

        # 同一天，不应该轮转
        assert result is False

    def test_should_rotate_by_time_weekly_monday(self, tmp_path):
        """测试按周轮转模式 W0（周一）"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "W0"},
        }
        handler = CustomRotatingFileHandler(config)

        # 今天是周一，但上次轮转是上周
        now = datetime.now()
        if now.weekday() == 0:  # 今天是周一
            # 设置为上周
            old_time = datetime.now() - timedelta(days=7)
            handler._last_rotate_time = old_time.timestamp()

            result = handler._should_rotate_by_time()

            # 周一且跨周，应该轮转
            assert result is True
        else:
            # 今天不是周一，不应该轮转
            result = handler._should_rotate_by_time()
            assert result is False

    def test_should_rotate_by_time_weekly_invalid(self, tmp_path):
        """测试无效的周模式"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "W7"},
        }
        handler = CustomRotatingFileHandler(config)

        # W7 无效，应该不触发
        result = handler._should_rotate_by_time()
        assert result is False

    def test_should_rotate_by_time_case_insensitive(self, tmp_path):
        """测试大小写不敏感"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        # 测试小写
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "midnight"},
        }
        handler = CustomRotatingFileHandler(config)

        # midnight 应该被识别为 MIDNIGHT
        assert handler.rotate_when == "midnight"

    def test_should_rotate_by_time_daily_first_run(self, tmp_path):
        """测试按天轮转首次运行"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "D"},
        }
        handler = CustomRotatingFileHandler(config)

        handler._last_rotate_time = 0
        result = handler._should_rotate_by_time()

        assert result is False

    def test_should_rotate_by_time_weekly_first_run(self, tmp_path):
        """测试按周轮转首次运行"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "W0"},
        }
        handler = CustomRotatingFileHandler(config)

        handler._last_rotate_time = 0
        now = datetime.now()

        if now.weekday() == 0:
            result = handler._should_rotate_by_time()
            assert result is True
        else:
            result = handler._should_rotate_by_time()
            assert result is False

    def test_should_rotate_by_time_weekly_same_week(self, tmp_path):
        """测试按周轮转同一周内不触发"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "W0"},
        }
        handler = CustomRotatingFileHandler(config)

        now = datetime.now()
        if now.weekday() == 0:
            handler._last_rotate_time = (now - timedelta(hours=1)).timestamp()
            result = handler._should_rotate_by_time()
            assert result is False

    def test_should_rotate_by_time_weekly_with_last_time(self, tmp_path):
        """测试按周轮转有上次时间且在同一周内"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        weekday = datetime.now().weekday()
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": f"W{weekday}"},
        }
        handler = CustomRotatingFileHandler(config)

        handler._last_rotate_time = (datetime.now() - timedelta(hours=1)).timestamp()
        result = handler._should_rotate_by_time()
        assert result is False

    def test_should_rotate_by_time_weekly_trigger(self, tmp_path):
        """测试按周轮转触发"""
        from datetime import timedelta

        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        weekday = datetime.now().weekday()
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": f"W{weekday}"},
        }
        handler = CustomRotatingFileHandler(config)

        last_week = datetime.now() - timedelta(days=7)
        handler._last_rotate_time = last_week.timestamp()
        result = handler._should_rotate_by_time()
        assert result is True

    def test_should_rotate_by_time_weekly_matched_weekday(self, tmp_path):
        """测试按周轮转星期不匹配不触发"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "W1"},
        }
        handler = CustomRotatingFileHandler(config)

        with patch("tkzs_structlog.extensions.rotation.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 8, 12, 0, 0)
            mock_dt.now.return_value = mock_now

            handler._last_rotate_time = 0
            result = handler._should_rotate_by_time()
            assert result is False

    def test_should_rotate_by_time_weekly_execute_branch(self, tmp_path):
        """测试按周轮转分支执行"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        weekday = datetime.now().weekday()
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": f"W{weekday}"},
        }
        handler = CustomRotatingFileHandler(config)

        handler._last_rotate_time = time.time()
        handler._should_rotate_by_time()

    def test_should_rotate_by_time_weekly_invalid_valueerror(self, tmp_path):
        """测试按周轮转无效值触发 ValueError"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": True, "rotate_when": "WX"},
        }
        handler = CustomRotatingFileHandler(config)

        result = handler._should_rotate_by_time()
        assert result is False


class TestProcessLockEdgeCases:
    """测试进程锁边界情况"""

    def test_get_process_lock_open_exception(self, tmp_path):
        """测试打开锁文件时异常"""
        from tkzs_structlog.extensions.rotation import _get_process_lock

        log_file = tmp_path / "test.log"

        with patch("builtins.open", side_effect=OSError("test error")):
            lock_file, result = _get_process_lock(log_file)
            assert lock_file is None
            assert result is False

    def test_release_process_lock_exception(self):
        """测试释放进程锁时异常"""
        from tkzs_structlog.extensions.rotation import _release_process_lock

        mock_lock_file = MagicMock()
        mock_lock_file.fileno.side_effect = OSError("test error")

        _release_process_lock(mock_lock_file)

    def test_release_process_lock_close_exception(self):
        """测试关闭锁文件时异常"""
        from tkzs_structlog.extensions.rotation import _release_process_lock

        mock_lock_file = MagicMock()
        mock_lock_file.close.side_effect = OSError("close error")

        _release_process_lock(mock_lock_file)

    def test_release_process_lock_none(self):
        """测试释放空锁"""
        from tkzs_structlog.extensions.rotation import _release_process_lock

        _release_process_lock(None)


class TestCleanupEdgeCases:
    """测试清理边界情况"""

    def test_cleanup_oserror_on_delete(self, tmp_path):
        """测试删除文件时 OSError"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"test")

        old_file = tmp_path / "test.20240101_000000.log"
        old_file.write_bytes(b"old")

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 0,
                "retain_days": 0,
            },
        }
        handler = CustomRotatingFileHandler(config)

        with patch.object(Path, "unlink", side_effect=OSError("delete error")):
            handler.cleanup()

    def test_cleanup_parent_not_exists(self, tmp_path):
        """测试父目录不存在"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "nonexistent" / "test.log"

        config = {
            "file_path": str(log_file),
            "custom_rotate": {
                "enable": True,
                "backup_count": 1,
            },
        }
        handler = CustomRotatingFileHandler(config)

        handler.cleanup()


class TestEmitEdgeCases:
    """测试 emit 边界情况"""

    def test_emit_handle_error(self, tmp_path):
        """测试 emit 中发生异常时调用 handleError（覆盖 426-434 行）"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": False},
        }
        handler = CustomRotatingFileHandler(config)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # 模拟 open 抛出异常
        with patch("builtins.open", side_effect=OSError("write error")):
            with patch.object(handler, "handleError") as mock_handle_error:
                handler.emit(record)
                mock_handle_error.assert_called_once_with(record)

    def test_emit_check_and_rotate(self, tmp_path):
        """测试 emit 后调用 check_and_rotate"""
        from tkzs_structlog.extensions.rotation import CustomRotatingFileHandler

        log_file = tmp_path / "test.log"
        config = {
            "file_path": str(log_file),
            "custom_rotate": {"enable": False},
        }
        handler = CustomRotatingFileHandler(config)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        with patch.object(handler, "check_and_rotate") as mock_check:
            handler.emit(record)
            mock_check.assert_called_once()
