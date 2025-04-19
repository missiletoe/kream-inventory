import traceback

from selenium.common import (NoSuchElementException,
                             StaleElementReferenceException, TimeoutException)
from selenium.webdriver.common.by import By


class MacroExceptions:
    @staticmethod
    def handle_model_number_modal(browser, log_callback):
        """모델번호 확인 모달 처리"""
        try:
            modal_container = browser.find_element(By.CSS_SELECTOR, 'div.layer_container')
            modal_title = modal_container.find_element(By.CSS_SELECTOR, 'div.layer_content h4.title, div.layer_content .title')
            
            if "모델번호" in modal_title.text:
                log_callback("모델번호 확인 모달 처리 중...")
                confirm_button = modal_container.find_element(By.CSS_SELECTOR, 'button.btn.full.solid.large')
                confirm_button.click()
                return True
            return True
        except (NoSuchElementException, TimeoutException):
            return True

    @staticmethod
    def handle_label_size_modal(browser, log_callback):
        """라벨 사이즈 확인 모달 처리"""
        try:
            modal_container = browser.find_element(By.CSS_SELECTOR, 'div.layer_container')
            if "안쪽 라벨 사이즈" in modal_container.text:
                log_callback("라벨 사이즈 확인 모달 처리 중...")
                
                checkboxes = modal_container.find_elements(By.CSS_SELECTOR, 'div.checkbox_item input.blind[type="checkbox"]')
                if len(checkboxes) == 0:
                    checkbox_labels = modal_container.find_elements(By.CSS_SELECTOR, 'div.checkbox_item label.check_label')
                    for label in checkbox_labels:
                        browser.execute_script("arguments[0].click();", label)
                else:
                    for checkbox in checkboxes:
                        if not checkbox.is_selected():
                            browser.execute_script("arguments[0].click();", checkbox)
                
                continue_button = modal_container.find_element(By.CSS_SELECTOR, 'button.btn.solid.full.large:not(.disabled)')
                continue_button.click()
                log_callback("라벨 사이즈 확인 완료")
                return True
            return True
        except (NoSuchElementException, TimeoutException):
            return True

    @staticmethod
    def handle_payment_modal(browser, log_callback):
        """결제 모달 처리"""
        try:
            modal_container = browser.find_element(By.CSS_SELECTOR, 'div.layer_container')
            checkboxes = modal_container.find_elements(By.CSS_SELECTOR, 'div.title-description-checkbox input[type="checkbox"]')
            
            if len(checkboxes) > 0:
                log_callback(f"체크박스 {len(checkboxes)}개 발견, 모두 선택합니다.")
                for i, checkbox in enumerate(checkboxes):
                    if not checkbox.is_selected():
                        try:
                            label = checkbox.find_element(By.XPATH, './ancestor::label')
                            browser.execute_script("arguments[0].click();", label)
                            log_callback(f"체크박스 {i+1} 선택 완료")
                        except:
                            browser.execute_script("arguments[0].click();", checkbox)
                            log_callback(f"체크박스 {i+1} 선택 완료 (직접 클릭)")
                
                return True
            return False
        except (NoSuchElementException, TimeoutException):
            return False

    # --- New Generic Exception Handlers ---

    @staticmethod
    def handle_timeout_exception(browser, log_callback, exception, context):
        """Handles TimeoutException by logging the error context."""
        error_msg = f"[{context}] Timeout 오류 발생: {str(exception)}"
        log_callback(error_msg)
        # Optionally log current URL for debugging
        try:
            log_callback(f"[{context}] 현재 URL: {browser.current_url}")
        except Exception as url_err:
            log_callback(f"[{context}] 현재 URL 로깅 중 오류: {url_err}")
        return False # Indicate failure for the current attempt

    @staticmethod
    def handle_no_such_element_exception(browser, log_callback, exception, context):
        """Handles NoSuchElementException by logging the error context."""
        error_msg = f"[{context}] 요소를 찾을 수 없음 오류: {str(exception)}"
        log_callback(error_msg)
        # Optionally log current URL or page source snippet for debugging
        try:
            log_callback(f"[{context}] 현재 URL: {browser.current_url}")
        except Exception as url_err:
            log_callback(f"[{context}] 현재 URL 로깅 중 오류: {url_err}")
        return False # Indicate failure for the current attempt

    @staticmethod
    def handle_stale_element_exception(browser, log_callback, exception, context):
        """Handles StaleElementReferenceException by logging the error context."""
        error_msg = f"[{context}] 오래된 요소 참조 오류: {str(exception)}. 페이지가 변경되었을 수 있습니다."
        log_callback(error_msg)
        # Stale element often means a refresh might help, but for now, just fail the attempt
        return False # Indicate failure for the current attempt

    @staticmethod
    def handle_general_exception(browser, log_callback, exception, context):
        """Handles generic exceptions by logging the error context and traceback."""
        error_msg = f"[{context}] 예상치 못한 오류 발생: {str(exception)}\n{traceback.format_exc()}"
        log_callback(error_msg)
        # Attempt recovery like refresh (optional, can add later)
        # try:
        #     log_callback(f"[{context}] 오류 발생. 페이지 새로고침 시도.")
        #     browser.refresh()
        #     time.sleep(1)
        # except Exception as refresh_err:
        #     log_callback(f"[{context}] 새로고침 중 오류: {refresh_err}")
        return False # Indicate failure for the current attempt 