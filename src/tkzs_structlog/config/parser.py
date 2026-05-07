"""tkzs-structlog 配置解析模块

将 JSONC 配置解析为 Python dataclass 或 Pydantic 模型，支持缓存。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from tkzs_structlog.config.validator import validate_config


@lru_cache(maxsize=128)
def parse_config_version(config_str: str) -> str:
    """解析配置版本号（带缓存）

    Args:
        config_str: 配置的字符串表示

    Returns:
        版本号
    """
    import json

    try:
        config = json.loads(config_str)
        return config.get("version", "1.0")
    except Exception:
        return "1.0"


def parse_config(config: dict[str, Any]) -> Any:
    """解析配置为 Pydantic 模型

    Args:
        config: 配置字典

    Returns:
        校验后的配置模型
    """
    return validate_config(config)


def config_to_dict(config_model: Any) -> dict[str, Any]:
    """将配置模型转换为字典

    Args:
        config_model: Pydantic 配置模型

    Returns:
        配置字典
    """
    if hasattr(config_model, "model_dump"):
        return config_model.model_dump()
    elif hasattr(config_model, "dict"):
        return config_model.dict()
    return dict(config_model)


def get_processor_names(config: dict[str, Any]) -> list[str]:
    """从配置中获取处理器名称列表

    Args:
        config: 配置字典

    Returns:
        处理器名称列表
    """
    return config.get("processors", [])


def get_handler_config(config: dict[str, Any], handler_name: str) -> dict[str, Any]:
    """获取指定处理器的配置

    Args:
        config: 配置字典
        handler_name: 处理器名称

    Returns:
        处理器配置字典
    """
    handlers = config.get("handlers", {})
    return handlers.get(handler_name, {})


def get_extension_config(config: dict[str, Any], extension_name: str) -> dict[str, Any]:
    """获取指定扩展的配置

    Args:
        config: 配置字典
        extension_name: 扩展名称

    Returns:
        扩展配置字典
    """
    extensions = config.get("extensions", {})
    return extensions.get(extension_name, {})
