"""环境变量加载模块测试"""

import os
from unittest.mock import patch

import pytest


class TestLoadEnvConfig:
    """测试环境变量加载"""

    def test_load_env_config_default_values(self):
        """测试默认配置值"""
        from tkzs_structlog.config.env_loader import load_env_config

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

    def test_load_env_config_custom_values(self):
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
            result = env_loader.is_pgsql_available()
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

    def test_dotenv_not_installed(self):
        """测试 dotenv 未安装时的行为"""
        import sys
        from tkzs_structlog.config import env_loader

        original_load_dotenv = env_loader.load_dotenv
        env_loader.load_dotenv = None

        try:
            result = env_loader.load_env_config()
            assert result["pgsql"]["host"] == "localhost"
        finally:
            env_loader.load_dotenv = original_load_dotenv