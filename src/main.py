#!/usr/bin/env python3
"""KREAM 인벤토리 관리 시스템의 메인 진입점입니다."""

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.core.logger_setup import log_input, setup_logger

logger = setup_logger(__name__)


def setup_imports():
    """시스템 경로를 설정하고 필요한 모듈을 임포트합니다."""
    # 먼저 경로 설정을 올바르게 수행
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)

    # 항상 상위 디렉토리를 시스템 경로에 추가 (src의 상위)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from src.core.browser import BrowserManager
    from src.core.config import ConfigManager
    from src.core.main_controller import MainController
    from src.core.plugin_manager import PluginManager
    from src.ui.main_window import MainWindow

    return BrowserManager, ConfigManager, MainController, PluginManager, MainWindow


def resource_path(relative_path):
    """PyInstaller로 빌드된 환경에서도 올바른 리소스 경로를 가져옵니다.

    Args:
        relative_path: 상대 경로

    Returns:
        str: 절대 경로
    """
    try:
        # PyInstaller가 실행 중인 경우의 임시 폴더 경로
        base_path = getattr(sys, "_MEIPASS", None)  # type: ignore
        if base_path is None:
            raise AttributeError("_MEIPASS not found")
    except AttributeError:
        # 일반 Python 실행 환경
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main() -> None:
    """애플리케이션의 메인 함수입니다."""
    logger.info("KREAM 인벤토리 애플리케이션 시작 중...")

    logger.info(f"Python 경로: {sys.executable}")
    logger.info(f"현재 작업 디렉토리: {os.getcwd()}")

    try:
        # 모듈 임포트 및 경로 설정
        BrowserManager, ConfigManager, MainController, PluginManager, MainWindow = (
            setup_imports()
        )
        logger.info(f"시스템 경로: {sys.path}")

        app = QApplication(sys.argv)

        # 설정 파일 경로 설정 - PyInstaller 환경을 고려한 경로 계산
        if getattr(sys, "frozen", False):
            # PyInstaller로 빌드된 앱 실행
            base_dir = Path(os.path.dirname(sys.executable)).parent
            config_path = os.path.join(base_dir, "Resources", "config.ini")

            # config.ini 파일이 없으면 현재 디렉토리에서 찾기
            if not os.path.exists(config_path):
                config_path = os.path.join(
                    os.path.dirname(os.path.abspath(sys.executable)), "config.ini"
                )

            logger.info(f"빌드된 앱 모드 - 설정 경로: {config_path}")
        else:
            # 개발 모드 실행
            base_dir = Path(__file__).parent.parent
            config_path = os.path.join(base_dir, "src", "config.ini")
            logger.info(f"개발 모드 - 설정 경로: {config_path}")

        # 설정 관리자 초기화
        config_manager = ConfigManager(config_path)
        config = config_manager.cfg

        # 브라우저 매니저 초기화
        browser_manager = BrowserManager(config)

        # 플러그인 매니저 초기화
        plugin_manager = PluginManager(browser_manager, config)

        # 플러그인 먼저 로드
        plugin_manager.load_plugins()

        # 컨트롤러 초기화 (이미 로드된 플러그인이 있는 plugin_manager를 사용)
        main_controller = MainController(plugin_manager)

        # 플러그인 매니저에 컨트롤러 설정
        plugin_manager.main_controller = main_controller

        # 메인 윈도우 초기화 및 표시
        window = MainWindow(plugin_manager, main_controller)
        main_controller.main_window = window
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        # 오류 로깅
        logger.error(f"오류 발생: {e}", exc_info=True)  # traceback 정보 포함

        # 사용자가 오류를 볼 수 있도록 대기 (PyInstaller 빌드 시)
        if getattr(sys, "frozen", False):
            log_input("엔터 키를 누르면 종료합니다...")


if __name__ == "__main__":
    main()
