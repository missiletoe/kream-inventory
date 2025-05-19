#!/usr/bin/env python3
"""KREAM 인벤토리 관리 시스템의 메인 진입점입니다."""

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

# 절대 임포트로 변경
try:
    # PyInstaller로 빌드된 앱에서는 이 경로를 sys.path에 추가
    if getattr(sys, "frozen", False):
        # 모듈 경로 초기화
        module_path = os.path.dirname(os.path.abspath(__file__))
        if module_path not in sys.path:
            sys.path.insert(0, module_path)

        # 상위 디렉토리 추가 (src 디렉토리의 상위 디렉토리)
        parent_path = os.path.dirname(module_path)
        if parent_path not in sys.path:
            sys.path.insert(0, parent_path)

        # 절대 임포트 사용
        from src.core.browser import BrowserManager
        from src.core.config import ConfigManager
        from src.core.main_controller import MainController
        from src.core.plugin_manager import PluginManager
        from src.ui.main_window import MainWindow
    else:
        # 개발 환경에서는 상대 임포트 사용
        from .core.browser import BrowserManager
        from .core.config import ConfigManager
        from .core.main_controller import MainController
        from .core.plugin_manager import PluginManager
        from .ui.main_window import MainWindow
except ImportError as e:
    # 임포트 오류 처리
    print(f"임포트 오류 발생: {e}")
    print(f"현재 시스템 경로: {sys.path}")
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f"현재 파일 위치: {os.path.abspath(__file__)}")

    # 대체 방법으로 임포트 시도
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)

        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from src.core.browser import BrowserManager
        from src.core.config import ConfigManager
        from src.core.main_controller import MainController
        from src.core.plugin_manager import PluginManager
        from src.ui.main_window import MainWindow

        print("대체 방법으로 임포트 성공")
    except ImportError as e2:
        print(f"대체 임포트 방법도 실패: {e2}")
        if not getattr(sys, "frozen", False):
            # 개발 환경에서만 재시도
            input("계속하려면 Enter 키를 누르세요...")
        else:
            # PyInstaller에서는 오류 출력 후 종료
            print(
                "앱을 종료합니다. 이 오류는 PyInstaller로 빌드된 앱에서 발생한 모듈 경로 문제입니다."
            )
            sys.exit(1)


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
    # 앱 시작 로그 출력 (디버깅용)
    print("KREAM 인벤토리 애플리케이션 시작 중...")

    # 현재 실행 중인 파이썬 및 경로 정보 출력 (디버깅용)
    print(f"Python 경로: {sys.executable}")
    print(f"현재 작업 디렉토리: {os.getcwd()}")

    try:
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

            print(f"빌드된 앱 모드 - 설정 경로: {config_path}")
        else:
            # 개발 모드 실행
            base_dir = Path(__file__).parent.parent
            config_path = os.path.join(base_dir, "src", "config.ini")
            print(f"개발 모드 - 설정 경로: {config_path}")

        # 설정 관리자 초기화
        config_manager = ConfigManager(config_path)
        config = config_manager.cfg

        # 브라우저 매니저 초기화
        browser_manager = BrowserManager(config)

        # 플러그인 매니저 초기화
        plugin_manager = PluginManager(browser_manager, config)

        # 컨트롤러 초기화
        main_controller = MainController(plugin_manager)

        # 플러그인 매니저에 컨트롤러 설정 및 플러그인 로드
        plugin_manager.main_controller = main_controller
        plugin_manager.load_plugins()

        # 메인 윈도우 초기화 및 표시
        window = MainWindow(plugin_manager, main_controller)
        main_controller.main_window = window
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        # 오류 로깅 및 출력 (디버깅용)
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()

        # 사용자가 오류를 볼 수 있도록 대기
        if getattr(sys, "frozen", False):
            input("엔터 키를 누르면 종료합니다...")


if __name__ == "__main__":
    main()
