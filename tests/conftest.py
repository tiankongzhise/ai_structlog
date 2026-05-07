"""pytest 配置"""

import sys
from pathlib import Path

import pytest

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def reset_structlog():
    """每个测试后重置 structlog"""
    yield
    try:
        from tkzs_structlog import reset_structlog

        reset_structlog()
    except Exception:
        pass
