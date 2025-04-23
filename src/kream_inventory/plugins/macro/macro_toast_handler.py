import re
import time

from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


class MacroToastHandler:
    def __init__(self, browser: WebDriver, log_handler=None):
        self.browser = browser
        self.log_handler = log_handler
        self.toast_history = []
        self.recent_messages = set()  # Track recently seen messages to avoid duplicates
        self.last_cleanup_time = time.time()

    def wait_for_element(self, by, selector, timeout=5):
        """
        요소를 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def wait_for_elements(self, by, selector, timeout=5):
        """
        요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소들의 리스트
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def _log_toast_message(self, message, allowed_key="TOAST_CONTENT"):
        """Log a toast message, avoiding duplicates"""
        # Create a hash of the message to track duplicates
        message_hash = hash(message)

        # Clear old messages periodically (every 60 seconds)
        current_time = time.time()
        if current_time - self.last_cleanup_time > 60:
            self.recent_messages.clear()
            self.last_cleanup_time = current_time

        # Only log if we haven't seen this message recently
        if message_hash not in self.recent_messages:
            if self.log_handler:
                self.log_handler.log(message, allowed_key=allowed_key)
            # Add to recently seen messages
            self.recent_messages.add(message_hash)

    def check_service_error(self, log_errors=True):
        """일시적인 서비스 장애 확인"""
        try:
            elements = self.wait_for_elements(By.CSS_SELECTOR, 'div.info_txt')
            for element in elements:
                if element.text == '일시적인 서비스 장애 입니다.':
                    if log_errors:
                        if self.log_handler:
                            self.log_handler.log("일시적인 서비스 장애 감지", allowed_key="TOAST_ERROR")
                    return True
            return False
        except (NoSuchElementException, StaleElementReferenceException):
            return False
        except Exception as e:
            if log_errors:
                if self.log_handler:
                    self.log_handler.log(f"서비스 오류 확인 중 예외 발생: {str(e)}", allowed_key="TOAST_ERROR")
            return False

    def check_toast_popup(self, wait_seconds=0, total_wait_time=0):
        """토스트 메시지 확인 및 처리"""
        result = {
            "status": "success",  # 'success', 'block', 'retry', 'error'
            "message": "",
            "delay": 0
        }

        # 토스트 팝업 확인 (최대 wait_seconds 초 동안 대기)
        start_time = time.time()
        while time.time() - start_time < wait_seconds:
            # 다양한 토스트 셀렉터 확인
            toast_selectors = [
                'div.toast.lg.show',
                'div.toast.lg:not(.hide)',
                'div.toast.sm.show',
                'div.toast.sm:not(.hide)',
                'div.layer_toast.show',
                'div.toast_alert.show',
                'div.toast_alert:not(.hide)',
                'div.toast_container .toast:not(.hide)'
            ]

            for selector in toast_selectors:
                toast_elements = self.wait_for_elements(By.CSS_SELECTOR, selector)
                if toast_elements:
                    for toast in toast_elements:
                        toast_text = toast.text.strip()
                        if not toast_text:
                            continue

                        # Toast 내용 저장
                        self.toast_history.append(toast_text)

                        # 토스트 내용 로깅 (중복 방지 로직 사용)
                        self._log_toast_message(f"[!] {toast_text}")

                        # Block 케이스 체크 (잠시 후 다시 시도)
                        if any(x in toast_text for x in ["잠시 후", "다시 시도", "요청 초과", "재시도", "방문자가 많아"]):
                            # 지연 시간 설정 (기본 30초, 번호가 있으면 추출)
                            delay_seconds = 30

                            # 숫자로 시작하는 시간 추출
                            time_match = re.search(r'(\d+)(?:초|분)', toast_text)
                            if time_match:
                                delay_value = int(time_match.group(1))
                                if '분' in time_match.group(0):
                                    delay_seconds = delay_value * 60
                                else:
                                    delay_seconds = delay_value

                            result["status"] = "block"
                            result["message"] = toast_text
                            result["delay"] = delay_seconds

                            self._log_toast_message(f"[BLOCKED] {toast_text} ({delay_seconds}초 대기)",
                                                    allowed_key="TOAST_BLOCK")

                            return result

                        # 다른 에러 메시지 케이스
                        if any(x in toast_text for x in ["오류", "실패", "error", "failed"]):
                            result["status"] = "error"
                            result["message"] = toast_text

                            self._log_toast_message(f"[ERROR] {toast_text}", allowed_key="TOAST_ERROR")

                            return result

                        # 재시도 가능 케이스
                        if any(x in toast_text for x in ["재시도", "retry"]):
                            result["status"] = "retry"
                            result["message"] = toast_text
                            result["delay"] = 5  # 기본 5초 대기

                            self._log_toast_message(f"[RETRY] {toast_text}", allowed_key="TOAST_RETRY")

                            return result

            # 토스트가 없으면 잠시 대기 후 다시 확인
            time.sleep(0.2)

        # 요청 횟수 초과 텍스트 체크 (페이지 소스)
        try:
            if "허용된 요청 횟수를 초과했습니다" in self.browser.page_source:
                error_message = "허용된 요청 횟수를 초과했습니다"
                result["status"] = "block"
                result["message"] = error_message
                result["delay"] = 30

                self._log_toast_message(f"[EXCEEDED TRIES] {error_message} (30초 대기)", allowed_key="REQUEST_LIMIT")

                return result
        except Exception as e:
            self._log_toast_message(f"요청 횟수 확인 중 오류: {str(e)}", allowed_key="ERROR")

        return result
