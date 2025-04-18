"""KREAM Inventory Management Application.

This package contains the core functionality for the KREAM inventory
management system.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from .core.config import ConfigManager
from .core.browser import BrowserManager
from .core.plugin_manager import PluginManager
from .ui import MainWindow


def main():
    """Initialize and run the KREAM inventory management application."""
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config = ConfigManager(config_path)

    # Initialize browser
    browser_manager = BrowserManager(config)
    driver = browser_manager.get_driver()

    # Create and load plugin manager
    plugin_manager = PluginManager(browser=driver, config=config)
    plugin_manager.load_plugins()

    # Create and run Qt application
    app = QApplication(sys.argv)
    window = MainWindow(plugin_manager=plugin_manager)
    window.show()
    exit_code = app.exec()

    # Cleanup
    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
