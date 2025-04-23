import re

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LoginManager:
    """로그인 상태 관리 및 자동 로그인 처리를 위한 클래스"""

    def __init__(self, browser):
        self.browser = browser

    def wait_for_element(self, by, selector, timeout=5):
        """
        요소를 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def wait_for_elements(self, by, selector, timeout=5):
        """
        요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소들의 리스트
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def is_logged_in(self):
        """현재 로그인 상태인지 확인"""
        try:
            # 로그인 시 표시되는 메뉴 아이콘 확인 (여러 선택자 시도)
            try:
                # 기존 선택자 시도
                menu_elements = self.wait_for_elements(By.CSS_SELECTOR, 'button.btn_my_menu, a.btn_my_menu', timeout=2)
                if len(menu_elements) > 0:
                    return True
            except:
                pass

            # 로그인 상태 확인을 위한 추가 선택자 시도
            try:
                # 로그인 링크가 없으면 로그인된 상태로 간주
                login_links = self.browser.find_elements(By.XPATH, "//a[contains(text(), '로그인')]")
                if len(login_links) == 0:
                    # 마이페이지 링크가 있는지 확인
                    my_page_links = self.browser.find_elements(By.XPATH, "//a[contains(text(), '마이페이지')]")
                    if len(my_page_links) > 0:
                        return True
            except:
                pass

            # URL을 통한 확인 (로그인 페이지가 아니면 로그인된 것으로 간주)
            current_url = self.browser.current_url
            if "login" not in current_url and "/my" in current_url:
                return True

            return False
        except:
            # 요소를 찾을 수 없으면 로그아웃 상태로 간주
            return False

    def relogin(self, email, password, switch_to_new_tab=True):
        """로그인 페이지로 이동 후 재로그인"""
        # 이메일 형식 검증
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False

        # 비밀번호 형식 검증 (최소 8자, 문자와 숫자 포함, 특수문자 허용)
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d).{8,}$'
        if not re.match(password_pattern, password):
            return False

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
            email_input = self.wait_for_element(By.CSS_SELECTOR, 'input[type="email"]')
            password_input = self.wait_for_element(By.CSS_SELECTOR, 'input[type="password"]')

            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)

            # 로그인 버튼 클릭
            login_button = self.wait_for_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()

            # 로그인 성공 확인 (로그인 후 페이지 로딩 대기)
            try:
                # 페이지 로딩 대기
                WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )

                # 로그인 상태 확인 (여러 방법 시도)
                login_success = False

                # 방법 1: is_logged_in 메서드 사용
                if self.is_logged_in():
                    login_success = True

                # 방법 2: URL 확인
                if not login_success and "login" not in self.browser.current_url:
                    login_success = True

                # 로그인 실패 시 예외 발생
                if not login_success:
                    raise TimeoutException("로그인 상태를 확인할 수 없습니다.")
            except Exception as e:
                print(f"로그인 확인 중 오류 발생: {str(e)}")
                raise TimeoutException("로그인 확인 실패")

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

    def check_and_relogin_if_needed(self, email, password, max_attempts=2):
        """로그인 상태 확인 후 필요시 재로그인"""
        # 첫 번째 확인
        if self.is_logged_in():
            return True

        print("로그인 상태가 아닙니다. 재로그인을 시도합니다.")

        # 재로그인 시도
        for attempt in range(max_attempts):
            print(f"로그인 시도 {attempt + 1}/{max_attempts}")

            # 재로그인 시도
            login_result = self.relogin(email, password)

            if login_result:
                print("재로그인 성공")
                return True

            # 실패 시 짧은 대기 후 다시 시도
            import time
            time.sleep(1)

        print("모든 로그인 시도 실패")
        return False
