import random
import threading
import time
import traceback
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
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
    
    def __init__(self, browser, config, plugin_manager=None):
        super().__init__(name="macro", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self._running = False
        self._log_history = []  # 로그 히스토리를 저장할 리스트
        self.login_manager = LoginManager(browser)
        self.toast_handler = ToastHandler(browser, self._log)
        self.error_handler = ErrorHandler(browser, self._log)
        
    def _log(self, message):
        """로그 메시지를 생성하고 발신"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # 로그 히스토리에 추가하지 않고 바로 발신
        self.log_message.emit(log_message)

    def start(self, product_id, size, quantity, email=None, password=None):
        # 매크로 쓰레드 시작
        if self._running:
            return
            
        self._running = True
        self.macro_status_changed.emit(True)  # 매크로 실행 상태 알림
        min_itv = int(self.config.get('Macro', 'min_interval', fallback='8'))
        max_itv = int(self.config.get('Macro', 'max_interval', fallback='18'))
        
        def run_macro():
            attempt = 0
            inventory_opened = False
            # 즉시 첫 번째 시도 시작
            self._log("매크로가 시작되었습니다. 즉시 첫 번째 시도를 진행합니다...")
            
            # 매크로 시작 시 즉시 올바른 보관판매 페이지로 이동
            self._navigate_to_inventory_page(product_id)
            
            while self._running:
                try:
                    # Check login status at the beginning of each attempt
                    if email and password and not self.login_manager.is_logged_in():
                        self._log("로그인 상태가 아니거나 로그인 페이지입니다. 재로그인을 시도합니다.")
                        if not self.login_manager.relogin(email, password):
                            self._log("재로그인 실패. 매크로를 종료합니다.")
                            self._running = False
                            self.macro_status_changed.emit(False)
                            break
                        self._log("재로그인 성공. 보관판매 페이지로 이동합니다.")
                        # Relogin successful, navigate back to the target page and restart the attempt
                        if not self._navigate_to_inventory_page(product_id):
                             self._log("보관판매 페이지로 이동 실패 후 재로그인. 매크로 종료.")
                             self._running = False
                             self.macro_status_changed.emit(False)
                             break
                        inventory_opened = False # Reset state after navigation
                        continue # Skip the rest of the current loop iteration

                    # 페이지 확인 (현재 URL에서 보관판매 페이지인지 바로 확인)
                    current_url = self.browser.current_url
                    
                    # 신청내역 페이지 확인
                    try:
                        title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
                        for element in title_elements:
                            if "신청 내역" in element.text:
                                inventory_opened = True
                                break
                        else:
                            # 신청내역 페이지가 아닌 경우
                            
                            # 보관판매 페이지 확인
                            if 'inventory' in current_url and product_id in current_url:
                                inventory_opened = False
                            # 그 외 다른 페이지 - 직접 보관판매 페이지로 이동
                            else:
                                self._log("예상 페이지가 아닙니다. 보관판매 페이지로 이동합니다.")
                                self._navigate_to_inventory_page(product_id)
                                inventory_opened = False
                                continue
                    except:
                        # 예외 발생 시 직접 보관판매 페이지로 이동
                        self._log("페이지 확인 중 오류 발생. 보관판매 페이지로 이동합니다.")
                        self._navigate_to_inventory_page(product_id)
                        inventory_opened = False
                        continue
                    
                    # 매크로 실행 (신청내역 페이지에 이미 있는 경우와 아닌 경우 구분)
                    attempt += 1
                    self._log(f"보관판매 신청 시도 {attempt}회 - 시작")
                    
                    if inventory_opened:
                        # 이미 신청내역 페이지에 있는 경우
                        success = self._process_payment_page()
                    else:
                        # 처음부터 시작하는 경우
                        success = self._attempt_sale(product_id, size, quantity)
                        # 성공했으면 inventory_opened를 True로 설정 (후속 처리를 위해)
                        if not self.browser.current_url.endswith(product_id):
                            inventory_opened = True
                    
                    if success:
                        self._log(f"보관판매 신청 시도 {attempt}회 - 성공! 매크로를 종료합니다.")
                        self._running = False
                        self.macro_status_changed.emit(False)  # 매크로 중지 상태 알림
                        break
                    else:
                        self._log(f"보관판매 신청 시도 {attempt}회 - 실패")
                        # 페이지 새로고침
                        self.browser.refresh()
                        # 페이지 로딩 확인
                        WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                        )
                        
                        # 페이지 로딩 시간 대기
                        time.sleep(0.5)
                        
                        # 새로고침 후 페이지 상태 다시 확인
                        try:
                            title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
                            for element in title_elements:
                                if "신청 내역" in element.text:
                                    inventory_opened = True
                                    break
                            else:
                                inventory_opened = False
                        except:
                            inventory_opened = False
                    
                    # 다음 시도 전 대기 (시도가 실패했을 때만)
                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        self._log(f"{wait_sec}초 후 다음 시도를 진행합니다...")
                        time.sleep(wait_sec)
                        
                except Exception as e:
                    error_msg = f"오류 발생 - {str(e)}\n{traceback.format_exc()}"
                    self._log(error_msg)
                    # 페이지 새로고침 후 재시도
                    self.browser.refresh()
                    # 페이지 로딩 확인
                    try:
                        WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                        )
                        
                        # 페이지 로딩 시간 대기
                        time.sleep(0.5)
                        
                        # 현재 페이지 상태 다시 확인
                        try:
                            title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
                            for element in title_elements:
                                if "신청 내역" in element.text:
                                    inventory_opened = True
                                    break
                            else:
                                inventory_opened = False
                        except:
                            inventory_opened = False
                    except:
                        inventory_opened = False
                    
                    # 다음 시도 전 대기
                    if self._running:
                        wait_sec = random.randint(min_itv, max_itv)
                        self._log(f"오류 발생 후 {wait_sec}초 후 재시도합니다...")
                        time.sleep(wait_sec)
            
            if not self._running:
                self._log("매크로 종료 - 작업이 중지되었습니다.")
            else:
                self._log("매크로 종료 - 작업이 완료되었습니다.")
                self.macro_status_changed.emit(False)  # 매크로 중지 상태 알림

        # Python 스레드 시작 (또는 QThread 사용 가능)
        threading.Thread(target=run_macro, daemon=True).start()

    def _attempt_sale(self, product_id, size, quantity):
        """보관판매 시도 메인 로직"""
        try:
            # 먼저 현재 페이지가 신청내역 페이지인지 확인
            try:
                title_elements = self.browser.find_elements(By.CSS_SELECTOR, 'span.title_txt')
                for element in title_elements:
                    if "신청 내역" in element.text:
                        return self._process_payment_page()
            except:
                pass

            # 1. 보관판매 페이지로 이동
            if not self._navigate_to_inventory_page(product_id):
                self._log("보관판매 페이지 이동 실패")
                return False

            # 2. 보관 신청 페이지 진입
            if not self._enter_inventory_application_page():
                self._log("보관 신청 페이지 진입 실패")
                return False

            # 3. 사이즈 선택 및 수량 입력
            if not self._select_size_and_quantity(size, quantity):
                self._log("사이즈 선택 및 수량 입력 실패")
                return False

            # 4. 계속하기 버튼 클릭 및 모달 처리
            if not self._proceed_with_sale():
                self._log("신청 계속 과정 실패")
                return False
                
            # 토스트 팝업 확인
            toast_result = self.toast_handler.check_toast_popup(2)
            if toast_result["status"] == "block":
                # 대기 시간이 긴 경우 (1시간 등)
                time.sleep(toast_result["delay"])
                return False
            elif toast_result["status"] == "retry":
                # 즉시 재시도
                return False
            elif toast_result["status"] == "error":
                self._log("팝업 처리 중 오류 발생")
                return False

            # 5. 신청내역 페이지로 이동했는지 확인
            self._log("신청내역 페이지 이동 대기 중...")
            
            # 페이지 로딩 시간 대기 (브라우저 성능 차이 고려)
            time.sleep(3)
            
            # URL 확인 또는 페이지 제목 확인을 통해 신청내역 페이지 감지
            try:
                WebDriverWait(self.browser, 10).until(
                    lambda driver: len([e for e in driver.find_elements(By.CSS_SELECTOR, 'span.title_txt') if "신청 내역" in e.text]) > 0
                )
                self._log("신청내역 페이지 진입 완료")
            except TimeoutException:
                self._log("신청내역 페이지로 이동하지 못했습니다.")
                return False
                
            # 6. 결제 정보 페이지 결제 처리
            return self._process_payment_page()

        except Exception as e:
            error_msg = f"오류 발생 - {str(e)}\n{traceback.format_exc()}"
            self._log(error_msg)
            return False

    def _navigate_to_inventory_page(self, product_id):
        """보관판매 페이지로 이동"""
        try:
            # 이미 해당 상품의 보관판매 페이지에 있는지 확인
            if self.browser.current_url.startswith(f'https://kream.co.kr/inventory/{product_id}'):

                # 페이지 요소가 로드되었는지 확인
                WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product, div.detail-product-container'))
                )
                return True
            
            # 다른 페이지에 있다면 직접 보관판매 페이지로 이동
            self._log(f"보관판매 페이지로 이동합니다: 상품 ID {product_id}")
            self.browser.get(f'https://kream.co.kr/inventory/{product_id}')
            
            # 페이지 로드 확인
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_product, div.detail-product-container'))
                )
                self._log("보관판매 페이지 로드 완료")
                return True
            except TimeoutException:
                self._log("보관판매 페이지를 찾을 수 없습니다. URL을 확인해주세요.")
                return False
                
        except Exception as e:
            self._log(f"보관판매 페이지 이동 중 오류 발생: {str(e)}")
            return False

    def _enter_inventory_application_page(self):
        """보관신청 페이지로 진입"""
        # 현재 페이지가 이미 수량 선택 페이지인지 확인
        is_inventory_page = len(self.browser.find_elements(By.CSS_SELECTOR, 'div.inventory_size_list')) > 0

        if not is_inventory_page:
            # 보관 신청 버튼 클릭 (보관판매 페이지로 이동)
            try:
                inventory_button = WebDriverWait(self.browser, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.inventory_btn, button.inventory_btn, a.btn_action[href*="inventory"]'))
                )
                inventory_button.click()
                time.sleep(2)  # 페이지 전환 대기
            except TimeoutException:
                self._log("보관 신청 버튼을 찾을 수 없습니다.")
                return False

        # 사이즈 목록을 기다림
        try:
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
            )
            return True
        except TimeoutException:
            self._log("사이즈 목록을 찾을 수 없습니다.")
            return False

    def _select_size_and_quantity(self, size, quantity):
        """사이즈 선택 및 수량 입력"""
        try:
            size_list = self.browser.find_element(By.CSS_SELECTOR, 'div.inventory_size_list')
            size_elements = size_list.find_elements(By.CSS_SELECTOR, 'div.inventory_size_item')
            
            if len(size_elements) == 0:
                self._log("사이즈 목록이 비어있습니다.")
                return False
                
            size_found = False
            for element in size_elements:
                try:
                    # 사이즈 텍스트 가져오기
                    size_text = element.find_element(By.CSS_SELECTOR, 'div.size').text.strip()
                    if size_text == size:
                        # 수량 입력란 찾기
                        try:
                            quantity_input = element.find_element(By.CSS_SELECTOR, 'input.counter_quantity_input')
                            # JavaScript를 사용하여 강제로 값 설정 (클릭과 clear가 작동하지 않을 경우 대비)
                            self.browser.execute_script("arguments[0].value = '';", quantity_input)
                            quantity_input.send_keys(quantity)
                            size_found = True
                            # 데이터가 잘 입력되었는지 확인
                            time.sleep(0.5)
                            actual_value = self.browser.execute_script("return arguments[0].value;", quantity_input)
                            if actual_value != quantity:
                                self._log(f"수량 입력이 제대로 되지 않았습니다. 입력된 값: {actual_value}, 예상 값: {quantity}")
                                return False
                            break
                        except NoSuchElementException:
                            self._log(f"사이즈 {size}의 수량 입력란을 찾을 수 없습니다.")
                            continue
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            if not size_found:
                self._log(f"사이즈 {size}를 찾을 수 없습니다.")
                return False
            
            return True
        except Exception as e:
            self._log(f"사이즈 선택 및 수량 입력 중 오류: {str(e)}")
            return False

    def _proceed_with_sale(self):
        """계속하기 버튼 클릭 및 모달 처리"""
        try:
            # 비활성화되지 않은 버튼 찾기
            continue_button = WebDriverWait(self.browser, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.full.solid:not(.disabled), div.complete_btn_box'))
            )
            continue_button.click()
            self._log("신청 계속 버튼 클릭")
            
            # 모달 처리
            if not MacroExceptions.handle_model_number_modal(self.browser, self._log):
                return False
            
            if not MacroExceptions.handle_label_size_modal(self.browser, self._log):
                return False
            
            return True
        except TimeoutException:
            self._log("활성화된 계속하기 버튼을 찾을 수 없습니다. 수량이 올바르게 입력되었는지 확인해주세요.")
            return False
        except Exception as e:
            self._log(f"계속하기 버튼 클릭 중 오류: {str(e)}")
            return False

    def _process_payment_page(self):
        """결제 정보 페이지 처리 로직"""
        try:
            # 필수 요소들이 모두 로드될 때까지 대기
            essential_selectors = ['div.payment_inventory']
            
            # 페이지 로딩 확인
            if not self.error_handler.verify_page_loading(essential_selectors):
                self._log("결제 페이지 요소를 찾을 수 없습니다. 보관판매 페이지로 돌아갑니다.")
                return False
            
            # 서비스 오류 확인
            if self.toast_handler.check_service_error():
                return False
            
            # 보증금 결제하기 버튼 클릭
            try:
                deposit_button = WebDriverWait(self.browser, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.display_button.large.dark_filled.active.block.bold'))
                )
                self._log("보증금 결제하기 버튼 클릭")
                self.browser.execute_script("arguments[0].click();", deposit_button)
            except (TimeoutException, NoSuchElementException):
                self._log("보증금 결제하기 버튼을 찾을 수 없습니다.")
                return False
            
            # 체크박스 처리
            if not MacroExceptions.handle_payment_modal(self.browser, self._log):
                self._log("결제 모달 체크박스 처리 실패")
                return False
            
            # 최종 결제 버튼이 활성화될 때까지 대기 (0.5초)
            time.sleep(0.5)
            try:
                final_payment_button = WebDriverWait(self.browser, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.display_button.large.gray_filled.block, div.layer_bottom div.bottom-button button'))
                )
                self._log("최종 보증금 결제 버튼 클릭")
                self.browser.execute_script("arguments[0].click();", final_payment_button)
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
                self._log(f"최종 결제 버튼을 찾을 수 없습니다: {str(e)}")
                return False
            
            # 토스트 팝업 확인
            toast_result = self.toast_handler.check_toast_popup(3)
            if toast_result["status"] != "success":
                self._log("결제 과정 중 오류가 발생했습니다.")
                return False
            
            # 완료 메시지 확인
            try:
                completion_message = WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'p.main_title'))
                )
                
                if "보관 신청이 완료되었습니다." in completion_message.text:
                    self._log("보관 신청이 완료되었습니다. 매크로 성공!")
                    return True
                else:
                    self._log("보관 신청 완료 메시지를 찾을 수 없습니다.")
                    return False
            except TimeoutException:
                # 토스트가 없고 완료 메시지도 없는 경우, 성공으로 처리
                self._log("완료 메시지를 찾을 수 없지만 오류도 감지되지 않아 성공으로 처리합니다.")
                return True
                
        except Exception as e:
            error_msg = f"결제 정보 페이지 처리 중 오류 발생 - {str(e)}"
            self._log(error_msg)
            return False
    
    def _check_payment_info_page(self):
        """결제 정보 페이지 진입 확인 및 처리"""
        self._log("결제 정보 페이지로 진행되었습니다.")
        return self._process_payment_page()

    def stop(self):
        if self._running:
            self._running = False
            self._log("매크로 중지 명령을 받았습니다. 현재 작업 완료 후 중지됩니다.")
            self.macro_status_changed.emit(False)  # 매크로 중지 상태 알림

    def start_macro(self, product_id: str, size: str, quantity: str, email: str = None, password: str = None):
        try:
            # config.ini에서 인터벌 값 가져오기
            min_itv = int(self.config.get('Macro', 'min_interval', fallback='8'))
            max_itv = int(self.config.get('Macro', 'max_interval', fallback='18'))
            
            # 실제 반복 실행 매크로 호출
            self.start(product_id, size, quantity, email, password)
            self._log(f"매크로가 초기화되었습니다. {min_itv}~{max_itv}초 간격으로 반복 실행됩니다.")
        except Exception as e:
            error_msg = f"매크로 실행 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
            self._log(error_msg)