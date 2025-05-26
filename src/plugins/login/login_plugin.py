"""크림 웹사이트 로그인 플러그인입니다.

이 모듈은 크림 웹사이트의 로그인 기능을 처리하는 플러그인을 제공합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

from src.core.plugin_base import PluginBase
from src.plugins.login.login_manager import LoginManager
from src.plugins.macro.macro_toast_handler import MacroToastHandler  # noqa: E501, F401

if TYPE_CHECKING:
    from configparser import ConfigParser

    from src.core.browser import BrowserManager
    from src.core.plugin_manager import PluginManager


class LoginPlugin(PluginBase, QObject):
    """크림 웹사이트의 로그인 작업을 처리합니다."""

    login_status = pyqtSignal(bool, str)

    def __init__(
        self: "LoginPlugin",
        name: str,
        browser: "BrowserManager",
        config: "ConfigParser",
        plugin_manager: Optional["PluginManager"] = None,
    ) -> None:
        """LoginPlugin을 초기화합니다."""
        PluginBase.__init__(
            self,
            name=name,
            browser=browser,
            config=config,  # ConfigParser 객체 직접 전달
            plugin_manager=plugin_manager,
        )
        QObject.__init__(self)
        actual_browser_driver: WebDriver = browser.get_driver()
        # LoginManager 인스턴스 생성
        self.login_manager = LoginManager(actual_browser_driver)
        # click_term 기본값 설정
        default_click_term = 8
        click_term = config.getint("Macro", "min_interval", fallback=default_click_term)
        self.toast_handler = MacroToastHandler(
            browser=actual_browser_driver, click_term=click_term
        )

    def login(self: "LoginPlugin", email: str, password: str) -> None:
        """크림 웹사이트에 로그인을 시도합니다."""
        # 로그인 페이지로 이동
        login_url = "https://kream.co.kr/login"
        self.browser.get_driver().get(login_url)

        # LoginManager를 사용하여 로그인 수행
        login_success = self.login_manager.login(email, password)

        # 로그인 결과 처리
        if login_success:
            self.login_status.emit(True, "로그인 성공")
        else:
            self.login_status.emit(False, "로그인 실패")

    def logout(self: "LoginPlugin") -> None:
        """크림 웹사이트에서 로그아웃을 시도합니다."""
        try:
            logout_success = self.login_manager.logout()
            if not logout_success:
                raise TimeoutException(
                    "로그아웃 실패: 로그아웃 처리가 완료되지 않았습니다."
                )
        except TimeoutException as e:
            raise TimeoutException(str(e))
        except Exception as e:
            raise Exception(f"로그아웃 실패: {str(e)}") from e
