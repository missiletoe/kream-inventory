"""토스트 메시지를 감지하고 처리하는 클래스입니다."""

import time
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class MacroToastHandler(QObject):
    """웹 페이지의 토스트 메시지를 감지하고 처리하는 클래스입니다.

    특정 토스트 메시지에 따라 작업을 일시 중단하거나 재시도합니다.
    """

    log_message_signal = pyqtSignal(str)

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

    def handle_toast(self: "MacroToastHandler") -> bool:
        """토스트 메시지를 감지하고 적절한 조치를 취합니다.

        Returns:
            bool: 토스트 메시지 처리 후 매크로를 즉시 반환(중단 또는 재시작 결정)해야 하면 True,
                  그렇지 않으면 False를 반환합니다.
        """
        # 가능한 모든 토스트 선택자 목록 - 가장 자주 사용되는 선택자를 먼저 배치
        toast_selectors: List[str] = [
            "div#toast.toast.lg.show",  # 실제 HTML에서 확인된 형식
            "div#toast.toast.mo.show",  # 실제 HTML에서 확인된 형식
            "div.toast.lg.show",  # ID 없이 클래스만 있는 경우
            "div.toast.mo.show",  # 모바일 버전일 수 있음
            "div.toast.show",  # 일반적인 클래스 조합
        ]

        for selector in toast_selectors:
            try:
                # 각 선택자에 대해 짧은 시간(1초)만 대기하여 더 빠르게 확인
                popup = WebDriverWait(self.browser, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )

                # 토스트 요소를 찾았으므로 처리 로직 실행
                popup_text = self._get_toast_text(popup)

                if popup_text:
                    return self._process_toast_message(popup_text)

            except TimeoutException:
                # 이 선택자로는 토스트를 찾지 못함, 다음 선택자 시도
                continue
            except Exception as e:
                self.log_message_signal.emit(
                    f'[{time.strftime("%H:%M:%S")}] 토스트 선택자 [{selector}] 처리 중 오류: {str(e)}'
                )

        # 모든 선택자를 시도했지만 토스트를 찾지 못함
        return False

    def _get_toast_text(self: "MacroToastHandler", toast_element: WebElement) -> str:
        """토스트 요소에서 텍스트를 추출합니다.

        여러 가능한 경로를 시도하여 텍스트를 가져옵니다.

        Args:
            toast_element: 토스트 WebElement

        Returns:
            str: 추출된 텍스트 또는 빈 문자열
        """
        # 먼저 요소 전체 텍스트 시도
        text = toast_element.text.strip()
        if text:
            return text

        # 내부 요소들을 시도
        try:
            # 제공된 HTML 구조에 맞는 선택자
            content_selectors = [
                "div.toast-content p",  # 실제 HTML에서 확인된 구조
                ".toast-content",  # 내용 컨테이너
                "p",  # 단순 p 태그
                ".toast-message",  # 일반적인 클래스 이름
                "span",  # span 태그
                "div",  # 내부 div
            ]

            for selector in content_selectors:
                try:
                    elements = toast_element.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        el_text = el.text.strip()
                        if el_text:
                            return el_text
                except Exception:
                    # 특정 선택자에서 오류가 발생하면 다음 선택자 시도
                    continue
        except Exception:
            # 내부 요소에서 텍스트를 가져오지 못함
            pass

        return ""  # 텍스트를 찾지 못한 경우

    def _process_toast_message(self: "MacroToastHandler", message: str) -> bool:
        """토스트 메시지 텍스트를 처리합니다.

        Args:
            message: 토스트 메시지 텍스트

        Returns:
            bool: 매크로를 중단하고 다음 루프로 진행해야 하면 True, 아니면 False
        """
        # 로그 메시지 출력
        self.log_message_signal.emit(f'[{time.strftime("%H:%M:%S")}] 토스트: {message}')

        # "신규 보관 신청이 제한된 카테고리의 상품입니다." 메시지 처리
        # 정확한 메시지와 부분 일치로 모두 확인
        if (
            "신규 보관 신청이 제한된 카테고리" in message
            or "신규 보관신청이 제한된 카테고리" in message
        ):

            self.log_message_signal.emit(
                f'[{time.strftime("%H:%M:%S")}] 카테고리 제한 - 최소 대기 후 재시도'
            )

            # 매우 짧은 대기 시간 (0.2초)
            time.sleep(0.2)

            # 페이지 새로고침 없이 즉시 다음 루프로 진행

            # True 반환으로 메인 루프에 매크로 작업 중단 및 재시도 신호 전송
            return True

        # 심각한 오류 메시지 처리
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
            # 약 1시간(3600초) 대기
            wait_seconds = 3600

            self.log_message_signal.emit(
                f'[{time.strftime("%H:%M:%S")}] 심각한 오류 발생. 약 {wait_seconds // 60}분간 매크로 중단 후 페이지 새로고침 및 재시도합니다.'
            )

            time.sleep(wait_seconds)

            self.log_message_signal.emit(
                f'[{time.strftime("%H:%M:%S")}] 페이지를 새로고침하고 매크로를 재시작합니다.'
            )

            try:
                # 페이지 새로고침
                self.browser.refresh()
                # 페이지가 완전히 로드될 때까지 대기
                WebDriverWait(self.browser, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
            except Exception as e:
                self.log_message_signal.emit(
                    f'[{time.strftime("%H:%M:%S")}] 페이지 새로고침 중 오류: {str(e)}'
                )

            # True 반환으로 메인 루프에 매크로 작업 중단 및 재시도 신호 전송
            return True

        # 그 외 토스트는 로그만 남기고 메인 로직 계속 진행
        return False
