# plugins/login_plugin.py

from PyQt6.QtCore import QObject, pyqtSignal
from src.core.plugin_base import PluginBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

class LoginPlugin(PluginBase, QObject):

    login_status = pyqtSignal(bool, str)

    def __init__(self, browser, config, plugin_manager=None):
        PluginBase.__init__(self, name="login", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        # 추가 초기화 필요시 수행

    def login(self, email, password):

        login_url = "https://kream.co.kr/login"
        self.browser.get(login_url)

        try:
            # 이메일/패스워드 입력 필드 대기 및 채우기
            wait = WebDriverWait(self.browser, 10)
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
            password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
            email_input.clear(); email_input.send_keys(email)
            password_input.clear(); password_input.send_keys(password)

            # 로그인 버튼 클릭
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()
            time.sleep(2)  # 페이지 전환 대기 (임시)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))  # 로그인 성공 판단

            # 성공 시그널
            self.login_status.emit(True, f"크림에 {email} 계정으로 로그인되었습니다.")

        except TimeoutException:

            # 실패 시그널
            self.login_status.emit(False, "로그인 실패: 이메일 또는 비밀번호를 확인해주세요.")