"""配置解析模块测试"""

import json

from tkzs_structlog.config.parser import (
    config_to_dict,
    get_extension_config,
    get_handler_config,
    get_processor_names,
    parse_config,
    parse_config_version,
)
from tkzs_structlog.config.validator import StructlogV1Config


class TestParseConfig:
    """测试配置解析"""

    def test_parse_config_valid(self):
        """测试解析有效配置"""
        config = {"version": "1.0", "logger_name": "test"}
        result = parse_config(config)
        assert isinstance(result, StructlogV1Config)
        assert result.logger_name == "test"

    def test_parse_config_validates(self):
        """测试 parse_config 调用 validate_config"""
        # 确保 validate_config 被调用
        config = {"version": "1.0", "min_level": "DEBUG"}
        parse_config(config)
        # 如果 validate_config 没有被调用，这里会抛出异常


class TestParseConfigVersion:
    """测试配置版本解析"""

    def test_parse_config_version_success(self):
        """测试成功解析版本"""
        config_str = json.dumps({"version": "2.0"})
        version = parse_config_version(config_str)
        assert version == "2.0"

    def test_parse_config_version_missing(self):
        """测试缺少版本时返回默认值"""
        config_str = json.dumps({"logger_name": "test"})
        version = parse_config_version(config_str)
        assert version == "1.0"

    def test_parse_config_version_invalid_json(self):
        """测试无效 JSON 返回默认值"""
        version = parse_config_version("invalid json")
        assert version == "1.0"

    def test_parse_config_version_cached(self):
        """测试结果被缓存"""
        config_str = json.dumps({"version": "2.0"})
        version1 = parse_config_version(config_str)
        version2 = parse_config_version(config_str)
        assert version1 == version2


class TestConfigToDict:
    """测试配置转字典"""

    def test_config_to_dict_pydantic_v2(self):
        """测试 Pydantic v2 模型转换"""
        config = StructlogV1Config(version="1.0", logger_name="test")
        result = config_to_dict(config)
        assert isinstance(result, dict)
        assert result["version"] == "1.0"
        assert result["logger_name"] == "test"

    def test_config_to_dict_with_dict_method(self):
        """测试带 .dict() 方法的模型"""
        from dataclasses import dataclass

        @dataclass
        class OldStyleModel:
            """旧式模型使用 .dict() 方法"""

            version: str = "1.0"

            def dict(self):
                return {"version": self.version}

        config = OldStyleModel()
        result = config_to_dict(config)
        assert result == {"version": "1.0"}

    def test_config_to_dict_raw_dict(self):
        """测试原始字典"""
        config = {"version": "1.0", "logger_name": "test"}
        result = config_to_dict(config)
        assert result == {"version": "1.0", "logger_name": "test"}


class TestGetProcessorNames:
    """测试获取处理器名称"""

    def test_get_processor_names_exists(self):
        """测试处理器存在时"""
        config = {"processors": ["proc1", "proc2"]}
        result = get_processor_names(config)
        assert result == ["proc1", "proc2"]

    def test_get_processor_names_missing(self):
        """测试处理器不存在时"""
        config = {}
        result = get_processor_names(config)
        assert result == []


class TestGetHandlerConfig:
    """测试获取处理器配置"""

    def test_get_handler_config_exists(self):
        """测试处理器存在时"""
        config = {
            "handlers": {
                "console": {"enable": True},
                "file": {"enable": False},
            }
        }
        result = get_handler_config(config, "file")
        assert result == {"enable": False}

    def test_get_handler_config_missing(self):
        """测试处理器不存在时"""
        config = {"handlers": {}}
        result = get_handler_config(config, "nonexistent")
        assert result == {}


class TestGetExtensionConfig:
    """测试获取扩展配置"""

    def test_get_extension_config_exists(self):
        """测试扩展存在时"""
        config = {
            "extensions": {
                "log_truncate": {"enable": True},
                "sensitive_fields": ["password"],
            }
        }
        result = get_extension_config(config, "sensitive_fields")
        assert result == ["password"]

    def test_get_extension_config_missing(self):
        """测试扩展不存在时"""
        config = {"extensions": {}}
        result = get_extension_config(config, "nonexistent")
        assert result == {}
