"""配置加载模块测试"""

import json
import tempfile
from pathlib import Path

import pytest

from tkzs_structlog.config.defaults import (
    get_default_config,
    merge_config,
)
from tkzs_structlog.config.loader import (
    get_default_config_path,
    get_env_config_path,
    load_config,
    load_config_file,
)
from tkzs_structlog.config.validator import (
    SUPPORTED_VERSIONS,
    StructlogV1Config,
    validate_config,
)
from tkzs_structlog.exceptions import (
    StructlogConfigFileNotFoundError,
    StructlogConfigParseError,
    StructlogConfigVersionError,
)


class TestDefaultConfig:
    """测试默认配置"""

    def test_get_default_config_returns_dict(self):
        """测试返回字典"""
        config = get_default_config()
        assert isinstance(config, dict)

    def test_get_default_config_with_version(self):
        """测试指定版本"""
        config_v1 = get_default_config("1.0")
        assert config_v1["version"] == "1.0"

        config_v2 = get_default_config("2.0")
        assert config_v2["version"] == "2.0"

    def test_default_config_has_required_fields(self):
        """测试默认配置包含必需字段"""
        config = get_default_config()
        assert "version" in config
        assert "logger_name" in config
        assert "min_level" in config
        assert "handlers" in config


class TestMergeConfig:
    """测试配置合并"""

    def test_merge_basic(self):
        """测试基础合并"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_config(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested(self):
        """测试嵌套合并"""
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"c": 3, "d": 4}}
        result = merge_config(base, override)
        assert result == {"a": {"b": 1, "c": 3, "d": 4}}

    def test_merge_empty_override(self):
        """测试空覆盖"""
        base = {"a": 1}
        result = merge_config(base, {})
        assert result == {"a": 1}


class TestLoadConfigFile:
    """测试配置文件加载"""

    def test_load_valid_json(self):
        """测试加载有效 JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "1.0", "logger_name": "test"}, f)
            f.flush()
            path = f.name

        try:
            config = load_config_file(path)
            assert config["version"] == "1.0"
            assert config["logger_name"] == "test"
        finally:
            Path(path).unlink()

    def test_load_valid_jsonc(self):
        """测试加载有效 JSONC（带注释）"""
        content = """
        {
            "version": "1.0",
            // 这是注释
            "logger_name": "test"
        }
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(content)
            f.flush()
            path = f.name

        try:
            config = load_config_file(path)
            assert config["version"] == "1.0"
            assert config["logger_name"] == "test"
        finally:
            Path(path).unlink()

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(StructlogConfigFileNotFoundError):
            load_config_file("/nonexistent/path/config.json")

    def test_load_invalid_json(self):
        """测试加载无效 JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            f.flush()
            path = f.name

        try:
            with pytest.raises(StructlogConfigParseError):
                load_config_file(path)
        finally:
            Path(path).unlink()

    def test_load_empty_file_returns_empty_dict(self):
        """空文件降级为空字典，后续 load_config 合并内置默认"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            f.flush()
            path = f.name

        try:
            config = load_config_file(path)
            assert config == {}
        finally:
            Path(path).unlink()

    def test_load_comment_only_file_returns_empty_dict(self):
        """仅注释的文件降级为空字典"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("// only comment\n")
            f.flush()
            path = f.name

        try:
            config = load_config_file(path)
            assert config == {}
        finally:
            Path(path).unlink()


class TestLoadConfig:
    """测试配置加载（多级降级）"""

    def test_load_with_custom_config(self):
        """测试自定义配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "1.0", "logger_name": "custom"}, f)
            f.flush()
            path = f.name

        try:
            config = load_config(path)
            assert config["logger_name"] == "custom"
            # 应该合并默认配置
            assert "handlers" in config
        finally:
            Path(path).unlink()

    def test_load_without_file(self):
        """测试无配置文件时使用默认"""
        config = load_config(None)
        assert isinstance(config, dict)
        assert "version" in config


class TestValidateConfig:
    """测试配置校验"""

    def test_validate_v1_config(self):
        """测试 V1 配置校验"""
        config = {
            "version": "1.0",
            "logger_name": "test",
            "min_level": "INFO",
        }
        validated = validate_config(config)
        assert isinstance(validated, StructlogV1Config)
        assert validated.version == "1.0"
        assert validated.logger_name == "test"

    def test_validate_normalizes_warn_level(self):
        """测试 WARN 级别标准化"""
        config = {
            "version": "1.0",
            "min_level": "WARN",
        }
        validated = validate_config(config)
        assert validated.min_level == "WARNING"

    def test_validate_invalid_version(self):
        """测试无效版本"""
        config = {"version": "99.0"}
        with pytest.raises(StructlogConfigVersionError):
            validate_config(config)

    def test_supported_versions(self):
        """测试支持的版本列表"""
        assert "1.0" in SUPPORTED_VERSIONS
        assert "2.0" in SUPPORTED_VERSIONS
        assert "2.1" in SUPPORTED_VERSIONS

    def test_validate_v2_config(self):
        """测试 V2 配置校验"""
        config = {
            "version": "2.0",
            "logger_name": "test",
            "extensions": {
                "sensitive_fields": ["password", "token"],
            },
        }
        validated = validate_config(config)
        assert validated.version == "2.0"
        assert validated.extensions.sensitive_fields == ["password", "token"]


class TestGetConfigModel:
    """测试获取配置模型"""

    def test_get_config_model_with_version(self):
        """测试指定版本获取模型"""
        from tkzs_structlog.config.validator import StructlogV2Config, get_config_model

        model = get_config_model("2.0")
        assert model == StructlogV2Config

    def test_get_config_model_none_defaults_to_v21(self):
        """测试版本为 None 时默认返回 V2.1 模型"""
        from tkzs_structlog.config.validator import StructlogV21Config, get_config_model

        model = get_config_model(None)
        assert model == StructlogV21Config

    def test_get_config_model_unknown_version(self):
        """测试未知版本返回 V2.1 模型"""
        from tkzs_structlog.config.validator import StructlogV21Config, get_config_model

        model = get_config_model("99.0")
        assert model == StructlogV21Config


class TestGetDefaultConfigPath:
    """测试获取默认配置路径"""

    def test_get_default_config_path_returns_path(self):
        """测试返回 Path 对象"""
        path = get_default_config_path()
        assert isinstance(path, Path)

    def test_get_default_config_path_has_filename(self):
        """测试路径包含配置文件名"""
        path = get_default_config_path()
        assert path.name == "structlog_config.json"


class TestGetEnvConfigPath:
    """测试环境配置文件路径获取"""

    def test_get_env_config_path_no_env(self):
        """测试没有环境变量时返回 None"""
        import os

        # 清除环境变量
        env_backup = os.environ.pop("STRUCTLOG_ENV", None)
        try:
            result = get_env_config_path()
            assert result is None
        finally:
            if env_backup:
                os.environ["STRUCTLOG_ENV"] = env_backup

    def test_get_env_config_path_empty_env(self):
        """测试空环境变量时返回 None"""
        result = get_env_config_path("")
        assert result is None


class TestLoadConfigFileEdgeCases:
    """测试配置文件加载边界情况"""

    def test_load_config_directory_raises_error(self):
        """测试目录路径抛出错误"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(StructlogConfigFileNotFoundError):
                load_config_file(tmpdir)

    def test_load_config_non_dict_raises_error(self):
        """测试非字典配置抛出错误"""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('"not a dict"')
            f.flush()
            path = f.name

        try:
            with pytest.raises(StructlogConfigParseError):
                load_config_file(path)
        finally:
            Path(path).unlink()

    def test_load_config_reraises_structlog_error(self):
        """测试 StructlogConfigFileNotFoundError 正确重抛"""
        with pytest.raises(StructlogConfigFileNotFoundError):
            load_config_file("/nonexistent/path/config.json")

    def test_load_config_with_env_var(self, monkeypatch):
        """测试环境变量指定配置文件"""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建环境配置文件
            env_file = Path(tmpdir) / "structlog_config.test_env.json"
            env_file.write_text('{"version": "1.0", "logger_name": "env_test"}', encoding="utf-8")

            # 设置环境变量
            monkeypatch.setenv("STRUCTLOG_ENV", "test_env")
            monkeypatch.setenv("STRUCTLOG_CONFIG_DIR", tmpdir)

            # 使用临时配置路径
            config = load_config(None)
            # 验证返回的是字典
            assert isinstance(config, dict)
        finally:
            # 手动清理
            import shutil

            if Path(tmpdir).exists():
                shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_config_use_env_false(self, monkeypatch):
        """测试禁用环境配置"""

        monkeypatch.setenv("STRUCTLOG_ENV", "some_env")

        # 传入 use_env=False，应该忽略环境变量
        config = load_config(None, use_env=False, use_default=True)
        assert isinstance(config, dict)

    def test_load_config_use_default_false(self, tmp_path):
        """测试禁用默认配置"""
        # 创建自定义配置
        config_file = tmp_path / "custom.json"
        config_file.write_text('{"version": "1.0", "custom_field": "value"}', encoding="utf-8")

        # 禁用默认配置合并
        config = load_config(str(config_file), use_default=False)
        # 应该只返回自定义配置
        assert "custom_field" in config
        assert "handlers" not in config

    def test_get_env_config_path_with_existing_file(self, tmp_path, monkeypatch):
        """测试获取存在的环境配置路径"""
        env_file = tmp_path / "structlog_config.dev.json"
        env_file.write_text('{"version": "1.0"}', encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("STRUCTLOG_ENV", "dev")

        result = get_env_config_path()
        assert result is not None
        assert "dev" in str(result)

    def test_get_env_config_path_nonexistent_env(self, tmp_path, monkeypatch):
        """测试不存在的环境配置"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("STRUCTLOG_ENV", "nonexistent_env")

        result = get_env_config_path()
        assert result is None


class TestGetDefaultConfigPathCwdBranch:
    """测试 get_default_config_path cwd 分支（行 35）"""

    def test_returns_cwd_path_when_config_exists_in_cwd(self, monkeypatch, tmp_path):
        """当 cwd 存在 structlog_config.json 时返回 cwd 路径"""
        # 在 tmp_path 创建配置文件
        config_file = tmp_path / "structlog_config.json"
        config_file.write_text('{"version": "1.0"}', encoding="utf-8")

        # 切换 cwd 到 tmp_path（此时 cwd 有配置文件）
        monkeypatch.chdir(tmp_path)

        result = get_default_config_path()
        assert result == config_file

    def test_returns_cwd_path_when_cwd_has_config_env_also_exists(self, monkeypatch, tmp_path):
        """cwd 有配置文件时优先于 root（行 35 覆盖）"""
        config_file = tmp_path / "structlog_config.json"
        config_file.write_text('{"version": "1.0"}', encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        # 多次调用，结果应一致
        result1 = get_default_config_path()
        result2 = get_default_config_path()
        assert result1 == result2 == config_file


class TestLoadConfigEnvAndDefaultFile:
    """测试 load_config 加载环境配置和默认配置文件（行 172, 178）"""

    def test_load_config_loads_env_file_when_it_exists(self, monkeypatch, tmp_path):
        """当环境配置文件存在时，加载该文件（行 172）"""
        env_file = tmp_path / "structlog_config.dev.json"
        env_file.write_text('{"version": "1.0", "logger_name": "from_env_file"}', encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("STRUCTLOG_ENV", "dev")

        config = load_config(None)  # config_path=None, use_env=True
        assert config["logger_name"] == "from_env_file"

    def test_load_config_loads_default_file_when_no_custom_or_env(self, monkeypatch, tmp_path):
        """当无 config_path 且无 env 时，加载默认配置文件（行 178）"""
        # 在 tmp_path 创建默认配置文件（cwd 有，但无 env）
        default_file = tmp_path / "structlog_config.json"
        default_file.write_text('{"version": "1.0", "logger_name": "from_default_file"}', encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("STRUCTLOG_ENV", raising=False)

        config = load_config(None)  # 无 config_path，无 env
        assert config["logger_name"] == "from_default_file"

    def test_load_config_prefers_env_over_default(self, monkeypatch, tmp_path):
        """环境配置文件优先于默认配置文件"""
        env_file = tmp_path / "structlog_config.prod.json"
        env_file.write_text('{"version": "1.0", "logger_name": "prod_logger"}', encoding="utf-8")
        default_file = tmp_path / "structlog_config.json"
        default_file.write_text('{"version": "1.0", "logger_name": "default_logger"}', encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("STRUCTLOG_ENV", "prod")

        config = load_config(None)
        assert config["logger_name"] == "prod_logger"
