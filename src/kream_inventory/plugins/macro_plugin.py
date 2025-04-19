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

# Constants for return values from attempt functions
PAYMENT_FAILURE = "PAYMENT_FAILURE"
PRE_PAYMENT_FAILURE = False
SUCCESS = True


class MacroPlugin(PluginBase, QObject):
    log_message = pyqtSignal(str)
    macro_status_changed = pyqtSignal(bool)  # True=실행 중, False=중지됨
    
    def __init__(self, browser: WebDriver, config, plugin_manager=None):
        super().__init__(name="macro", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self._running = False
        self.login_manager = LoginManager(browser)
        self.toast_handler = ToastHandler(browser, self._direct_log)
        self.error_handler = ErrorHandler(browser, self._log)
        self._original_window_handle = None # Store original tab handle
        
    def _direct_log(self, message):
        """Logs a message directly without filtering, intended for critical messages like toasts."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_message.emit(log_message)

    def _log(self, message, allowed_key=None):
        """로그 메시지를 생성하고 필터링하여 발신"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # Define allowed log messages/patterns (keys can be used for easier identification)
        allowed_logs = {
            "START": "매크로 구동 시작",
            "STOP": "매크로 구동 정지",
            "ATTEMPT_FAIL": "보관판매 신청 시도 {attempt}회 — 실패", # Placeholder for attempt number
            "RELOGIN_SUCCESS": "재로그인 성공",
            "PAGE_ENTRY_SUCCESS": "{page_name} 페이지 진입 성공", # Placeholder for page name
            "FINAL_SUCCESS": "보관판매 신청 완료. 매크로 정지"
            # Toast messages are handled by _direct_log via ToastHandler
        }

        # Check if the message matches an allowed pattern or if an allowed_key is provided
        should_log = False
        if allowed_key and allowed_key in allowed_logs:
             # Format message if necessary (e.g., for attempt number, page name)
             # This part needs refinement based on how parameters are passed
             formatted_message_template = allowed_logs[allowed_key]
             # Simple placeholder replacement for now
             if "{attempt}" in formatted_message_template:
                 # Requires attempt number passed somehow, maybe as part of the message string itself initially?
                 # Example: self._log(f"ATTEMPT_FAIL:{attempt}", allowed_key="ATTEMPT_FAIL")
                 # Or pass parameters: self._log("some internal detail", allowed_key="ATTEMPT_FAIL", attempt=attempt)
                 # Let's assume the message itself contains the final string for now
                 log_message = f"[{timestamp}] {message}" # Use the pre-formatted message
                 should_log = True
             elif "{page_name}" in formatted_message_template:
                 log_message = f"[{timestamp}] {message}" # Use the pre-formatted message
                 should_log = True
             else:
                 # For exact matches like START, STOP, RELOGIN_SUCCESS, FINAL_SUCCESS
                 if message == formatted_message_template:
                      should_log = True

        # Fallback: Check if the raw message matches any allowed message (useful if allowed_key isn't used)
        if not should_log:
            for key, allowed_msg_template in allowed_logs.items():
                # Handle templates vs exact matches
                if "{attempt}" in allowed_msg_template or "{page_name}" in allowed_msg_template:
                     # Check if the message starts with the non-placeholder part
                     base_msg = allowed_msg_template.split("{")[0]
                     if message.startswith(base_msg):
                          log_message = f"[{timestamp}] {message}" # Log the full message passed in
                          should_log = True
                          break
                elif message == allowed_msg_template:
                     should_log = True
                     break


        if should_log:
            self.log_message.emit(log_message)
        # Else: Do nothing, filter out the log

    def start(self, product_id, size, quantity, email=None, password=None):
        if self._running:
            return False

        try:
            original_handles = set(self.browser.window_handles)
            self._original_window_handle = self.browser.current_window_handle
            self.browser.execute_script("window.open('', '_blank');")
            WebDriverWait(self.browser, 5).until(lambda d: len(d.window_handles) > len(original_handles))
            new_window_handle = list(set(self.browser.window_handles) - original_handles)[0]
            self.browser.switch_to.window(new_window_handle)
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "새 탭 열기")
            if self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                try:
                    self.browser.switch_to.window(self._original_window_handle)
                except Exception as switch_back_err:
                    pass
            self._original_window_handle = None
            return False

        self._running = True
        self.macro_status_changed.emit(True)
        min_itv = int(self.config.get('Macro', 'min_interval', fallback='8'))
        max_itv = int(self.config.get('Macro', 'max_interval', fallback='18'))
        
        def run_macro():
            attempt = 0
            inventory_opened = False
            total_wait_time = 0 # Initialize total wait time

            self._log("매크로 구동 시작", allowed_key="START")

            if not self._navigate_to_inventory_page(product_id):
                 self._running = False
                 self.macro_status_changed.emit(False)
                 try:
                    self.browser.close()
                    self.browser.switch_to.window(self._original_window_handle)
                 except: pass
                 self._log("매크로 구동 정지", allowed_key="STOP")
                 return

            while self._running:
                try:
                    if email and password and (not self.login_manager.is_logged_in() or self.browser.current_url == 'https://kream.co.kr/login'):
                        if not self.login_manager.relogin(email, password, switch_to_new_tab=False):
                            self._running = False
                            break
                        self._log("재로그인 성공", allowed_key="RELOGIN_SUCCESS")
                        total_wait_time = 0 # Reset wait time after relogin
                        if not self._navigate_to_inventory_page(product_id):
                             self._running = False
                             break
                        inventory_opened = False
                        continue

                    try:
                        current_url = self.browser.current_url
                        inventory_opened = "신청 내역" in WebDriverWait(self.browser, 1).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'title_txt')]"))
                        ).text

                        if not inventory_opened and not (current_url.startswith(f'https://kream.co.kr/inventory/{product_id}')):
                            if not self._navigate_to_inventory_page(product_id):
                                time.sleep(random.randint(3, 7))
                                continue
                    except TimeoutException:
                        inventory_opened = False
                        current_url = self.browser.current_url
                        if not current_url.startswith(f'https://kream.co.kr/inventory/{product_id}'):
                             if not self._navigate_to_inventory_page(product_id):
                                 time.sleep(random.randint(3, 7))
                                 continue
                    except Exception as e:
                        MacroExceptions.handle_general_exception(self.browser, self._log, e, "페이지 상태 확인")
                        inventory_opened = False
                        time.sleep(random.randint(3, 7))
                        continue

                    attempt += 1

                    if inventory_opened:
                        result = self._process_payment_page(total_wait_time)
                    else:
                        result = self._attempt_sale(product_id, size, quantity, total_wait_time)

                    if result == SUCCESS:
                        self._log("보관판매 신청 완료. 매크로 정지", allowed_key="FINAL_SUCCESS")
                        self._running = False
                        break

                    else:
                        self._log(f"보관판매 신청 시도 {attempt}회 — 실패", allowed_key="ATTEMPT_FAIL")

                        if result == PAYMENT_FAILURE:
                            try:
                                self.browser.refresh()
                                WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                                time.sleep(0.5)
                                if not self._navigate_to_inventory_page(product_id):
                                     self._running = False
                                     break
                                inventory_opened = False
                            except Exception as e:
                                MacroExceptions.handle_general_exception(self.browser, self._log, e, "결제 실패 후 새로고침/재이동")
                                self._running = False
                                break

                        if self._running:
                            wait_sec = random.randint(min_itv, max_itv)
                            self._log(f"{wait_sec}초 대기 시작 (누적: {total_wait_time + wait_sec}초)")
                            for i in range(wait_sec):
                                if not self._running: break
                                time.sleep(1)
                            if self._running:
                                total_wait_time += wait_sec
                            if not self._running: break

                except Exception as e:
                    if not MacroExceptions.handle_general_exception(self.browser, self._log, e, "매크로 실행 루프"):
                        try:
                            self.browser.refresh()
                            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                            time.sleep(1)
                        except Exception as recovery_err:
                             MacroExceptions.handle_general_exception(self.browser, self._log, recovery_err, "오류 복구(새로고침)")
                             self._running = False
                             break

                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        for _ in range(wait_sec):
                            if not self._running: break
                            time.sleep(1)
                        if not self._running: break

            self._log("매크로 구동 정지", allowed_key="STOP")

            self._running = False
            self.macro_status_changed.emit(False)

            try:
                if self.browser.current_window_handle != self._original_window_handle:
                     self.browser.close()
                if self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                     self.browser.switch_to.window(self._original_window_handle)
            except Exception as cleanup_err:
                 pass
            finally:
                 self._original_window_handle = None

        thread = threading.Thread(target=run_macro, daemon=True)
        thread.start()

        return True

    def _attempt_sale(self, product_id, size, quantity, total_wait_time):
        """보관판매 시도 (시작 페이지 -> 결제 페이지 전까지).
        Returns: SUCCESS(True), PRE_PAYMENT_FAILURE(False), or PAYMENT_FAILURE.
        """
        try:
            if not self._enter_inventory_application_page():
                if f'/inventory/{product_id}' not in self.browser.current_url:
                    if not self._navigate_to_inventory_page(product_id):
                         return PRE_PAYMENT_FAILURE
                return PRE_PAYMENT_FAILURE

            if not self._select_size_and_quantity(size, quantity):
                return PRE_PAYMENT_FAILURE

            if not self._proceed_with_sale():
                return PRE_PAYMENT_FAILURE

            toast_result = self.toast_handler.check_toast_popup(3, total_wait_time)
            if toast_result["status"] == "block":
                 return PRE_PAYMENT_FAILURE
            elif toast_result["status"] == "retry":
                 return PRE_PAYMENT_FAILURE
            elif toast_result["status"] == "error":
                 return PRE_PAYMENT_FAILURE

            try:
                 WebDriverWait(self.browser, 15).until(
                     EC.any_of(
                         EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'title_txt') and contains(text(),'신청 내역')]")),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.payment_inventory'))
                     )
                 )
                 self._log("신청 내역 페이지 진입 성공", allowed_key="PAGE_ENTRY_SUCCESS")
            except TimeoutException as e:
                 MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "신청내역/결제 페이지 이동 확인")
                 return PRE_PAYMENT_FAILURE

            payment_result = self._process_payment_page(total_wait_time)

            return payment_result

        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_attempt_sale")
            return PRE_PAYMENT_FAILURE

    def _navigate_to_inventory_page(self, product_id):
        """지정한 상품의 보관판매 페이지로 이동"""
        target_url = f'https://kream.co.kr/inventory/{product_id}'
        try:
            current_url = self.browser.current_url
            if current_url.startswith(target_url):
                 try:
                    WebDriverWait(self.browser, 5).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                        )
                    )
                    return True
                 except TimeoutException as e:
                     MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관판매 페이지 요소 로딩 확인 (이미 해당 페이지)")
                     self.browser.refresh()
                     WebDriverWait(self.browser, 10).until(
                         EC.any_of(
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                             EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                         )
                     )
                     return True

            self.browser.get(target_url)

            try:
                WebDriverWait(self.browser, 15).until(
                     EC.any_of(
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product')),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-product-container')),
                         EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                     )
                )
                self._log("보관판매 페이지 진입 성공", allowed_key="PAGE_ENTRY_SUCCESS")
                time.sleep(0.5)
                return True
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관판매 페이지 로드")
                return False

        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_navigate_to_inventory_page")
            return False

    def _enter_inventory_application_page(self):
        """보관신청 버튼 클릭 -> 사이즈/수량 선택 페이지 진입"""
        try:
            if WebDriverWait(self.browser, 1).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))):
                 return True
        except TimeoutException:
            try:
                inventory_button_xpath = "//a[contains(@class, 'inventory_btn')] | //button[contains(@class, 'inventory_btn')] | //a[contains(@class, 'btn_action') and contains(@href, 'inventory')]"
                inventory_button = WebDriverWait(self.browser, 5).until(
                    EC.element_to_be_clickable((By.XPATH, inventory_button_xpath))
                )
                self.browser.execute_script("arguments[0].click();", inventory_button)
                time.sleep(1)

                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                )
                self._log("사이즈/수량 선택 페이지 진입 성공", allowed_key="PAGE_ENTRY_SUCCESS")
                return True
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "보관 신청 버튼 클릭 후 사이즈 목록 로딩")
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
            size_list_container = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
            )
            size_elements = size_list_container.find_elements(By.CSS_SELECTOR, 'div.inventory_size_item')

            if not size_elements:
                return False

            size_found = False
            for element in size_elements:
                try:
                    size_text_element = element.find_element(By.CSS_SELECTOR, 'div.size')
                    size_text = size_text_element.text.strip()

                    if size_text == size:
                        quantity_input = element.find_element(By.CSS_SELECTOR, 'input.counter_quantity_input')
                        self.browser.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", quantity_input)
                        time.sleep(0.2)
                        self.browser.execute_script("arguments[0].value = '';", quantity_input)
                        quantity_input.send_keys(str(quantity))
                        size_found = True

                        time.sleep(0.3)
                        actual_value = self.browser.execute_script("return arguments[0].value;", quantity_input)
                        if str(actual_value) != str(quantity):
                            return False
                        break
                except (NoSuchElementException, StaleElementReferenceException) as e:
                    continue
                except Exception as e:
                     MacroExceptions.handle_general_exception(self.browser, self._log, e, f"특정 사이즈({size_text}) 처리")
                     continue

            if not size_found:
                return False

            return True
        except TimeoutException as e:
             MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "사이즈 목록 컨테이너 로딩")
             return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_select_size_and_quantity")
            return False

    def _proceed_with_sale(self):
        """계속하기 버튼 클릭 및 관련 모달 처리"""
        try:
            proceed_button_xpath = "//a[contains(@class, 'btn') and contains(@class, 'solid') and not(contains(@class, 'disabled'))] | //button[contains(@class, 'btn') and contains(@class, 'solid') and not(contains(@class, 'disabled'))] | //div[contains(@class,'complete_btn_box')]//button[not(@disabled)]"
            continue_button = WebDriverWait(self.browser, 7).until(
                EC.element_to_be_clickable((By.XPATH, proceed_button_xpath))
            )
            self.browser.execute_script("arguments[0].scrollIntoView(true);", continue_button)
            time.sleep(0.3)
            self.browser.execute_script("arguments[0].click();", continue_button)

            if not MacroExceptions.handle_model_number_modal(self.browser, self._log):
                return False
            if not MacroExceptions.handle_label_size_modal(self.browser, self._log):
                 return False

            return True
        except TimeoutException as e:
            MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "계속하기 버튼 찾기/클릭")
            return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_proceed_with_sale")
            return False

    def _process_payment_page(self, total_wait_time):
        """결제 정보 페이지 처리 로직. Returns SUCCESS(True) or PAYMENT_FAILURE."""
        try:
            try:
                 WebDriverWait(self.browser, 10).until(
                     EC.presence_of_element_located((By.CSS_SELECTOR, 'div.payment_inventory'))
                 )
            except TimeoutException as e:
                 if not MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "결제 정보 영역 로딩"):
                      if "보관 신청이 완료되었습니다" in self.browser.page_source:
                           return SUCCESS
                      if self.toast_handler.check_service_error(log_errors=False):
                           return PAYMENT_FAILURE
                      return PAYMENT_FAILURE

            if self.toast_handler.check_service_error():
                 return PAYMENT_FAILURE

            # Check service error toast before proceeding
            service_error_toast_result = self.toast_handler.check_toast_popup(1, total_wait_time, check_only_service_error=True)
            if service_error_toast_result["status"] == "error":
                 return PAYMENT_FAILURE
            elif service_error_toast_result["status"] == "block":
                 time.sleep(service_error_toast_result['delay'])
                 return PAYMENT_FAILURE

            try:
                 deposit_button_xpath = "//button[contains(@class, 'display_button') and contains(., '보증금 결제하기')]"
                 deposit_button = WebDriverWait(self.browser, 2).until(
                     EC.element_to_be_clickable((By.XPATH, deposit_button_xpath))
                 )
                 self.browser.execute_script("arguments[0].scrollIntoView(true);", deposit_button)
                 time.sleep(0.3)
                 self.browser.execute_script("arguments[0].click();", deposit_button)
            except TimeoutException:
                 pass
            except Exception as click_err:
                 return PAYMENT_FAILURE

            if not MacroExceptions.handle_payment_modal(self.browser, self._log):
                return PAYMENT_FAILURE

            try:
                final_payment_button_xpath = "//div[contains(@class, 'layer_bottom')]//button[contains(@class, 'display_button') and not(@disabled)]"
                final_payment_button = WebDriverWait(self.browser, 7).until(
                    EC.element_to_be_clickable((By.XPATH, final_payment_button_xpath))
                )
                self.browser.execute_script("arguments[0].scrollIntoView(true);", final_payment_button)
                time.sleep(0.3)
                self.browser.execute_script("arguments[0].click();", final_payment_button)
            except TimeoutException as e:
                MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "최종 결제 버튼 찾기/클릭")
                return PAYMENT_FAILURE
            except Exception as e:
                 MacroExceptions.handle_general_exception(self.browser, self._log, e, "최종 결제 버튼 클릭")
                 return PAYMENT_FAILURE

            toast_result = self.toast_handler.check_toast_popup(7, total_wait_time)
            if toast_result["status"] == "success":
                 time.sleep(0.5)
            elif toast_result["status"] == "error":
                 return PAYMENT_FAILURE
            elif toast_result["status"] == "block":
                 time.sleep(toast_result['delay'])
                 return PAYMENT_FAILURE

            try:
                 WebDriverWait(self.browser, 10).until(
                     EC.presence_of_element_located((By.XPATH, "//p[contains(text(), '보관 신청이 완료되었습니다.')] | //div[contains(@class,'complete_title')]"))
                 )
                 return SUCCESS
            except TimeoutException as e:
                 MacroExceptions.handle_timeout_exception(self.browser, self._log, e, "완료 메시지/페이지 로딩")
                 return PAYMENT_FAILURE

        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "_process_payment_page")
            return PAYMENT_FAILURE

    def _check_payment_info_page(self):
        """(DEPRECATED - Not Used)"""
        return False

    def stop(self):
        """매크로 실행 중지 요청"""
        if self._running:
            self._running = False
        else:
            pass

    def start_macro(self, product_id: str, size: str, quantity: str, email: str = None, password: str = None):
        """매크로 시작을 요청하고 스레드를 생성하여 start 메소드를 호출"""
        try:
            started_successfully = self.start(product_id, size, quantity, email, password)

            if started_successfully:
                 return True
            else:
                 self._running = False
                 self.macro_status_changed.emit(False)
                 return False
        except Exception as e:
            MacroExceptions.handle_general_exception(self.browser, self._log, e, "start_macro 초기화")
            self._running = False
            self.macro_status_changed.emit(False)
            return False
