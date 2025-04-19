import os
import sys

from PyQt6.QtWidgets import QApplication

from .core.browser import BrowserManager
from .core.config import ConfigManager
from .core.plugin_manager import PluginManager
from .ui import MainWindow


def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config = ConfigManager(config_path)

    browser_manager = BrowserManager(config)
    driver = browser_manager.get_driver()

    plugin_manager = PluginManager(browser=driver, config=config)
    plugin_manager.load_plugins()

    app = QApplication(sys.argv)
    window = MainWindow(plugin_manager=plugin_manager)
    window.show()
    exit_code = app.exec()

    # Cleanup
    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
