"""tkzs-structlog 配置层模块

E1: 配置加载模块
E2: 配置校验模块
E3: 配置解析模块
"""

from tkzs_structlog.config.defaults import (
    DEFAULT_CONFIG,
    get_default_config,
    merge_config,
)
from tkzs_structlog.config.loader import (
    get_default_config_path,
    get_env_config_path,
    load_config,
    load_config_file,
)
from tkzs_structlog.config.parser import (
    config_to_dict,
    get_extension_config,
    get_handler_config,
    get_processor_names,
    parse_config,
)
from tkzs_structlog.config.validator import (
    CONFIG_MODELS,
    SUPPORTED_VERSIONS,
    StructlogV1Config,
    StructlogV2Config,
    StructlogV3Config,
    StructlogV4Config,
    StructlogV21Config,
    get_config_model,
    validate_config,
)

__all__ = [
    # defaults
    "DEFAULT_CONFIG",
    "get_default_config",
    "merge_config",
    # loader
    "get_default_config_path",
    "get_env_config_path",
    "load_config",
    "load_config_file",
    # validator
    "CONFIG_MODELS",
    "SUPPORTED_VERSIONS",
    "StructlogV1Config",
    "StructlogV2Config",
    "StructlogV21Config",
    "StructlogV3Config",
    "StructlogV4Config",
    "get_config_model",
    "validate_config",
    # parser
    "config_to_dict",
    "get_extension_config",
    "get_handler_config",
    "get_processor_names",
    "parse_config",
]
