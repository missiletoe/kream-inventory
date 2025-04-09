import sys
import os
from PyQt6.QtWidgets import QApplication
from src.core.config import ConfigManager
from src.core.browser import BrowserManager
from src.core.plugin_manager import PluginManager
from src.ui.main_window import MainWindow


def main():
    # 설정 파일 로드
    config_path = os.path.expanduser('./config.ini')
    config = ConfigManager(config_path)

    # 브라우저 초기화
    browser_manager = BrowserManager(config)
    driver = browser_manager.get_driver()

    # 플러그인 매니저 생성 및 플러그인 로딩
    plugin_manager = PluginManager(browser=driver, config=config)
    plugin_manager.load_plugins()

    # Qt 어플리케이션 생성 및 실행
    app = QApplication(sys.argv)
    window = MainWindow(plugin_manager=plugin_manager)
    window.show()
    exit_code = app.exec()

    # 종료 처리
    browser_manager.quit()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
