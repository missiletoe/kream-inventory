import time
import traceback

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .macro_log_handler import MacroLogHandler


class MacroExceptions:
    @staticmethod
    def _get_log_function(log_param):
        """Helper method to extract the appropriate log function from param"""
        if isinstance(log_param, MacroLogHandler):
            return log_param.log
        else:
            return log_param

    @staticmethod
    def wait_for_element(browser, by, selector, timeout=5):
        """
        요소를 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            browser: 웹드라이버 인스턴스
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소
        """
        return WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    @staticmethod
    def wait_for_elements(browser, by, selector, timeout=5):
        """
        요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            browser: 웹드라이버 인스턴스
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소들의 리스트
        """
        return WebDriverWait(browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    @staticmethod
    def handle_model_number_modal(browser, log_handler):
        """모델번호 확인 모달 처리"""
        try:
            # Wait briefly for modal to appear
            WebDriverWait(browser, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
            )

            # Check if it's the model number modal
            modals = MacroExceptions.wait_for_elements(browser, By.CSS_SELECTOR, 'div.layer_container')
            for modal in modals:
                try:
                    title = modal.find_element(By.CSS_SELECTOR, 'div.layer_header .title').text
                    if "모델번호" in title:
                        # Find the confirm button in this specific modal
                        confirm_btn = modal.find_element(By.CSS_SELECTOR, 'div.btn_layer_confirm')
                        confirm_btn.click()
                        time.sleep(0.5)
                        log_handler.log("모델번호 확인 모달 처리 완료")
                        return True
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            # No model number modal found or already dismissed
            return True

        except TimeoutException:
            # No modal appeared
            return True
        except Exception as e:
            log_handler.log(f"모델번호 모달 처리 중 오류: {str(e)}")
            return False

    @staticmethod
    def handle_label_size_modal(browser, log_handler):
        """라벨 사이즈 확인 모달 처리"""
        try:
            # Wait briefly for modal to appear
            WebDriverWait(browser, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
            )

            # Check if it's the label size modal
            modals = MacroExceptions.wait_for_elements(browser, By.CSS_SELECTOR, 'div.layer_container')
            for modal in modals:
                try:
                    content = modal.text
                    if "라벨" in content and "사이즈" in content:
                        # Find the confirm button in this specific modal
                        confirm_btn = modal.find_element(By.CSS_SELECTOR, 'div.btn_layer_confirm')
                        confirm_btn.click()
                        time.sleep(0.5)
                        log_handler.log("라벨 사이즈 확인 모달 처리 완료")
                        return True
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            # No label size modal found or already dismissed
            return True

        except TimeoutException:
            # No modal appeared
            return True
        except Exception as e:
            log_handler.log(f"라벨 사이즈 모달 처리 중 오류: {str(e)}")
            return False

    @staticmethod
    def handle_payment_modal(browser, log_handler):
        """결제 모달 처리"""
        try:
            # Wait for payment confirmation modal
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
            )

            # Check all modals
            modals = MacroExceptions.wait_for_elements(browser, By.CSS_SELECTOR, 'div.layer_container')
            for modal in modals:
                try:
                    # Check if payment related (looking for keywords)
                    modal_text = modal.text.lower()
                    if "결제" in modal_text or "payment" in modal_text or "보증금" in modal_text:
                        # Try to find checkboxes and check them
                        checkboxes = modal.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                        for checkbox in checkboxes:
                            if not checkbox.is_selected():
                                try:
                                    # Try clicking the associated label instead of the checkbox
                                    parent = checkbox.find_element(By.XPATH, './..')
                                    browser.execute_script("arguments[0].click();", parent)
                                except Exception as e:
                                    # Fall back to direct checkbox click
                                    log_handler.log(f"체크박스 레이블 클릭 실패, 직접 클릭 시도: {str(e)}")
                                    browser.execute_script("arguments[0].click();", checkbox)

                        # Find and click confirm button
                        confirm_buttons = modal.find_elements(By.CSS_SELECTOR, 'a.btn_link, button.btn')
                        for button in confirm_buttons:
                            if "확인" in button.text or "동의" in button.text or "계속" in button.text:
                                browser.execute_script("arguments[0].click();", button)
                                time.sleep(0.5)
                                log_handler.log("결제 확인 모달 처리 완료")
                                return True
                except Exception as e:
                    log_handler.log(f"모달 내 버튼 클릭 실패: {str(e)}")
                    continue

            # No relevant modal found or already confirmed
            return True

        except TimeoutException:
            # No modal appeared, which is fine
            return True
        except Exception as e:
            log_handler.log(f"결제 모달 처리 중 오류: {str(e)}")
            return False

    # --- New Generic Exception Handlers ---

    @staticmethod
    def handle_timeout_exception(browser, log_handler, e, operation_name="작업"):
        """타임아웃 예외 처리"""
        if log_handler:
            log_handler.log(f"{operation_name} 타임아웃: {str(e)}", allowed_key="ERROR")

        # False를 반환하여 작업을 계속할 수 없음을 알림
        return False

    @staticmethod
    def handle_element_exception(browser, log_handler, e, operation_name="요소 처리"):
        """요소 관련 예외 처리"""
        if log_handler:
            if isinstance(e, NoSuchElementException):
                log_handler.log(f"{operation_name} 중 요소를 찾을 수 없음: {str(e)}", allowed_key="ERROR")
            elif isinstance(e, StaleElementReferenceException):
                log_handler.log(f"{operation_name} 중 요소 참조 오류: {str(e)}", allowed_key="ERROR")
            else:
                log_handler.log(f"{operation_name} 중 요소 관련 오류: {str(e)}", allowed_key="ERROR")

        # False를 반환하여 작업을 계속할 수 없음을 알림
        return False

    @staticmethod
    def handle_general_exception(browser, log_handler, e, operation_name="작업", detailed_logging=False):
        """일반 예외 처리 (더 자세한 로깅 포함)"""
        # 오류 유형에 따라 다르게 처리
        if isinstance(e, TimeoutException):
            return MacroExceptions.handle_timeout_exception(browser, log_handler, e, operation_name)
        elif isinstance(e, (NoSuchElementException, StaleElementReferenceException)):
            return MacroExceptions.handle_element_exception(browser, log_handler, e, operation_name)
        elif isinstance(e, WebDriverException) and "no such window" in str(e).lower():
            if log_handler:
                log_handler.log(f"브라우저 창이 닫혔습니다: {str(e)}", allowed_key="ERROR")
            return False

        # 기타 예외 처리
        error_message = str(e)
        error_type = type(e).__name__

        if log_handler:
            log_message = f"{operation_name} 중 예외 발생: [{error_type}] {error_message}"
            log_handler.log(log_message, allowed_key="EXCEPTION")

            if detailed_logging:
                # 스택 트레이스 로깅 (개발 및 디버깅용)
                stack_trace = traceback.format_exc()
                log_handler.log(f"스택 트레이스: {stack_trace}", allowed_key="EXCEPTION")

        # 특정 키워드에 따라 자동 처리 결정
        recoverable_keywords = ["timeout", "stale", "not found", "temporary"]

        for keyword in recoverable_keywords:
            if keyword in error_message.lower():
                if log_handler:
                    log_handler.log(f"복구 가능 오류 감지: {keyword}", allowed_key="ERROR")
                return True  # 복구 가능

        # 기본적으로 복구 불가능
        return False
