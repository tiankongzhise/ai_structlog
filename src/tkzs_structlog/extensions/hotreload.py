"""tkzs-structlog 热重载模块

C3: 配置热重载功能，支持配置文件变更监听和自动重新加载。
"""

from __future__ import annotations

import importlib
import threading
from pathlib import Path
from typing import Any, Callable

try:
    import watchdog.events
    import watchdog.observers

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class ConfigFileHandler:
    """配置文件事件处理器"""

    def __init__(
        self,
        config_path: str | Path,
        on_reload: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.on_reload = on_reload
        self._reload_lock = threading.Lock()

    def on_modified(self, event: Any) -> None:
        """配置文件被修改"""
        if event.src_path != str(self.config_path):
            return

        with self._reload_lock:
            try:
                # 重新加载配置
                from tkzs_structlog.config import load_config_file

                new_config = load_config_file(self.config_path)
                if self.on_reload:
                    self.on_reload(new_config)
            except Exception:
                pass


class ConfigHotReloader:
    """配置热重载器"""

    def __init__(
        self,
        config_path: str | Path,
        on_reload: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog is required for hot reload. Please install it with: pip install watchdog")

        self.config_path = Path(config_path)
        self.on_reload = on_reload
        self._is_running = False
        self._observer: watchdog.observers.Observer | None = None

    def start(self) -> None:
        """启动热重载"""
        if self._is_running:
            return

        self._is_running = True
        self._observer = watchdog.observers.Observer()

        handler = ConfigFileHandler(self.config_path, self.on_reload)
        event_handler = watchdog.events.FileSystemEventHandler()
        event_handler.on_modified = handler.on_modified  # type: ignore

        self._observer.schedule(
            event_handler,
            str(self.config_path.parent),
            recursive=False,
        )
        self._observer.start()

    def stop(self) -> None:
        """停止热重载"""
        if not self._is_running:
            return

        self._is_running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running


def reload_processor(processor_path: str) -> Any:
    """重新加载处理器

    Args:
        processor_path: 处理器路径

    Returns:
        重新加载后的处理器
    """
    try:
        module_path, class_name = processor_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        importlib.reload(module)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError):
        return None
