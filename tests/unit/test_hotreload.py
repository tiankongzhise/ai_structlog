"""热重载模块测试"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tkzs_structlog.extensions.hotreload import (
    ConfigFileHandler,
    ConfigHotReloader,
    WATCHDOG_AVAILABLE,
    reload_processor,
)


class TestConfigFileHandler:
    """测试配置文件处理器"""

    def test_init(self):
        """测试初始化"""
        handler = ConfigFileHandler("config.json")
        assert handler.config_path == Path("config.json")
        assert handler.on_reload is None

    def test_init_with_callback(self):
        """测试带回调初始化"""
        callback = MagicMock()
        handler = ConfigFileHandler("config.json", on_reload=callback)
        assert handler.on_reload == callback

    def test_init_with_pathlib(self, tmp_path):
        """测试使用Path对象初始化"""
        config_file = tmp_path / "config.json"
        handler = ConfigFileHandler(config_file)
        assert handler.config_path == config_file

    def test_on_modified_ignores_other_files(self):
        """测试忽略其他文件的修改"""
        handler = ConfigFileHandler("config.json")
        event = MagicMock()
        event.src_path = "/other/path/file.txt"

        handler.on_modified(event)
        # 不应该调用 on_reload

    def test_on_modified_reloads_config(self, tmp_path):
        """测试修改时重新加载配置"""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"version": "1.0"}', encoding="utf-8")

        callback = MagicMock()
        handler = ConfigFileHandler(config_file, on_reload=callback)

        event = MagicMock()
        event.src_path = str(config_file)

        handler.on_modified(event)

        callback.assert_called_once()

    def test_on_modified_handles_error(self, tmp_path):
        """测试处理错误"""
        handler = ConfigFileHandler(tmp_path / "nonexistent.json")
        # on_reload is None, so it should handle gracefully
        event = MagicMock()
        event.src_path = str(tmp_path / "nonexistent.json")

        # 不应该抛出异常
        handler.on_modified(event)

    def test_on_modified_with_callback_error(self, tmp_path):
        """测试回调抛出错误时处理"""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"version": "1.0"}', encoding="utf-8")

        def error_callback(config):
            raise RuntimeError("test error")

        handler = ConfigFileHandler(config_file, on_reload=error_callback)

        event = MagicMock()
        event.src_path = str(config_file)

        # 不应该抛出异常
        handler.on_modified(event)

    def test_reload_lock(self):
        """测试重载锁"""
        handler = ConfigFileHandler("config.json")
        assert hasattr(handler, "_reload_lock")


class TestConfigHotReloader:
    """测试配置热重载器"""

    def test_init_without_watchdog(self):
        """测试watchdog不可用时初始化"""
        if WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is available")

        with pytest.raises(ImportError):
            ConfigHotReloader("config.json")

    def test_init_with_watchdog(self):
        """测试watchdog可用时初始化"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        assert reloader.config_path == Path("config.json")
        assert not reloader.is_running

    def test_init_with_pathlib(self, tmp_path):
        """测试使用Path对象初始化"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        config_file = tmp_path / "config.json"
        reloader = ConfigHotReloader(config_file)
        assert reloader.config_path == config_file

    def test_init_with_callback(self):
        """测试带回调初始化"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        callback = MagicMock()
        reloader = ConfigHotReloader("config.json", on_reload=callback)
        assert reloader.on_reload == callback

    def test_is_running_property(self):
        """测试is_running属性"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        assert reloader.is_running is False

    def test_start(self):
        """测试启动"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        reloader.start()
        assert reloader.is_running
        reloader.stop()

    def test_start_multiple_times(self):
        """测试多次启动"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        reloader.start()
        assert reloader.is_running

        # 再次启动不应该出错
        reloader.start()
        assert reloader.is_running

        reloader.stop()

    def test_stop(self):
        """测试停止"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        reloader.start()
        assert reloader.is_running
        reloader.stop()
        assert not reloader.is_running

    def test_stop_when_not_running(self):
        """测试停止未运行的重载器"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is not available")

        reloader = ConfigHotReloader("config.json")
        # 停止未启动的重载器不应该出错
        reloader.stop()


class TestReloadProcessor:
    """测试处理器重载"""

    def test_reload_processor_success(self):
        """测试成功重载处理器"""
        # 重新加载一个已知存在的模块
        result = reload_processor("tkzs_structlog.config.loader")
        assert result is not None

    def test_reload_processor_invalid_path(self):
        """测试无效路径"""
        result = reload_processor("invalid.path")
        assert result is None

    def test_reload_processor_no_class(self):
        """测试路径不包含类名"""
        result = reload_processor("tkzs_structlog")
        assert result is None

    def test_reload_processor_invalid_class(self):
        """测试无效类名"""
        result = reload_processor("tkzs_structlog.config.loader.NonExistentClass")
        assert result is None

    def test_reload_processor_empty_path(self):
        """测试空路径"""
        result = reload_processor("")
        assert result is None


class TestWatchdogAvailability:
    """测试watchdog可用性"""

    def test_watchdog_flag(self):
        """测试WATCHDOG_AVAILABLE标志"""
        assert isinstance(WATCHDOG_AVAILABLE, bool)

    def test_watchdog_can_be_imported(self):
        """测试watchdog可以导入"""
        if WATCHDOG_AVAILABLE:
            try:
                import watchdog.events
                import watchdog.observers
                assert True
            except ImportError:
                pytest.fail("watchdog should be importable when WATCHDOG_AVAILABLE is True")
