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

    def test_str_max_length_non_positive_skips_truncation(self):
        """str_max_length≤0 时不截断字符串"""
        self.truncator.maxstring = 0
        long_s = "a" * 100
        assert self.truncator.truncate_str(long_s) == long_s

    def test_seq_max_elements_non_positive_no_symmetric_cut(self):
        """seq_max_elements≤0 时不做对称元素截断"""
        long_list = list(range(20))
        result = self.truncator.repr_iter(long_list, 0, 0, repr)
        assert ", ...," not in result

    def test_atomic_types_not_truncated(self):
        """int/float/bool/None 保持 reprlib 默认表示"""
        assert self.truncator.repr(42) == "42"
        assert self.truncator.repr(1.5) == "1.5"
        assert self.truncator.repr(True) == "True"
        assert self.truncator.repr(None) == "None"

    def test_empty_string_and_empty_list(self):
        assert self.truncator.truncate_str("") == ""
        assert self.truncator.repr([]) == "[]"

    def test_unicode_emoji_symmetric_truncate(self):
        """中文按字符切片对称截断（长度显著缩短）"""
        self.truncator.maxstring = 8
        s = "你好" * 30
        out = self.truncator.truncate_str(s)
        assert len(out) < len(s)
        assert "..." in out


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
        TruncateProcessor(None, "info", event_dict)
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

    def test_truncate_respects_zero_str_max_length(self):
        """str_max_length=0 时不截断 args"""
        config = {
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 0,
                    "seq_max_elements": 50,
                    "max_depth": 3,
                }
            }
        }
        set_global_config(config)
        event_dict = {"args": "y" * 200}
        TruncateProcessor(None, "info", event_dict)
        assert event_dict["args"] == "y" * 200


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


class TestTypeNameCaching:
    """测试类型名称缓存"""

    def test_get_type_name(self):
        """测试获取类型名称"""
        from tkzs_structlog.extensions.processors import _get_type_name

        result = _get_type_name("hello")
        assert result == "str"

        result = _get_type_name(123)
        assert result == "int"

        result = _get_type_name([1, 2, 3])
        assert result == "list"


class TestTruncatorAdvanced:
    """测试截断器高级功能"""

    def test_set_config_invalid_regex(self):
        """测试设置无效正则"""
        truncator = CustomTruncator()
        # 无效的正则表达式不应该崩溃
        truncator.set_config(ignore_fields_regex="[invalid(")
        assert truncator._compiled_regex is None

    def test_set_config_all_params(self):
        """测试设置所有参数"""
        truncator = CustomTruncator()
        truncator.set_config(
            max_depth=5,
            str_max_length=128,
            seq_max_elements=100,
            dict_max_pairs=50,
            ignore_types=["MyClass"],
            ignore_fields=["password"],
            ignore_fields_pattern=["*_secret"],
            ignore_fields_regex=r"^.*$",
            depth_warning=False,
        )
        assert truncator.max_depth == 5
        assert truncator.maxstring == 128
        assert truncator.ignore_types == ["MyClass"]

    def test_repr_iter_depth_warning(self):
        """测试可迭代对象的深度警告"""
        truncator = CustomTruncator()
        truncator.maxlist = 4
        truncator.max_depth = 2
        truncator.depth_warning = True

        long_list = list(range(100))
        # level >= max_depth 时应该显示警告
        result = truncator.repr_iter(long_list, level=3, maxlen=4, method=repr)
        assert "MAX_DEPTH" in result

    def test_repr_max_depth_warning_disabled(self):
        """测试深度警告禁用"""
        truncator = CustomTruncator()
        truncator.max_depth = 2
        truncator.depth_warning = False

        deep_obj = {"level": 1}
        result = truncator.repr(deep_obj, level=3)
        assert "MAX_DEPTH" not in result

    def test_truncate_processor_with_kwargs(self):
        """测试截断 kwargs"""
        config = {
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 20,
                    "max_depth": 3,
                }
            }
        }
        set_global_config(config)

        event_dict = {"kwargs": "x" * 100}
        result = TruncateProcessor(None, "info", event_dict)
        assert len(result["kwargs"]) <= 23  # 10 + ... + 10

    def test_truncate_processor_with_return_value(self):
        """测试截断 return_value"""
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

        event_dict = {"return_value": "x" * 100}
        result = TruncateProcessor(None, "info", event_dict)
        assert len(result["return_value"]) == 13

    def test_truncate_processor_ignore_ignored_fields(self):
        """测试忽略已配置的字段"""
        config = {
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 10,
                    "max_depth": 3,
                    "ignore_fields": ["args"],
                }
            }
        }
        set_global_config(config)

        event_dict = {"args": "x" * 100}
        result = TruncateProcessor(None, "info", event_dict)
        # args 应该被忽略，不截断
        assert result["args"] == "x" * 100

    def test_truncate_processor_ignore_ignored_fields_pattern(self):
        """测试忽略通过模式配置的字段"""
        config = {
            "extensions": {
                "log_truncate": {
                    "enable": True,
                    "str_max_length": 10,
                    "max_depth": 3,
                    "ignore_fields_pattern": ["*_secret"],
                }
            }
        }
        set_global_config(config)

        event_dict = {"my_secret": "x" * 100}
        result = TruncateProcessor(None, "info", event_dict)
        # my_secret 应该被忽略，不截断
        assert result["my_secret"] == "x" * 100

    def test_sensitive_data_processor_no_fields(self):
        """测试无敏感字段配置"""
        config = {"extensions": {"sensitive_fields": []}}
        set_global_config(config)

        event_dict = {"username": "john"}
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result == event_dict

    def test_sensitive_data_processor_builtin_rules(self):
        """测试内置脱敏规则"""
        config = {"extensions": {"sensitive_fields": ["password", "phone", "id_card", "bank_card"]}}
        set_global_config(config)

        event_dict = {
            "password": "secret123",
            "phone": "13812345678",
            "id_card": "110101199001011234",
            "bank_card": "6222021234567890",
        }
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result["password"] == "******"
        assert result["phone"].startswith("138")
        assert result["phone"].endswith("5678")
        assert result["id_card"].startswith("110101")
        assert result["bank_card"].startswith("6222")

    def test_sensitive_data_processor_non_string_value(self):
        """测试非字符串值不脱敏"""
        config = {"extensions": {"sensitive_fields": ["password"]}}
        set_global_config(config)

        event_dict = {"password": 123}  # 不是字符串
        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result["password"] == 123

    def test_filter_processor_empty_exclude(self):
        """测试空排除列表"""
        config = {"extensions": {"filter_rules": {"exclude": []}}}
        set_global_config(config)

        event_dict = {"username": "john"}
        result = FilterProcessor(None, "info", event_dict)
        assert result == event_dict

    def test_filter_processor_empty_include(self):
        """测试空包含列表"""
        config = {"extensions": {"filter_rules": {"include": []}}}
        set_global_config(config)

        event_dict = {"username": "john"}
        result = FilterProcessor(None, "info", event_dict)
        assert result == event_dict

    def test_processor_non_dict_input(self):
        """测试非字典输入"""
        # TruncateProcessor
        result = TruncateProcessor(None, "info", "not a dict")
        assert result == "not a dict"

        # SensitiveDataProcessor
        result = SensitiveDataProcessor(None, "info", "not a dict")
        assert result == "not a dict"

        # FilterProcessor
        result = FilterProcessor(None, "info", "not a dict")
        assert result == "not a dict"

    def test_processor_no_global_config(self):
        """测试无全局配置"""
        set_global_config({})

        # 应该直接返回原始值
        event_dict = {"key": "value"}
        result = TruncateProcessor(None, "info", event_dict)
        assert result == event_dict

        result = SensitiveDataProcessor(None, "info", event_dict)
        assert result == event_dict

        result = FilterProcessor(None, "info", event_dict)
        assert result == event_dict
