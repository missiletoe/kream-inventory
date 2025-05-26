"""Selenium WebDriver 관련 유틸리티 함수들을 제공합니다."""

from __future__ import annotations

from typing import TYPE_CHECKING, Pattern, Union

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


def wait_for_element(
    browser: WebDriver, by: str, selector: str, timeout: int = 5
) -> WebElement:
    """페이지에 요소가 나타날 때까지 기다립니다.

    Args:
        browser: WebDriver 인스턴스입니다.
        by: 요소를 찾는 방법입니다 (예: By.CSS_SELECTOR).
        selector: 요소의 선택자입니다.
        timeout: 최대 대기 시간(초)입니다.

    Returns:
        찾은 WebElement입니다.

    Raises:
        TimeoutException: 지정된 시간 내에 요소를 찾지 못한 경우.
    """
    return WebDriverWait(browser, timeout).until(
        ec.presence_of_element_located((by, selector))
    )


def wait_for_elements(
    browser: WebDriver, by: str, selector: str, timeout: int = 5
) -> list[WebElement]:
    """페이지에 여러 요소가 나타날 때까지 기다립니다.

    Args:
        browser: WebDriver 인스턴스입니다.
        by: 요소를 찾는 방법입니다 (예: By.CSS_SELECTOR).
        selector: 요소의 선택자입니다.
        timeout: 최대 대기 시간(초)입니다.

    Returns:
        찾은 WebElement 목록입니다.

    Raises:
        TimeoutException: 지정된 시간 내에 요소를 찾지 못한 경우.
    """
    return WebDriverWait(browser, timeout).until(
        ec.presence_of_all_elements_located((by, selector))
    )


def wait_for_element_if_visible(
    browser: WebDriver, by: str, selector: str, timeout: int = 5
) -> WebElement | None:
    """페이지에서 요소가 보이게 될 때까지 기다립니다.

    Args:
        browser: WebDriver 인스턴스입니다.
        by: 요소를 찾는 방법입니다 (예: By.CSS_SELECTOR).
        selector: 요소의 선택자입니다.
        timeout: 최대 대기 시간(초)입니다.

    Returns:
        찾은 WebElement이거나, 보이지 않으면 None입니다.
    """
    try:
        element = WebDriverWait(browser, timeout).until(
            ec.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        return None


def wait_for_element_clickable(
    browser: WebDriver, by: str, selector: str, timeout: int = 5
) -> WebElement | None:
    """요소가 클릭 가능할 때까지 최대 timeout 초 동안 대기하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        by: 요소를 찾는 방법 (예: By.CSS_SELECTOR).
        selector: 요소를 찾기 위한 선택자입니다.
        timeout: 최대 대기 시간 (초)입니다.

    Returns:
        클릭 가능한 WebElement 또는 None (타임아웃 또는 예외 발생 시)입니다.
    """
    try:
        return WebDriverWait(browser, timeout).until(
            ec.element_to_be_clickable((by, selector))
        )
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return None


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
    import re  # 함수 내 지역 import 유지

    current_url = browser.current_url

    if isinstance(url_pattern, str):
        return url_pattern in current_url
    else:  # 정규식 패턴인 경우
        return re.search(url_pattern, current_url) is not None
