"""Selenium 관련 헬퍼 함수들을 제공합니다."""

from typing import List, Optional, Pattern, Union

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_for_element(
    browser: WebDriver, by: str, selector: str, timeout: int = 10
) -> Optional[WebElement]:
    """요소를 찾을 때까지 최대 timeout 초 동안 대기하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        by: 요소를 찾는 방법 (예: "css selector", "xpath" 등)입니다.
        selector: 요소를 찾기 위한 선택자입니다.
        timeout: 최대 대기 시간 (초)입니다.

    Returns:
        찾은 WebElement 또는 None (타임아웃 시)입니다.
    """
    try:
        return WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return None


def wait_for_element_clickable(
    browser: WebDriver, by: str, selector: str, timeout: int = 10
) -> Optional[WebElement]:
    """요소가 클릭 가능할 때까지 최대 timeout 초 동안 대기하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        by: 요소를 찾는 방법 (예: "css selector", "xpath" 등)입니다.
        selector: 요소를 찾기 위한 선택자입니다.
        timeout: 최대 대기 시간 (초)입니다.

    Returns:
        클릭 가능한 WebElement 또는 None (타임아웃 시)입니다.
    """
    try:
        return WebDriverWait(browser, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return None


def wait_for_elements(
    browser: WebDriver, by: str, selector: str, timeout: int = 10
) -> List[WebElement]:
    """요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        by: 요소를 찾는 방법 (예: "css selector", "xpath" 등)입니다.
        selector: 요소를 찾기 위한 선택자입니다.
        timeout: 최대 대기 시간 (초)입니다.

    Returns:
        찾은 WebElement 목록 또는 빈 리스트 (타임아웃 시)입니다.
    """
    try:
        return WebDriverWait(browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return []


def safe_click(element: WebElement) -> bool:
    """안전하게 요소를 클릭하는 함수입니다.

    Args:
        element: 클릭할 웹 요소입니다.

    Returns:
        성공 여부 (True/False)입니다.
    """
    try:
        element.click()
        return True
    except Exception:
        return False


def is_url_matching(browser: WebDriver, url_pattern: Union[str, Pattern[str]]) -> bool:
    """현재 URL이 패턴과 일치하는지 확인하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        url_pattern: URL 패턴 (문자열 또는 정규식)입니다.

    Returns:
        일치 여부 (True/False)입니다.
    """
    import re

    current_url = browser.current_url

    if isinstance(url_pattern, str):
        return url_pattern in current_url
    else:  # 정규식 패턴인 경우
        return re.search(url_pattern, current_url) is not None
