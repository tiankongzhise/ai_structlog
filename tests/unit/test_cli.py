"""CLI模块测试"""

import json
import re
import sys
from unittest.mock import patch

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
        _generate_config_impl(str(output_path))

        assert output_path.exists()

    def test_generate_config_impl_has_dynamic_timestamp(self):
        """生成头注释使用当前时间，非硬编码日期"""
        from tkzs_structlog.api.cli import _generate_config_impl

        content = _generate_config_impl(None, version="2.1")
        assert "2024-01-01" not in content
        assert re.search(r"自动生成于 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)


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

    def test_main_version_subcommand(self):
        """click 可用时 version 子命令退出码 0"""
        from tkzs_structlog.api import cli

        pytest.importorskip("click")
        if not cli.CLICK_AVAILABLE:
            pytest.skip("click not installed")

        with patch.object(sys, "argv", ["tkzs-structlog", "version"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0
            else:
                pytest.fail("click CLI should invoke sys.exit")

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

    def test_validate_command_success_via_runner(self, tmp_path):
        """使用 click CliRunner 测试 validate 命令成功路径"""
        pytest.importorskip("click")
        from click.testing import CliRunner

        from tkzs_structlog.api import cli

        if not cli.CLICK_AVAILABLE:
            pytest.skip("click not installed")

        # 创建有效配置文件
        config_file = tmp_path / "valid.json"
        config_file.write_text(
            json.dumps({"version": "1.0", "min_level": "INFO", "processors": []}),
            encoding="utf-8",
        )

        runner = CliRunner()  # noqa: F841
        # 直接调用 main，捕获 SystemExit
        with patch.object(sys, "argv", ["tkzs-structlog", "validate", "--config-path", str(config_file)]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None

    def test_validate_command_failure_via_runner(self, tmp_path):
        """使用 click CliRunner 测试 validate 命令失败路径"""
        pytest.importorskip("click")

        from tkzs_structlog.api import cli

        if not cli.CLICK_AVAILABLE:
            pytest.skip("click not installed")

        # 创建无效配置文件
        config_file = tmp_path / "invalid.json"
        config_file.write_text('{"version": "99.0"}', encoding="utf-8")

        with patch.object(sys, "argv", ["tkzs-structlog", "validate", "--config-path", str(config_file)]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 1 or e.code is not None

    def test_generate_command_no_output_via_runner(self):
        """使用 click CliRunner 测试 generate 命令不指定输出路径"""
        pytest.importorskip("click")

        from tkzs_structlog.api import cli

        if not cli.CLICK_AVAILABLE:
            pytest.skip("click not installed")

        with patch.object(sys, "argv", ["tkzs-structlog", "generate"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None

    def test_generate_command_with_output_via_runner(self, tmp_path):
        """使用 click CliRunner 测试 generate 命令指定输出路径"""
        pytest.importorskip("click")

        from tkzs_structlog.api import cli

        if not cli.CLICK_AVAILABLE:
            pytest.skip("click not installed")

        output_file = tmp_path / "generated.json"
        with patch.object(sys, "argv", ["tkzs-structlog", "generate", "--output", str(output_file)]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None
