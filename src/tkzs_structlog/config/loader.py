"""tkzs-structlog 配置加载模块

支持 JSONC 配置文件加载、环境变量适配、多环境配置。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pyjson5

from tkzs_structlog.config.defaults import get_default_config, merge_config
from tkzs_structlog.exceptions import (
    StructlogConfigFileNotFoundError,
    StructlogConfigParseError,
)


def get_default_config_path() -> Path:
    """获取默认配置文件路径

    依次查找：
    1. 当前工作目录
    2. 项目根目录（向上查找）
    """
    cwd = Path.cwd()
    root = Path(__file__).parent.parent.parent.parent  # 项目根目录

    for base_dir in [cwd, root]:
        config_path = base_dir / "structlog_config.json"
        if config_path.exists():
            return config_path

    return cwd / "structlog_config.json"


def get_env_config_path(env: str | None = None) -> Path | None:
    """获取环境特定配置文件路径

    Args:
        env: 环境名称，如 "dev", "prod", "test"

    Returns:
        环境配置文件路径，若不存在返回 None
    """
    if env is None:
        env = os.environ.get("STRUCTLOG_ENV", "")

    if not env:
        return None

    default_path = get_default_config_path()
    env_path = default_path.parent / f"structlog_config.{env}.json"

    if env_path.exists():
        return env_path

    return None


def load_config_file(config_path: str | Path) -> dict[str, Any]:
    """加载配置文件

    支持 JSON 和 JSONC（带注释的 JSON）格式。

    Args:
        config_path: 配置文件路径

    Returns:
        解析后的配置字典

    Raises:
        StructlogConfigFileNotFoundError: 配置文件不存在
        StructlogConfigParseError: 配置文件解析失败
    """
    path = Path(config_path)

    if not path.exists():
        raise StructlogConfigFileNotFoundError(
            config_path=str(path),
            reason=f"Configuration file not found: {path}",
        )

    if path.is_dir():
        raise StructlogConfigFileNotFoundError(
            config_path=str(path),
            reason="Config path is a directory, not a file",
        )

    try:
        # 尝试 UTF-8 编码读取
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试带错误替换的读取
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        # 尝试 JSONC 解析（支持注释）
        try:
            config = pyjson5.loads(content)
        except Exception:
            # JSONC 解析失败，尝试标准 JSON
            config = json.loads(content)

        if not isinstance(config, dict):
            raise StructlogConfigParseError(
                config_path=str(path),
                reason="Config file must contain a JSON object",
            )

        return config

    except StructlogConfigFileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise StructlogConfigParseError(
            config_path=str(path),
            reason=f"Invalid JSON syntax: {e.msg} at line {e.lineno}, column {e.colno}",
            fix_suggestion="Please check the JSON syntax, ensure all quotes and brackets are balanced",
        )
    except Exception as e:
        raise StructlogConfigParseError(
            config_path=str(path),
            reason=f"Failed to parse config file: {str(e)}",
        )


def load_config(
    config_path: str | Path | None = None,
    use_env: bool = True,
    use_default: bool = True,
) -> dict[str, Any]:
    """加载配置，支持多级降级

    加载优先级：
    1. 自定义配置文件（config_path）
    2. 环境特定配置（structlog_config.{env}.json）
    3. 默认配置（structlog_config.json）
    4. 内置默认配置

    Args:
        config_path: 自定义配置文件路径
        use_env: 是否使用环境特定配置
        use_default: 是否使用内置默认配置

    Returns:
        加载的配置字典
    """
    config: dict[str, Any] = {}

    # 1. 尝试自定义配置
    if config_path:
        config = load_config_file(config_path)
    else:
        # 2. 尝试环境特定配置
        if use_env:
            env_path = get_env_config_path()
            if env_path:
                config = load_config_file(env_path)

        # 3. 尝试默认配置文件
        if not config:
            default_path = get_default_config_path()
            if default_path.exists():
                config = load_config_file(default_path)

    # 4. 使用内置默认配置填充
    if not config and use_default:
        config = get_default_config(config.get("version"))

    # 5. 与默认配置合并，确保所有字段存在
    if use_default:
        version = config.get("version") if config else None
        default = get_default_config(version)
        config = merge_config(default, config)

    return config
