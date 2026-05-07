"""tkzs-structlog 默认配置模块

定义内置默认配置，配置缺失时自动使用此默认值。
"""

from __future__ import annotations

from typing import Any

# V1.0 基础配置
DEFAULT_CONFIG_V1: dict[str, Any] = {
    "version": "1.0",
    "logger_name": "structlog_auto",
    "min_level": "INFO",
    "bridge_std_logging": True,
    "context_bind": False,
    "processors": [
        "structlog.processors.TimeStamper",
        "structlog.dev.ConsoleRenderer",
    ],
    "handlers": {
        "console": {"enable": True},
        "file": {
            "enable": False,
            "file_path": "./logs/structlog.log",
            "encoding": "utf-8",
        },
    },
}

# V2.0 增强配置
DEFAULT_CONFIG_V2: dict[str, Any] = {
    **DEFAULT_CONFIG_V1,
    "version": "2.0",
    "extensions": {
        "log_truncate": {
            "enable": False,
            "max_depth": 3,
            "str_max_length": 256,
            "seq_max_elements": 50,
            "dict_max_pairs": 30,
            "ignore_types": [],
            "ignore_fields": [],
        },
        "sensitive_fields": ["password", "phone", "id_card", "bank_card"],
        "trace_id_bind": False,
        "filter_rules": {"exclude": [], "include": []},
        "config_hot_reload": False,
        "elk_compatible": False,
        "sentry_enable": False,
        "sentry_dsn": None,
    },
    "handlers": {
        **DEFAULT_CONFIG_V1["handlers"],
        "file": {
            **DEFAULT_CONFIG_V1["handlers"]["file"],
            "custom_rotate": {
                "enable": False,
                "max_bytes": 10485760,  # 10MB
                "backup_count": 10,
                "retain_days": 7,
                "rotate_when": "MIDNIGHT",
                "interval": 1,
                "compress": False,
                "compress_method": "gzip",
                "compress_concurrency": 2,
                "compress_async": True,
            },
        },
    },
}

# V2.1 优化配置
DEFAULT_CONFIG_V21: dict[str, Any] = {
    **DEFAULT_CONFIG_V2,
    "version": "2.1",
    "extensions": {
        **DEFAULT_CONFIG_V2["extensions"],
        "log_truncate": {
            **DEFAULT_CONFIG_V2["extensions"]["log_truncate"],
            "ignore_fields_pattern": [],
            "ignore_fields_regex": None,
            "depth_warning": True,
        },
    },
}

# 当前最新版本默认配置
DEFAULT_CONFIG = DEFAULT_CONFIG_V21


def get_default_config(version: str | None = None) -> dict[str, Any]:
    """获取指定版本的默认配置

    Args:
        version: 配置版本号，如 "1.0", "2.0", "2.1" 等

    Returns:
        指定版本的默认配置字典
    """
    version_map = {
        "1.0": DEFAULT_CONFIG_V1,
        "2.0": DEFAULT_CONFIG_V2,
        "2.1": DEFAULT_CONFIG_V21,
    }

    if version is None:
        return DEFAULT_CONFIG.copy()

    return version_map.get(version, DEFAULT_CONFIG.copy())


def merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并配置字典

    Args:
        base: 基础配置
        override: 覆盖配置

    Returns:
        合并后的配置字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
