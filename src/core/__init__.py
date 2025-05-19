"""코어 모듈.

이 모듈은 애플리케이션의 핵심 기능을 포함합니다.
"""

from .browser import BrowserManager
from .config import ConfigManager
from .plugin_manager import PluginManager

__all__ = ["BrowserManager", "ConfigManager", "PluginManager"]
