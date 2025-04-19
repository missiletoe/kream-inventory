from . import kream_inventory

import sys
import os
from PyQt6.QtWidgets import QApplication
from src.kream_inventory.core.config import ConfigManager
from src.kream_inventory.core.browser import BrowserManager
from src.kream_inventory.core.plugin_manager import PluginManager
from src.kream_inventory.ui import MainWindow


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

    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
