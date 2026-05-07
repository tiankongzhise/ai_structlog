"""tkzs-structlog 异常模块

定义项目所有自定义异常类型，遵循异常处理规范。
所有异常继承 StructlogBaseError，包含错误类型、字段、原因和修复建议。
"""

from __future__ import annotations

from typing import Any


class StructlogBaseError(Exception):
    """Structlog 异常基类

    所有自定义异常继承此类，包含以下属性：
    - error_type: 错误类型（如 ConfigError/ProcessorError）
    - error_field: 错误字段（若有）
    - reason: 错误原因
    - fix_suggestion: 修复建议
    """

    def __init__(
        self,
        error_type: str,
        error_field: str | None = None,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        self.error_type = error_type
        self.error_field = error_field
        self.reason = reason
        self.fix_suggestion = fix_suggestion
        message = self._format_message()
        super().__init__(message)

    def _format_message(self) -> str:
        """格式化异常消息"""
        parts = [f"[{self.error_type}]"]
        if self.error_field:
            parts.append(f"Field: {self.error_field}")
        if self.reason:
            parts.append(f"Reason: {self.reason}")
        if self.fix_suggestion:
            parts.append(f"Fix: {self.fix_suggestion}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"error_type={self.error_type!r}, "
            f"error_field={self.error_field!r}, "
            f"reason={self.reason!r}, "
            f"fix_suggestion={self.fix_suggestion!r}"
            f")>"
        )


class StructlogConfigError(StructlogBaseError):
    """配置错误基类"""

    def __init__(
        self,
        error_field: str | None = None,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_type="ConfigError",
            error_field=error_field,
            reason=reason,
            fix_suggestion=fix_suggestion,
        )


class StructlogConfigFileNotFoundError(StructlogConfigError):
    """配置文件未找到"""

    def __init__(
        self,
        config_path: str,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_field="config_path",
            reason=reason or f"Configuration file not found: {config_path}",
            fix_suggestion=fix_suggestion or "Please check if the file exists or provide a valid config path",
        )


class StructlogConfigParseError(StructlogConfigError):
    """配置文件解析错误"""

    def __init__(
        self,
        config_path: str,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_field="config_content",
            reason=reason or f"Failed to parse configuration file: {config_path}",
            fix_suggestion=fix_suggestion or "Please check if the JSON/JSONC syntax is valid",
        )


class StructlogConfigVersionError(StructlogConfigError):
    """配置版本不支持"""

    def __init__(
        self,
        version: str,
        supported_versions: list[str] | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        supported = supported_versions or ["1.0", "2.0", "2.1", "3.0", "4.0"]
        super().__init__(
            error_field="version",
            reason=f"Unsupported config version: {version}",
            fix_suggestion=(fix_suggestion or f"Supported versions: {', '.join(supported)}"),
        )


class StructlogProcessorError(StructlogBaseError):
    """处理器错误基类"""

    def __init__(
        self,
        processor_name: str | None = None,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_type="ProcessorError",
            error_field=processor_name,
            reason=reason,
            fix_suggestion=fix_suggestion,
        )


class StructlogProcessorImportError(StructlogProcessorError):
    """处理器导入错误"""

    def __init__(
        self,
        processor_path: str,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            processor_name=processor_path,
            reason=reason or f"Failed to import processor: {processor_path}",
            fix_suggestion=fix_suggestion or "Please check if the processor path is correct",
        )


class StructlogProcessorInstantiateError(StructlogProcessorError):
    """处理器实例化错误"""

    def __init__(
        self,
        processor_name: str,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            processor_name=processor_name,
            reason=reason or f"Failed to instantiate processor: {processor_name}",
            fix_suggestion=fix_suggestion or "Please check the processor parameters",
        )


class StructlogNotInitedError(StructlogBaseError):
    """Structlog 未初始化错误"""

    def __init__(
        self,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_type="NotInitedError",
            reason=reason or "Structlog has not been initialized",
            fix_suggestion=fix_suggestion or "Please call init_structlog() first",
        )


class StructlogHandlerError(StructlogBaseError):
    """处理器错误"""

    def __init__(
        self,
        handler_name: str | None = None,
        reason: str | None = None,
        fix_suggestion: str | None = None,
    ) -> None:
        super().__init__(
            error_type="HandlerError",
            error_field=handler_name,
            reason=reason,
            fix_suggestion=fix_suggestion,
        )
