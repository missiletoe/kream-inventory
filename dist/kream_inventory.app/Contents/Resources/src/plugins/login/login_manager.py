"""로그인 상태를 관리하고 자동 로그인을 처리합니다.

이 모듈은 크림 웹사이트의 로그인 상태를 관리하고 자동 로그인을 수행하는 클래스를 제공합니다.
"""

import re

from selenium.common.exceptions import TimeoutException

# from selenium.webdriver.common.by import By # By 임포트 제거 또는 str로 사용
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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

    def wait_for_element(
        self: "LoginManager", by: str, selector: str, timeout: int = 5
    ) -> WebElement:
        """페이지에 요소가 나타날 때까지 기다립니다.

        Args:
            by: 요소를 찾는 방법입니다 (예: "css selector").
            selector: 요소의 선택자입니다.
            timeout: 최대 대기 시간(초)입니다.

        Returns:
            찾은 WebElement입니다.
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def wait_for_elements(
        self: "LoginManager", by: str, selector: str, timeout: int = 5
    ) -> list[WebElement]:
        """페이지에 여러 요소가 나타날 때까지 기다립니다.

        Args:
            by: 요소를 찾는 방법입니다 (예: "css selector").
            selector: 요소의 선택자입니다.
            timeout: 최대 대기 시간(초)입니다.

        Returns:
            찾은 WebElement 목록입니다.
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def wait_for_element_if_visible(
        self: "LoginManager", by: str, selector: str, timeout: int = 5
    ) -> WebElement | None:
        """페이지에서 요소가 보이게 될 때까지 기다립니다.

        Args:
            by: 요소를 찾는 방법입니다 (예: "css selector").
            selector: 요소의 선택자입니다.
            timeout: 최대 대기 시간(초)입니다.

        Returns:
            찾은 WebElement이거나, 보이지 않으면 None입니다.
        """
        try:
            element = WebDriverWait(self.browser, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def is_logged_in(self: "LoginManager") -> bool:
        """사용자가 현재 로그인되어 있는지 확인합니다."""
        try:
            # Attempt to find elements indicating a logged-in state
            try:
                menu_elements = self.wait_for_elements(
                    "css selector", "button.btn_my_menu, a.btn_my_menu", timeout=2
                )
                if len(menu_elements) > 0:
                    return True
            except TimeoutException:
                pass  # Element not found, continue checking

            try:
                # By.XPATH 대신 "xpath" 문자열 사용
                login_links = self.browser.find_elements(
                    "xpath", "//a[contains(text(), '로그인')]"
                )
                if not login_links:
                    my_page_links = self.browser.find_elements(
                        "xpath", "//a[contains(text(), '마이페이지')]"
                    )
                    if my_page_links:
                        return True
            except Exception:
                pass  # Ignore errors during this check

            current_url = self.browser.current_url
            if "login" not in current_url and current_url.startswith(
                "https://kream.co.kr/"
            ):
                return True

            return False
        except Exception:
            return False  # If any error occurs, assume not logged in

    def relogin(
        self: "LoginManager", email: str, password: str, switch_to_new_tab: bool = True
    ) -> bool:
        """로그인 페이지로 이동하여 다시 로그인을 시도합니다."""
        valid, _ = self.validate_credentials(email, password)
        if not valid:
            return False

        original_handle = self.browser.current_window_handle
        target_handle = original_handle

        if switch_to_new_tab:
            try:
                self.browser.execute_script("window.open('');")
                new_handle = [
                    handle
                    for handle in self.browser.window_handles
                    if handle != original_handle
                ][0]
                self.browser.switch_to.window(new_handle)
                target_handle = new_handle
            except Exception:
                pass  # Failed to open new tab, continue in current tab

        try:
            self.browser.get("https://kream.co.kr/login")
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located(("css selector", 'input[type="email"]'))
            )

            email_input = self.wait_for_element("css selector", 'input[type="email"]')
            password_input = self.wait_for_element(
                "css selector", 'input[type="password"]'
            )

            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)

            login_button = self.wait_for_element(
                "css selector", 'button[type="submit"]'
            )
            login_button.click()

            WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located(("css selector", "body"))
            )
            return True

        except TimeoutException:
            if switch_to_new_tab and target_handle != original_handle:
                self.browser.close()
                self.browser.switch_to.window(original_handle)
            return False

        except Exception:
            if switch_to_new_tab and target_handle != original_handle:
                try:
                    self.browser.close()
                    self.browser.switch_to.window(original_handle)
                except Exception:
                    pass  # Ignore errors during tab closing/switching
            return False

    def check_and_relogin_if_needed(
        self: "LoginManager", email: str, password: str, max_attempts: int = 2
    ) -> bool:
        """로그인 상태를 확인하고 필요한 경우 다시 로그인합니다."""
        if self.is_logged_in():
            return True

        # print("로그인 상태가 아닙니다. 재로그인을 시도합니다.") # Logged by caller if needed

        for _attempt in range(max_attempts):
            # print(f"로그인 시도 {attempt + 1}/{max_attempts}") # Logged by caller if needed
            if self.relogin(email, password):
                # print("재로그인 성공") # Logged by caller if needed
                return True
            import time

            time.sleep(1)

        # print("모든 로그인 시도 실패") # Logged by caller if needed
        return False

    def login_via_alternative_method(
        self: "LoginManager", email: str, password: str
    ) -> None:
        """대체 로그인 방법을 위한 플레이스홀더입니다."""
        # This method is a placeholder and should be implemented if needed.
        # For now, it does nothing.
        pass

    def handle_login_success(self: "LoginManager") -> None:
        """로그인 후 작업(예: 쿠키 정책 동의)을 처리합니다."""
        try:
            accept_cookie_btn = self.wait_for_element_if_visible(
                "xpath", "//button[contains(text(), '모두 동의하기')]", timeout=2
            )
            if accept_cookie_btn:
                accept_cookie_btn.click()
        except TimeoutException:
            pass  # Cookie consent button not found or not visible
        except Exception:
            pass  # Ignore other errors during cookie handling
