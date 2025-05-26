"""애플리케이션의 플러그인 로딩 및 접근을 관리합니다."""

from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from src.core.browser import BrowserManager
from src.core.logger_setup import setup_logger, trace_log
from src.core.plugin_base import PluginBase
from src.plugins import LoginPlugin, MacroPlugin, SearchPlugin
from src.plugins.search import DetailPlugin

if TYPE_CHECKING:
    from src.core.main_controller import MainController

# 전역 로거 설정
logger = setup_logger(__name__)


class PluginManager:
    """애플리케이션 플러그인의 로딩, 초기화, 검색을 처리합니다."""

    def __init__(
        self: PluginManager,
        browser: BrowserManager,
        config: ConfigParser,
        main_controller: Optional[MainController] = None,
    ) -> None:
        """PluginManager를 초기화합니다.

        Args:
            browser: 브라우저 관리자 인스턴스입니다.
            config: 설정 파서 인스턴스입니다.
            main_controller: 메인 컨트롤러 인스턴스입니다.
        """
        self.browser = browser
        self.config = config
        self.plugins: Dict[str, PluginBase] = {}
        self.main_controller = main_controller

    def load_plugins(self: PluginManager) -> None:
        """사용 가능한 모든 플러그인을 로드합니다.

        TODO: 하드코딩하는 대신 동적으로 플러그인을 검색하도록 수정해야 합니다.
        """
        plugin_classes: list[Type[PluginBase]] = [
            LoginPlugin,
            SearchPlugin,
            DetailPlugin,
            MacroPlugin,
        ]

        for cls in plugin_classes:
            self._init_plugin(cls)

    def _init_plugin(self: PluginManager, plugin_class: Type[PluginBase]) -> None:
        """단일 플러그인 클래스를 초기화하고 해당 인스턴스를 저장합니다.

        Args:
            plugin_class: 초기화할 플러그인의 클래스입니다.
        """
        try:
            plugin_name = plugin_class.__name__.lower().replace("plugin", "")
            trace_log(
                logger,
                f"Initializing plugin {plugin_class.__name__} with name '{plugin_name}'",
                level="DEBUG",
            )
            plugin_instance = plugin_class(
                name=plugin_name,
                browser=self.browser,
                config=self.config,
                plugin_manager=self,
            )
            self.plugins[plugin_instance.name] = plugin_instance
            trace_log(
                logger,
                f"Added plugin '{plugin_instance.name}' to plugins dictionary",
                level="DEBUG",
            )
        except Exception as e:
            trace_log(
                logger,
                f"Error initializing plugin {plugin_class.__name__}: {e}",
                level="ERROR",
            )

    def get_plugin(self: PluginManager, name: str) -> Optional[Any]:
        """이름으로 로드된 플러그인을 검색합니다.

        Args:
            name: 검색할 플러그인의 이름입니다.

        Returns:
            플러그인 인스턴스를 찾으면 반환하고, 그렇지 않으면 None을 반환합니다.
        """
        plugin = self.plugins.get(name)
        if plugin is None:
            trace_log(
                logger,
                f"Plugin '{name}' is not found. Available plugins: {list(self.plugins.keys())}",
                level="WARNING",
            )
        return plugin
