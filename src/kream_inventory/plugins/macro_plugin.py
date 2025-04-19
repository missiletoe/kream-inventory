import random
import threading
import time
import traceback
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.kream_inventory.core.plugin_base import PluginBase
from src.kream_inventory.plugins.error_handler import ErrorHandler
from src.kream_inventory.plugins.login_manager import LoginManager
from src.kream_inventory.plugins.macro_exceptions import MacroExceptions
from src.kream_inventory.plugins.toast_handler import ToastHandler


class MacroPlugin(PluginBase, QObject):
    log_message = pyqtSignal(str)
    macro_status_changed = pyqtSignal(bool)  # True=실행 중, False=중지됨
    
    def __init__(self, browser: WebDriver, config, plugin_manager=None):
        super().__init__(name="macro", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self._running = False
        self._log_history = []  # 로그 히스토리를 저장할 리스트
        self.login_manager = LoginManager(browser)
        self.toast_handler = ToastHandler(browser, self._log)
        self.error_handler = ErrorHandler(browser, self._log)
        self._original_window_handle = None # Store original tab handle
        
    def _log(self, message):
        """로그 메시지를 생성하고 발신"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # 로그 히스토리에 추가하지 않고 바로 발신
        self.log_message.emit(log_message)

    def start(self, product_id, size, quantity, email=None, password=None):
        # 매크로 쓰레드 시작
        if self._running:
            self._log("매크로가 이미 실행 중입니다.")
            return False # Indicate failure to start

        # --- 새 탭 열기 시작 ---
        try:
            # 현재 탭 저장
            original_handles = set(self.browser.window_handles)
            self._original_window_handle = self.browser.current_window_handle
            self._log("새 탭을 열고 매크로를 시작합니다...")
            # 새 탭 열기 (빈 페이지)
            self.browser.execute_script("window.open('', '_blank');")
            # 새로 열린 탭으로 전환 (기존 핸들셋과 비교하여 새 핸들 찾기)
            WebDriverWait(self.browser, 5).until(lambda d: len(d.window_handles) > len(original_handles))
            new_window_handle = list(set(self.browser.window_handles) - original_handles)[0]
            self.browser.switch_to.window(new_window_handle)
            self._log("새 탭으로 전환되었습니다.")
        except Exception as e:
            # Use MacroExceptions handler
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "새 탭 열기")
            # 원래 탭으로 돌아가기 시도
            if self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                try:
                    self.browser.switch_to.window(self._original_window_handle)
                except Exception as switch_back_err:
                    self._log(f"원래 탭으로 복귀 중 오류: {switch_back_err}")
            self._original_window_handle = None # Reset handle
            return False # 새 탭 열기 실패 시 매크로 시작 안함, False 반환
        # --- 새 탭 열기 끝 ---

        self._running = True
        self.macro_status_changed.emit(True)  # 매크로 실행 상태 알림
        min_itv = int(self.config.get('Macro', 'min_interval', fallback='8'))
        max_itv = int(self.config.get('Macro', 'max_interval', fallback='18'))
        
        def run_macro():
            attempt = 0
            inventory_opened = False
            # 즉시 첫 번째 시도 시작
            self._log("매크로가 시작되었습니다. 즉시 첫 번째 시도를 진행합니다...")
            
            # 매크로 시작 시 즉시 올바른 보관판매 페이지로 이동 (새 탭에서)
            if not self._navigate_to_inventory_page(product_id):
                 self._log("초기 보관판매 페이지 로드 실패. 매크로를 종료합니다.")
                 
                 # 스레드 종료 전 상태 업데이트 및 정리
                 self._running = False
                 self.macro_status_changed.emit(False)
                 
                 # 실패 시 새 탭 닫기
                 try: 
                    self.browser.close()
                    self.browser.switch_to.window(self._original_window_handle)
                 except:
                    pass
                 return # Exit thread

            while self._running:
                try:
                    # 0. 로그인 상태 확인 및 재로그인 (매 시도마다)
                    if email and password and (not self.login_manager.is_logged_in() or self.browser.current_url == 'https://kream.co.kr/login'):
                        self._log("로그인 상태가 아니거나 로그인 페이지입니다. 재로그인을 시도합니다.")
                        if not self.login_manager.relogin(email, password, switch_to_new_tab=False):
                            self._log("재로그인 실패. 매크로를 종료합니다.")
                            self._running = False
                            break
                        self._log("재로그인 성공. 보관판매 페이지로 이동합니다.")
                        # 재로그인 후 다시 목표 페이지로 이동
                        if not self._navigate_to_inventory_page(product_id):
                             self._log("보관판매 페이지로 이동 실패 후 재로그인. 매크로 종료.")
                             self._running = False
                             break
                        inventory_opened = False # 페이지 상태 리셋
                        continue # 다음 루프 반복 시작

                    # 1. 현재 페이지 상태 확인 ('신청 내역' 페이지 또는 보관판매 페이지)
                    try:
                        current_url = self.browser.current_url
                        title_elements = WebDriverWait(self.browser, 3).until(
                             EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.title_txt'))
                        )
                        inventory_opened = any("신청 내역" in element.text for element in title_elements)

                        # 신청 내역 페이지가 아니고, 올바른 보관판매 페이지도 아니라면 이동
                        if not inventory_opened and not (current_url.startswith(f'https://kream.co.kr/inventory/{product_id}')):
                            self._log("예상 페이지가 아닙니다. 보관판매 페이지로 이동합니다.")
                            if not self._navigate_to_inventory_page(product_id):
                                self._log("보관판매 페이지 이동 실패. 다음 시도까지 대기.")
                                time.sleep(random.randint(3, 7)) # Wait before next attempt
                                continue # Skip rest of loop, retry navigation
                    except TimeoutException as e:
                        MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "페이지 상태 확인")
                        current_url = self.browser.current_url
                        inventory_opened = False
                        if not current_url.startswith(f'https://kream.co.kr/inventory/{product_id}'):
                             self._log("페이지 확인 타임아웃. 보관판매 페이지로 이동 시도.")
                             if not self._navigate_to_inventory_page(product_id):
                                 self._log("보관판매 페이지 이동 실패. 다음 시도까지 대기.")
                                 time.sleep(random.randint(3, 7))
                                 continue
                    except Exception as e:
                        # Use MacroExceptions handler
                        MacroExceptions.handle_general_exception(self.browser, self._log, e, "페이지 상태 확인")
                        inventory_opened = False
                        # Try to refresh as a recovery attempt
                        try:
                            self.browser.refresh()
                            time.sleep(1)
                        except Exception:
                            self._log("새로고침 실패. 다음 시도까지 대기.")
                        time.sleep(random.randint(3, 7))
                        continue # Skip rest of loop

                    # 2. 매크로 실행 (신청 내역 페이지 vs. 보관 판매 페이지)
                    attempt += 1
                    self._log(f"보관판매 신청 시도 {attempt}회 - 시작")

                    if inventory_opened:
                        # 이미 '신청 내역' 페이지 (결제 페이지)
                        success = self._process_payment_page()
                    else:
                        # 보관 판매 페이지에서 시작
                        success = self._attempt_sale(product_id, size, quantity)
                        # _attempt_sale 내부에서 성공 시 _process_payment_page 호출됨
                        # _attempt_sale의 반환값은 최종 성공 여부

                    # 3. 결과 처리 및 다음 시도 준비
                    if success:
                        self._log(f"보관판매 신청 시도 {attempt}회 - 성공! 매크로를 종료합니다.")
                        self._running = False
                        break
                        # Exit while loop
                    else:
                        self._log(f"보관판매 신청 시도 {attempt}회 - 실패")
                        # 실패 시 페이지 새로고침 (현재 탭에서)
                        try:
                            self._log("페이지를 새로고침합니다.")
                            self.browser.refresh()
                            WebDriverWait(self.browser, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                            )
                            time.sleep(0.5) # 페이지 안정화 대기
                        except Exception as e:
                            MacroExceptions.handle_general_exception(self.browser, self._log, e, "실패 후 새로고침")
                            # Continue to wait for next attempt even if refresh failed

                    # 다음 시도 전 대기 (시도 실패 시)
                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        self._log(f"{wait_sec}초 후 다음 시도를 진행합니다...")
                        # time.sleep 대신 중지 명령을 확인할 수 있도록 루프 사용
                        for _ in range(wait_sec):
                            if not self._running:
                                break
                            time.sleep(1)
                        if not self._running: # Check again after loop
                            break
                            # Exit while loop if stopped during wait

                except Exception as e:
                    # 루프 내에서 발생한 예상치 못한 오류 처리
                    if not MacroExceptions.handle_general_exception(self.browser, self._log, e, "매크로 실행 루프"):
                        # If handler indicates unrecoverable error, try recovery
                        try:
                            self._log("오류 발생. 페이지 새로고침 후 재시도를 시도합니다.")
                            self.browser.refresh()
                            WebDriverWait(self.browser, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                            )
                            time.sleep(1) # 추가 대기
                        except Exception as recovery_err:
                             MacroExceptions.handle_general_exception(self.browser, self._log, recovery_err, "오류 복구(새로고침)")
                             self._log("오류 복구 실패. 매크로를 중지합니다.")
                             self._running = False
                             break # Exit while loop

                    # 다음 시도 전 대기
                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        self._log(f"오류 복구 시도 후 {wait_sec}초 후 재시도합니다...")
                        for _ in range(wait_sec):
                            if not self._running:
                                break
                            time.sleep(1)
                        if not self._running: # Check again after loop
                           break
                           # Exit while loop if stopped during wait

            # --- 매크로 스레드 종료 처리 ---
            final_status_message = "작업이 중단되었습니다." if self._running else "작업이 완료되었습니다." # _running=True면 중단된 것
            self._log(f"매크로 종료 - {final_status_message}")

            self._running = False # 확실하게 상태 업데이트
            self.macro_status_changed.emit(False) # UI에 상태 전파

            # 매크로 종료 후 새 탭 닫고 원래 탭으로 돌아가기
            try:
                if self.browser.current_window_handle != self._original_window_handle:
                     self._log("매크로 탭을 닫습니다.")
                     self.browser.close()
                if self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                     self._log("원래 탭으로 돌아갑니다.")
                     self.browser.switch_to.window(self._original_window_handle)
            except Exception as cleanup_err:
                 self._log(f"탭 정리 중 오류 발생: {cleanup_err}")
            finally:
                 self._original_window_handle = None # 핸들 초기화

        # Python 스레드 시작
        thread = threading.Thread(target=run_macro, daemon=True)
        thread.start()

        return True # 스레드 시작 성공 알림

    def _attempt_sale(self, product_id, size, quantity):
        """보관판매 시도 메인 로직 (시작 페이지 -> 결제 페이지 전까지)"""
        try:
            # 1. 보관 신청 페이지 진입 시도 (현재 페이지가 보관판매 페이지라고 가정)
            if not self._enter_inventory_application_page():
                self._log("보관 신청 페이지 진입 실패 (_attempt_sale)")
                # 현재 페이지가 inventory 페이지가 맞는지 재확인 및 이동 시도
                if f'/inventory/{product_id}' not in self.browser.current_url:
                    self._log("잘못된 페이지 감지. 보관판매 페이지로 재이동 시도.")
                    if not self._navigate_to_inventory_page(product_id):
                         return False # 재이동 실패 시 현재 시도 실패
                return False # 진입 실패 시 현재 시도 실패

            # 2. 사이즈 선택 및 수량 입력
            if not self._select_size_and_quantity(size, quantity):
                self._log("사이즈 선택 및 수량 입력 실패 (_attempt_sale)")
                # 실패 시 페이지 복구 (예: 새로고침)
                try:
                    self.browser.refresh()
                    time.sleep(1)
                except Exception:
                    pass
                return False

            # 3. 계속하기 버튼 클릭 및 모달 처리
            if not self._proceed_with_sale():
                self._log("신청 계속 과정 실패 (_attempt_sale)")
                # 실패 시 페이지 복구 (예: 새로고침)
                try:
                    self.browser.refresh()
                    time.sleep(1)
                except Exception:
                    pass
                return False

            # 4. 토스트 팝업 확인 (진행 버튼 클릭 후)
            toast_result = self.toast_handler.check_toast_popup(3) # Slightly longer wait
            if toast_result["status"] == "block":
                self._log(f"진행 중 블락 팝업 감지. {toast_result['delay']}초 대기 후 재시도 필요.")
                time.sleep(toast_result["delay"])
                return False # Indicate failure for this attempt
            elif toast_result["status"] == "retry":
                self._log("진행 중 재시도 팝업 감지. 재시도 필요.")
                return False # Indicate failure for this attempt
            elif toast_result["status"] == "error":
                self._log("팝업 처리 중 오류 발생. 재시도 필요.")
                return False

            # 5. 신청내역 페이지(결제 페이지)로 이동했는지 확인 및 대기
            self._log("신청내역 페이지(결제 페이지) 이동 대기 중...")
            try:
                 WebDriverWait(self.browser, 15).until( # Increased wait time
                     EC.any_of(
                         EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'title_txt') and contains(text(),'신청 내역')]")),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.payment_inventory')) # Check for payment page elements too
                     )
                 )
                 self._log("신청내역 또는 결제 페이지 진입 확인")
            except TimeoutException as e:
                 # Use MacroExceptions handler
                 MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "신청내역/결제 페이지 이동 확인")
                 self._log(f"현재 URL: {self.browser.current_url}")
                 # 실패 시 복구 시도 (예: 새로고침)
                 try:
                     self.browser.refresh()
                     time.sleep(1)
                 except Exception:
                     pass
                 return False # Indicate failure for this attempt

            # 6. 결제 정보 페이지 처리 호출
            # 이 단계에 도달했다면 결제 페이지로 이동한 것이므로, 결제 로직 호출
            return self._process_payment_page() # 결제 결과(True/False)를 반환

        except Exception as e:
            # Use MacroExceptions handler
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_attempt_sale")
            error_msg = f"보관판매 시도 (_attempt_sale) 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
            self._log(error_msg)
            # 오류 발생 시 복구 시도
            try:
                self.browser.refresh()
                time.sleep(1)
            except Exception as refresh_err:
                MacroExceptions.handle_general_exception(self.browser, self._log, refresh_err, "_attempt_sale 오류 후 새로고침")
            return False # Indicate failure

    def _navigate_to_inventory_page(self, product_id):
        """지정한 상품의 보관판매 페이지로 이동"""
        target_url = f'https://kream.co.kr/inventory/{product_id}'
        try:
            current_url = self.browser.current_url
            # 이미 해당 상품의 보관판매 페이지거나 관련 페이지에 있는지 확인
            if current_url.startswith(target_url):
                 # 페이지 요소가 로드되었는지 확인하여 페이지 상태 검증
                 try:
                    WebDriverWait(self.browser, 5).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list')) # 사이즈 목록
                        )
                    )
                    self._log("이미 보관판매 관련 페이지에 있습니다.")
                    return True
                 except TimeoutException as e:
                     # Use MacroExceptions handler
                     MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관판매 페이지 요소 로딩 확인 (이미 해당 페이지)")
                     self._log("현재 페이지 URL은 맞지만, 요소 로딩 실패. 새로고침 시도.")
                     self.browser.refresh()
                     # 새로고침 후 다시 요소 로딩 확인 (여기서 Timeout 발생 시 아래 except Exception에서 처리)
                     WebDriverWait(self.browser, 10).until(
                         EC.any_of(
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                         )
                     )
                     self._log("새로고침 후 페이지 로드 확인.")
                     return True

            # 다른 페이지에 있다면 직접 보관판매 페이지로 이동
            self._log(f"보관판매 페이지로 이동합니다: {target_url}")
            self.browser.get(target_url)

            # 페이지 로드 확인 (더 많은 요소와 긴 대기 시간)
            try:
                WebDriverWait(self.browser, 15).until(
                     EC.any_of(
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                     )
                )
                self._log("보관판매 페이지 로드 완료")
                time.sleep(0.5) # 안정화 대기
                return True
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관판매 페이지 로드")
                try: self._log(f"현재 URL: {self.browser.current_url}")
                except Exception: pass
                return False

        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_navigate_to_inventory_page")
            return False

    def _enter_inventory_application_page(self):
        """보관신청 버튼 클릭 -> 사이즈/수량 선택 페이지 진입"""
        try:
            # 현재 페이지가 이미 수량 선택 페이지인지 확인 (더 확실한 선택자 사용)
            if WebDriverWait(self.browser, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))):
                self._log("이미 사이즈/수량 선택 페이지입니다.")
                return True
        except TimeoutException:
            # 사이즈 목록이 없으면 버튼 클릭 시도
            try:
                # 보관 신청 버튼 찾기 (여러 선택자 가능성 고려)
                inventory_button_xpath = "//a[contains(@class, 'inventory_btn')] | //button[contains(@class, 'inventory_btn')] | //a[contains(@class, 'btn_action') and contains(@href, 'inventory')]"
                inventory_button = WebDriverWait(self.browser, 5).until(
                    EC.element_to_be_clickable((By.XPATH, inventory_button_xpath))
                )
                self._log("보관 신청 버튼 클릭 시도.")
                self.browser.execute_script("arguments[0].click();", inventory_button)
                time.sleep(2) # 페이지 전환 대기

                # 클릭 후 사이즈 목록이 나타나는지 확인
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                )
                self._log("사이즈/수량 선택 페이지 진입 확인.")
                return True
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관 신청 버튼 클릭 후 사이즈 목록 로딩")
                try: self._log(f"현재 URL: {self.browser.current_url}")
                except Exception: pass
                return False
            except Exception as e:
                MacroExceptions.handle_general_exception(self.browser, self._log, e, "보관 신청 버튼 클릭")
                return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_enter_inventory_application_page (외부)")
            return False

    def _select_size_and_quantity(self, size, quantity):
        """사이즈 선택 및 수량 입력"""
        try:
            # 사이즈 목록 컨테이너 대기
            size_list_container = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
            )
            # 사이즈 아이템 목록 찾기
            size_elements = size_list_container.find_elements(By.CSS_SELECTOR, 'div.inventory_size_item')

            if not size_elements:
                self._log("사이즈 목록 요소를 찾을 수 없습니다.")
                return False

            size_found = False
            for element in size_elements:
                try:
                    # 사이즈 텍스트 추출 및 비교 (공백 제거)
                    size_text_element = element.find_element(By.CSS_SELECTOR, 'div.size')
                    size_text = size_text_element.text.strip()

                    if size_text == size:
                        self._log(f"사이즈 '{size}' 찾음. 수량 입력 시도...")
                        # 수량 입력 필드 찾기
                        quantity_input = element.find_element(By.CSS_SELECTOR, 'input.counter_quantity_input')

                        # 입력 필드와 상호작용 전 스크롤 (필요 시)
                        self.browser.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", quantity_input)
                        time.sleep(0.2)

                        # 수량 입력 (기존 값 지우고 입력)
                        # quantity_input.clear() # clear()가 불안정할 수 있음
                        self.browser.execute_script("arguments[0].value = '';", quantity_input) # JS로 초기화
                        quantity_input.send_keys(str(quantity)) # 숫자를 문자열로 변환하여 입력
                        self._log(f"수량 '{quantity}' 입력 완료.")
                        size_found = True

                        # 입력값 확인 (JS 사용)
                        time.sleep(0.5) # 입력 반영 대기
                        actual_value = self.browser.execute_script("return arguments[0].value;", quantity_input)
                        if str(actual_value) != str(quantity):
                            self._log(f"수량 입력 확인 실패. 입력된 값: '{actual_value}', 요청 값: '{quantity}'. 재시도 필요.")
                            return False # 입력 실패 시 False 반환
                        break # 맞는 사이즈 찾았으면 루프 종료
                except (NoSuchElementException, StaleElementReferenceException) as e:
                    if isinstance(e, NoSuchElementException):
                         MacroExceptions.handle_no_such_element_exception(self.browser, self._log, e, "사이즈/수량 요소 찾기 (루프 내)")
                    elif isinstance(e, StaleElementReferenceException):
                         MacroExceptions.handle_stale_element_exception(self.browser, self._log, e, "사이즈/수량 요소 찾기 (루프 내)")
                    continue # Continue to next element
                except Exception as e:
                     MacroExceptions.handle_general_exception(self.browser, self._log, e, f"특정 사이즈({size_text}) 처리")
                     continue # Continue to next element

            if not size_found:
                self._log(f"요청한 사이즈 '{size}'를 목록에서 찾을 수 없습니다.")
                return False

            return True # 모든 과정 성공 시 True 반환
        except TimeoutException as e:
             MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "사이즈 목록 컨테이너 로딩")
             return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_select_size_and_quantity")
            return False

    def _proceed_with_sale(self):
        """계속하기 버튼 클릭 및 관련 모달 처리"""
        try:
            # '계속하기' 또는 유사한 의미의 활성화된 버튼 찾기
            # 버튼은 a 태그 또는 button 태그일 수 있음, 비활성화 상태(.disabled) 제외
            proceed_button_xpath = "//a[contains(@class, 'btn') and contains(@class, 'solid') and not(contains(@class, 'disabled'))] | //button[contains(@class, 'btn') and contains(@class, 'solid') and not(contains(@class, 'disabled'))] | //div[contains(@class,'complete_btn_box')]//button[not(@disabled)]"
            continue_button = WebDriverWait(self.browser, 7).until(
                EC.element_to_be_clickable((By.XPATH, proceed_button_xpath))
            )
            self._log("계속하기 버튼 클릭 시도.")
            self.browser.execute_script("arguments[0].scrollIntoView(true);", continue_button)
            time.sleep(0.3)
            self.browser.execute_script("arguments[0].click();", continue_button)
            self._log("계속하기 버튼 클릭 완료.")

            # 모달 처리 (필요한 모달만 순서대로 호출)
            # 예: 모델 번호 확인 모달
            if not MacroExceptions.handle_model_number_modal(self.browser, self._log):
                self._log("모델 번호 모달 처리 실패.")
                return False # 모달 처리 실패 시 False 반환

            # 예: 라벨 사이즈 확인 모달
            if not MacroExceptions.handle_label_size_modal(self.browser, self._log):
                 self._log("라벨 사이즈 모달 처리 실패.")
                 return False # 모달 처리 실패 시 False 반환

            # 모든 모달 처리 성공 시 True 반환
            return True
        except TimeoutException as e:
            MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "계속하기 버튼 찾기/클릭")
            # 현재 버튼 상태 로깅 시도
            try:
                all_buttons = self.browser.find_elements(By.XPATH, "//a[contains(@class, 'btn')] | //button[contains(@class, 'btn')]")
                button_states = [(b.text, b.is_enabled()) for b in all_buttons if 'btn' in b.get_attribute('class')]
                self._log(f"현재 페이지 버튼 상태: {button_states}")
            except Exception as log_err:
                 self._log(f"버튼 상태 로깅 중 오류: {log_err}")
            return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_proceed_with_sale")
            return False

    def _process_payment_page(self):
        """결제 정보 페이지 처리 로직 (체크박스, 최종 결제 버튼)"""
        try:
            self._log("결제 정보 페이지 처리 시작...")
            # 1. 필수 요소 로딩 확인 (결제 정보 영역)
            try:
                 WebDriverWait(self.browser, 10).until(
                     EC.presence_of_element_located((By.CSS_SELECTOR, 'div.payment_inventory'))
                 )
                 self._log("결제 정보 영역 로드 확인.")
            except TimeoutException as e:
                 if not MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "결제 정보 영역 로딩"):
                      # 추가 확인 로직 (이미 완료 or 서비스 오류)
                      if "보관 신청이 완료되었습니다" in self.browser.page_source:
                           self._log("이미 완료된 페이지로 보입니다. 성공 처리.")
                           return True
                      if self.toast_handler.check_service_error(log_errors=False):
                           self._log("서비스 오류 토스트 감지됨.")
                           return False
                      return False # 로딩 실패

            # 2. 서비스 오류 토스트 확인
            if self.toast_handler.check_service_error():
                 return False # 오류 감지 시 실패

            # 3. '보증금 결제하기' 버튼 클릭 (필요 시)
            # 이 로직은 handle_payment_modal 전에 필요한 경우에만 수행되어야 함.
            # 일반적으로는 이전 단계(_proceed_with_sale)에서 이미 결제 모달이 뜬 상태일 수 있음.
            # 만약 별도의 '보증금 결제하기' 버튼이 있다면 여기서 클릭.
            try:
                 # 이 버튼이 항상 존재하지 않을 수 있으므로, TimeoutException을 정상 처리
                 deposit_button_xpath = "//button[contains(@class, 'display_button') and contains(., '보증금 결제하기')]"
                 deposit_button = WebDriverWait(self.browser, 3).until(
                     EC.element_to_be_clickable((By.XPATH, deposit_button_xpath))
                 )
                 self._log("보증금 결제하기 버튼 발견 및 클릭 시도.")
                 self.browser.execute_script("arguments[0].scrollIntoView(true);", deposit_button)
                 time.sleep(0.3)
                 self.browser.execute_script("arguments[0].click();", deposit_button)
                 self._log("보증금 결제하기 버튼 클릭 완료.")
            except TimeoutException:
                 self._log("보증금 결제하기 버튼 없음. 결제 모달 직접 처리 진행.")
            except Exception as click_err:
                 self._log(f"보증금 결제 버튼 클릭 중 오류: {click_err}")
                 return False

            # 4. 결제 모달 처리 (체크박스 등)
            if not MacroExceptions.handle_payment_modal(self.browser, self._log):
                self._log("결제 모달 처리(체크박스 등) 실패.")
                return False

            # 5. 최종 결제 버튼 클릭
            try:
                # 최종 결제 버튼 선택자 (더 구체적일 수 있음)
                final_payment_button_xpath = "//div[contains(@class, 'layer_bottom')]//button[contains(@class, 'display_button') and not(@disabled)]"
                final_payment_button = WebDriverWait(self.browser, 7).until(
                    EC.element_to_be_clickable((By.XPATH, final_payment_button_xpath))
                )
                self._log("최종 결제 버튼 클릭 시도.")
                self.browser.execute_script("arguments[0].scrollIntoView(true);", final_payment_button)
                time.sleep(0.3)
                self.browser.execute_script("arguments[0].click();", final_payment_button)
                self._log("최종 결제 버튼 클릭 완료.")
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "최종 결제 버튼 찾기/클릭")
                return False
            except Exception as e:
                 MacroExceptions.handle_general_exception(self.browser, self._log, e, "최종 결제 버튼 클릭")
                 return False

            # 6. 결제 후 토스트 팝업 확인
            toast_result = self.toast_handler.check_toast_popup(7) # 결제 후 결과 대기 시간 증가
            if toast_result["status"] == "success":
                 self._log("결제 성공 토스트 확인됨.")
                 # 성공 토스트 후 실제 완료 페이지 로드를 기다리는 것이 좋음
                 time.sleep(1) # 잠시 대기
            elif toast_result["status"] == "error":
                 self._log("결제 과정 중 오류 토스트 발생.")
                 return False # 오류 토스트 시 실패
            elif toast_result["status"] == "block":
                 self._log(f"결제 후 블락 팝업 감지. {toast_result['delay']}초 대기 후 재시도 필요.")
                 time.sleep(toast_result['delay'])
                 return False # 블락 시 실패 (현재 시도 기준)
            # 'retry' 상태 처리 추가 가능

            # 7. 최종 완료 상태 확인 (완료 페이지 로딩)
            try:
                 # 완료 페이지의 특정 요소나 텍스트로 성공 여부 판단
                 WebDriverWait(self.browser, 10).until(
                     EC.presence_of_element_located((By.XPATH, "//p[contains(text(), '보관 신청이 완료되었습니다.')] | //div[contains(@class,'complete_title')]"))
                 )
                 self._log("보관 신청 완료 확인됨. 매크로 최종 성공!")
                 return True # 최종 성공
            except TimeoutException as e:
                 MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "완료 메시지/페이지 로딩")
                 self._log(f"현재 URL: {self.browser.current_url}")
                 # 여기서 URL 기반으로 성공 여부 판단 시도 가능
                 # if "complete" in self.browser.current_url: return True
                 self._log("완료 상태 불확실. 잠재적 오류 가능성으로 실패 처리.")
                 return False # 완료 확인 불가 시 실패 처리

        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_process_payment_page")
            error_msg = f"결제 정보 페이지 처리 중 예상치 못한 오류 발생: {str(e)}\n{traceback.format_exc()}"
            self._log(error_msg)
            return False # 예외 발생 시 실패

    def _check_payment_info_page(self):
        """(사용되지 않는 것으로 보임) 결제 정보 페이지 진입 확인 및 처리"""
        # 이 함수는 현재 호출되지 않는 것 같습니다. _attempt_sale -> _process_payment_page 흐름으로 통합됨.
        self._log("결제 정보 페이지로 진행되었습니다. (_check_payment_info_page 호출됨 - 비정상)")
        # return self._process_payment_page()
        return False # 안전하게 False 반환

    def stop(self):
        """매크로 실행 중지 요청"""
        if self._running:
            self._running = False
            self._log("매크로 중지 명령 수신. 현재 진행 중인 작업 완료 또는 대기 후 스레드가 종료됩니다.")
            # 상태 변경 시그널은 스레드가 실제로 종료될 때 run_macro 내부에서 emit됨
        else:
            self._log("매크로가 실행 중이지 않아 중지할 수 없습니다.")

    # 컨트롤러에서 호출되는 진입점 메소드
    def start_macro(self, product_id: str, size: str, quantity: str, email: str = None, password: str = None):
        """매크로 시작을 요청하고 스레드를 생성하여 start 메소드를 호출"""
        try:
            self._log(f"매크로 시작 요청: Product ID={product_id}, Size={size}, Quantity={quantity}")
            # self.start 메소드를 호출하여 새 탭 열기 및 스레드 시작 시도
            # self.start는 스레드 시작 요청 성공 시 True, 실패(예: 탭 열기 실패) 시 False 반환
            started_successfully = self.start(product_id, size, quantity, email, password)

            if started_successfully:
                 self._log(f"매크로 시작 스레드가 성공적으로 요청되었습니다. 새 탭에서 실행됩니다.")
                 return True
            else:
                 # self.start 내부에서 이미 실패 로그 기록됨
                 self._log(f"매크로 시작 요청 실패.")
                 # 실패 시 상태 확실히 업데이트
                 self._running = False
                 self.macro_status_changed.emit(False)
                 return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "start_macro 초기화")
            self._running = False
            self.macro_status_changed.emit(False)
            return False
