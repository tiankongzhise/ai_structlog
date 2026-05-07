"""处理器构建模块测试"""

import pytest

from tkzs_structlog.core.processor_builder import (
    ProcessorBuilder,
    get_processor_builder,
    get_processor_class,
    reset_processor_builder,
)
from tkzs_structlog.exceptions import (
    StructlogProcessorImportError,
    StructlogProcessorInstantiateError,
)


class TestProcessorBuilder:
    """测试处理器构建器"""

    def setup_method(self):
        """每个测试前重置"""
        reset_processor_builder()

    def teardown_method(self):
        """每个测试后重置"""
        reset_processor_builder()

    def test_build_basic_processors(self):
        """测试构建基础处理器"""
        builder = ProcessorBuilder()
        specs = [
            "structlog.processors.TimeStamper",
            "structlog.processors.StackInfoRenderer",
        ]
        processors = builder.build(specs)
        assert len(processors) == 2

    def test_build_with_kwargs(self):
        """测试带参数的处理器构建"""
        builder = ProcessorBuilder()
        specs = ["structlog.processors.TimeStamper"]
        kwargs = {"structlog.processors.TimeStamper": {"fmt": "%Y-%m-%d", "utc": True}}
        processors = builder.build(specs, kwargs)
        assert len(processors) == 1

    def test_build_invalid_processor(self):
        """测试构建无效处理器"""
        builder = ProcessorBuilder()
        specs = ["nonexistent.module.Processor"]
        with pytest.raises(StructlogProcessorImportError):
            builder.build(specs)

    def test_cache_processors(self):
        """测试处理器缓存"""
        builder = ProcessorBuilder()
        specs = ["structlog.processors.TimeStamper"]

        p1 = builder.build(specs)
        p2 = builder.build(specs)
        # 应该是同一实例
        assert p1[0] is p2[0]

    def test_clear_cache(self):
        """测试清空缓存"""
        builder = ProcessorBuilder()
        specs = ["structlog.processors.TimeStamper"]
        builder.build(specs)
        builder.clear_cache()
        # 清空后应该能重新构建
        p = builder.build(specs)
        assert len(p) == 1

    def test_get_global_builder(self):
        """测试获取全局构建器"""
        builder1 = get_processor_builder()
        builder2 = get_processor_builder()
        assert builder1 is builder2


class TestGetProcessorClass:
    """测试获取处理器类"""

    def test_get_valid_processor(self):
        """测试获取有效处理器"""
        cls = get_processor_class("structlog.processors.TimeStamper")
        assert cls is not None

    def test_get_invalid_processor(self):
        """测试获取无效处理器"""
        with pytest.raises(StructlogProcessorImportError):
            get_processor_class("nonexistent.module.Class")


class TestProcessorInstantiationError:
    """测试处理器实例化错误"""

    def test_instantiation_error(self):
        """测试处理器实例化失败时抛出 StructlogProcessorInstantiateError"""
        from tkzs_structlog.exceptions import StructlogProcessorInstantiateError
        import sys
        import types

        builder = ProcessorBuilder()

        # 创建一个可以导入但实例化失败的处理器
        test_module = types.ModuleType("test_failing_processor")
        sys.modules["test_failing_processor"] = test_module

        class FailingProcessor:
            def __init__(self):
                raise ValueError("Intentional failure")

        test_module.FailingProcessor = FailingProcessor

        try:
            specs = ["test_failing_processor.FailingProcessor"]
            with pytest.raises(StructlogProcessorInstantiateError):
                builder.build(specs)
        finally:
            del sys.modules["test_failing_processor"]


class TestFunctionProcessor:
    """测试函数类型处理器"""

    def test_function_processor_not_instantiated(self):
        """测试函数类型处理器不需要实例化"""
        import sys
        import types

        builder = ProcessorBuilder()

        # 创建一个函数类型的处理器
        test_module = types.ModuleType("test_function_processor")
        sys.modules["test_function_processor"] = test_module

        def test_filter_processor(logger, method_name, event_dict):
            """测试用的过滤器函数（不是类）"""
            return event_dict

        test_module.TestFilterProcessor = test_filter_processor

        try:
            specs = ["test_function_processor.TestFilterProcessor"]
            processors = builder.build(specs)
            assert len(processors) == 1
            # 函数类型处理器应该直接返回函数本身
            assert processors[0] is test_filter_processor
        finally:
            del sys.modules["test_function_processor"]
