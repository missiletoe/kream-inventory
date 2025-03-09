from PyQt6.QtCore import QObject, pyqtSignal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

class LoginManager(QObject):
    login_status = pyqtSignal(bool, str)

    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    def _perform_login(self, email, password):
        login_url = 'https://kream.co.kr/login'
        self.browser.get(login_url)

        try:
            email_input = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
            password_input = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))

            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)

            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()
            time.sleep(2)
            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

            return True
        
        except TimeoutException:
            return False

    def login(self, email, password):
        if self._perform_login(email, password):
            self.login_status.emit(True, f"크림에 {email} 계정으로 로그인되었습니다.")
        else:
            self.login_status.emit(False, "로그인 실패: 이메일 또는 비밀번호를 확인해주세요.")
    
    def relogin(self, email, pw):
        self.login_status.emit(False, f'[{time.strftime("%H:%M:%S")}] 로그인 세션이 만료되었습니다. 다시 로그인합니다.')
        if self._perform_login(email, pw):
            self.login_status.emit(True, f'[{time.strftime("%H:%M:%S")}] 크림에 {email} 계정으로 로그인되었습니다.')

        self.login_status.emit(True, f'[{time.strftime("%H:%M:%S")}] 크림에 {email} 계정으로 로그인되었습니다.')