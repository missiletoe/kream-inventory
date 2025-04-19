from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LoginManager:
    def __init__(self, browser):
        self.browser = browser
        
    def is_logged_in(self):
        """로그인 상태 확인"""
        try:
            # 로그인 페이지인지 확인
            if 'login' in self.browser.current_url:
                return False
                
            # 상단 헤더에 로그아웃 버튼이 있는지 확인
            WebDriverWait(self.browser, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.top_link[href="/"]'))
            )
            return True
        except (TimeoutException, NoSuchElementException):
            return False
            
    def relogin(self, email, password):
        """로그인 재시도"""
        try:
            # 로그인 페이지 확인
            if 'login' not in self.browser.current_url:
                self.browser.get('https://kream.co.kr/login')
                
            # 이메일 입력
            email_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # 비밀번호 입력
            password_input = self.browser.find_element(By.CSS_SELECTOR, 'input[type="password"]')
            password_input.clear()
            password_input.send_keys(password)
            
            # 로그인 버튼 클릭
            login_button = self.browser.find_element(By.CSS_SELECTOR, 'button.btn.full.solid')
            login_button.click()
            
            # 로그인 완료 확인
            WebDriverWait(self.browser, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.top_link[href="/"]'))
            )
            
            return True
        except (TimeoutException, NoSuchElementException) as e:
            print(f"로그인 실패: {str(e)}")
            return False
            
    def check_and_relogin_if_needed(self, email, password):
        """로그인 상태 확인 후 필요시 재로그인"""
        if not self.is_logged_in():
            return self.relogin(email, password)
        return True 