"""토스트 메시지를 감지하고 처리하는 클래스입니다."""

import time
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# logger_setup 임포트
from src.core.logger_setup import setup_logger


class MacroToastHandler(QObject):
    """웹 페이지의 토스트 메시지를 감지하고 처리하는 클래스입니다.

    특정 토스트 메시지에 따라 작업을 일시 중단하거나 재시도합니다.
    """

    log_message_signal = pyqtSignal(str)
    last_toast_message = ""
    last_toast_time = 0.0

    def __init__(
        self: "MacroToastHandler",
        browser: WebDriver,
        click_term: int,
        parent: Optional[QObject] = None,
    ) -> None:
        """새로운 MacroToastHandler 객체를 초기화합니다.

        Args:
            browser (WebDriver): Selenium WebDriver 인스턴스입니다.
            click_term (int): 특정 조건에서 대기할 시간 (초)입니다.
            parent (Optional[QObject], optional): 부모 QObject입니다. 기본값은 None입니다.
        """
        super().__init__(parent)
        self.browser = browser
        self.click_term = click_term

        # logger_setup을 사용하여 로거 설정
        self.logger = setup_logger(__name__)
        self.logger.info("Toast Handler 초기화됨")

    def handle_toast(self: "MacroToastHandler") -> bool:
        """토스트 메시지를 감지하고 적절한 조치를 취합니다.

        Returns:
            bool: 토스트 메시지 처리 후 매크로를 즉시 반환(중단 또는 재시작 결정)해야 하면 True,
                  그렇지 않으면 False를 반환합니다.
        """
        toast_selectors: List[str] = [
            "div#toast.toast.lg.show",
            "div#toast.toast.mo.show",
            "div.toast.lg.show",
            "div.toast.mo.show",
            "div.toast.show",
        ]

        for selector in toast_selectors:
            try:
                popup = WebDriverWait(self.browser, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                popup_text = self._get_toast_text(popup)

                if popup_text:
                    self.logger.debug(
                        f"토스트 감지됨: '{popup_text}' (선택자: {selector})"
                    )
                    return self._process_toast_message(popup_text)

            except TimeoutException:
                continue
            except Exception as e:
                # UI 및 파일 로깅
                error_msg = f"토스트 메시지 처리 중 오류: {str(e)}"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_message_signal.emit(f"[{timestamp}] {error_msg}")
                self.logger.error(error_msg, exc_info=True)

        return False

    def _get_toast_text(self: "MacroToastHandler", toast_element: WebElement) -> str:
        """토스트 요소에서 텍스트를 추출합니다.

        여러 가능한 경로를 시도하여 텍스트를 가져옵니다.

        Args:
            toast_element: 토스트 WebElement

        Returns:
            str: 추출된 텍스트 또는 빈 문자열
        """
        text = toast_element.text.strip()
        if text:
            return text
        try:
            content_selectors = [
                "div.toast-content p",
                ".toast-content",
                "p",
                ".toast-message",
                "span",
                "div",
            ]
            for selector in content_selectors:
                try:
                    elements = toast_element.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        el_text = el.text.strip()
                        if el_text:
                            return el_text
                except Exception:
                    continue
        except Exception as e:
            self.logger.warning(
                f"토스트 내부 텍스트 추출 중 오류: {str(e)}", exc_info=True
            )
        return ""

    def _process_toast_message(self: "MacroToastHandler", message: str) -> bool:
        """토스트 메시지 텍스트를 처리합니다.

        Args:
            message: 토스트 메시지 텍스트

        Returns:
            bool: 매크로를 중단하고 다음 루프로 진행해야 하면 True, 아니면 False
        """
        current_time = time.time()
        if (
            message == self.last_toast_message
            and current_time - self.last_toast_time < 2
        ):
            self.logger.debug(f"중복 토스트 메시지 감지됨 (무시): {message}")
            return False

        self.last_toast_message = message
        self.last_toast_time = current_time

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{message}"
        self.log_message_signal.emit(f"[{timestamp}] {log_message}")
        self.logger.info(log_message)

        if (
            "신규 보관 신청이 제한된 카테고리" in message
            or "신규 보관신청이 제한된 카테고리" in message
        ):
            wait_seconds = self.click_term
            timestamp_wait = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # UI 및 파일 로그에 대기 시간 출력
            self.log_message_signal.emit(
                f"[{timestamp_wait}] 보관 제한 카테고리 감지 - 약 {wait_seconds}초 대기 후 재시도"
            )
            self.logger.info(
                f"보관 제한 카테고리 감지 - 약 {wait_seconds}초 대기 후 재시도"
            )
            time.sleep(wait_seconds)
            return True

        error_keywords = [
            "상대방의 입찰 삭제",
            "카드사 응답실패",
            "예상치 못한 오류",
            "인터넷",
            "와이파이",
            "모바일 데이터",
            "비행기모드",
        ]

        if any(keyword in message for keyword in error_keywords):
            wait_seconds = 3600
            log_msg_ui = f"약 {wait_seconds // 60}분간 매크로 중단 후 재시도 예정"
            log_msg_file = f"심각한 오류 감지 (키워드: {[k for k in error_keywords if k in message]}). {log_msg_ui}"

            timestamp_ui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_message_signal.emit(f"[{timestamp_ui}] {log_msg_ui}")
            self.logger.warning(log_msg_file)

            time.sleep(wait_seconds)

            refresh_msg = "페이지 새로고침 후 매크로 재시작"
            timestamp_ui_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_message_signal.emit(f"[{timestamp_ui_refresh}] {refresh_msg}")
            self.logger.info(refresh_msg)

            try:
                self.browser.refresh()
                WebDriverWait(self.browser, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
            except Exception as e:
                error_msg_ui = f"페이지 새로고침 중 오류 발생: {str(e)}"
                error_msg_file = f"페이지 새로고침 중 오류 발생: {str(e)}"
                timestamp_ui_error = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_message_signal.emit(f"[{timestamp_ui_error}] {error_msg_ui}")
                self.logger.error(error_msg_file, exc_info=True)

            return True

        return False
