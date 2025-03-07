from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyQt6.QtWidgets import QApplication
import time
import sys
from browser_manager import BrowserManager
from search_product import SearchProduct
from ui import UI

class KreamMacro:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.browser = self.browser_manager.driver  # BrowserManager의 WebDriver 재사용
        self.search_product = SearchProduct(self.browser_manager)  # 검색 기능 추가
        self.ui = UI()  # UI 추가
        self.is_logged_in = False
        
        # UI 시그널 연결
        self.ui.search_signal.connect(self.search_product.search)
        self.ui.next_signal.connect(self.search_product.next_result)
        self.ui.prev_signal.connect(self.search_product.prev_result)
        self.search_product.search_result_signal.connect(self.ui.update_product_info)
        self.ui.login_signal.connect(self.login)
        self.ui.macro_signal.connect(self.start_macro)

    def login(self, email, pw):
        self.browser.get('https://kream.co.kr/login')
        try:
            email_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            password_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(pw)

            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
            ).click()

            time.sleep(1)
            toast = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="toast"]'))
            ).text

            if toast == '이메일 또는 비밀번호를 확인해주세요':
                self.ui.update_log(f'로그인 실패: {toast}')
                self.ui.email_input.clear()
                self.ui.pw_input.clear()
            else:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                )
                self.ui.update_log(f'크림에 {email} 계정으로 로그인되었습니다.')
                self.is_logged_in = True
                self.ui.email_input.setEnabled(False)
                self.ui.pw_input.setEnabled(False)
                self.ui.start_macro_button.setEnabled(True)
        except Exception as e:
            self.ui.update_log(f'로그인 오류: {e}')
    
    def login_button_clicked(self):
        email = self.ui.email_input.text()
        pw = self.ui.pw_input.text()
        if self.is_valid_email(email):
            if self.is_valid_password(pw):
                self.login(email, pw)
            else:
                self.ui.update_log("비밀번호 오류: 영문, 숫자, 특수문자를 조합해서 입력해주세요. (8-16자)")
        else:
            self.ui.update_log("이메일 오류: 이메일 주소를 정확히 입력해주세요.")

    def relogin(self, email, pw):
        self.ui.update_log(f'[{time.strftime("%H:%M:%S")}] 로그인 세션이 만료되었습니다. 다시 로그인합니다.')
        self.login(email, pw)
    
    def get_product_details(self, product_id):
        self.browser.get(f'https://kream.co.kr/products/{product_id}')
        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
            details = self.browser.find_elements(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info"]')
            colors = self.browser.find_element(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info color-target"]').text
            return {
                "release_price": details[0].text,
                "model_number": details[1].text,
                "release_date": details[2].text,
                "color": colors
            }
        except Exception as e:
            self.ui.update_log(f'제품 정보 조회 실패: {e}')
        return None
    
    def start_macro(self, email, password, product_id):
        self.ui.update_log(f"매크로 시작: 제품 ID {product_id}")
        details = self.get_product_details(product_id)
        if details:
            self.ui.update_log(f"제품 정보: {details}")
        self.ui.update_log("매크로 종료")

    def close(self):
        self.browser_manager.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UI()
    window.show()
    sys.exit(app.exec())