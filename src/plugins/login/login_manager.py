"""로그인 상태를 관리하고 자동 로그인을 처리합니다.

이 모듈은 크림 웹사이트의 로그인 상태를 관리하고 자동 로그인을 수행하는 클래스를 제공합니다.
"""

import re

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from src.core.selenium_helpers import wait_for_element, wait_for_element_clickable


class LoginManager:
    """로그인 상태를 관리하고 자동 로그인 프로세스를 처리합니다."""

    @staticmethod
    def validate_credentials(email: str, password: str) -> tuple[bool, str]:
        """이메일과 비밀번호 형식을 확인합니다.

        Args:
            email: 확인할 이메일 주소입니다.
            password: 확인할 비밀번호입니다.

        Returns:
            유효성 여부를 나타내는 불리언과 오류 메시지 문자열을 담은 튜플입니다.
        """
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        password_pattern = r"^(?=.*[A-Za-z])(?=.*\d).{8,16}$"
        if not re.match(email_pattern, email):
            return False, "유효하지 않은 이메일 형식입니다."
        if not re.match(password_pattern, password):
            return (
                False,
                "비밀번호는 8자 이상 16자 이하이며, 문자와 숫자를 포함해야 합니다.",
            )
        return True, ""

    def __init__(self: "LoginManager", browser: WebDriver) -> None:
        """이 클래스는 WebDriver 인스턴스를 사용하여 LoginManager를 초기화합니다."""
        self.browser = browser

    def is_logged_in(self: "LoginManager") -> bool:
        """사용자가 현재 로그인되어 있는지 확인합니다."""
        try:
            if self.browser.current_url.startswith("https://kream.co.kr/login"):
                return False
            else:
                return True
        except Exception:
            return False

    def login(self: "LoginManager", email: str, password: str) -> bool:
        """현재 페이지에서 로그인을 시도합니다.

        이 함수는 현재 브라우저의 URL이 로그인 페이지라고 가정하고 동작합니다.
        로그인 페이지로의 이동은 이 함수 외부에서 처리해야 합니다.

        Args:
            email: 사용자 이메일입니다.
            password: 사용자 비밀번호입니다.

        Returns:
            로그인 성공 시 True, 실패 시 False를 반환합니다.
        """
        is_valid, _ = self.validate_credentials(
            email, password
        )  # 반환값 변경에 따른 수정
        if not is_valid:
            return False

        try:
            email_input = wait_for_element(
                self.browser, By.CSS_SELECTOR, "input[type='email']", timeout=5
            )
            password_input = wait_for_element(
                self.browser, By.CSS_SELECTOR, "input[type='password']", timeout=5
            )
            if not email_input or not password_input:
                return False

            email_input.clear()
            password_input.clear()
            email_input.send_keys(email)
            password_input.send_keys(password)

            login_button = wait_for_element_clickable(
                self.browser,
                By.XPATH,
                '//button[contains(text(),"로그인")]',
                timeout=5,
            )
            if not login_button:
                return False
            login_button.click()
            return True

        except Exception:
            return False

    def logout(self: "LoginManager") -> bool:
        """크림 웹사이트에서 로그아웃을 시도합니다.

        Returns:
            로그아웃 성공 시 True, 실패 시 False를 반환합니다.
        """
        logout_url = "https://kream.co.kr/logout"
        landing_url = "https://kream.co.kr/"
        try:
            self.browser.get(logout_url)

            # 로그아웃 후 랜딩 페이지로 이동하는지 확인
            try:
                WebDriverWait(self.browser, 5).until(ec.url_to_be(landing_url))
                return True
            except TimeoutException:
                return False

        except Exception:
            return False
