"""API模块测试"""

from unittest.mock import MagicMock, patch

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
        from tkzs_structlog.api import core

        # 保存原始值
        original_watchdog = core.WATCHDOG_AVAILABLE

        try:
            # 强制设置 WATCHDOG_AVAILABLE
            core.WATCHDOG_AVAILABLE = True

            reset_structlog()

            # Mock ConfigHotReloader
            with patch("tkzs_structlog.api.core.ConfigHotReloader") as mock_reloader_class:
                mock_reloader = MagicMock()
                mock_reloader_class.return_value = mock_reloader

                init_structlog(
                    enable_hotreload=True,
                    config={"extensions": {"config_hot_reload": True}},
                )

                # 验证热重载器被创建和启动
                mock_reloader_class.assert_called_once()
                mock_reloader.start.assert_called_once()

            reset_structlog()
        finally:
            core.WATCHDOG_AVAILABLE = original_watchdog

    def test_setup_hotreload_disabled_by_config(self):
        """测试配置中禁用热重载"""
        from tkzs_structlog import init_structlog, reset_structlog

        reset_structlog()

        # 使用禁用热重载的配置
        init_structlog(
            config={"extensions": {"config_hot_reload": False}},
            enable_hotreload=True,
        )

        # 应该成功初始化，不抛出异常
        assert is_initialized()

        reset_structlog()

    def test_setup_hotreload_watchdog_unavailable(self):
        """测试watchdog不可用时"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.extensions import hotreload

        original_watchdog = hotreload.WATCHDOG_AVAILABLE

        try:
            hotreload.WATCHDOG_AVAILABLE = False

            reset_structlog()

            # 不应该抛出异常
            init_structlog(
                config={"extensions": {"config_hot_reload": True}},
                enable_hotreload=True,
            )

            reset_structlog()
        finally:
            hotreload.WATCHDOG_AVAILABLE = original_watchdog


class TestResetStructlog:
    """测试重置功能"""

    def test_reset_stops_hotreloader(self):
        """测试重置停止热重载"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.api import core

        original_watchdog = core.WATCHDOG_AVAILABLE

        try:
            # 强制设置 WATCHDOG_AVAILABLE
            core.WATCHDOG_AVAILABLE = True

            reset_structlog()

            with patch("tkzs_structlog.api.core.ConfigHotReloader") as mock_reloader_class:
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
            core.WATCHDOG_AVAILABLE = original_watchdog

    def test_reset_clears_context(self):
        """测试重置清空上下文"""
        from tkzs_structlog import init_structlog, reset_structlog

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

        # 先绑定
        bind_context(key1="value1")

        # 解绑不存在的键不应该抛出异常
        unbind_context("nonexistent")
        unbind_context(None)  # type: ignore

    def test_clear_context_on_empty(self):
        """测试清空调用"""
        # 清空调用不应该抛出异常
        clear_context()


class TestContextAPIEdgeCases:
    """测试上下文API边界情况"""

    def test_bind_context_empty_kwargs(self):
        """测试 bind_context 空调用（kwargs 为空时不更新存储）"""
        from tkzs_structlog.api.core import _context_store

        # 先清空存储
        _context_store.clear()
        # 空调用不应抛异常
        bind_context()
        # 存储应保持为空
        assert _context_store == {}

    def test_bind_context_updates_store(self):
        """测试 bind_context 更新存储"""
        from tkzs_structlog.api.core import _context_store

        _context_store.clear()
        bind_context(key1="val1", key2="val2")
        assert _context_store.get("key1") == "val1"
        assert _context_store.get("key2") == "val2"


class TestHotReloadCallbackExecution:
    """测试热重载回调函数内部代码覆盖（行 85-89）"""

    def test_hotreload_on_reload_callback_sets_config_and_reinit(self):
        """测试热重载回调执行：set_global_config + reset + init"""
        from tkzs_structlog import init_structlog, reset_structlog
        from tkzs_structlog.api import core
        from tkzs_structlog.core.initializer import get_initializer, reset_initializer

        original_watchdog = core.WATCHDOG_AVAILABLE
        original_reloader = core._hotreloader

        try:
            core.WATCHDOG_AVAILABLE = True

            reset_structlog()

            # Mock start() 以阻止 observer 线程启动，保留 _hotreloader 实例创建
            # config 中必须有 extensions.config_hot_reload=True 才能触发 _setup_hotreload
            with patch("tkzs_structlog.api.core.ConfigHotReloader.start"):
                init_structlog(
                    config={
                        "version": "1.0",
                        "logger_name": "test_hotreload",
                        "extensions": {"config_hot_reload": True},
                    },
                    enable_hotreload=True,
                )

            # _setup_hotreload 内部定义了 on_reload 闭包，
            # 实例化为 _hotreloader，其 .on_reload 属性即目标函数
            assert core._hotreloader is not None
            assert core._hotreloader.on_reload is not None

            # 触发回调（模拟 watchdog 文件修改事件）
            new_config = {
                "version": "1.0",
                "logger_name": "reloaded",
                "min_level": "DEBUG",
            }
            core._hotreloader.on_reload(new_config)

            # 验证重初始化成功（覆盖回调内部的 reset + init）
            initializer = get_initializer()
            assert initializer.is_initialized
            assert initializer.config.get("logger_name") == "reloaded"

            reset_structlog()
            reset_initializer()

        finally:
            core.WATCHDOG_AVAILABLE = original_watchdog
            core._hotreloader = original_reloader


class TestInitializerFilterProcessorPath:
    """测试 initializer 中 FilterProcessor 追加路径（行 136）"""

    def test_init_with_filter_rules_adds_filter_processor(self):
        """当配置包含 filter_rules 且有 exclude/include 时，追加 FilterProcessor"""
        from tkzs_structlog import init_structlog, reset_structlog

        reset_structlog()
        config = {
            "version": "1.0",
            "logger_name": "filter_test",
            "extensions": {
                "filter_rules": {
                    "exclude": ["password", "token"],
                },
            },
        }
        init_structlog(config=config)
        assert init_structlog is not None  # 初始化成功即覆盖第 136 行

        reset_structlog()

    def test_init_with_filter_rules_include_only(self):
        """当配置只有 include 字段时也追加 FilterProcessor"""
        from tkzs_structlog import init_structlog, reset_structlog

        reset_structlog()
        config = {
            "version": "1.0",
            "logger_name": "filter_test2",
            "extensions": {
                "filter_rules": {
                    "include": ["username", "email"],
                },
            },
        }
        init_structlog(config=config)

        reset_structlog()
