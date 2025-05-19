"""Selenium WebDriver 인스턴스를 관리합니다."""

from configparser import ConfigParser
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

if TYPE_CHECKING:
    from ..stubs import chromedriver_autoinstaller
else:
    import chromedriver_autoinstaller


class BrowserManager:
    """브라우저 자동화를 위한 Selenium WebDriver 인스턴스를 관리합니다."""

    def __init__(self: "BrowserManager", config: ConfigParser) -> None:
        """설정을 사용하여 BrowserManager를 초기화합니다.

        Args:
            config: 브라우저 설정을 위한 설정 객체입니다.
        """
        self.config = config
        self.driver: WebDriver | None = None

    def get_driver(self: "BrowserManager") -> WebDriver:
        """기존 WebDriver 인스턴스를 반환하거나, 없으면 새로 생성하여 반환합니다."""
        if not self.driver:
            options = Options()

            user_agent = self.config.get("Browser", "user_agent", fallback=None)

            if user_agent:
                options.add_argument(f"user-agent={user_agent}")

            if self.config.getboolean("Browser", "headless", fallback=False):
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--start-maximized")
                options.add_experimental_option(
                    "excludeSwitches", ["enable-automation"]
                )
                options.add_experimental_option("useAutomationExtension", False)

            # 크롬 드라이버 자동 설치를 위한 코드 추가
            try:
                chromedriver_autoinstaller.install()
            except Exception as e:
                print(f"Chrome 드라이버 자동 설치 중 오류: {e}")

            # 추가 Chrome 옵션
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            try:
                self.driver = webdriver.Chrome(options=options)
                # 드라이버 생성 성공 로그
                print("Chrome WebDriver 초기화 성공")
            except Exception as e:
                print(f"Chrome WebDriver 초기화 실패: {e}")
                raise

        return self.driver

    def quit(self: "BrowserManager") -> None:
        """WebDriver를 종료하고 모든 관련 창을 닫습니다."""
        if self.driver:
            self.driver.quit()
            self.driver = None
