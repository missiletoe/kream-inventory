import time
from datetime import datetime, timedelta

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By


class ToastHandler:
    def __init__(self, browser, log_callback):
        self.browser = browser
        self.log = log_callback
        
    def check_toast_popup(self, wait_seconds=3):
        """토스트 팝업 메시지를 확인하고 처리"""
        try:
            # 토스트 팝업 확인 (여러 가능한 선택자 시도)
            toast_selectors = [
                'div.toast', 
                'div.toast-content',
                'div.toast-message',
                'div.snackbar',
                'div.alert-toast',
                'div.toast.sm.show'
            ]
            
            toast_found = False
            popup_text = ""
            logged_popup_text = ""  # Variable to store the already logged message
            
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
                                self.log(f"팝업 메시지: {popup_text}")
                                logged_popup_text = popup_text # Store the logged message
                                toast_found = True
                                break
                    
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
                                    # Only log if it's a new message or wasn't logged before
                                    if popup_text != logged_popup_text:
                                        self.log(f"팝업 메시지(지연 감지): {popup_text}")
                                    toast_found = True
                                    break
                        
                        if toast_found:
                            break
                            
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
            
            # 팝업 메시지별 처리
            if toast_found and popup_text:
                # 신규 보관신청이 제한된 카테고리의 상품
                if "신규 보관신청이 제한된 카테고리의 상품입니다" in popup_text:
                    self.log("신규 보관신청이 제한된 카테고리입니다. 다시 시도합니다.")
                    return {"status": "retry", "delay": 0}
                    
                # 일시적인 오류로 인한 재시도
                elif "상대방의 입찰 삭제" in popup_text or "인터넷, 와이파이" in popup_text:
                    delay = 3600  # 1시간 대기
                    block_time = datetime.now() + timedelta(seconds=delay)
                    self.log(f"[{datetime.now().strftime('%H:%M:%S')} ~ {block_time.strftime('%H:%M:%S')}] 매크로 중단")
                    self.log("일시적인 오류로 인해 1시간 후 다시 시도합니다.")
                    return {"status": "block", "delay": delay}
                    
                # 기타 오류 메시지
                else:
                    self.log(f"팝업 메시지 감지: {popup_text}. 다시 시도합니다.")
                    return {"status": "retry", "delay": 0}
            
            return {"status": "success", "delay": 0}
            
        except Exception as e:
            self.log(f"팝업 메시지 확인 중 오류: {str(e)}")
            return {"status": "error", "delay": 0}
    
    def check_service_error(self):
        """서비스 오류 확인"""
        try:
            error_element = self.browser.find_element(By.CSS_SELECTOR, 'div.info_txt')
            if error_element.text == '일시적인 서비스 장애 입니다.':
                self.log(f"일시적인 서비스 장애입니다. 다시 시도합니다.")
                return True
            return False
        except (NoSuchElementException, StaleElementReferenceException):
            return False 