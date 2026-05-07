"""CLI模块测试"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCLIValidate:
    """测试CLI验证功能"""

    def test_validate_config_impl_success(self, tmp_path):
        """测试验证成功"""
        from tkzs_structlog.api.cli import _validate_config_impl

        # 创建有效配置
        config_file = tmp_path / "valid_config.json"
        config_data = {
            "version": "1.0",
            "logger_name": "test",
            "min_level": "INFO",
            "processors": [],
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        success, errors = _validate_config_impl(str(config_file))
        assert success is True
        assert errors == []

    def test_validate_config_impl_invalid_json(self, tmp_path):
        """测试无效JSON"""
        from tkzs_structlog.api.cli import _validate_config_impl

        # 创建无效JSON配置
        config_file = tmp_path / "invalid_config.json"
        config_file.write_text("not valid json", encoding="utf-8")

        success, errors = _validate_config_impl(str(config_file))
        assert success is False
        assert len(errors) > 0

    def test_validate_config_impl_file_not_found(self):
        """测试配置文件不存在"""
        from tkzs_structlog.api.cli import _validate_config_impl

        success, errors = _validate_config_impl("/nonexistent/path/config.json")
        assert success is False
        assert len(errors) > 0

    def test_validate_config_impl_validation_error(self, tmp_path):
        """测试配置验证错误"""
        from tkzs_structlog.api.cli import _validate_config_impl

        # 创建无效配置（缺少必需字段）
        config_file = tmp_path / "invalid_config.json"
        config_file.write_text('{"version": "99.0"}', encoding="utf-8")

        success, errors = _validate_config_impl(str(config_file))
        assert success is False
        assert len(errors) > 0


class TestCLIGenerate:
    """测试CLI生成功能"""

    def test_generate_config_impl_returns_content(self):
        """测试生成配置返回内容"""
        from tkzs_structlog.api.cli import _generate_config_impl

        content = _generate_config_impl(None, env="test", version="2.1")

        assert isinstance(content, str)
        assert "tkzs-structlog" in content
        assert "2.1" in content

    def test_generate_config_impl_with_env(self):
        """测试生成带环境的配置"""
        from tkzs_structlog.api.cli import _generate_config_impl

        content = _generate_config_impl(None, env="production")

        assert "production" in content

    def test_generate_config_impl_with_output(self, tmp_path):
        """测试生成配置到文件"""
        from tkzs_structlog.api.cli import _generate_config_impl

        output_path = tmp_path / "generated_config.json"
        content = _generate_config_impl(str(output_path), version="2.1")

        # 文件应该存在
        assert output_path.exists()

        # 返回内容应该匹配
        file_content = output_path.read_text(encoding="utf-8")
        assert file_content == content

    def test_generate_config_impl_different_versions(self):
        """测试不同版本生成"""
        from tkzs_structlog.api.cli import _generate_config_impl

        for version in ["1.0", "2.0", "2.1", "3.0", "4.0"]:
            content = _generate_config_impl(None, version=version)
            assert version in content

    def test_generate_config_impl_no_env(self):
        """测试无环境时生成"""
        from tkzs_structlog.api.cli import _generate_config_impl

        content = _generate_config_impl(None, env=None)
        assert "default" in content

    def test_generate_config_impl_to_nested_path(self, tmp_path):
        """测试生成到嵌套路径"""
        from tkzs_structlog.api.cli import _generate_config_impl

        output_path = tmp_path / "subdir" / "nested" / "config.json"
        content = _generate_config_impl(str(output_path))

        assert output_path.exists()


class TestCLIMain:
    """测试CLI主入口"""

    def test_main_without_click(self):
        """测试click不可用时"""
        from tkzs_structlog.api import cli

        # 模拟click不可用
        original_value = cli.CLICK_AVAILABLE
        cli.CLICK_AVAILABLE = False

        try:
            result = cli.main()
            assert result == 1
        finally:
            cli.CLICK_AVAILABLE = original_value

    def test_click_available_flag(self):
        """测试CLICK_AVAILABLE标志"""
        from tkzs_structlog.api import cli

        # 标志应该存在
        assert hasattr(cli, "CLICK_AVAILABLE")
        assert isinstance(cli.CLICK_AVAILABLE, bool)


class TestCLIVersion:
    """测试CLI版本命令"""

    def test_version_import(self):
        """测试版本导入"""
        from tkzs_structlog._version import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)


class TestCLIIntegration:
    """CLI集成测试"""

    def test_cli_entry_point(self):
        """测试CLI入口点"""
        from tkzs_structlog.api import cli

        # 模拟click不可用的情况
        original_value = cli.CLICK_AVAILABLE
        cli.CLICK_AVAILABLE = False

        try:
            result = cli.main()
            assert result == 1
        finally:
            cli.CLICK_AVAILABLE = original_value
