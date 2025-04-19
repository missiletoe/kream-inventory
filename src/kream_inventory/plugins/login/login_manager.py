import time

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LoginManager:
    """로그인 상태 관리 및 자동 로그인 처리를 위한 클래스"""
    
    def __init__(self, browser):
        self.browser = browser
        
    def is_logged_in(self):
        """현재 로그인 상태인지 확인"""
        try:
            # 로그인 시 표시되는 메뉴 아이콘 확인
            menu_elements = self.browser.find_elements(By.CSS_SELECTOR, 'button.btn_my_menu, a.btn_my_menu')
            return len(menu_elements) > 0
        except:
            # 요소를 찾을 수 없으면 로그아웃 상태로 간주
            return False
            
    def relogin(self, email, password, switch_to_new_tab=True):
        """로그인 페이지로 이동 후 재로그인"""
        current_url = self.browser.current_url
        original_handle = self.browser.current_window_handle
        target_handle = original_handle
        
        if switch_to_new_tab:
            # 새 탭에서 로그인 (기존 탭 보존)
            try:
                self.browser.execute_script("window.open('');")
                new_handle = [handle for handle in self.browser.window_handles if handle != original_handle][0]
                self.browser.switch_to.window(new_handle)
                target_handle = new_handle
            except Exception as e:
                # 새 탭 열기 실패 시 현재 탭에서 계속
                pass
        
        try:
            self.browser.get("https://kream.co.kr/login")
            
            # 로그인 페이지 로딩 대기
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            
            # 이메일, 비밀번호 입력
            email_input = self.browser.find_element(By.CSS_SELECTOR, 'input[type="email"]')
            password_input = self.browser.find_element(By.CSS_SELECTOR, 'input[type="password"]')
            
            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)
            
            # 로그인 버튼 클릭
            login_button = self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
            
            # 로그인 성공 확인 (로그인 후 페이지 로딩 대기)
            WebDriverWait(self.browser, 10).until(
                lambda driver: self.is_logged_in() or "login" not in driver.current_url
            )
            
            if not switch_to_new_tab:
                # 원래 페이지로 돌아가기 (필요시)
                if current_url and current_url != self.browser.current_url and "login" not in current_url:
                    self.browser.get(current_url)
                    
                    # 페이지 로딩 대기 (최소한의 로딩 확인)
                    WebDriverWait(self.browser, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                    )
            
            return True
            
        except TimeoutException:
            if switch_to_new_tab and target_handle != original_handle:
                # 로그인 실패 시 원래 탭으로 돌아가기
                self.browser.close()
                self.browser.switch_to.window(original_handle)
            return False
            
        except Exception as e:
            if switch_to_new_tab and target_handle != original_handle:
                # 오류 발생 시 원래 탭으로 돌아가기
                try:
                    self.browser.close()
                    self.browser.switch_to.window(original_handle)
                except:
                    # 탭 닫기/전환 중 오류 무시
                    pass
            return False
            
    def check_and_relogin_if_needed(self, email, password):
        """로그인 상태 확인 후 필요시 재로그인"""
        if not self.is_logged_in():
            return self.relogin(email, password)
        return True 