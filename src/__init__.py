"""크림 인벤토리 애플리케이션을 초기화합니다."""

# Standard library imports
import os
import sys

from PyQt6.QtWidgets import QApplication

from src.kream_inventory.core.browser import BrowserManager
from src.kream_inventory.core.config import ConfigManager
from src.kream_inventory.core.main_controller import MainController
from src.kream_inventory.core.plugin_manager import PluginManager
from src.kream_inventory.ui import MainWindow


# pylint: disable=wrong-import-position
def main() -> None:
    """크림 인벤토리 애플리케이션을 실행합니다."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)

    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    config = ConfigManager(config_path)

    browser_manager = BrowserManager(config.cfg)

    app = QApplication(sys.argv)

    plugin_manager = PluginManager(browser=browser_manager, config=config.cfg)

    # 먼저 플러그인을 로드하여 plugin_manager.plugins가 채워지도록 합니다.
    plugin_manager.load_plugins()

    # 그 후 메인 컨트롤러를 생성하면 이미 로드된 플러그인을 참조할 수 있습니다.
    main_controller = MainController(plugin_manager=plugin_manager)
    plugin_manager.main_controller = main_controller

    window = MainWindow(plugin_manager=plugin_manager, main_controller=main_controller)
    window.show()
    exit_code = app.exec()

    # 종료 시 브라우저를 명시적으로 종료
    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
