from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time


class ErrorHandler:
    def __init__(self, browser, log_callback):
        self.browser = browser
        self.log = log_callback
        
    def check_wrong_page(self, product_id):
        """잘못된 페이지 확인 및 처리"""
        # 페이지 로딩 시간 대기 (브라우저 성능 차이 고려)
        time.sleep(3)
        
        # 현재 페이지 확인
        current_url = self.browser.current_url
        
        # 신청내역 페이지 확인 (span.title_txt 요소에서 텍스트 확인)
        try:
            title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
            for element in title_elements:
                if "신청 내역" in element.text:
                    return {"status": "application_page", "message": "신청내역 페이지 감지됨"}
        except:
            pass
            
        # 보관판매 페이지 확인
        if 'inventory' in current_url and product_id in current_url:
            return {"status": "inventory_page", "message": "보관판매 페이지 감지됨"}
            
        # 그 외 다른 페이지
        else:
            self.log("예상 페이지가 아닙니다. 새로고침합니다.")
            self.browser.refresh()
            
            # 페이지가 완전히 로드될 때까지 대기
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                )
                
                # 페이지 로딩 시간 대기 (브라우저 성능 차이 고려)
                time.sleep(3)
                
                # 새로고침 후 페이지 다시 확인
                try:
                    title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
                    for element in title_elements:
                        if "신청 내역" in element.text:
                            return {"status": "application_page", "message": "새로고침 후 신청내역 페이지 감지됨"}
                except:
                    pass
                    
                if 'inventory' in self.browser.current_url and product_id in self.browser.current_url:
                    return {"status": "inventory_page", "message": "새로고침 후 보관판매 페이지 감지됨"}
                else:
                    return {"status": "unknown_page", "message": "새로고침 후에도 예상 페이지가 아닙니다."}
            
            except TimeoutException:
                return {"status": "error", "message": "페이지 로딩 실패"}
    
    def verify_page_loading(self, selectors):
        """페이지 로딩 확인"""
        for selector in selectors:
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                self.log(f"필수 요소를 찾을 수 없습니다: {selector}")
                return False
        return True
    
    def check_login_required(self, email, password):
        """로그인 필요 여부 확인"""
        if 'login' in self.browser.current_url:
            self.log("로그인이 필요합니다.")
            return True
        return False 