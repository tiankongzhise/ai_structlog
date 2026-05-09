"""版本模块测试"""

import pytest


class TestVersion:
    """测试版本信息"""

    def test_version_exists(self):
        """测试版本字符串存在"""
        from tkzs_structlog._version import __version__, version

        assert __version__ is not None
        assert version is not None
        assert __version__ == version

    def test_version_tuple_exists(self):
        """测试版本元组存在"""
        from tkzs_structlog._version import __version_tuple__, version_tuple

        assert __version_tuple__ is not None
        assert version_tuple is not None
        assert __version_tuple__ == version_tuple

    def test_version_is_string(self):
        """测试版本是字符串"""
        from tkzs_structlog._version import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_tuple_is_tuple(self):
        """测试版本元组是元组类型"""
        from tkzs_structlog._version import __version_tuple__

        assert isinstance(__version_tuple__, tuple)
        assert len(__version_tuple__) >= 2

    def test_version_format(self):
        """测试版本格式"""
        from tkzs_structlog._version import __version__

        # 版本字符串应该包含数字
        assert any(char.isdigit() for char in __version__)

    def test_commit_id_exists(self):
        """测试commit_id存在"""
        from tkzs_structlog._version import __commit_id__, commit_id

        # commit_id 可以是 None
        assert __commit_id__ is commit_id

    def test_all_exports(self):
        """测试所有导出"""
        from tkzs_structlog._version import (
            __all__,
        )

        assert "__version__" in __all__
        assert "__version_tuple__" in __all__
        assert "__commit_id__" in __all__


class TestPublicAPI:
    """测试公共 API 导入 — 回归验证 claude_deepseek Bug #1"""

    def test_all_exception_imports(self):
        """测试所有异常类可从根包导入"""
        from tkzs_structlog import (
            StructlogBaseError,
            StructlogConfigError,
            StructlogConfigFileNotFoundError,
            StructlogConfigParseError,
            StructlogConfigVersionError,
            StructlogHandlerError,
            StructlogNotInitedError,
            StructlogProcessorError,
            StructlogProcessorImportError,
            StructlogProcessorInstantiateError,
        )

        # 验证所有异常都继承自 StructlogBaseError
        assert issubclass(StructlogConfigError, StructlogBaseError)
        assert issubclass(StructlogConfigFileNotFoundError, StructlogBaseError)
        assert issubclass(StructlogConfigParseError, StructlogBaseError)
        assert issubclass(StructlogConfigVersionError, StructlogBaseError)
        assert issubclass(StructlogHandlerError, StructlogBaseError)
        assert issubclass(StructlogNotInitedError, StructlogBaseError)
        assert issubclass(StructlogProcessorError, StructlogBaseError)
        assert issubclass(StructlogProcessorImportError, StructlogBaseError)
        assert issubclass(StructlogProcessorInstantiateError, StructlogBaseError)

    def test_version_dynamic_access(self):
        """测试 __version__ 动态属性访问"""
        from tkzs_structlog import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_in_all(self):
        """测试 __version__ 在 __all__ 中"""
        from tkzs_structlog import __all__

        assert "__version__" in __all__

    def test_all_api_exports(self):
        """测试所有核心 API 可从根包导入"""
        from tkzs_structlog import (
            bind_context,
            clear_context,
            get_logger,
            init_structlog,
            is_initialized,
            reset_structlog,
            unbind_context,
        )

        assert callable(init_structlog)
        assert callable(get_logger)
        assert callable(bind_context)
        assert callable(unbind_context)
        assert callable(clear_context)
        assert callable(reset_structlog)
        assert callable(is_initialized)

    def test_config_exports(self):
        """测试配置模块可从根包导入"""
        from tkzs_structlog import (
            DEFAULT_CONFIG,
            SUPPORTED_VERSIONS,
            get_default_config,
            load_config,
            validate_config,
        )

        assert DEFAULT_CONFIG is not None
        assert SUPPORTED_VERSIONS is not None
        assert callable(get_default_config)
        assert callable(load_config)
        assert callable(validate_config)

    def test_core_exports(self):
        """测试核心模块可从根包导入"""
        from tkzs_structlog import (
            LoggerFactory,
            ProcessorBuilder,
            StructlogInitializer,
        )

        assert StructlogInitializer is not None
        assert ProcessorBuilder is not None
        assert LoggerFactory is not None

    def test_attribute_error_for_unknown_attr(self):
        """测试访问不存在的属性抛出 AttributeError"""
        import tkzs_structlog

        with pytest.raises(AttributeError):
            _ = tkzs_structlog.nonexistent_attr_xyz
