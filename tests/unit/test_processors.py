"""处理器模块测试"""


from tkzs_structlog.extensions.processors import (
    CustomTruncator,
    FilterProcessor,
    SensitiveDataProcessor,
    TruncateProcessor,
    mask_value,
    set_global_config,
)


class TestCustomTruncator:
    """测试自定义截断器"""

    def setup_method(self):
        """每个测试前重置"""
        self.truncator = CustomTruncator()

    def test_truncate_str_short(self):
        """测试截断短字符串（不截断）"""
        short_str = "hello"
        result = self.truncator.truncate_str(short_str)
        assert result == short_str

    def test_truncate_str_long(self):
        """测试截断长字符串（对称截断）"""
        self.truncator.maxstring = 10
        long_str = "a" * 100
        result = self.truncator.truncate_str(long_str)
        # 对称截断：前5个 + ... + 后5个 = 13个字符
        assert len(result) == 13
        assert result.startswith("aaaaa")
        assert result.endswith("aaaaa")
        assert "..." in result

    def test_truncate_str_boundary(self):
        """测试边界情况"""
        self.truncator.maxstring = 10
        exact_str = "a" * 10
        result = self.truncator.truncate_str(exact_str)
        assert result == exact_str

    def test_repr_str(self):
        """测试字符串 repr"""
        self.truncator.maxstring = 20
        result = self.truncator.repr_str("hello world", 0)
        assert result == "hello world"

    def test_repr_iter_list_short(self):
        """测试可迭代对象（短列表）"""
        short_list = [1, 2, 3]
        result = self.truncator.repr_iter(short_list, 0, 50, repr)
        assert "1" in result

    def test_repr_iter_list_long(self):
        """测试可迭代对象（长列表，对称截断）"""
        self.truncator.maxlist = 4
        long_list = list(range(100))
        result = self.truncator.repr_iter(long_list, 0, 4, repr)
        assert "..." in result

    def test_is_field_ignored_exact(self):
        """测试字段精确匹配忽略"""
        self.truncator.ignore_fields = ["password", "secret"]
        assert self.truncator.is_field_ignored("password")
        assert self.truncator.is_field_ignored("secret")
        assert not self.truncator.is_field_ignored("username")

    def test_is_field_ignored_pattern(self):
        """测试字段通配符匹配忽略"""
        self.truncator.ignore_fields_pattern = ["*_id", "session_*"]
        assert self.truncator.is_field_ignored("user_id")
        assert self.truncator.is_field_ignored("session_token")
        assert not self.truncator.is_field_ignored("id_user")

    def test_is_field_ignored_regex(self):
        """测试字段正则匹配忽略"""
        self.truncator.ignore_fields_regex = r"^.*_(id|token)$"
        self.truncator.set_config(ignore_fields_regex=r"^.*_(id|token)$")
        assert self.truncator.is_field_ignored("user_id")
        assert self.truncator.is_field_ignored("session_token")
        assert not self.truncator.is_field_ignored("username")

    def test_repr_with_ignore_types(self):
        """测试忽略类型"""
        self.truncator.ignore_types = ["CustomClass"]

        class CustomClass:
            def __repr__(self):
                return "CUSTOM_REPR"

        obj = CustomClass()
        result = self.truncator.repr(obj)
        assert "CUSTOM_REPR" in result

    def test_repr_depth_warning(self):
        """测试深度警告"""
        self.truncator.max_depth = 2
        self.truncator.depth_warning = True
        self.truncator.maxstring = 100

        # 创建一个嵌套对象
        deep_obj = {"level": 1}
        result = self.truncator.repr(deep_obj, level=3)
        assert "MAX_DEPTH" in result


class TestMaskValue:
    """测试脱敏函数"""

    def test_mask_password(self):
        """测试密码脱敏（全部隐藏）"""
        result = mask_value("my_secret_password", (0, 0, "******"))
        assert result == "******"

    def test_mask_phone(self):
        """测试手机号脱敏"""
        result = mask_value("13812345678", (3, 4, "******"))
        assert result.startswith("138")
        assert result.endswith("5678")
        assert "******" in result

    def test_mask_short_value(self):
        """测试短值脱敏"""
        result = mask_value("123", (3, 4, "******"))
        assert result == "******"


class TestTruncateProcessor:
    """测试截断处理器"""

    def test_truncate_disabled(self):
        """测试禁用截断"""
        config = {"extensions": {"log_truncate": {"enable": False}}}
        set_global_config(config)

        event_dict = {"args": "x" * 300}
        result = TruncateProcessor(None, "info", event_dict)
        # 不应截断
        assert event_dict["args"] == "x" * 300

    def test_truncate_string(self):
        """测试字符串截断"""
        config = {
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 10,
                    "max_depth": 3,
                }
            }
        }
        set_global_config(config)

        event_dict = {"args": "x" * 100}
        result = TruncateProcessor(None, "info", event_dict)
        # 对称截断：前5个 + ... + 后5个 = 13个字符
        assert len(result["args"]) == 13


class TestSensitiveDataProcessor:
    """测试敏感信息脱敏处理器"""

    def test_mask_password(self):
        """测试密码脱敏"""
        config = {"extensions": {"sensitive_fields": ["password"]}}
        set_global_config(config)

        event_dict = {"password": "secret123"}
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result["password"] == "******"

    def test_mask_phone(self):
        """测试手机号脱敏"""
        config = {"extensions": {"sensitive_fields": ["phone"]}}
        set_global_config(config)

        event_dict = {"phone": "13812345678"}
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result["phone"].startswith("138")
        assert result["phone"].endswith("5678")

    def test_no_mask_other_fields(self):
        """测试其他字段不脱敏"""
        config = {"extensions": {"sensitive_fields": []}}
        set_global_config(config)

        event_dict = {"username": "john", "password": "secret"}
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result["username"] == "john"


class TestFilterProcessor:
    """测试过滤处理器"""

    def test_exclude_fields(self):
        """测试排除字段"""
        config = {"extensions": {"filter_rules": {"exclude": ["password"]}}}
        set_global_config(config)

        event_dict = {"username": "john", "password": "secret"}
        result = FilterProcessor(None, "info", event_dict)
        assert "username" in result
        assert "password" not in result

    def test_include_fields(self):
        """测试包含字段"""
        config = {"extensions": {"filter_rules": {"include": ["username"]}}}
        set_global_config(config)

        event_dict = {"username": "john", "password": "secret"}
        result = FilterProcessor(None, "info", event_dict)
        assert result == {"username": "john"}

    def test_no_filter(self):
        """测试不过滤"""
        config = {"extensions": {"filter_rules": {}}}
        set_global_config(config)

        event_dict = {"username": "john"}
        result = FilterProcessor(None, "info", event_dict)
        assert result == event_dict
