"""크림 인벤토리 애플리케이션.

이 패키지는 크림 인벤토리 애플리케이션의 핵심 로직과 UI를 포함합니다.
"""

import os
import sys

from PyQt6.QtWidgets import QApplication

from .core.browser import BrowserManager
from .core.config import ConfigManager
from .core.main_controller import MainController
from .core.plugin_manager import PluginManager
from .ui import MainWindow


def main() -> None:
    """크림 인벤토리 애플리케이션을 실행합니다."""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if project_root not in sys.path:
        sys.path.append(project_root)

    # src 폴더 내부의 config.ini를 참조
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")

    if not os.path.exists(config_path):
        sys.exit(1)

    config_manager = ConfigManager(config_path)

    try:
        import chromedriver_autoinstaller

        chromedriver_autoinstaller.install()
    except Exception:
        pass

    try:
        browser_manager = BrowserManager(config_manager.cfg)
    except Exception:
        sys.exit(1)

    plugin_manager = PluginManager(browser=browser_manager, config=config_manager.cfg)

    app = QApplication(sys.argv)

    plugin_manager.load_plugins()

    main_controller = MainController(plugin_manager=plugin_manager, main_window=None)
    plugin_manager.main_controller = main_controller

    window = MainWindow(plugin_manager=plugin_manager, main_controller=main_controller)
    main_controller.main_window = window

    main_controller.update_plugin_references()

    window.show()
    exit_code = app.exec()

    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
