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
    def handle_model_number_modal(browser, log_handler):
        """모델번호 확인 모달 처리"""
        try:
            # Wait briefly for modal to appear
            WebDriverWait(browser, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
            )
            
            # Check if it's the model number modal
            modals = browser.find_elements(By.CSS_SELECTOR, 'div.layer_container')
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
            modals = browser.find_elements(By.CSS_SELECTOR, 'div.layer_container')
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
            modals = browser.find_elements(By.CSS_SELECTOR, 'div.layer_container')
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
                                except:
                                    # Fall back to direct checkbox click
                                    browser.execute_script("arguments[0].click();", checkbox)
                                    
                        # Find and click confirm button
                        confirm_buttons = modal.find_elements(By.CSS_SELECTOR, 'a.btn_link, button.btn')
                        for button in confirm_buttons:
                            if "확인" in button.text or "동의" in button.text or "계속" in button.text:
                                browser.execute_script("arguments[0].click();", button)
                                time.sleep(0.5)
                                log_handler.log("결제 확인 모달 처리 완료")
                                return True
                except:
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
    def handle_timeout_exception(browser, log_handler, exception, context):
        """Handles TimeoutException by logging the error context."""
        if log_handler:
            log_handler.log(f"[타임아웃] {context}: {str(exception)}")
            return True
        return False

    @staticmethod
    def handle_no_such_element_exception(browser, log_handler, exception, context):
        """Handles NoSuchElementException by logging the error context."""
        if log_handler:
            log_handler.log(f"[엘리먼트 미발견] {context}: {str(exception)}")
            return True
        return False

    @staticmethod
    def handle_stale_element_exception(browser, log_handler, exception, context):
        """Handles StaleElementReferenceException by logging the error context."""
        if log_handler:
            log_handler.log(f"[오래된 요소 참조 오류] {context}: {str(exception)}")
            return True
        return False

    @staticmethod
    def handle_general_exception(browser, log_handler, exception, context):
        """Handles generic exceptions by logging the error context and traceback."""
        if log_handler:
            trace_msg = traceback.format_exc()
            if len(trace_msg) > 1000:
                trace_msg = trace_msg[:900] + "...(생략)..." + trace_msg[-100:]
            
            if isinstance(exception, TimeoutException):
                log_handler.log(f"[타임아웃] {context}: {str(exception)}")
            elif isinstance(exception, (NoSuchElementException, StaleElementReferenceException)):
                log_handler.log(f"[엘리먼트 미발견] {context}: {str(exception)}")
            elif isinstance(exception, WebDriverException):
                log_handler.log(f"[웹드라이버 오류] {context}: {str(exception)}")
            else:
                log_handler.log(f"[예외발생] {context}: {str(exception)}")
                log_handler.log(f"[상세오류] {trace_msg}")
                
            # 페이지 오류 확인
            try:
                if browser is not None:
                    if "500" in browser.title or "error" in browser.title.lower():
                        log_handler.log(f"서버 오류 페이지 감지: {browser.title}")
                        return False
                    
                    try:
                        error_elements = browser.find_elements(By.CSS_SELECTOR, 'div.error_message, div.info_txt, div.layer_toast.show')
                        for element in error_elements:
                            if element.is_displayed():
                                error_text = element.text.strip()
                                if error_text:
                                    log_handler.log(f"오류 메시지 감지: {error_text}")
                                    return False
                    except:
                        pass
            except:
                pass
                
            return True  # 예외 처리 성공
        return False  # 로그 핸들러 없음 (예외 처리 실패) 