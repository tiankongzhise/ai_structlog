"""tkzs-structlog CLI模块

B2: 命令行工具，支持 validate、generate、version 命令。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import click

    CLICK_AVAILABLE = True
except ImportError:  # pragma: no cover
    CLICK_AVAILABLE = False  # pragma: no cover


def _validate_config_impl(config_path: str) -> tuple[bool, list[str]]:
    """验证配置文件实现

    Args:
        config_path: 配置文件路径

    Returns:
        (是否成功, 错误信息列表)
    """
    from tkzs_structlog.config import load_config_file, validate_config

    errors: list[str] = []

    try:
        config = load_config_file(config_path)
        validate_config(config)
        return True, []
    except Exception as e:
        errors.append(str(e))
        return False, errors


def _generate_config_impl(
    output_path: str | None,
    env: str | None = None,
    version: str = "2.1",
) -> str:
    """生成默认配置文件实现

    Args:
        output_path: 输出路径
        env: 环境名称
        version: 配置版本

    Returns:
        生成的配置内容
    """
    from tkzs_structlog.config.defaults import get_default_config

    config = get_default_config(version)

    # 添加注释
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comment = f"""# tkzs-structlog 配置文件 (版本 {version})
# 自动生成于 {generated_at}
# 环境: {env or "default"}

"""

    content = json.dumps(config, indent=2, ensure_ascii=False)
    full_content = comment + content

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(full_content, encoding="utf-8")

    return full_content


def main() -> int:
    """CLI 主入口

    Returns:
        退出码
    """
    if not CLICK_AVAILABLE:
        print("Error: click is required for CLI. Install with: pip install click")
        return 1

    @click.group()
    def cli() -> None:
        """tkzs-structlog 命令行工具"""
        pass

    @cli.command()
    @click.option(
        "--config-path",
        "-c",
        default="structlog_config.json",
        help="配置文件路径",
    )
    def validate(config_path: str) -> None:
        """校验配置文件合法性"""
        click.echo(f"Validating config: {config_path}")
        success, errors = _validate_config_impl(config_path)

        if success:
            click.echo(click.style("✓ Config is valid", fg="green"))
        else:
            click.echo(click.style("✗ Config is invalid", fg="red"))
            for error in errors:
                click.echo(click.style(f"  - {error}", fg="red"))
            sys.exit(1)

    @cli.command()
    @click.option(
        "--output",
        "-o",
        default=None,
        help="输出文件路径",
    )
    @click.option(
        "--env",
        "-e",
        default=None,
        help="环境名称 (dev/prod/test)",
    )
    @click.option(
        "--version",
        "-v",
        default="2.1",
        help="配置版本",
    )
    def generate(output: str | None, env: str | None, version: str) -> None:
        """生成默认配置文件"""
        content = _generate_config_impl(output, env, version)

        if output:
            click.echo(click.style(f"✓ Config generated: {output}", fg="green"))
        else:
            click.echo(content)

    @cli.command()
    def version() -> None:
        """显示版本信息"""
        from tkzs_structlog._version import __version__

        click.echo(f"tkzs-structlog: {__version__}")
        click.echo("Supported config versions: 1.0, 2.0, 2.1, 3.0, 4.0")

    return cli()  # type: ignore[no-any-return]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
