"""tkzs-structlog 处理器构建模块

D2: 负责构建和实例化 structlog 处理器链。
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, Callable

from tkzs_structlog.exceptions import (
    StructlogProcessorImportError,
    StructlogProcessorInstantiateError,
)

# 内置处理器映射（快速访问）
BUILTIN_PROCESSORS: dict[str, Callable[..., Any]] = {}


def _import_processor(processor_path: str) -> Callable[..., Any]:
    """动态导入处理器

    Args:
        processor_path: 处理器路径，如 "structlog.processors.TimeStamper"

    Returns:
        处理器类或函数

    Raises:
        StructlogProcessorImportError: 处理器导入失败
    """
    try:
        module_path, class_name = processor_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)  # type: ignore[no-any-return]
    except (ValueError, ImportError, AttributeError) as e:
        raise StructlogProcessorImportError(
            processor_path=processor_path,
            reason=f"Failed to import processor: {processor_path}. Error: {str(e)}",
        )


@lru_cache(maxsize=256)
def get_processor_class(processor_path: str) -> Callable[..., Any]:
    """获取处理器类（带缓存）

    Args:
        processor_path: 处理器路径

    Returns:
        处理器类或函数
    """
    return _import_processor(processor_path)


class ProcessorBuilder:
    """处理器构建器

    负责将配置中的处理器字符串路径转换为实际的处理器实例。
    """

    def __init__(self) -> None:
        self._processor_cache: dict[str, Any] = {}

    def build(
        self,
        processor_specs: list[str],
        processor_kwargs: dict[str, dict[str, Any]] | None = None,
    ) -> list[Any]:
        """构建处理器链

        Args:
            processor_specs: 处理器路径列表
            processor_kwargs: 处理器参数映射，key 为处理器名称，value 为参数字典

        Returns:
            处理器实例列表

        Raises:
            StructlogProcessorInstantiateError: 处理器实例化失败
        """
        if processor_kwargs is None:
            processor_kwargs = {}

        processors: list[Any] = []
        for spec in processor_specs:
            try:
                processor = self._build_processor(spec, processor_kwargs.get(spec, {}))
                processors.append(processor)
            except StructlogProcessorImportError:
                raise
            except Exception as e:
                raise StructlogProcessorInstantiateError(
                    processor_name=spec,
                    reason=f"Failed to instantiate processor: {spec}. Error: {str(e)}",
                )

        return processors

    def _build_processor(
        self,
        processor_spec: str,
        kwargs: dict[str, Any],
    ) -> Any:
        """构建单个处理器

        Args:
            processor_spec: 处理器路径
            kwargs: 处理器参数

        Returns:
            处理器实例或函数
        """
        # 检查缓存
        cache_key = f"{processor_spec}:{str(kwargs)}"
        if cache_key in self._processor_cache:
            return self._processor_cache[cache_key]

        # 获取处理器类或函数
        processor_cls = get_processor_class(processor_spec)

        # 如果是函数（不是类），直接返回
        # structlog 过滤器函数不需要实例化
        if not isinstance(processor_cls, type):
            processor = processor_cls
        elif kwargs:
            processor = processor_cls(**kwargs)
        else:
            processor = processor_cls()

        # 缓存实例
        self._processor_cache[cache_key] = processor

        return processor

    def clear_cache(self) -> None:
        """清空处理器缓存"""
        self._processor_cache.clear()
        get_processor_class.cache_clear()


# 全局处理器构建器实例
_default_builder: ProcessorBuilder | None = None


def get_processor_builder() -> ProcessorBuilder:
    """获取全局处理器构建器

    Returns:
        ProcessorBuilder 实例
    """
    global _default_builder
    if _default_builder is None:
        _default_builder = ProcessorBuilder()
    return _default_builder


def reset_processor_builder() -> None:
    """重置全局处理器构建器"""
    global _default_builder
    if _default_builder is not None:
        _default_builder.clear_cache()
    _default_builder = None
