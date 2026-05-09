"""tkzs-structlog 处理器实现

C1: 截断处理器、脱敏处理器、过滤处理器。
structlog 处理器是过滤器函数，不是类。
"""

from __future__ import annotations

import fnmatch
import re
import reprlib
import threading
from functools import lru_cache
from typing import Any, Type

from tkzs_structlog.config import get_extension_config

# 全局配置存储（线程安全）
_global_config: dict[str, Any] = {}
_config_lock = threading.RLock()


def set_global_config(config: dict[str, Any]) -> None:
    """设置全局配置（线程安全）"""
    global _global_config
    with _config_lock:
        _global_config = config


def get_global_config() -> dict[str, Any]:
    """获取全局配置（线程安全）

    Returns:
        全局配置字典的副本
    """
    with _config_lock:
        return _global_config.copy()


@lru_cache(maxsize=1024)
def _get_cached_type_name(obj_type: Type[Any]) -> str:
    """缓存类型名称"""
    return obj_type.__name__


def _get_type_name(obj: Any) -> str:
    """获取对象类型名称"""
    return _get_cached_type_name(type(obj))  # type: ignore[arg-type]


class CustomTruncator(reprlib.Repr):
    """自定义截断器

    实现分层、分类型、对称截断。使用 _config_hash 检测配置变更，
    避免每次日志事件重复调用 set_config 产生不必要的属性赋值开销。
    """

    def __init__(self) -> None:
        super().__init__()
        self.max_depth = 3
        self.maxstring = 256
        self.maxlist = 50
        self.maxdict = 30
        self.maxset = 50
        self.ignore_types: list[str] = []
        self.ignore_fields: list[str] = []
        self.ignore_fields_pattern: list[str] = []
        self.ignore_fields_regex: str | None = None
        self.depth_warning = True
        self._compiled_regex: re.Pattern[str] | None = None
        self._config_hash: int = 0

    def set_config(
        self,
        max_depth: int = 3,
        str_max_length: int = 256,
        seq_max_elements: int = 50,
        dict_max_pairs: int = 30,
        ignore_types: list[str] | None = None,
        ignore_fields: list[str] | None = None,
        ignore_fields_pattern: list[str] | None = None,
        ignore_fields_regex: str | None = None,
        depth_warning: bool = True,
    ) -> None:
        """设置截断配置（仅配置变更时更新，避免每次日志事件重复赋值）"""
        # 计算配置哈希，无变更则跳过
        new_hash = hash((
            max_depth, str_max_length, seq_max_elements, dict_max_pairs,
            tuple(ignore_types or []), tuple(ignore_fields or []),
            tuple(ignore_fields_pattern or []), ignore_fields_regex, depth_warning,
        ))
        if new_hash == self._config_hash:
            return
        self._config_hash = new_hash

        self.max_depth = max_depth
        self.maxstring = str_max_length
        self.maxlist = seq_max_elements
        self.maxdict = dict_max_pairs
        self.maxset = seq_max_elements
        self.ignore_types = ignore_types or []
        self.ignore_fields = ignore_fields or []
        self.ignore_fields_pattern = ignore_fields_pattern or []
        self.ignore_fields_regex = ignore_fields_regex
        self.depth_warning = depth_warning

        # 编译正则表达式
        if ignore_fields_regex:
            try:
                self._compiled_regex = re.compile(ignore_fields_regex)
            except re.error:
                self._compiled_regex = None

    def truncate_str(self, s: str) -> str:
        """截断字符串（对称截断）"""
        if not s:
            return s
        if self.maxstring <= 0:
            return s
        if len(s) <= self.maxstring:
            return s
        half = self.maxstring // 2
        return f"{s[:half]}...{s[-half:]}"

    def repr_str(self, obj: str, level: int) -> str:
        """字符串表示"""
        return self.truncate_str(obj)

    def repr_iter(self, obj: Any, level: int, maxlen: int, method: object = None) -> str:
        """可迭代对象表示（对称截断）

        method 参数由 reprlib.Repr 父类传入（repr1 方法），本实现不使用。
        """
        items = list(obj)
        if maxlen <= 0:
            return reprlib.Repr.repr(self, items)
        if len(items) <= maxlen:
            return reprlib.Repr.repr(self, items)

        half = maxlen // 2
        head = items[:half]
        tail = items[-half:]
        head_str = reprlib.Repr.repr(self, head)
        tail_str = reprlib.Repr.repr(self, tail)
        base_str = head_str[:-1] + f", ..., {tail_str[1:]}"

        # 递归深度警告
        if self.depth_warning and level >= self.max_depth:
            base_str = f"{base_str}[MAX_DEPTH={self.max_depth}]"

        return base_str

    def is_field_ignored(self, field_name: str) -> bool:
        """检查字段是否应被忽略"""
        # 1. 精确匹配
        if field_name in self.ignore_fields:
            return True

        # 2. 通配符匹配
        for pattern in self.ignore_fields_pattern:
            if fnmatch.fnmatch(field_name, pattern):
                return True

        # 3. 正则匹配
        if self._compiled_regex and self._compiled_regex.match(field_name):
            return True

        return False

    def repr(self, obj: Any, level: int = 0) -> str:
        """获取对象的字符串表示"""
        type_name = _get_type_name(obj)

        # 检查是否在忽略类型列表中
        if type_name in self.ignore_types:
            return reprlib.Repr.repr(self, obj)

        # 深度控制 + 警告
        if level >= self.max_depth:
            truncated = reprlib.Repr.repr(self, obj)[: self.maxstring]
            suffix = f"...[MAX_DEPTH={self.max_depth}]" if self.depth_warning else ""
            return truncated + suffix

        # reprlib.Repr.repr() 只接受一个参数
        return reprlib.Repr.repr(self, obj)


# 全局截断器实例
_truncator = CustomTruncator()


# 脱敏规则
SENSITIVE_MASK_RULES: dict[str, tuple[int, int, str]] = {
    "password": (0, 0, "******"),  # 全部隐藏
    "phone": (3, 4, "******"),  # 保留前3后4
    "id_card": (6, 4, "******"),  # 保留前6后4
    "bank_card": (4, 4, "******"),  # 保留前4后4
}


def mask_value(value: str, rule: tuple[int, int, str]) -> str:
    """根据规则脱敏"""
    prefix_len, suffix_len, mask_char = rule
    value_len = len(value)

    if prefix_len == 0 and suffix_len == 0:
        return mask_char

    if value_len <= prefix_len + suffix_len:
        return mask_char

    prefix = value[:prefix_len] if prefix_len > 0 else ""
    suffix = value[-suffix_len:] if suffix_len > 0 else ""
    mask_len = value_len - prefix_len - suffix_len
    mask = mask_char * min(mask_len, len(mask_char))

    return f"{prefix}{mask}{suffix}"


# ============================================================
# 处理器函数 - structlog 过滤器
# ============================================================


def TruncateProcessor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """日志截断处理器

    Args:
        logger: 日志器
        method_name: 方法名
        event_dict: 事件字典

    Returns:
        处理后的事件字典
    """
    # 确保返回字典
    if not isinstance(event_dict, dict):
        return event_dict

    config = get_global_config()
    if not config:
        return event_dict

    truncate_config = get_extension_config(config, "log_truncate")
    if not truncate_config or not truncate_config.get("enable", False):
        return event_dict

    # 更新截断器配置
    _truncator.set_config(
        max_depth=truncate_config.get("max_depth", 3),
        str_max_length=truncate_config.get("str_max_length", 256),
        seq_max_elements=truncate_config.get("seq_max_elements", 50),
        dict_max_pairs=truncate_config.get("dict_max_pairs", 30),
        ignore_types=truncate_config.get("ignore_types", []),
        ignore_fields=truncate_config.get("ignore_fields", []),
        ignore_fields_pattern=truncate_config.get("ignore_fields_pattern", []),
        ignore_fields_regex=truncate_config.get("ignore_fields_regex"),
        depth_warning=truncate_config.get("depth_warning", True),
    )

    # 截断 args、kwargs、return_value
    for key in ["args", "kwargs", "return_value"]:
        if key in event_dict and not _truncator.is_field_ignored(key):
            event_dict[key] = _truncator.repr(event_dict[key])

    return event_dict


def SensitiveDataProcessor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """敏感信息脱敏处理器

    Args:
        logger: 日志器
        method_name: 方法名
        event_dict: 事件字典

    Returns:
        处理后的事件字典
    """
    # 确保返回字典
    if not isinstance(event_dict, dict):
        return event_dict

    config = get_global_config()
    if not config:
        return event_dict

    sensitive_fields = config.get("extensions", {}).get("sensitive_fields", [])
    if not sensitive_fields:
        return event_dict

    # 合并内置规则和自定义字段
    all_rules = dict(SENSITIVE_MASK_RULES)
    for field in sensitive_fields:
        if field not in all_rules:
            all_rules[field] = (0, 0, "******")  # pragma: no cover

    # 处理敏感字段
    for key, value in event_dict.items():
        if key in all_rules and isinstance(value, str):
            event_dict[key] = mask_value(value, all_rules[key])

    return event_dict


def FilterProcessor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """日志过滤处理器

    Args:
        logger: 日志器
        method_name: 方法名
        event_dict: 事件字典

    Returns:
        处理后的事件字典，或 None 表示过滤掉
    """
    # 确保返回字典
    if not isinstance(event_dict, dict):
        return event_dict

    config = get_global_config()
    if not config:
        return event_dict

    filter_rules = config.get("extensions", {}).get("filter_rules", {})
    exclude_fields = filter_rules.get("exclude", [])
    include_fields = filter_rules.get("include", [])

    # 如果有 include 列表，只保留指定字段
    if include_fields:
        return {k: v for k, v in event_dict.items() if k in include_fields}

    # 如果有 exclude 列表，过滤掉指定字段
    if exclude_fields:
        return {k: v for k, v in event_dict.items() if k not in exclude_fields}

    return event_dict
