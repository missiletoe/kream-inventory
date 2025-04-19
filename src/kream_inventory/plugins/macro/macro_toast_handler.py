import time
from datetime import datetime, timedelta
import traceback

from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.kream_inventory.plugins.macro.macro_log_handler import MacroLogHandler

class MacroToastHandler:
    def __init__(self, browser: WebDriver, log_callback=None, log_handler=None):
        self.browser = browser
        
        # Support both direct callback and LogHandler instance
        if log_handler and isinstance(log_handler, MacroLogHandler):
            self.log_handler = log_handler
            self.log = log_handler.direct_log
        else:
            # For backward compatibility
            self.log_handler = None
            self.log = log_callback

    def check_service_error(self, log_errors=True):
        """일시적인 서비스 장애 확인"""
        try:
            error_element = self.browser.find_element(By.CSS_SELECTOR, 'div.info_txt')
            if error_element.text == '일시적인 서비스 장애 입니다.':
                if log_errors:
                    self.log(f"일시적인 서비스 장애 감지")
                return True
            return False
        except (NoSuchElementException, StaleElementReferenceException):
            return False
        except Exception as e:
            if log_errors:
                self.log(f"서비스 오류 확인 중 예외 발생: {str(e)}")
            return False

    def check_toast_popup(self, wait_seconds=3, total_wait_time=0, check_only_service_error=False):
        """팝업 메시지를 확인하고 상태와 필요한 지연 시간을 반환합니다.
        
        Args:
            wait_seconds (int): 초기 팝업 확인 대기 시간 (초).
            total_wait_time (int): 매크로 실행 중 누적된 대기 시간 (초).
            check_only_service_error (bool): True이면 '일시적인 서비스 장애' 메시지만 확인.

        Returns:
            dict: {"status": "success"|"retry"|"block"|"error", "delay": <지연 시간(초)>}
                  status:
                      "success": 문제 없음
                      "retry": 재시도 필요 (오류 팝업 등)
                      "block": 장시간 대기 필요 (입찰 삭제, 네트워크 오류 등)
                      "error": 팝업 확인 중 오류 발생
                  delay: "block" 상태일 때 대기해야 할 시간 (초)
        """
        try:
            # Handle check_only_service_error flag
            if check_only_service_error:
                try:
                    error_element = self.browser.find_element(By.CSS_SELECTOR, 'div.info_txt')
                    if error_element.text == '일시적인 서비스 장애 입니다.':
                        self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 팝업 메시지 감지: {error_element.text}")
                        return {"status": "error", "delay": 0} # Treat service error as immediate error for retry/stop
                    return {"status": "success", "delay": 0} # No service error found
                except (NoSuchElementException, StaleElementReferenceException):
                    return {"status": "success", "delay": 0} # No service error element found
                except Exception as e:
                     self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 서비스 오류 확인 중 오류: {str(e)}")
                     return {"status": "error", "delay": 0}


            toast_selectors = [
                "div.layer_toast.show",  # Kream 일반 토스트
                "div.swal2-popup.swal2-toast.swal2-show", # SweetAlert2 토스트
                "div.Toastify__toast--error", # React-Toastify 오류
                "div.Toastify__toast--warning", # React-Toastify 경고
                 "div.info_txt" # 서비스 장애 메시지 확인용 (추가)
            ]
            
            toast_found = False
            popup_text = ""
            
            # 초기 확인 (기존 팝업이 이미 떠 있을 수 있음)
            for selector in toast_selectors:
                try:
                    popups = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    for popup in popups:
                        # 팝업이 보이는지 확인
                        is_visible = self.browser.execute_script(
                            "return (arguments[0].offsetWidth > 0 && arguments[0].offsetHeight > 0) || " +
                            "window.getComputedStyle(arguments[0]).display !== 'none' || " +
                            "window.getComputedStyle(arguments[0]).visibility !== 'hidden' || " +
                            "'show' in arguments[0].getAttribute('class')", 
                            popup
                        )
                        
                        if is_visible:
                            popup_text = popup.text.strip()
                            if popup_text:
                                # Ignore empty or irrelevant toasts
                                if popup_text != "찜하기": # Example of an irrelevant toast
                                    toast_found = True
                                    break
                                else:
                                     popup_text = "" # Reset if irrelevant
                    
                    if toast_found:
                        break
                        
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            
            # 짧은 대기 후 한 번 더 확인 (애니메이션 효과 등으로 늦게 나타날 수 있음)
            if not toast_found:
                time.sleep(wait_seconds)
                
                for selector in toast_selectors:
                    try:
                        popups = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        for popup in popups:
                            is_visible = self.browser.execute_script(
                                "return (arguments[0].offsetWidth > 0 && arguments[0].offsetHeight > 0) || " +
                                "window.getComputedStyle(arguments[0]).display !== 'none' || " +
                                "window.getComputedStyle(arguments[0]).visibility !== 'hidden' || " +
                                "'show' in arguments[0].getAttribute('class')", 
                                popup
                            )
                            
                            if is_visible:
                                popup_text = popup.text.strip()
                                if popup_text:
                                    toast_found = True
                                    break
                        
                        if toast_found:
                            break
                            
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
            
            # 팝업 메시지별 처리
            if toast_found and popup_text:

                # 서비스 장애 메시지 처리 (check_only_service_error=False일 때도 확인)
                if popup_text == '일시적인 서비스 장애 입니다.':
                    self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 팝업 메시지 감지: {popup_text}")
                    return {"status": "error", "delay": 0} # Treat service error as immediate error

                # Block conditions
                elif "상대방의 입찰 삭제" in popup_text or "인터넷, 와이파이" in popup_text or "잠시 후 다시 시도" in popup_text:
                    base_delay = 3600  # 1시간 기본 대기
                    actual_delay = max(0, base_delay - total_wait_time) # 누적 대기 시간 제외
                    
                    block_start_time = datetime.now()
                    block_end_time = block_start_time + timedelta(seconds=actual_delay)
                    
                    self.log(f"[{block_start_time.strftime('%H:%M:%S')}] 팝업 메시지 감지: {popup_text}")
                    if actual_delay > 0:
                        self.log(f"[{block_start_time.strftime('%H:%M:%S')} ~ {block_end_time.strftime('%H:%M:%S')}] 매크로 {actual_delay}초 동안 중단 (누적 대기: {total_wait_time}초 차감)")
                    else:
                        self.log(f"[{block_start_time.strftime('%H:%M:%S')}] 누적 대기 시간({total_wait_time}초)이 1시간을 초과하여 즉시 재시도합니다.")
                    return {"status": "block", "delay": actual_delay}
                    
                # Retry conditions (non-blocking errors)
                else:
                    self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 팝업 메시지 감지: {popup_text}")
                    return {"status": "retry", "delay": 0}
            
            # No relevant toast found
            return {"status": "success", "delay": 0}
            
        except Exception as e:
            self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 팝업 메시지 확인 중 오류: {traceback.format_exc()}")
            return {"status": "error", "delay": 0} 