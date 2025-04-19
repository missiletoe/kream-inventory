import random
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.kream_inventory.core.plugin_base import PluginBase
from src.kream_inventory.plugins.login.login_manager import LoginManager
from src.kream_inventory.plugins.macro.macro_error_handler import MacroErrorHandler
from src.kream_inventory.plugins.macro.macro_exceptions import MacroExceptions
from src.kream_inventory.plugins.macro.macro_log_handler import MacroLogHandler
from src.kream_inventory.plugins.macro.macro_toast_handler import MacroToastHandler

# Constants for return values from attempt functions
PAYMENT_FAILURE = "PAYMENT_FAILURE"
PRE_PAYMENT_FAILURE = False
SUCCESS = True


class MacroPlugin(PluginBase, QObject):
    macro_status_changed = pyqtSignal(bool)  # True=실행 중, False=중지됨
    
    def __init__(self, browser: WebDriver, config, plugin_manager=None):
        super().__init__(name="macro", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self._running = False
        self.log_handler = MacroLogHandler()
        self.login_manager = LoginManager(browser)
        self.toast_handler = MacroToastHandler(browser, log_handler=self.log_handler)
        self.error_handler = MacroErrorHandler(browser, log_handler=self.log_handler)
        self._original_window_handle = None # Store original tab handle
        
        # Forward log signal from log_handler to listeners of this class
        self.log_message = self.log_handler.log_message

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
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "새 탭 열기")
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

            self.log_handler.log("매크로 구동 시작", allowed_key="START")

            if not self._navigate_to_inventory_page(product_id):
                 self._running = False
                 self.macro_status_changed.emit(False)
                 try:
                    self.browser.close()
                    self.browser.switch_to.window(self._original_window_handle)
                 except: pass
                 self.log_handler.log("매크로 구동 정지", allowed_key="STOP")
                 return

            while self._running:
                try:
                    # Check if browser window is still available
                    try:
                        self.browser.current_url  # This will throw an exception if window is closed
                    except Exception:
                        self._running = False
                        break
                        
                    if email and password and (not self.login_manager.is_logged_in() or self.browser.current_url == 'https://kream.co.kr/login'):
                        if not self.login_manager.relogin(email, password, switch_to_new_tab=False):
                            self._running = False
                            break
                        self.log_handler.log("재로그인 성공", allowed_key="RELOGIN_SUCCESS")
                        total_wait_time = 0 # Reset wait time after relogin
                        if not self._navigate_to_inventory_page(product_id):
                             self._running = False
                             break
                        inventory_opened = False
                        continue

                    try:
                        current_url = self.browser.current_url
                        try:
                            page_title = WebDriverWait(self.browser, 1).until(
                                EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'title_txt')]"))
                            ).text
                            inventory_opened = "신청 내역" in page_title
                        except:
                            inventory_opened = False
                            
                        if not inventory_opened and not (current_url.startswith(f'https://kream.co.kr/inventory/{product_id}')):
                            if not self._navigate_to_inventory_page(product_id):
                                time.sleep(random.randint(3, 7))
                                continue
                    except TimeoutException:
                        inventory_opened = False
                        try:
                            current_url = self.browser.current_url
                            if not current_url.startswith(f'https://kream.co.kr/inventory/{product_id}'):
                                if not self._navigate_to_inventory_page(product_id):
                                    time.sleep(random.randint(3, 7))
                                    continue
                        except Exception:
                            # Window might be closed
                            self._running = False
                            break
                    except Exception as e:
                        if "no such window" in str(e).lower():
                            self._running = False
                            break
                        MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "페이지 상태 확인")
                        inventory_opened = False
                        time.sleep(random.randint(3, 7))
                        continue

                    attempt += 1

                    if inventory_opened:
                        result = self._process_payment_page(total_wait_time)
                    else:
                        result = self._attempt_sale(product_id, size, quantity, total_wait_time)

                    if result == SUCCESS:
                        self.log_handler.log("보관판매 신청 완료. 매크로 정지", allowed_key="FINAL_SUCCESS")
                        self._running = False
                        break

                    else:
                        self.log_handler.log(f"보관판매 신청 시도 {attempt}회 — 실패", allowed_key="ATTEMPT_FAIL")

                        # Wait the configured interval without refreshing
                        if self._running:
                            wait_sec = random.randint(min_itv, max_itv)
                            self.log_handler.log(f"{wait_sec}초 대기 시작 (누적: {total_wait_time + wait_sec}초)")
                            for i in range(wait_sec):
                                if not self._running: break
                                time.sleep(1)
                            if self._running:
                                total_wait_time += wait_sec
                            if not self._running: break

                except Exception as e:
                    if "no such window" in str(e).lower():
                        self._running = False
                        break
                        
                    if not MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "매크로 실행 루프"):
                        try:
                            if "window" not in str(e).lower():  # Only refresh if not a window error
                                self.browser.refresh()
                                WebDriverWait(self.browser, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                                time.sleep(1)
                        except Exception:
                            self._running = False
                            break

                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        for _ in range(wait_sec):
                            if not self._running: break
                            time.sleep(1)
                        if not self._running: break

            self.log_handler.log("매크로 구동 정지", allowed_key="STOP")

            self._running = False
            self.macro_status_changed.emit(False)

            try:
                self.browser.current_url  # Check if window still exists
                if self.browser.current_window_handle != self._original_window_handle:
                     self.browser.close()
                if self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                     self.browser.switch_to.window(self._original_window_handle)
            except Exception:
                 pass
            finally:
                 self._original_window_handle = None

        thread = threading.Thread(target=run_macro, daemon=True)
        thread.start()

        return True

    def _attempt_sale(self, product_id, size, quantity, total_wait_time):
        try:
            # Check for service error and toast message early
            if self.toast_handler.check_service_error():
                return PRE_PAYMENT_FAILURE

            # Check for existing toast popups that may block further interaction
            toast_result = self.toast_handler.check_toast_popup(wait_seconds=1, total_wait_time=total_wait_time)
            if toast_result["status"] != "success":
                return PRE_PAYMENT_FAILURE

            # Get to the inventory page for the product
            inventory_url = f"https://kream.co.kr/inventory/{product_id}"
            
            # Only navigate if we're not already there
            if not self.browser.current_url.startswith(inventory_url):
                self.browser.get(inventory_url)
                time.sleep(1)  # Allow page to initialize
                
                # Check if we ended up on the correct page
                page_check = self.error_handler.check_wrong_page(product_id)
                if page_check["status"] != "inventory_page":
                    if page_check["status"] == "application_page":
                        return self._process_payment_page(total_wait_time)
                    return PRE_PAYMENT_FAILURE
            
            # Wait for essential page elements
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_sell'))
                )
            except TimeoutException:
                return PRE_PAYMENT_FAILURE

            # Enter inventory application page
            if not self._enter_inventory_application_page():
                return PRE_PAYMENT_FAILURE
                
            # Select size and quantity
            if not self._select_size_and_quantity(size, quantity):
                return PRE_PAYMENT_FAILURE

            # Proceed with the sale - just wait and click
            if not self._proceed_with_sale():
                return PRE_PAYMENT_FAILURE
                
            # Check if we've entered the payment info page
            return self._check_payment_info_page()
            
        except Exception as e:
            if "no such window" in str(e).lower():
                # Window closed error - let the main loop handle it
                raise e
            
            if not MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "보관판매 시도"):
                return PAYMENT_FAILURE
            return PRE_PAYMENT_FAILURE

    def _navigate_to_inventory_page(self, product_id):
        try:
            inventory_url = f"https://kream.co.kr/inventory/{product_id}"
            self.browser.get(inventory_url)
            
            # Wait for page to load
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
            )
            time.sleep(0.5)  # Additional short wait for page to initialize
            
            # Check if we're on the expected page
            page_check = self.error_handler.check_wrong_page(product_id)
            if page_check["status"] == "inventory_page" or page_check["status"] == "application_page":
                return True
            else:
                # Try one more time with product page first
                try:
                    product_url = f"https://kream.co.kr/products/{product_id}"
                    self.browser.get(product_url)
                    WebDriverWait(self.browser, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-price'))
                    )
                    # Find and click the "보관판매" button
                    sell_buttons = self.browser.find_elements(By.CSS_SELECTOR, 'button.btn_action')
                    for button in sell_buttons:
                        if '보관판매' in button.text or 'INVENTORY SELL' in button.text.upper():
                            button.click()
                            WebDriverWait(self.browser, 10).until(
                                lambda d: 'inventory' in d.current_url
                            )
                            return True
                    return False
                except Exception:
                    return False
        except Exception as e:
            if "no such window" in str(e).lower():
                raise e
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "보관판매 페이지 이동")
            return False

    def _enter_inventory_application_page(self):
        try:
            # Fast check for service error
            if self.toast_handler.check_service_error():
                return False
                
            # Wait for sell button to be present
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.btn_action'))
            )
            
            # Find sell button
            sell_buttons = self.browser.find_elements(By.CSS_SELECTOR, 'a.btn_action')
            for button in sell_buttons:
                try:
                    if '보관판매' in button.text or 'INVENTORY SELL' in button.text.upper():
                        button.click()
                        # Wait for size selection page to load
                        WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_sell.sell_immediate'))
                        )
                        return True
                except StaleElementReferenceException:
                    continue
            return False
            
        except TimeoutException:
            return False
        except Exception as e:
            if "no such window" in str(e).lower():
                raise e
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "보관판매 신청 페이지 진입")
            return False

    def _select_size_and_quantity(self, size, quantity):
        try:
            # Check again for service error
            if self.toast_handler.check_service_error():
                return False
                
            # Wait for size selection to be available
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.select_item, div.size_item'))
            )
            
            # Select size
            size_selected = False
            
            # First try div.select_item pattern
            size_elements = self.browser.find_elements(By.CSS_SELECTOR, 'div.select_item')
            for element in size_elements:
                try:
                    size_text = element.find_element(By.CSS_SELECTOR, 'span.size').text.strip()
                    if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                        element.click()
                        size_selected = True
                        break
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            
            # If not found, try div.size_item pattern
            if not size_selected:
                size_elements = self.browser.find_elements(By.CSS_SELECTOR, 'div.size_item')
                for element in size_elements:
                    try:
                        size_text = element.text.strip()
                        if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                            element.click()
                            size_selected = True
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
            
            if not size_selected:
                return False
            
            # Select quantity if quantity selection exists
            try:
                # Wait for quantity input to be present after size selection
                WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input.input_amount'))
                )
                
                quantity_input = self.browser.find_element(By.CSS_SELECTOR, 'input.input_amount')
                current_qty = quantity_input.get_attribute('value')
                
                if current_qty != quantity:
                    quantity_input.clear()
                    quantity_input.send_keys(quantity)
            except TimeoutException:
                # Some products might not have quantity selection, proceed anyway
                pass
            except Exception:
                # Continue anyway, it might work with default quantity
                pass
            
            return True
            
        except TimeoutException:
            return False
        except Exception as e:
            if "no such window" in str(e).lower():
                raise e
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "사이즈/수량 선택")
            return False

    def _proceed_with_sale(self):
        try:
            # Find and click the submit button
            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.btn_confirm'))
            )
            
            submit_button = self.browser.find_element(By.CSS_SELECTOR, 'div.btn_confirm')
            if 'disabled' in submit_button.get_attribute('class'):
                return False
                
            submit_button.click()
            
            # Wait for next page to load (either application page or payment page)
            WebDriverWait(self.browser, 10).until(
                lambda d: "신청" in d.title or "결제" in d.title
            )
            
            return True
            
        except TimeoutException:
            return False
        except Exception as e:
            if "no such window" in str(e).lower():
                raise e
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "신청 버튼 클릭")
            return False

    def _process_payment_page(self, total_wait_time):
        try:
            # Verify we're on the payment page or application page
            try:
                current_title = WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span.title_txt, title'))
                ).text
                if "신청 내역" in current_title:
                    return SUCCESS  # Already on confirmation page, consider success
            except:
                # Title check failed, continue with normal flow
                pass
                
            # Check for any toast messages/errors
            toast_result = self.toast_handler.check_toast_popup(wait_seconds=1, total_wait_time=total_wait_time)
            if toast_result["status"] != "success":
                if toast_result["status"] == "block":
                    # Handle long blocking delay, return failure but let main loop handle wait
                    return PRE_PAYMENT_FAILURE
                elif toast_result["status"] == "error" or toast_result["status"] == "retry":
                    return PRE_PAYMENT_FAILURE
            
            # Wait for payment agreement checkbox if exists
            try:
                agreement_checkbox = WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'label.checkbox_label'))
                )
                if not agreement_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]').is_selected():
                    agreement_checkbox.click()
            except TimeoutException:
                # Checkbox might not exist, continue
                pass
            except NoSuchElementException:
                # Checkbox might have different structure, try alternate approach
                try:
                    checkboxes = self.browser.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    for checkbox in checkboxes:
                        if not checkbox.is_selected():
                            # Use JavaScript to click since it might be obscured
                            self.browser.execute_script("arguments[0].click();", checkbox)
                except:
                    # Continue even if checkbox handling fails
                    pass
                    
            # Check for service error again before proceeding
            if self.toast_handler.check_service_error():
                return PRE_PAYMENT_FAILURE
                
            # Find and click the final payment button
            payment_buttons = self.browser.find_elements(By.CSS_SELECTOR, 'div.btn_confirm, button.btn_action')
            
            payment_button_found = False
            for button in payment_buttons:
                try:
                    button_text = button.text.strip()
                    if '결제하기' in button_text or '신청하기' in button_text or '보관판매' in button_text:
                        # Check if button is disabled
                        if 'disabled' in button.get_attribute('class'):
                            return PRE_PAYMENT_FAILURE
                            
                        button.click()
                        payment_button_found = True
                        break
                except StaleElementReferenceException:
                    continue
                
            if not payment_button_found:
                return PRE_PAYMENT_FAILURE
                
            # Check for any confirmation dialog and accept it
            try:
                WebDriverWait(self.browser, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
                )
                confirm_buttons = self.browser.find_elements(By.CSS_SELECTOR, 'div.btn_layer_confirm, div.btn_confirm')
                for button in confirm_buttons:
                    if button.is_displayed() and (button.text.strip() == '확인' or '확인' in button.text):
                        button.click()
                        break
            except TimeoutException:
                # No confirmation dialog, continue
                pass
                
            # Wait for success indication - either page change or success message
            # Wait for success toast or completion page
            try:
                # Wait for application completion page or successful toast
                WebDriverWait(self.browser, 10).until(
                    lambda d: any(["신청 내역" in element.text for element in 
                                    d.find_elements(By.CSS_SELECTOR, 'span.title_txt')])
                             or any(["완료" in element.text for element in 
                                      d.find_elements(By.CSS_SELECTOR, 'div.layer_toast.show')])
                )
                return SUCCESS
            except TimeoutException:
                return PAYMENT_FAILURE  # Could be stuck on payment page
                
        except Exception as e:
            if "no such window" in str(e).lower():
                raise e
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "결제/신청 처리")
            return PAYMENT_FAILURE

    def _check_payment_info_page(self):
        # Placeholder for any specific checks on the payment info page
        return True
        
    def stop(self):
        self._running = False
        self.macro_status_changed.emit(False)
        self.log_handler.log("매크로 구동 정지 요청됨", allowed_key="STOP")
        return True
        
    def start_macro(self, product_id: str, size: str, quantity: str, email: str = None, password: str = None):
        """호환성을 위한 start() 메소드 별칭"""
        return self.start(product_id, size, quantity, email, password)
