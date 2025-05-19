"""크림 인벤토리 애플리케이션의 모든 플러그인을 위한 기본 클래스입니다."""

from configparser import ConfigParser
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject

from .browser import BrowserManager

if TYPE_CHECKING:
    from .plugin_manager import PluginManager


class PluginBase(QObject):
    """모든 플러그인을 위한 기본 클래스로, 공통 기능과 인터페이스를 제공합니다."""

    def __init__(
        self: "PluginBase",
        name: str,
        browser: BrowserManager,
        config: ConfigParser,
        plugin_manager: Optional["PluginManager"] = None,
    ) -> None:
        """PluginBase를 초기화합니다.

        Args:
            name: 플러그인의 이름입니다.
            browser: 브라우저 관리자 인스턴스입니다.
            config: ConfigParser 인스턴스입니다 (ConfigManager가 아님).
            plugin_manager: 사용 가능한 경우 플러그인 관리자 인스턴스입니다.
        """
        super().__init__()
        self.name = name
        self.browser = browser
        self.config = config
        self.plugin_manager = plugin_manager
