"""tkzs-structlog 配置校验模块

使用 Pydantic 模型进行配置校验。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class HandlerConsoleConfig(BaseModel):
    """控制台处理器配置"""

    enable: bool = True


class HandlerFileRotateConfig(BaseModel):
    """文件轮转配置"""

    enable: bool = False
    max_bytes: int = Field(default=10485760, ge=0)  # 10MB
    backup_count: int = Field(default=10, ge=0)
    retain_days: int = Field(default=7, ge=0)
    rotate_when: Literal["H", "D", "MIDNIGHT", "W0", "W6"] = "MIDNIGHT"
    interval: int = Field(default=1, ge=1)
    compress: bool = False
    compress_method: Literal["gzip", "lz4", "zstd"] = "gzip"
    compress_concurrency: int = Field(default=2, ge=1, le=10)
    compress_async: bool = True


class HandlerFileConfig(BaseModel):
    """文件处理器配置"""

    enable: bool = False
    file_path: str = "./logs/structlog.log"
    encoding: str = "utf-8"
    custom_rotate: HandlerFileRotateConfig | None = None


class HandlerPgsqlConfig(BaseModel):
    """PGSQL 处理器配置"""

    enable: bool = False
    table_name: str = "structlog_logs"
    batch_size: int = Field(default=100, ge=1, le=1000)
    flush_interval: int = Field(default=5, ge=1, le=60)
    pool_size: int = Field(default=5, ge=1, le=20)


class HandlerRedisConfig(BaseModel):
    """Redis 处理器配置"""

    enable: bool = False
    key_prefix: str = "structlog:"
    batch_size: int = Field(default=100, ge=1, le=1000)
    flush_interval: int = Field(default=5, ge=1, le=60)


class HandlersConfig(BaseModel):
    """处理器配置"""

    console: HandlerConsoleConfig = Field(default_factory=HandlerConsoleConfig)
    file: HandlerFileConfig = Field(default_factory=HandlerFileConfig)
    pgsql: HandlerPgsqlConfig = Field(default_factory=HandlerPgsqlConfig)
    redis: HandlerRedisConfig = Field(default_factory=HandlerRedisConfig)


class LogTruncateConfig(BaseModel):
    """日志截断配置"""

    enable: bool = False
    max_depth: int = Field(default=3, ge=0)
    str_max_length: int = Field(default=256, ge=0)
    seq_max_elements: int = Field(default=50, ge=0)
    dict_max_pairs: int = Field(default=30, ge=0)
    ignore_types: list[str] = Field(default_factory=list)
    ignore_fields: list[str] = Field(default_factory=list)
    ignore_fields_pattern: list[str] = Field(default_factory=list)
    ignore_fields_regex: str | None = None
    depth_warning: bool = True


class ExtensionsConfig(BaseModel):
    """扩展功能配置"""

    log_truncate: LogTruncateConfig = Field(default_factory=LogTruncateConfig)
    sensitive_fields: list[str] = Field(default_factory=lambda: ["password", "phone", "id_card", "bank_card"])
    trace_id_bind: bool = False
    filter_rules: dict[str, Any] = Field(default_factory=dict)
    config_hot_reload: bool = False
    elk_compatible: bool = False
    sentry_enable: bool = False
    sentry_dsn: str | None = None


class StructlogV1Config(BaseModel):
    """V1.0 版本配置模型"""

    version: str = "1.0"
    logger_name: str = "structlog_auto"
    min_level: Literal["DEBUG", "INFO", "WARN", "ERROR", "WARNING"] = "INFO"
    bridge_std_logging: bool = True
    context_bind: bool = False
    processors: list[str] = Field(
        default_factory=lambda: [
            "structlog.processors.TimeStamper",
            "structlog.dev.ConsoleRenderer",
        ]
    )
    handlers: HandlersConfig = Field(default_factory=HandlersConfig)

    @field_validator("min_level")
    @classmethod
    def normalize_min_level(cls, v: str) -> str:
        """标准化日志级别，WARN 映射为 WARNING"""
        if v == "WARN":
            return "WARNING"
        return v


class StructlogV2Config(StructlogV1Config):
    """V2.0 版本配置模型"""

    version: str = "2.0"
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)


class StructlogV21Config(StructlogV2Config):
    """V2.1 版本配置模型"""

    version: str = "2.1"


class StructlogV3Config(StructlogV21Config):
    """V3.0 版本配置模型"""

    version: str = "3.0"


class StructlogV4Config(StructlogV3Config):
    """V4.0 版本配置模型"""

    version: str = "4.0"


# 版本到模型的映射
CONFIG_MODELS = {
    "1.0": StructlogV1Config,
    "2.0": StructlogV2Config,
    "2.1": StructlogV21Config,
    "3.0": StructlogV3Config,
    "4.0": StructlogV4Config,
}

SUPPORTED_VERSIONS = list(CONFIG_MODELS.keys())


def validate_config(config: dict[str, Any]) -> StructlogV1Config:
    """校验配置

    Args:
        config: 配置字典

    Returns:
        校验后的配置模型

    Raises:
        StructlogConfigVersionError: 不支持的配置版本
        ValidationError: 配置校验失败
    """
    version = config.get("version", "1.0")

    if version not in CONFIG_MODELS:
        from tkzs_structlog.exceptions import StructlogConfigVersionError

        raise StructlogConfigVersionError(
            version=version,
            supported_versions=SUPPORTED_VERSIONS,
        )

    model = CONFIG_MODELS[version]
    return model.model_validate(config)


def get_config_model(version: str | None = None) -> type[StructlogV1Config]:
    """获取指定版本的配置模型

    Args:
        version: 配置版本

    Returns:
        配置模型类
    """
    if version is None:
        version = "2.1"

    return CONFIG_MODELS.get(version, StructlogV21Config)
