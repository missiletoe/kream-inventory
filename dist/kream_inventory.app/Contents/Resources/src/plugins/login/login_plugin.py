"""크림 웹사이트 로그인 플러그인입니다.

이 모듈은 크림 웹사이트의 로그인 기능을 처리하는 플러그인을 제공합니다.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.plugin_base import PluginBase
from src.plugins.login.login_manager import LoginManager
from src.plugins.macro.macro_toast_handler import (
    MacroToastHandler,
)  # noqa: E501, F401

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
        # click_term 기본값 설정
        default_click_term = 8
        click_term = config.getint("Macro", "min_interval", fallback=default_click_term)
        self.toast_handler = MacroToastHandler(
            browser=actual_browser_driver, click_term=click_term
        )

    def login(self: "LoginPlugin", email: str, password: str) -> None:
        """크림 웹사이트에 로그인을 시도합니다."""
        valid, msg = LoginManager.validate_credentials(email, password)
        if not valid:
            error_msg = f"로그인 실패: {msg}"
            QMessageBox.warning(None, "로그인 형식 오류", error_msg)
            self.login_status.emit(False, error_msg)
            return

        login_url = "https://kream.co.kr/login"
        self.browser.get_driver().get(login_url)

        try:
            wait = WebDriverWait(self.browser.get_driver(), 3)
            email_input = self.browser.get_driver().find_element(
                By.CSS_SELECTOR, 'input[type="email"]'
            )
            password_input = self.browser.get_driver().find_element(
                By.CSS_SELECTOR, 'input[type="password"]'
            )
            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)

            wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.login-btn-box"))
            ).click()
            time.sleep(2)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            # 로그인 성공 여부 확인
            current_url = self.browser.get_driver().current_url
            if "login" not in current_url:
                self.login_status.emit(True, "로그인 성공")
            else:
                # 로그인 페이지에 머물러 있는 경우 오류 메시지 확인
                error_msgs = self.browser.get_driver().find_elements(
                    By.CSS_SELECTOR, ".input_error"
                )
                if error_msgs and any(msg.is_displayed() for msg in error_msgs):
                    error_text = next(
                        (msg.text for msg in error_msgs if msg.is_displayed()),
                        "이메일 또는 비밀번호가 잘못되었습니다.",
                    )
                    self.login_status.emit(False, f"로그인 실패: {error_text}")
                else:
                    self.login_status.emit(False, "로그인 실패: 알 수 없는 오류")
            return

        except TimeoutException:
            self.login_status.emit(
                False, "로그인 실패: 이메일 또는 비밀번호를 확인해주세요."
            )

    def logout(self: "LoginPlugin") -> None:
        """크림 웹사이트에서 로그아웃을 시도합니다."""
        logout_url = "https://kream.co.kr/logout"
        landing_url = "https://kream.co.kr/"
        try:
            self.browser.get_driver().get(logout_url)

            wait = WebDriverWait(self.browser.get_driver(), 5)
            wait.until(EC.url_to_be(landing_url))
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        except TimeoutException:
            raise TimeoutException(
                "로그아웃 실패: 로그아웃 페이지에 접속할 수 없습니다."
            )
        except Exception as e:
            raise Exception(f"로그아웃 실패: {str(e)}") from e
