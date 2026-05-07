"""版本模块测试"""

import pytest


class TestVersion:
    """测试版本信息"""

    def test_version_exists(self):
        """测试版本字符串存在"""
        from tkzs_structlog._version import __version__, version

        assert __version__ is not None
        assert version is not None
        assert __version__ == version

    def test_version_tuple_exists(self):
        """测试版本元组存在"""
        from tkzs_structlog._version import __version_tuple__, version_tuple

        assert __version_tuple__ is not None
        assert version_tuple is not None
        assert __version_tuple__ == version_tuple

    def test_version_is_string(self):
        """测试版本是字符串"""
        from tkzs_structlog._version import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_tuple_is_tuple(self):
        """测试版本元组是元组类型"""
        from tkzs_structlog._version import __version_tuple__

        assert isinstance(__version_tuple__, tuple)
        assert len(__version_tuple__) >= 2

    def test_version_format(self):
        """测试版本格式"""
        from tkzs_structlog._version import __version__

        # 版本字符串应该包含数字
        assert any(char.isdigit() for char in __version__)

    def test_commit_id_exists(self):
        """测试commit_id存在"""
        from tkzs_structlog._version import __commit_id__, commit_id

        # commit_id 可以是 None
        assert __commit_id__ is commit_id

    def test_all_exports(self):
        """测试所有导出"""
        from tkzs_structlog._version import (
            __all__,
            __commit_id__,
            __version__,
            __version_tuple__,
            commit_id,
            version,
            version_tuple,
        )

        assert "__version__" in __all__
        assert "__version_tuple__" in __all__
        assert "__commit_id__" in __all__
