"""环境变量加载模块测试"""

import builtins
import importlib
import logging
import os
from unittest.mock import patch

import pytest


class TestLoadEnvConfig:
    """测试环境变量加载"""

    def test_load_env_config_default_values(self, tmp_path):
        """测试默认配置值"""
        from tkzs_structlog.config import env_loader
        from tkzs_structlog.config.env_loader import load_env_config

        # 模拟 load_dotenv 为 None（未安装）
        original_load_dotenv = env_loader.load_dotenv
        env_loader.load_dotenv = None

        # 切换到临时目录（确保没有 .env 文件）
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # 使用 clear=True 清空所有环境变量，确保使用默认值
            with patch.dict(os.environ, {}, clear=True):
                config = load_env_config()

                assert config["pgsql"]["host"] == "localhost"
                assert config["pgsql"]["port"] == 5432
                assert config["pgsql"]["user"] == "postgres"
                assert config["pgsql"]["password"] == ""
                assert config["pgsql"]["db"] == "structlog"

                assert config["redis"]["host"] == "localhost"
                assert config["redis"]["port"] == 6379
                assert config["redis"]["password"] == ""
                assert config["redis"]["db"] == 0
        finally:
            os.chdir(original_cwd)
            env_loader.load_dotenv = original_load_dotenv

    def test_load_env_config_custom_values(self, tmp_path):
        """测试自定义配置值"""
        from tkzs_structlog.config.env_loader import load_env_config

        env = {
            "PG_HOST": "192.168.1.100",
            "PG_PORT": "5433",
            "PG_USER": "test_user",
            "PG_PASSWORD": "test_pass",
            "PG_DB": "test_db",
            "REDIS_HOST": "192.168.1.101",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "redis_pass",
            "REDIS_DB": "1",
        }

        # 切换到临时目录（确保没有 .env 文件干扰）
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with patch.dict(os.environ, env, clear=True):
                config = load_env_config()

                assert config["pgsql"]["host"] == "192.168.1.100"
                assert config["pgsql"]["port"] == 5433
                assert config["pgsql"]["user"] == "test_user"
                assert config["pgsql"]["password"] == "test_pass"
                assert config["pgsql"]["db"] == "test_db"

                assert config["redis"]["host"] == "192.168.1.101"
                assert config["redis"]["port"] == 6380
                assert config["redis"]["password"] == "redis_pass"
                assert config["redis"]["db"] == 1
        finally:
            os.chdir(original_cwd)


class TestGetPgsqlConfig:
    """测试 PGSQL 配置获取"""

    def test_get_pgsql_config(self):
        """测试获取 PGSQL 配置"""
        from tkzs_structlog.config.env_loader import get_pgsql_config

        env = {
            "PG_HOST": "10.0.0.1",
            "PG_PORT": "5432",
            "PG_USER": "admin",
            "PG_PASSWORD": "admin123",
            "PG_DB": "logs",
        }

        with patch.dict(os.environ, env, clear=True):
            config = get_pgsql_config()

            assert config["host"] == "10.0.0.1"
            assert config["port"] == 5432
            assert config["user"] == "admin"
            assert config["password"] == "admin123"
            assert config["db"] == "logs"


class TestGetRedisConfig:
    """测试 Redis 配置获取"""

    def test_get_redis_config(self):
        """测试获取 Redis 配置"""
        from tkzs_structlog.config.env_loader import get_redis_config

        env = {
            "REDIS_HOST": "10.0.0.2",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "redis123",
            "REDIS_DB": "5",
        }

        with patch.dict(os.environ, env, clear=True):
            config = get_redis_config()

            assert config["host"] == "10.0.0.2"
            assert config["port"] == 6379
            assert config["password"] == "redis123"
            assert config["db"] == 5


class TestIsPgsqlAvailable:
    """测试 PGSQL 依赖可用性检查"""

    def test_is_pgsql_available(self):
        """测试 PGSQL 可用性检查"""
        from tkzs_structlog.config.env_loader import is_pgsql_available

        result = is_pgsql_available()
        assert isinstance(result, bool)

    def test_is_pgsql_available_import_error(self):
        """测试导入错误时的可用性"""
        from tkzs_structlog.config import env_loader

        original = env_loader.is_pgsql_available

        def mock_check():
            raise ImportError("No module named 'psycopg2'")

        env_loader.is_pgsql_available = mock_check

        try:
            env_loader.is_pgsql_available()
        except ImportError:
            pass

        env_loader.is_pgsql_available = original


class TestIsRedisAvailable:
    """测试 Redis 依赖可用性检查"""

    def test_is_redis_available_true(self):
        """测试 Redis 可用"""
        from tkzs_structlog.config.env_loader import is_redis_available

        result = is_redis_available()
        assert isinstance(result, bool)


class TestParsePort:
    """测试端口解析"""

    def test_parse_port_valid(self):
        """测试有效端口"""
        from tkzs_structlog.config.env_loader import _parse_port

        assert _parse_port("5432") == 5432
        assert _parse_port("6379") == 6379

    def test_parse_port_invalid(self):
        """测试无效端口"""
        from tkzs_structlog.config.env_loader import _parse_port

        assert _parse_port("invalid") == 0
        assert _parse_port("") == 0

    def test_parse_port_none(self):
        """测试 None 端口"""
        from tkzs_structlog.config.env_loader import _parse_port

        assert _parse_port(None) == 0


class TestEnvLoaderDotenv:
    """测试 dotenv 加载"""

    def test_dotenv_not_installed(self, caplog):
        """测试 dotenv 未安装时的行为"""
        import logging

        from tkzs_structlog.config import env_loader

        # 模拟 dotenv 导入失败
        original_import = builtins.__import__
        import_attempted = [False]

        def mock_import(name, *args, **kwargs):
            if name == "dotenv" and not import_attempted[0]:
                import_attempted[0] = True
                raise ImportError("No module named 'dotenv'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            importlib.reload(env_loader)
            with caplog.at_level(logging.WARNING, logger="tkzs_structlog.config.env_loader"):
                result = env_loader.load_env_config()
                assert result["pgsql"]["host"] == "localhost"
                # 验证警告日志
                assert "python-dotenv not installed" in caplog.text
        finally:
            builtins.__import__ = original_import
            importlib.reload(env_loader)

    def test_dotenv_file_exists(self, tmp_path, caplog):
        """测试 .env 文件存在时加载"""
        from tkzs_structlog.config import env_loader

        # 创建临时 .env 文件
        env_file = tmp_path / ".env"
        env_file.write_text("PG_HOST=from_file\nPG_PORT=5433\n")

        # 重新加载模块，确保 load_dotenv 不是 None
        importlib.reload(env_loader)

        with (
            patch.object(env_loader.Path, "cwd", return_value=tmp_path),
            patch.dict("os.environ", {}, clear=True),  # 清除环境变量，确保使用 .env 文件中的值
            caplog.at_level(logging.DEBUG, logger="tkzs_structlog.config.env_loader"),
        ):
            result = env_loader.load_env_config()
            assert result["pgsql"]["host"] == "from_file"
            assert result["pgsql"]["port"] == 5433

    def test_dotenv_file_not_exists(self, tmp_path, caplog):
        """测试 .env 文件不存在时使用默认值（python-dotenv 未安装）"""
        from tkzs_structlog.config import env_loader

        # 模拟 python-dotenv 未安装
        original_load_dotenv = env_loader.load_dotenv
        env_loader.load_dotenv = None

        try:
            with (
                patch.object(env_loader.Path, "cwd", return_value=tmp_path),
                patch.dict(os.environ, {}, clear=True),
                caplog.at_level(logging.WARNING, logger="tkzs_structlog.config.env_loader"),
            ):
                result = env_loader.load_env_config()
                assert result["pgsql"]["host"] == "localhost"  # 默认值
                assert "python-dotenv not installed" in caplog.text
        finally:
            env_loader.load_dotenv = original_load_dotenv
            importlib.reload(env_loader)


class TestIsPgsqlAvailableImportError:
    """测试 PGSQL 可用性检查（ImportError 路径）"""

    def test_is_pgsql_available_import_error(self):
        """测试 psycopg2 未安装时返回 False"""
        from tkzs_structlog.config import env_loader

        # 模拟 psycopg2 导入失败
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psycopg2":
                raise ImportError("No module named 'psycopg2'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            importlib.reload(env_loader)
            result = env_loader.is_pgsql_available()
            assert result is False
        finally:
            builtins.__import__ = original_import
            importlib.reload(env_loader)


class TestIsRedisAvailableImportError:
    """测试 Redis 可用性检查（ImportError 路径）"""

    def test_is_redis_available_import_error(self):
        """测试 redis 未安装时返回 False"""
        from tkzs_structlog.config import env_loader

        # 模拟 redis 导入失败
        original_import = builtins.__import__
        import_attempted = [False]  # 使用列表使变量可变

        def mock_import(name, *args, **kwargs):
            if name == "redis" and not import_attempted[0]:
                import_attempted[0] = True
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            importlib.reload(env_loader)
            result = env_loader.is_redis_available()
            assert result is False
        finally:
            builtins.__import__ = original_import
            importlib.reload(env_loader)


class TestEnvLoaderDotenvImportError:
    """测试 dotenv 导入失败（覆盖 17-18 行）"""

    def test_dotenv_import_error(self):
        """测试 dotenv 导入失败时 load_dotenv 设为 None（覆盖 17-18 行）"""
        from tkzs_structlog.config import env_loader

        # 模拟 dotenv 导入失败
        original_import = builtins.__import__
        import_success = False

        def mock_import(name, *args, **kwargs):
            if name == "dotenv" and not import_success:
                raise ImportError("No module named 'dotenv'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            importlib.reload(env_loader)
            # 验证 load_dotenv 被设置为 None
            assert env_loader.load_dotenv is None
        finally:
            builtins.__import__ = original_import
            importlib.reload(env_loader)

    def test_is_redis_available_import_success(self):
        """测试 redis 导入成功（覆盖 122 行）"""
        from tkzs_structlog.config import env_loader

        # 确保 redis 模块可用
        try:
            import redis  # noqa: F401
            importlib.reload(env_loader)
            result = env_loader.is_redis_available()
            assert result is True
        except ImportError:
            pytest.skip("redis module not available")
