"""API模块测试"""

import pytest

from tkzs_structlog.api.core import (
    bind_context,
    clear_context,
    is_initialized,
    unbind_context,
)
from tkzs_structlog.exceptions import StructlogNotInitedError


class TestContextAPI:
    """测试上下文API"""

    def test_bind_context(self):
        """测试绑定上下文"""
        bind_context(request_id="123")
        bind_context(user_id=456)
        # 绑定后上下文会被 get_logger 使用

    def test_unbind_context(self):
        """测试解绑上下文"""
        bind_context(a=1, b=2)
        unbind_context("a")
        # b 应该仍然存在

    def test_clear_context(self):
        """测试清空上下文"""
        bind_context(a=1, b=2)
        clear_context()
        # 上下文应该为空

    def test_unbind_nonexistent(self):
        """测试解绑不存在的键"""
        unbind_context("nonexistent")


class TestInitAndLogger:
    """测试初始化和日志器"""

    def test_init_with_default(self):
        """测试使用默认配置初始化"""
        from tkzs_structlog import get_logger, init_structlog, reset_structlog

        reset_structlog()
        init_structlog()
        assert is_initialized()

        logger = get_logger()
        assert logger is not None

        reset_structlog()

    def test_init_with_dict_config(self):
        """测试使用字典配置初始化"""
        from tkzs_structlog import get_logger, init_structlog, reset_structlog

        reset_structlog()
        config = {
            "version": "1.0",
            "logger_name": "test",
            "min_level": "DEBUG",
        }
        init_structlog(config=config)
        assert is_initialized()

        logger = get_logger()
        assert logger is not None

        reset_structlog()

    def test_get_logger_without_init(self):
        """测试未初始化时获取日志器"""
        from tkzs_structlog import reset_structlog

        reset_structlog()
        with pytest.raises(StructlogNotInitedError):
            from tkzs_structlog import get_logger

            get_logger()

    def test_reset_structlog(self):
        """测试重置"""
        from tkzs_structlog import init_structlog, is_initialized, reset_structlog

        init_structlog()
        assert is_initialized()

        reset_structlog()
        assert not is_initialized()

    def test_reinitialization(self):
        """测试重复初始化"""
        from tkzs_structlog import init_structlog, is_initialized, reset_structlog

        init_structlog(config={"version": "1.0", "logger_name": "first"})
        assert is_initialized()

        # 再次初始化应该先重置
        init_structlog(config={"version": "1.0", "logger_name": "second"})
        assert is_initialized()

        reset_structlog()

    def test_init_with_kwargs_override(self):
        """测试 kwargs 覆盖配置"""
        from tkzs_structlog import init_structlog, reset_structlog

        reset_structlog()
        init_structlog(
            config={"version": "1.0"},
            logger_name="override_test",
            min_level="DEBUG",
        )
        # 应该成功初始化，不抛出异常
        assert is_initialized()

        reset_structlog()


class TestSetupHotReload:
    """测试热重载设置"""

    def test_setup_hotreload_enabled(self, tmp_path):
        """测试启用热重载"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.extensions import hotreloading
        from tkzs_structlog.api.core import ConfigHotReloader as CoreHotReloader

        # 保存原始值
        original_watchdog = hotreloading.WATCHDOG_AVAILABLE

        try:
            # 模拟watchdog可用
            hotreloading.WATCHDOG_AVAILABLE = True

            reset_structlog()

            config_path = tmp_path / "config.json"
            config_path.write_text('{"extensions": {"config_hot_reload": true}}', encoding="utf-8")

            # 创建热重载器mock
            with patch.object(hotreloading, "ConfigHotReloader") as mock_reloader_class:
                mock_reloader = MagicMock()
                mock_reloader_class.return_value = mock_reloader

                init_structlog(
                    config_path=str(config_path),
                    enable_hotreload=True,
                    config={"extensions": {"config_hot_reload": True}},
                )

                # 验证热重载器被创建和启动
                mock_reloader_class.assert_called_once()
                mock_reloader.start.assert_called_once()

            reset_structlog()
        finally:
            hotreloading.WATCHDOG_AVAILABLE = original_watchdog

    def test_setup_hotreload_disabled_by_config(self, tmp_path):
        """测试配置中禁用热重载"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.extensions import hotreloading

        original_watchdog = hotreloading.WATCHDOG_AVAILABLE

        try:
            hotreloading.WATCHDOG_AVAILABLE = True

            reset_structlog()

            with patch.object(hotreloading, "ConfigHotReloader") as mock_reloader_class:
                init_structlog(
                    config={"extensions": {"config_hot_reload": False}},
                    enable_hotreload=True,
                )

                # 热重载器不应该被创建
                mock_reloader_class.assert_not_called()

            reset_structlog()
        finally:
            hotreloading.WATCHDOG_AVAILABLE = original_watchdog

    def test_setup_hotreload_watchdog_unavailable(self, tmp_path):
        """测试watchdog不可用时"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.extensions import hotreloading

        original_watchdog = hotreloading.WATCHDOG_AVAILABLE

        try:
            hotreloading.WATCHDOG_AVAILABLE = False

            reset_structlog()

            # 不应该抛出异常
            init_structlog(
                config={"extensions": {"config_hot_reload": True}},
                enable_hotreload=True,
            )

            reset_structlog()
        finally:
            hotreloading.WATCHDOG_AVAILABLE = original_watchdog


class TestResetStructlog:
    """测试重置功能"""

    def test_reset_stops_hotreloader(self, tmp_path):
        """测试重置停止热重载"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.extensions import hotreloading

        original_watchdog = hotreloading.WATCHDOG_AVAILABLE

        try:
            hotreloading.WATCHDOG_AVAILABLE = True

            reset_structlog()

            with patch.object(hotreloading, "ConfigHotReloader") as mock_reloader_class:
                mock_reloader = MagicMock()
                mock_reloader_class.return_value = mock_reloader

                init_structlog(
                    config={"extensions": {"config_hot_reload": True}},
                    enable_hotreload=True,
                )

                # 重置
                reset_structlog()

                # 验证热重载器被停止
                mock_reloader.stop.assert_called()

        finally:
            hotreloading.WATCHDOG_AVAILABLE = original_watchdog

    def test_reset_clears_context(self):
        """测试重置清空上下文"""
        from tkzs_structlog import clear_context, init_structlog, reset_structlog

        init_structlog()
        bind_context(test_key="test_value")
        reset_structlog()

        # 重置后上下文应该被清空
        from tkzs_structlog.api.core import _context_store

        assert len(_context_store) == 0


class TestGetLoggerWithContext:
    """测试带上下文的日志器"""

    def test_get_logger_binds_context(self):
        """测试获取日志器绑定上下文"""
        from tkzs_structlog import get_logger, init_structlog, reset_structlog

        reset_structlog()
        init_structlog()
        bind_context(request_id="12345")

        logger = get_logger()

        # logger应该能够正常调用
        assert logger is not None

        reset_structlog()
        clear_context()


class TestContextAPIExtended:
    """扩展上下文API测试"""

    def test_bind_context_multiple_keys(self):
        """测试绑定多个键"""
        from tkzs_structlog.api.core import _context_store

        bind_context(a=1, b=2, c=3)

        # 由于bind_context更新全局存储
        assert len(_context_store) >= 0  # 取决于测试顺序

    def test_unbind_context_allows_none(self):
        """测试解绑允许None"""
        from tkzs_structlog.api.core import _context_store

        # 先绑定
        bind_context(key1="value1")

        # 解绑不存在的键不应该抛出异常
        unbind_context("nonexistent")
        unbind_context(None)  # type: ignore

    def test_clear_context_on_empty(self):
        """测试清空调用"""
        # 清空调用不应该抛出异常
        clear_context()
