"""异常模块测试"""

from tkzs_structlog.exceptions import (
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


class TestStructlogBaseError:
    """测试基础异常"""

    def test_basic_error(self):
        """测试基础错误"""
        error = StructlogBaseError(
            error_type="TestError",
            error_field="test_field",
            reason="Test reason",
            fix_suggestion="Fix this",
        )
        assert error.error_type == "TestError"
        assert error.error_field == "test_field"
        assert error.reason == "Test reason"
        assert error.fix_suggestion == "Fix this"
        assert "TestError" in str(error)

    def test_error_without_optional_fields(self):
        """测试可选字段为空"""
        error = StructlogBaseError(error_type="TestError")
        assert error.error_type == "TestError"
        assert error.error_field is None
        assert error.reason is None
        assert error.fix_suggestion is None

    def test_repr(self):
        """测试 __repr__ 方法"""
        error = StructlogBaseError(
            error_type="TestError",
            error_field="test_field",
            reason="Test reason",
            fix_suggestion="Fix this",
        )
        # 显式调用 repr() 覆盖 __repr__ 方法
        error_repr = repr(error)
        assert "StructlogBaseError" in error_repr
        assert "error_type=" in error_repr


class TestStructlogConfigError:
    """测试配置错误"""

    def test_config_error(self):
        """测试配置错误"""
        error = StructlogConfigError(
            error_field="version",
            reason="Invalid version",
            fix_suggestion="Use 1.0",
        )
        assert error.error_type == "ConfigError"
        assert error.error_field == "version"


class TestStructlogConfigFileNotFoundError:
    """测试配置文件未找到错误"""

    def test_file_not_found(self):
        """测试文件未找到"""
        error = StructlogConfigFileNotFoundError(
            config_path="/path/to/config.json",
            reason="Configuration file not found: /path/to/config.json",
        )
        assert error.error_field == "config_path"
        assert "/path/to/config.json" in error.reason


class TestStructlogConfigParseError:
    """测试配置文件解析错误"""

    def test_parse_error(self):
        """测试解析错误"""
        error = StructlogConfigParseError(
            config_path="/path/to/config.json",
            reason="Invalid JSON",
        )
        assert error.error_field == "config_content"


class TestStructlogConfigVersionError:
    """测试配置版本错误"""

    def test_version_error(self):
        """测试版本错误"""
        error = StructlogConfigVersionError(
            version="99.0",
            supported_versions=["1.0", "2.0"],
        )
        assert error.error_field == "version"
        assert "99.0" in error.reason


class TestStructlogProcessorError:
    """测试处理器错误"""

    def test_processor_error(self):
        """测试处理器错误"""
        error = StructlogProcessorError(
            processor_name="MyProcessor",
            reason="Processor failed",
        )
        assert error.error_type == "ProcessorError"
        assert error.error_field == "MyProcessor"


class TestStructlogProcessorImportError:
    """测试处理器导入错误"""

    def test_import_error(self):
        """测试导入错误"""
        error = StructlogProcessorImportError(
            processor_path="nonexistent.Processor",
            reason="Module not found",
        )
        assert error.error_type == "ProcessorError"


class TestStructlogProcessorInstantiateError:
    """测试处理器实例化错误"""

    def test_instantiate_error(self):
        """测试实例化错误"""
        error = StructlogProcessorInstantiateError(
            processor_name="MyProcessor",
            reason="Init failed",
        )
        assert error.error_type == "ProcessorError"


class TestStructlogNotInitedError:
    """测试未初始化错误"""

    def test_not_inited_error(self):
        """测试未初始化错误"""
        error = StructlogNotInitedError()
        assert error.error_type == "NotInitedError"


class TestStructlogHandlerError:
    """测试处理器错误"""

    def test_handler_error(self):
        """测试处理器错误"""
        error = StructlogHandlerError(
            handler_name="console",
            reason="Handler failed",
        )
        assert error.error_type == "HandlerError"
        assert error.error_field == "console"
