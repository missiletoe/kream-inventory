import os
import sys

from PyQt6.QtWidgets import QApplication

from .core.browser import BrowserManager
from .core.config import ConfigManager
from .core.plugin_manager import PluginManager
from .ui import MainWindow


def main():
    # 프로젝트 루트 디렉토리의 config.ini를 사용하도록 경로 설정
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_path = os.path.join(project_root, 'config.ini')

    # 설정 파일 존재 확인
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)
        
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
