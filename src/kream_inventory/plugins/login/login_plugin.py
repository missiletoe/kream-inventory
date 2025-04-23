import re
import time

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.kream_inventory.core.plugin_base import PluginBase
from src.kream_inventory.plugins.macro.macro_toast_handler import MacroToastHandler


class LoginPlugin(PluginBase, QObject):

    login_status = pyqtSignal(bool, str)

    def __init__(self, browser, config, plugin_manager=None):
        PluginBase.__init__(self, name="login", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        # 토스트 메시지 핸들러 초기화
        self.toast_handler = MacroToastHandler(browser)

    def login(self, email, password):
        # 이메일 형식 검증
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.login_status.emit(False, "로그인 실패: 유효하지 않은 이메일 형식입니다.")
            return

        # 비밀번호 형식 검증 (8-16자, 문자와 숫자 포함, 특수문자 허용)
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d).{8,16}$'
        if not re.match(password_pattern, password):
            self.login_status.emit(False, "로그인 실패: 비밀번호는 8자 이상 16자 이하이며, 문자와 숫자를 포함해야 합니다. 특수문자도 사용 가능합니다.")
            return

        login_url = "https://kream.co.kr/login"
        landing_url = "https://kream.co.kr/"
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
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))  # 페이지 로드 확인

            # 토스트 메시지 확인 (로그인 실패 시 토스트 메시지가 표시됨)
            toast_result = self.toast_handler.check_toast_popup(wait_seconds=3)

            # 토스트 메시지가 있으면 로그인 실패로 간주
            if toast_result["message"]:
                self.login_status.emit(False, f"로그인 실패: {toast_result['message']}")
                return

            # URL 확인 (로그인 성공 시 로그인 페이지가 아닌 다른 페이지로 리다이렉트됨)
            current_url = self.browser.current_url

            # 로그인 페이지에 머물러 있으면 실패로 간주
            if "login" in current_url:
                self.login_status.emit(False, f"로그인 실패: 로그인 페이지에서 벗어나지 못했습니다.")
                return

            # 로그인 후 메뉴 요소 확인 (추가 검증)
            login_success = False

            # 방법 1: 메뉴 요소 확인
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.btn_my_menu, a.btn_my_menu')))
                login_success = True
            except TimeoutException:
                # 메뉴 요소를 찾지 못하면 다른 방법으로 확인
                pass

            # 방법 2: 로그인 링크 부재 확인
            if not login_success:
                try:
                    # 로그인 링크가 없으면 로그인된 상태로 간주
                    login_links = self.browser.find_elements(By.XPATH, "//a[contains(text(), '로그인')]")
                    if len(login_links) == 0:
                        # 마이페이지 링크가 있는지 확인
                        my_page_links = self.browser.find_elements(By.XPATH, "//a[contains(text(), '마이페이지')]")
                        if len(my_page_links) > 0:
                            login_success = True
                except:
                    pass

            # 방법 3: URL 확인 (이미 위에서 확인했지만 추가 검증)
            if not login_success and "login" not in current_url:
                # 로그인 페이지가 아니면 일단 성공으로 간주
                login_success = True

            # 로그인 성공 여부에 따라 시그널 발생
            if login_success:
                # 성공 시그널
                self.login_status.emit(True, f"크림에 {email} 계정으로 로그인되었습니다.")
            else:
                # 실패 시그널
                self.login_status.emit(False, "로그인 실패: 로그인 상태를 확인할 수 없습니다.")

        except TimeoutException:
            # 실패 시그널
            self.login_status.emit(False, "로그인 실패: 이메일 또는 비밀번호를 확인해주세요.")

    def logout(self):
        logout_url = "https://kream.co.kr/logout"
        landing_url = "https://kream.co.kr/"
        try:
            self.browser.get(logout_url)

            wait = WebDriverWait(self.browser, 3)
            wait.until(EC.url_to_be(landing_url))
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        except TimeoutException:
            raise TimeoutException("로그아웃 실패: 로그아웃 페이지에 접속할 수 없습니다.")
        except Exception as e:
            raise Exception(f"로그아웃 실패: {str(e)}")
