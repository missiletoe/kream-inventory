"""Selenium WebDriver 인스턴스를 관리합니다."""

import logging  # noqa: F401 # 로깅 모듈 임포트
from configparser import ConfigParser
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

# logger_setup 임포트
from src.core.logger_setup import setup_logger

if TYPE_CHECKING:
    from ..stubs import chromedriver_autoinstaller
else:
    import chromedriver_autoinstaller

# 전역 로거 설정
logger = setup_logger(__name__)


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
                logger.info(
                    "Headless 모드로 브라우저를 설정합니다."
                )  # 헤드리스 모드 설정 로그 추가
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--start-maximized")
                options.add_experimental_option(
                    "excludeSwitches", ["enable-automation"]
                )
                options.add_experimental_option("useAutomationExtension", False)

            # 크롬 드라이버 자동 설치
            try:
                logger.info("ChromeDriver 자동 설치를 시도합니다...")
                chromedriver_autoinstaller.install()
                logger.info("ChromeDriver 자동 설치 완료.")
            except Exception as e:
                logger.error(f"ChromeDriver 자동 설치 중 오류: {e}", exc_info=True)
                # 설치 실패 시에도 일단 진행하도록 둘 수 있으나, 심각한 오류로 간주하고 raise 할 수도 있음

            # 추가 Chrome 옵션
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            try:
                logger.info("Chrome WebDriver 초기화를 시도합니다...")
                self.driver = webdriver.Chrome(options=options)
                logger.info("Chrome WebDriver 초기화 성공.")
            except Exception as e:
                logger.error(f"Chrome WebDriver 초기화 실패: {e}", exc_info=True)
                raise

        return self.driver

    def quit(self: "BrowserManager") -> None:
        """WebDriver를 종료하고 모든 관련 창을 닫습니다."""
        if self.driver:
            logger.info("WebDriver를 종료합니다.")  # 종료 로그 추가
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver 종료 완료.")
