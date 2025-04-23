import random
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import TimeoutException
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

# attempt 함수의 반환 값에 대한 상수
PAYMENT_FAILURE = "PAYMENT_FAILURE"
PRE_PAYMENT_FAILURE = False
SUCCESS = True


class MacroPlugin(PluginBase, QObject):
    macro_status_changed = pyqtSignal(bool)  # True=실행 중, False=중지됨
    log_message = pyqtSignal(str)  # 로그 메시지 신호

    def __init__(self, browser: WebDriver, config, plugin_manager=None):
        super().__init__(name="macro", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self._running = False
        self.log_handler = MacroLogHandler(config)
        self.login_manager = LoginManager(browser)
        self.toast_handler = MacroToastHandler(browser, log_handler=self.log_handler)
        self.error_handler = MacroErrorHandler(browser, log_handler=self.log_handler)
        self._original_window_handle = None  # 원래 탭 핸들 저장

        # log_handler의 로그 신호를 이 클래스의 리스너에게 연결
        self.log_handler.log_message.connect(self.log_message.emit)

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
                except Exception:
                    pass
            self._original_window_handle = None
            return False

        self._running = True
        self.macro_status_changed.emit(True)
        min_itv = int(self.config.get('Macro', 'min_interval', fallback='8'))
        max_itv = int(self.config.get('Macro', 'max_interval', fallback='18'))

        def run_macro():
            attempt = 0
            total_wait_time = 0  # 총 대기 시간 초기화

            self.log_handler.log("매크로 구동 시작", allowed_key="START")

            # 매크로 시작 시 바로 보관판매 페이지로 이동
            if not self._navigate_to_inventory_page(product_id):
                self.log_handler.log("보관판매 페이지 이동 실패, 매크로 중단", allowed_key="ERROR")
                self._running = False
                return

            while self._running:
                try:
                    # 브라우저 창이 여전히 사용 가능한지 확인
                    try:
                        self.browser.current_url  # 창이 닫히면 예외가 발생함
                    except Exception:
                        self.log_handler.log("브라우저 창 감지 불가, 매크로 종료", allowed_key="ERROR")
                        self._running = False
                        break

                    # --- 로그인 확인 ---
                    if 'login' in self.browser.current_url:
                        self.log_handler.log("로그인 상태 확인 또는 재로그인 시도", allowed_key="LOGIN_CHECK")
                        if not self.login_manager.relogin(email, password, switch_to_new_tab=False):
                            self.log_handler.log("재로그인 실패, 매크로 중단", allowed_key="ERROR")
                            self._running = False
                            break
                        self.log_handler.log("재로그인 성공", allowed_key="RELOGIN_SUCCESS")
                        total_wait_time = 0

                        # 재로그인 후에는 항상 처음부터 시작
                        if not self._navigate_to_inventory_page(product_id):
                            self.log_handler.log("재로그인 후 페이지 이동 실패, 매크로 중단", allowed_key="ERROR")
                            self._running = False
                            break
                        continue  # 처음부터 루프 재시작

                    # --- 현재 페이지 상태 판별 --- 
                    page_indicators = self.check_page_indicators(product_id)
                    current_url = page_indicators["current_url"]
                    is_success_page = page_indicators["is_success_page"]
                    is_application_page = page_indicators["is_application_page"]
                    is_inventory_page = page_indicators["is_inventory_page"]

                    # --- 상태에 따른 액션 --- 

                    # 1. 최종 성공 페이지 감지
                    if is_success_page:
                        self.log_handler.log("보관판매 신청 완료 확인됨. 매크로 정지", allowed_key="FINAL_SUCCESS")
                        self._running = False
                        break

                    # 2. "신청 내역" 페이지 또는 결제 페이지 처리
                    elif is_application_page:
                        self.log_handler.log("신청 내역 또는 결제 페이지 감지", allowed_key="APP_PAYMENT_DETECT")
                        try:
                            result = self._process_payment_page()
                            if result == SUCCESS:
                                self.log_handler.log("결제 처리 후 성공 확인. 매크로 정지", allowed_key="FINAL_SUCCESS")
                                self._running = False
                                break
                            elif result == PAYMENT_FAILURE:
                                self.log_handler.log("결제 처리 실패 감지. 0.5초 후 재시도", allowed_key="PAYMENT_FAIL_RETRY")
                                time.sleep(0.5)
                                # 재시도를 위해 페이지 상태 재확인 필요 -> continue loop
                                continue
                        except Exception as payment_error:
                            self.log_handler.log(f"신청 내역/결제 페이지 처리 중 오류 발생: {str(payment_error)}", allowed_key="ERROR")
                            # "신청 내역" 페이지에서 오류 발생 시 새로고침 후 재시작
                            if is_application_page:
                                self.log_handler.log("신청 내역 페이지 오류. 새로고침 후 재시작합니다.", allowed_key="APP_PAGE_REFRESH")
                                try:
                                    self.browser.refresh()
                                    WebDriverWait(self.browser, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                                except Exception as refresh_err:
                                    self.log_handler.log(f"새로고침 중 오류: {str(refresh_err)}. 매크로 중단.", allowed_key="ERROR")
                                    self._running = False
                                    break  # 외부 while 루프 종료
                                # 현재 페이지 상태 초기화 및 루프 재시작
                                try:
                                    if not self._navigate_to_inventory_page(product_id):
                                        self.log_handler.log("새로고침 후 페이지 이동 실패, 매크로 중단", allowed_key="ERROR")
                                        self._running = False
                                        break  # 외부 while 루프 종료
                                    continue  # 루프 재시작
                                except Exception as nav_err:
                                    self.log_handler.log(f"새로고침 후 페이지 이동 중 오류: {str(nav_err)}. 매크로 중단.",
                                                         allowed_key="ERROR")
                                    self._running = False
                                    break  # 외부 while 루프 종료
                            else:
                                # 다른 결제 관련 페이지 오류는 일단 루프 계속 진행
                                self.log_handler.log("결제 관련 페이지 오류. 잠시 후 재시도합니다.", allowed_key="ERROR")
                                time.sleep(0.5)
                                continue

                    # 3. 인벤토리 페이지 또는 사이즈/수량 선택 페이지 처리
                    elif is_inventory_page:
                        self.log_handler.log("인벤토리 또는 사이즈/수량 페이지 감지", allowed_key="INV_SALE_DETECT")
                        result = None  # 결과 초기화
                        try:
                            # --- 보관판매 접수 신청 단계 ---
                            result = self._submit_consignment_application(size, quantity, total_wait_time)

                            # --- 결과 처리 ---
                            if result == SUCCESS:
                                self.log_handler.log("신청 시도 후 성공 확인. 매크로 정지", allowed_key="FINAL_SUCCESS")
                                self._running = False
                                break  # 외부 루프 종료
                            elif result == PRE_PAYMENT_FAILURE:
                                self.log_handler.log("이전 단계 실패 감지. 잠시 후 재시도.", allowed_key="PRE_PAYMENT_FAIL_RETRY")
                                time.sleep(random.randint(0, 1))
                                continue  # 상태를 재평가하기 위해 루프 재시작
                            elif result == PAYMENT_FAILURE:
                                self.log_handler.log("결제 단계 실패 감지. 루프 계속하여 상태 재확인.",
                                                     allowed_key="PAYMENT_FAIL_CONTINUE")
                                time.sleep(0.2)
                                continue
                            else:  # None 또는 예상치 못한 결과
                                self.log_handler.log(
                                    f"알 수 없는 _submit_consignment_application 결과 ({result}). 페이지 상태 재확인",
                                    allowed_key="WARN")
                                time.sleep(0.2)
                                continue

                        except Exception as attempt_error:
                            # _submit_consignment_application 과정 중 발생한 오류 처리
                            self.log_handler.log(
                                f"신청 시도(_submit_consignment_application) 중 오류 발생: {str(attempt_error)}",
                                allowed_key="ERROR")
                            self.log_handler.log("신청 시도 중 오류. 새로고침 후 재시작합니다.", allowed_key="ATTEMPT_REFRESH")
                            try:
                                self.browser.refresh()
                                WebDriverWait(self.browser, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                            except Exception as refresh_err:
                                self.log_handler.log(f"새로고침 중 오류: {str(refresh_err)}. 매크로 중단.", allowed_key="ERROR")
                                self._running = False
                                break  # 외부 루프 종료

                            # 새로고침 후 인벤토리 페이지로 다시 이동
                            try:
                                if not self._navigate_to_inventory_page(product_id):
                                    self.log_handler.log("새로고침 후 페이지 이동 실패, 매크로 중단", allowed_key="ERROR")
                                    self._running = False
                                    break  # 외부 루프 종료
                                continue  # 루프 재시작
                            except Exception as nav_err:
                                self.log_handler.log(f"새로고침 후 페이지 이동 중 오류: {str(nav_err)}. 매크로 중단.",
                                                     allowed_key="ERROR")
                                self._running = False
                                break  # 외부 루프 종료

                    # 4. 알 수 없는 페이지 -> 시작 페이지로 이동 시도
                    else:
                        self.log_handler.log(f"알 수 없는 페이지 상태 감지 (URL: {current_url}). 시작 페이지로 이동 시도.",
                                             allowed_key="UNKNOWN_PAGE_HANDLER")
                        try:
                            # 페이지 이동 시도
                            page_moved = self._navigate_to_inventory_page(product_id)

                            # 시도 횟수 증가
                            attempt += 1
                            self.log_handler.log(f"보관판매 신청 시도 {attempt}회", allowed_key="ATTEMPT")

                            # 페이지 이동 실패 시 대기 후 계속
                            if not page_moved:
                                self.log_handler.log("알 수 없는 페이지에서 시작 페이지 이동 실패. 잠시 후 재시도.", allowed_key="ERROR")
                                time.sleep(random.randint(1, 3))
                            else:
                                # 페이지 이동 성공 시 대기 로직 구현
                                wait_sec = random.randint(min_itv, max_itv)
                                page_source_for_toast = self.browser.page_source.lower()

                                # 토스트 메시지 확인
                                toast_result = self.toast_handler.check_toast_popup(wait_seconds=0.2,
                                                                                    total_wait_time=total_wait_time)
                                delay_reason = "기본 간격"

                                if toast_result["status"] == "block" and toast_result["delay"] > 0:
                                    wait_sec = max(wait_sec, toast_result["delay"])
                                    delay_reason = f"토스트 블록 ({toast_result['message']})"
                                elif toast_result["status"] == "retry" and toast_result["delay"] > 0:
                                    wait_sec = max(wait_sec, toast_result["delay"])
                                    delay_reason = f"토스트 재시도 ({toast_result['message']})"
                                elif "허용된 요청 횟수를 초과했습니다" in page_source_for_toast:
                                    wait_sec = max(wait_sec, 30)
                                    delay_reason = "요청 횟수 초과 감지"

                                self.log_handler.log(
                                    f"{wait_sec}초 대기 ({delay_reason}, 누적: {total_wait_time + wait_sec}초)",
                                    allowed_key="WAIT")

                                # 초 단위로 대기하면서 중단 여부 확인
                                for i in range(wait_sec * 5):
                                    if not self._running: break

                                if self._running:
                                    total_wait_time += wait_sec

                            if not self._running: break
                            continue  # 상태를 재평가하기 위해 루프 재시작
                        except Exception as nav_error_unknown:
                            self.log_handler.log(f"알 수 없는 페이지 처리 중 페이지 이동 오류: {str(nav_error_unknown)}. 매크로 중단.",
                                                 allowed_key="ERROR")
                            self._running = False
                            break  # 외부 루프 종료

                    # 이 코드는 위의 else 블록에서 항상 continue 또는 break가 실행되므로 도달할 수 없음
                    # 대기 로직은 각 케이스별로 적절한 위치에 구현해야 함

                except Exception as main_loop_error:
                    if "no such window" in str(main_loop_error).lower():
                        self.log_handler.log("브라우저 창 닫힘 감지 (메인 루프), 매크로 종료", allowed_key="ERROR")
                        self._running = False
                        break

                    # 일반적인 예외 처리 후 새로고침 및 재시작 시도
                    self.log_handler.log(f"메인 루프 예외 발생: {str(main_loop_error)}. 새로고침 후 재시작 시도.", allowed_key="ERROR")
                    MacroExceptions.handle_general_exception(self.browser, self.log_handler, main_loop_error,
                                                             "매크로 실행 루프")

                    try:
                        self.browser.refresh()
                        WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                    except Exception as e:
                        self.log_handler.log(f"메인 루프 오류 후 새로고침 실패: {str(e)}. 매크로 중단.", allowed_key="ERROR")
                        self._running = False
                        break

                    # 페이지 이동 재시도
                    try:
                        if not self._navigate_to_inventory_page(product_id):
                            self.log_handler.log("메인 루프 오류 후 페이지 이동 실패, 매크로 중단", allowed_key="ERROR")
                            self._running = False
                            break
                        continue  # 루프 재시작
                    except Exception as nav_err_main:
                        self.log_handler.log(f"메인 루프 오류 후 페이지 이동 실패: {str(nav_err_main)}. 매크로 중단.", allowed_key="ERROR")
                        self._running = False
                        break

            # 매크로 종료 시, 최종 성공 여부 한 번 더 확인
            try:
                current_url = self.browser.current_url
                page_source = self.browser.page_source.lower()

                if "보관 신청이 완료되었습니다." in page_source:
                    self.log_handler.log("최종 페이지 확인: 보관판매 성공", allowed_key="FINAL_CHECK_SUCCESS")
                else:
                    self.log_handler.log("최종 페이지 확인: 보관판매 미확인", allowed_key="FINAL_CHECK_UNKNOWN")
            except Exception as e:
                self.log_handler.log(f"최종 페이지 확인 중 오류: {str(e)}", allowed_key="ERROR")

            self.log_handler.log("매크로 구동 정지", allowed_key="STOP")

            self._running = False
            self.macro_status_changed.emit(False)

            try:
                # 창이 여전히 존재하는지 확인 (예외가 발생하면 창이 존재하지 않는 것)
                window_exists = bool(self.browser.current_url)  # 결과를 변수에 할당하여 실제로 사용
                if window_exists and self.browser.current_window_handle != self._original_window_handle:
                    self.browser.close()
                if window_exists and self._original_window_handle and self._original_window_handle in self.browser.window_handles:
                    self.browser.switch_to.window(self._original_window_handle)
            except Exception as e:
                self.log_handler.log(f"브라우저 창 정리 중 오류: {str(e)}", allowed_key="ERROR")
            finally:
                self._original_window_handle = None

        thread = threading.Thread(target=run_macro, daemon=True)
        thread.start()

        return True

    def _submit_consignment_application(self, size, quantity, total_wait_time):
        """보관판매 접수 신청 - 유저가 가지고 있는 물건을 보관판매로 맡기기 위한 신청 처리"""
        try:
            # 서비스 에러 확인 (빠른 확인)
            if self.toast_handler.check_service_error():
                return PRE_PAYMENT_FAILURE

            # 토스트 팝업 확인 (짧은 대기)
            toast_result = self.toast_handler.check_toast_popup(wait_seconds=0.2, total_wait_time=total_wait_time)
            if toast_result["status"] != "success":
                return PRE_PAYMENT_FAILURE

            # 성공 페이지인지 확인
            if self._check_if_success_page():
                self.log_handler.log("성공 페이지 확인됨", allowed_key="SUCCESS_URL")
                return SUCCESS

            # 현재 URL 확인
            current_url = self.browser.current_url

            # 바로 사이즈 및 수량 선택 시도
            self.log_handler.log("사이즈/수량 선택 시도", allowed_key="SIZE_QTY_PAGE")
            if not self._select_size_and_quantity(size, quantity):
                self.log_handler.log("사이즈/수량 선택 실패", allowed_key="SIZE_QTY_FAIL")
                return PRE_PAYMENT_FAILURE

            # 신청 버튼 클릭
            if not self._proceed_with_sale():
                self.log_handler.log("신청 버튼 클릭 실패", allowed_key="PROCEED_FAIL")
                return PRE_PAYMENT_FAILURE

            # 페이지 전환 확인 - 최대 3초간 대기
            for _ in range(3):
                # 성공 페이지 확인
                if self._check_if_success_page():
                    self.log_handler.log("신청 완료 페이지 확인", allowed_key="ORDER_COMPLETE_DETECTED")
                    return SUCCESS

                # 결제 페이지 확인
                current_url = self.browser.current_url
                if 'payment' in current_url or 'order' in current_url:
                    self.log_handler.log("결제 페이지 확인", allowed_key="PAYMENT_URL_DETECTED")
                    return self._process_payment_page()

                # 토스트 메시지 확인
                toast_result = self.toast_handler.check_toast_popup(wait_seconds=0.2)
                if toast_result["status"] != "success":
                    self.log_handler.log("토스트 메시지 발생", allowed_key="TRANSITION_TOAST")
                    return PRE_PAYMENT_FAILURE

                # 잠시 대기 후 다시 확인
                time.sleep(0.3)

            # 페이지 전환이 안됐으면 실패로 처리
            self.log_handler.log("페이지 전환 실패", allowed_key="TRANSITION_FAILED")
            return PRE_PAYMENT_FAILURE

        except Exception as e:
            if "no such window" in str(e).lower():
                raise e

            # 오류 발생 시, 성공 페이지인지 마지막으로 확인
            try:
                if self._check_if_success_page():
                    self.log_handler.log("오류 발생했으나 성공 확인됨", allowed_key="ERROR_BUT_SUCCESS")
                    return SUCCESS
            except Exception as e:
                self.log_handler.log(f"성공 페이지 확인 중 추가 오류: {str(e)}", allowed_key="ERROR")

            # 처리되지 않은 예외 로깅
            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "보관판매 접수 신청")
            return PRE_PAYMENT_FAILURE

    def _navigate_to_inventory_page(self, product_id):
        """보관판매 페이지로 이동"""
        try:
            # 제품 ID 확인
            if not product_id:
                self.log_handler.log("제품 ID가 없습니다. 제품을 먼저 선택해주세요.", allowed_key="ERROR")
                return False

            self.log_handler.log(f"제품 ID: {product_id}로 이동 시도", allowed_key="DEBUG")

            # 현재 URL 확인
            current_url = self.browser.current_url
            self.log_handler.log(f"현재 URL: {current_url}", allowed_key="DEBUG")

            # 인벤토리 페이지로 직접 이동
            inventory_url = f"https://kream.co.kr/inventory/{product_id}"
            self.browser.get(inventory_url)

            # 페이지 로딩 대기
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
            )

            # 인벤토리 페이지 확인
            current_url = self.browser.current_url
            self.log_handler.log(f"페이지 로딩 후 URL: {current_url}", allowed_key="DEBUG")

            if 'inventory' in current_url and product_id in current_url:
                self.log_handler.log("인벤토리 페이지 확인됨", allowed_key="DEBUG")
                return True

            # 상품 페이지를 통해 인벤토리 페이지로 이동 시도
            self.log_handler.log("인벤토리 페이지가 아님, 상품 페이지로 이동 시도", allowed_key="DEBUG")
            product_url = f"https://kream.co.kr/products/{product_id}"
            self.browser.get(product_url)

            # 상품 페이지 로딩 대기
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail-price'))
            )

            # 보관판매 버튼 찾기 및 클릭
            self.log_handler.log("보관판매 버튼 찾기 시도", allowed_key="DEBUG")
            sell_buttons = self.wait_for_elements(By.CSS_SELECTOR, 'button.btn_action')
            self.log_handler.log(f"버튼 {len(sell_buttons)}개 발견", allowed_key="DEBUG")

            found_button = False
            for button in sell_buttons:
                try:
                    button_text = button.text
                    self.log_handler.log(f"버튼 텍스트: {button_text}", allowed_key="DEBUG")
                    if '보관판매' in button_text or 'INVENTORY SELL' in button_text.upper():
                        self.log_handler.log("보관판매 버튼 발견, 클릭 시도", allowed_key="DEBUG")
                        found_button = True
                        button.click()

                        # 인벤토리 페이지로 이동 확인
                        WebDriverWait(self.browser, 10).until(
                            lambda d: 'inventory' in d.current_url
                        )
                        self.log_handler.log("인벤토리 페이지로 이동 성공", allowed_key="DEBUG")
                        return True
                except Exception as e:
                    self.log_handler.log(f"버튼 처리 중 오류: {str(e)}", allowed_key="ERROR")
                    continue

            if not found_button:
                self.log_handler.log("보관판매 버튼을 찾을 수 없음", allowed_key="ERROR")

            self.log_handler.log("보관판매 페이지로 이동 실패", allowed_key="ERROR")
            return False

        except Exception as e:
            if "no such window" in str(e).lower():
                raise e

            self.log_handler.log("보관판매 페이지 이동 중 오류 발생", allowed_key="ERROR")
            return False

    def _enter_inventory_application_page(self):
        """보관판매 신청 페이지 진입"""
        try:
            # 서비스 에러 확인
            if self.toast_handler.check_service_error():
                return False

            # 보관판매 버튼 선택자
            button_selectors = [
                'a.btn_action',
                'button.btn_action',
                'div[class*="inventory_sell"] a[class*="btn"]',
                'button[class*="inventory_sell"]',
                'div[class*="inventory_info"] a[class*="btn"]',
                'div[class*="fixed_btn_box"] button'
            ]

            # 버튼 찾기
            sell_button = None
            for selector in button_selectors:
                try:
                    buttons = self.wait_for_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if not button.is_displayed():
                            continue

                        # 버튼 클래스 이름으로 판별
                        button_class = button.get_attribute('class')
                        if button_class and (
                                'inventory' in button_class.lower()
                                or 'sell' in button_class.lower()
                                or 'storage' in button_class.lower()):
                            sell_button = button
                            break
                except Exception as e:
                    self.log_handler.log(f"버튼 확인 중 오류: {str(e)}", allowed_key="ERROR")
                    continue

                if sell_button:
                    break

            # 버튼을 찾지 못했으면 실패
            if not sell_button:
                self.log_handler.log("보관판매 버튼을 찾을 수 없습니다", allowed_key="NO_SELL_BUTTON")
                return False

            # 버튼 클릭
            try:
                self.log_handler.log("보관판매 버튼 클릭", allowed_key="SELL_BUTTON_CLICKED")
                sell_button.click()
            except Exception as e:
                self.log_handler.log(f"보관판매 버튼 직접 클릭 실패, JS 클릭 시도: {str(e)}", allowed_key="ERROR")
                try:
                    self.browser.execute_script("arguments[0].click();", sell_button)
                except Exception as js_e:
                    self.log_handler.log(f"보관판매 버튼 JS 클릭 실패: {str(js_e)}", allowed_key="SELL_BUTTON_CLICK_FAIL")
                    return False

            # 페이지 전환 확인
            try:
                WebDriverWait(self.browser, 10).until(
                    lambda d: '/sale' in d.current_url or 'inventory_sell' in d.page_source
                )
                return True
            except Exception as e:
                self.log_handler.log(f"사이즈/수량 선택 페이지 전환 실패: {str(e)}", allowed_key="SALE_PAGE_TIMEOUT")
                return False

        except Exception as e:
            if "no such window" in str(e).lower():
                raise e

            self.log_handler.log("보관판매 신청 페이지 진입 중 오류 발생", allowed_key="ERROR")
            return False

    def _select_size_and_quantity(self, size, quantity):
        """사이즈 및 수량 선택"""
        try:
            # 서비스 에러 확인
            if self.toast_handler.check_service_error():
                return False

            # 사이즈 항목 로딩 대기
            try:
                WebDriverWait(self.browser, 10).until(
                    lambda d: len(d.find_elements(
                        By.CSS_SELECTOR,
                        'div.inventory_size_item, div.select_item, div.size_item'
                    )) > 0
                )
            except TimeoutException:
                self.log_handler.log("사이즈 선택 요소를 찾을 수 없습니다", allowed_key="NO_SIZE_ELEMENTS")
                return False

            # 사이즈 선택 및 수량 입력 성공 여부
            size_input_success = False

            # 1. 새로운 UI 패턴 (inventory_size_item) 시도
            size_items = self.wait_for_elements(By.CSS_SELECTOR, 'div.inventory_size_item')
            for item in size_items:
                try:
                    size_text = item.find_element(By.CSS_SELECTOR, 'div.size').text.strip()

                    # 사이즈 일치 확인
                    if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                        # 수량 입력 필드 찾기
                        quantity_input = item.find_element(By.CSS_SELECTOR, 'input.counter_quantity_input')

                        # 수량 입력
                        quantity_input.click()
                        time.sleep(0.2)
                        quantity_input.clear()
                        time.sleep(0.2)
                        quantity_input.send_keys(quantity)

                        self.log_handler.log(f"사이즈 {size_text}에 수량 {quantity} 입력됨", allowed_key="SIZE_QTY_INPUT")
                        size_input_success = True
                        break
                except Exception as e:
                    self.log_handler.log(f"사이즈/수량 입력 중 오류: {str(e)}", allowed_key="ERROR")
                    continue

            # 2. 이전 UI 방식 시도
            if not size_input_success:
                # div.select_item 패턴 시도
                size_elements = self.wait_for_elements(By.CSS_SELECTOR, 'div.select_item')
                for element in size_elements:
                    try:
                        size_text = element.find_element(By.CSS_SELECTOR, 'span.size').text.strip()
                        if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                            element.click()
                            self.log_handler.log(f"사이즈 {size_text} 선택됨", allowed_key="SIZE_SELECTED")
                            size_input_success = True
                            break
                    except Exception as e:
                        self.log_handler.log(f"사이즈 선택 중 오류: {str(e)}", allowed_key="ERROR")
                        continue

                # div.size_item 패턴 시도
                if not size_input_success:
                    size_elements = self.wait_for_elements(By.CSS_SELECTOR, 'div.size_item')
                    for element in size_elements:
                        try:
                            size_text = element.text.strip()
                            if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                                element.click()
                                self.log_handler.log(f"사이즈 {size_text} 선택됨", allowed_key="SIZE_SELECTED")
                                size_input_success = True
                                break
                        except Exception as e:
                            self.log_handler.log(f"사이즈 아이템 선택 중 오류: {str(e)}", allowed_key="ERROR")
                            continue

                # 수량 입력
                if size_input_success:
                    quantity_elements = self.wait_for_elements(
                        By.CSS_SELECTOR,
                        'input.input_amount, input[placeholder*="수량"], input[name*="quantity"]'
                    )

                    if quantity_elements:
                        try:
                            quantity_input = quantity_elements[0]
                            quantity_input.clear()
                            quantity_input.send_keys(quantity)
                            self.log_handler.log(f"수량 {quantity} 입력됨", allowed_key="QUANTITY_SET")
                        except Exception as e:
                            self.log_handler.log(f"수량 입력 실패: {str(e)}", allowed_key="QUANTITY_FAIL")
                            return False

            # 3. 플러스 버튼 클릭 방식 시도
            if not size_input_success:
                size_items = self.wait_for_elements(By.CSS_SELECTOR, 'div.inventory_size_item')
                for item in size_items:
                    try:
                        size_text = item.find_element(By.CSS_SELECTOR, 'div.size').text.strip()
                        if size_text == size or (size == "ONE SIZE" and size_text.upper() == "ONE SIZE"):
                            # 플러스 버튼 찾기 및 클릭
                            plus_button = item.find_element(By.CSS_SELECTOR, 'button:has(.ico-count-plus)')
                            for _ in range(int(quantity)):
                                plus_button.click()
                                time.sleep(0.1)

                            self.log_handler.log(f"사이즈 {size_text}에 플러스 버튼으로 수량 {quantity} 설정됨",
                                                 allowed_key="PLUS_BUTTON_CLICKED")
                            size_input_success = True
                            break
                    except Exception as e:
                        self.log_handler.log(f"플러스 버튼 클릭 중 오류: {str(e)}", allowed_key="ERROR")
                        continue

            # 사이즈/수량 입력 실패 시
            if not size_input_success:
                self.log_handler.log(f"사이즈 {size}에 수량을 입력할 수 없습니다", allowed_key="SIZE_QTY_FAIL")
                return False

            return True

        except Exception as e:
            if "no such window" in str(e).lower():
                raise e

            self.log_handler.log("사이즈/수량 선택 중 오류 발생", allowed_key="ERROR")
            return False

    def _proceed_with_sale(self):
        """신청 계속 버튼 클릭 및 모달 처리"""

        # 신청 계속 페이지 전환 확인
        try:
            WebDriverWait(self.browser, 10).until(
                lambda d: self._check_if_application_page() or self._check_if_success_page()
            )
            self.log_handler.log("신청 내역 또는 성공 페이지로 전환 확인됨", allowed_key="PAGE_TRANSITION_SUCCESS")
        except Exception as e:
            self.log_handler.log(f"페이지 전환 확인 실패: {str(e)}", allowed_key="PAGE_TRANSITION_FAIL")
            return False

        try:

            # 보증금 결제하기 버튼 찾기 시도
            try:
                # 먼저 complete_btn_box 내의 버튼 찾기 시도
                submit_button = self.wait_for_element(By.CSS_SELECTOR, 'div.complete_btn_box a.btn')
                if not submit_button.is_displayed():
                    submit_button = None
            except Exception:
                try:
                    # 이전 방식으로 시도
                    submit_button = self.wait_for_element(By.CSS_SELECTOR, 'div.order-agreements-button')
                    if not submit_button.is_displayed():
                        submit_button = None
                except Exception:
                    submit_button = None

            # 버튼을 찾지 못했으면 실패
            if not submit_button:
                self.log_handler.log("신청 계속 버튼을 찾을 수 없습니다", allowed_key="NO_BUTTON")
                return False

            # 버튼 클릭
            try:
                self.log_handler.log("신청 계속 버튼 클릭", allowed_key="BUTTON_CLICKED")
                submit_button.click()
                time.sleep(0.2)
            except Exception as e:
                self.log_handler.log(f"직접 클릭 실패, JS 클릭 시도: {str(e)}", allowed_key="ERROR")
                try:
                    self.browser.execute_script("arguments[0].click();", submit_button)
                    time.sleep(0.2)
                except Exception as js_e:
                    self.log_handler.log(f"신청 계속 버튼 클릭 실패: {str(js_e)}", allowed_key="CLICK_ERROR")
                    return False

            # 모달 처리
            try:
                # 모달 대기
                modal_container = WebDriverWait(self.browser, 5).until(
                    EC.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        'div.layer_container, div.modal_container'
                    ))
                )

                # 체크박스 처리
                checkboxes = modal_container.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                for checkbox in checkboxes:
                    if not checkbox.is_selected():
                        try:
                            # 레이블 클릭
                            label = checkbox.find_element(By.XPATH, './following-sibling::label | ../label')
                            label.click()
                            time.sleep(0.1)
                        except Exception as e:
                            self.log_handler.log(f"레이블 클릭 실패, 직접 클릭 시도: {str(e)}", allowed_key="ERROR")
                            try:
                                # 직접 클릭
                                checkbox.click()
                                time.sleep(0.1)
                            except Exception as click_e:
                                self.log_handler.log(f"직접 클릭 실패, JS 클릭 시도: {str(click_e)}", allowed_key="ERROR")
                                # JS 클릭
                                self.browser.execute_script("arguments[0].click();", checkbox)
                                time.sleep(0.1)

                # 모달 내 버튼 찾기
                modal_buttons = modal_container.find_elements(
                    By.CSS_SELECTOR,
                    'button.display_button, button.dark_filled, button.solid, button.btn, a.btn'
                )
                visible_buttons = [b for b in modal_buttons if b.is_displayed()]

                # 버튼 클릭 (5번째 버튼 또는 확인/동의 버튼)
                if len(visible_buttons) >= 5:
                    # 5번째 버튼 클릭
                    try:
                        visible_buttons[4].click()
                        time.sleep(0.2)
                    except Exception as e:
                        self.log_handler.log(f"5번째 버튼 직접 클릭 실패, JS 클릭 시도: {str(e)}", allowed_key="ERROR")
                        try:
                            self.browser.execute_script("arguments[0].click();", visible_buttons[4])
                            time.sleep(0.2)
                        except Exception as js_e:
                            self.log_handler.log(f"5번째 버튼 JS 클릭 실패: {str(js_e)}", allowed_key="ERROR")

                # 5번째 버튼이 없거나 클릭 실패한 경우, 확인/동의 버튼 찾아서 클릭
                try:
                    # 확인/동의 버튼을 클래스로 찾기
                    confirm_button = modal_container.find_element(
                        By.CSS_SELECTOR,
                        'button.btn_confirm, button.btn_agree, button.confirm-button, button.agree-button'
                    )
                    if confirm_button.is_displayed():
                        button = confirm_button
                    else:
                        button = None
                except Exception:
                    button = None

                # 클래스로 찾지 못한 경우 첫 번째 보이는 버튼 사용
                if not button and visible_buttons:
                    button = visible_buttons[0]

                if button:
                    try:
                        button.click()
                        time.sleep(0.2)
                        return True
                    except Exception as e:
                        self.log_handler.log(f"확인/동의 버튼 직접 클릭 실패, JS 클릭 시도: {str(e)}", allowed_key="ERROR")
                        try:
                            self.browser.execute_script("arguments[0].click();", button)
                            time.sleep(0.2)
                            return True
                        except Exception as js_e:
                            self.log_handler.log(f"확인/동의 버튼 JS 클릭 실패: {str(js_e)}", allowed_key="ERROR")

            except Exception as e:
                # 모달이 없을 수도 있으므로 무시
                self.log_handler.log(f"모달 처리 중 오류 (무시됨): {str(e)}", allowed_key="ERROR")

            return True

        except Exception as e:
            if "no such window" in str(e).lower():
                raise e

            # 오류 발생 시, 성공 페이지인지 확인
            try:
                if self._check_if_success_page():
                    self.log_handler.log("오류 발생했으나 성공 확인됨", allowed_key="ERROR_BUT_SUCCESS")
                    return SUCCESS
            except Exception as success_check_e:
                self.log_handler.log(f"성공 페이지 확인 중 추가 오류: {str(success_check_e)}", allowed_key="ERROR")

            MacroExceptions.handle_general_exception(self.browser, self.log_handler, e, "신청 진행")
            return False

    def _process_payment_page(self, current_url=None):
        """결제 페이지 처리"""
        try:
            # 먼저 성공 페이지인지 확인 (빠른 확인)
            if self._check_if_success_page():
                self.log_handler.log("결제 완료 페이지 감지됨", allowed_key="SUCCESS_REDIRECT")
                return SUCCESS

            # 결제 버튼 클릭 시도
            try:
                # 보증금 결제 버튼 찾기
                payment_buttons = self.wait_for_elements(
                    By.CSS_SELECTOR,
                    "button.display_button, button.btn_action, button.dark_filled, button.solid, button.btn_payment"
                )

                self.log_handler.log(f"결제 버튼 {len(payment_buttons)}개 발견", allowed_key="BUTTON_COUNT")

                # 5번째 버튼이 보증금 결제 버튼임
                if len(payment_buttons) >= 5:
                    try:
                        fifth_button = payment_buttons[4]  # 0-based index, so 5th button is index 4
                        if fifth_button.is_displayed():
                            self.log_handler.log("보증금 결제 버튼 클릭", allowed_key="PAYMENT_BUTTON_FIFTH")
                            fifth_button.click()
                            time.sleep(0.2)
                    except Exception as e:
                        try:
                            # JavaScript로 클릭 시도
                            self.browser.execute_script("arguments[0].click();", payment_buttons[4])
                            self.log_handler.log("보증금 결제 버튼 JS 클릭", allowed_key="PAYMENT_BUTTON_FIFTH_JS")
                            time.sleep(0.2)
                        except Exception as js_e:
                            self.log_handler.log(f"보증금 결제 버튼 클릭 실패: {str(js_e)}", allowed_key="PAYMENT_CLICK_ERROR")
                            return PAYMENT_FAILURE

                # 모달 창 처리
                try:
                    # 모달 레이어 대기 (짧은 타임아웃, 없을 수도 있음)
                    WebDriverWait(self.browser, 1).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            'div.layer_container, div.modal_container'
                        ))
                    )

                    # 모달 내에서 체크박스 처리
                    modal_containers = self.wait_for_elements(
                        By.CSS_SELECTOR,
                        'div.layer_container, div.modal_container'
                    )
                    for modal in modal_containers:
                        # 체크박스 처리
                        checkboxes = modal.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                        for checkbox in checkboxes:
                            if not checkbox.is_selected():
                                try:
                                    # 레이블 클릭이 더 안정적
                                    label = checkbox.find_element(By.XPATH, '../label')
                                    label.click()
                                    time.sleep(0.1)
                                except Exception as label_e:
                                    self.log_handler.log(f"레이블 클릭 실패, 직접 클릭 시도: {str(label_e)}", allowed_key="ERROR")
                                    try:
                                        # 직접 클릭
                                        checkbox.click()
                                        time.sleep(0.1)
                                    except Exception as click_e:
                                        self.log_handler.log(f"직접 클릭 실패, JS 클릭 시도: {str(click_e)}", allowed_key="ERROR")
                                        # JS로 클릭
                                        self.browser.execute_script("arguments[0].click();", checkbox)
                                        time.sleep(0.1)

                    # 모달 내 버튼 찾기 및 클릭
                    for modal in modal_containers:
                        buttons = modal.find_elements(
                            By.CSS_SELECTOR,
                            'button.display_button, button.dark_filled, button.solid, button.btn'
                        )

                        for button in buttons:
                            if not button.is_displayed():
                                continue

                            # 결제 관련 버튼 확인 (클래스 이름으로 판별)
                            button_class = button.get_attribute('class')
                            if button_class and (
                                    'confirm' in button_class.lower() or
                                    'agree' in button_class.lower() or
                                    'payment' in button_class.lower() or
                                    'btn_confirm' in button_class.lower() or
                                    'btn_agree' in button_class.lower() or
                                    'btn_payment' in button_class.lower()
                            ):
                                try:
                                    self.log_handler.log("모달 내 버튼 클릭", allowed_key="MODAL_BUTTON_CLICK")
                                    button.click()
                                    time.sleep(0.2)
                                    break
                                except Exception as e:
                                    self.log_handler.log(f"모달 버튼 직접 클릭 실패, JS 클릭 시도: {str(e)}", allowed_key="ERROR")
                                    try:
                                        self.browser.execute_script("arguments[0].click();", button)
                                        time.sleep(0.2)
                                        break
                                    except Exception as js_e:
                                        self.log_handler.log(f"모달 버튼 JS 클릭 실패: {str(js_e)}", allowed_key="ERROR")
                                        continue

                except Exception as e:
                    # 모달이 없을 수도 있으므로 무시
                    self.log_handler.log(f"모달 처리 중 오류 (무시됨): {str(e)}", allowed_key="ERROR")

                # 최종 성공 확인
                time.sleep(0.5)  # 짧은 대기 후 성공 확인
                if self._check_if_success_page():
                    self.log_handler.log("결제 완료 확인됨", allowed_key="SUCCESS_AFTER_PAYMENT")
                    return SUCCESS

            except Exception as payment_click_error:
                self.log_handler.log("결제 버튼 처리 중 오류", allowed_key="PAYMENT_CLICK_ERROR")
                return PAYMENT_FAILURE

            return PAYMENT_FAILURE  # 기본적으로 실패 반환

        except Exception as e:
            self.log_handler.log("결제 처리 중 오류", allowed_key="PAYMENT_PROCESS_ERROR")
            return PAYMENT_FAILURE

    def stop(self):
        self._running = False
        self.macro_status_changed.emit(False)
        self.log_handler.log("매크로 구동 정지 요청됨", allowed_key="STOP")
        return True

    def start_macro(self, product_id: str, size: str, quantity: str, email: str = None, password: str = None):
        """호환성을 위한 start() 메소드 별칭"""
        return self.start(product_id, size, quantity, email, password)

    def _check_if_success_page(self):
        """성공 페이지인지 확인"""
        try:
            # 1. URL 확인 (가장 신뢰할 수 있는 방법)
            current_url = self.browser.current_url
            if 'inventory/detail' in current_url or 'order/complete' in current_url:
                self.log_handler.log("성공 URL 확인됨", allowed_key="SUCCESS_URL_HELPER")
                return True

            # 2. 완료 텍스트 확인
            completion_texts = ["보관 신청이 완료되었습니다", "신청이 완료되었습니다", "보관판매 완료", "보관 신청 완료"]
            for text in completion_texts:
                elements = self.wait_for_elements(By.XPATH, f"//p[contains(text(), '{text}')]")
                if elements:
                    self.log_handler.log(f"완료 텍스트 확인: '{text}'", allowed_key="SUCCESS_TEXT_HELPER")
                    return True

            # 3. 페이지 소스에서 성공 키워드 확인
            page_source = self.browser.page_source.lower()
            if "보관 신청이 완료되었습니다." in page_source:
                self.log_handler.log("성공 페이지 내용 감지됨", allowed_key="SUCCESS_CONTENT_HELPER")
                return True

        except Exception as e:
            self.log_handler.log(f"성공 페이지 확인 중 오류: {str(e)}", allowed_key="ERROR")
            return False

        # 위 조건 중 어느 것도 일치하지 않으면 성공 페이지가 아님
        return False

    def _check_if_application_page(self):
        """현재 페이지가 신청 내역 페이지인지 확인"""
        try:
            title_elements = WebDriverWait(self.browser, 1).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h2.title'))
            )
            for element in title_elements:
                if "신청 내역" in element.text:
                    self.log_handler.log("신청 내역 페이지 확인됨", allowed_key="APPLICATION_PAGE_DETECTED")
                    return True
        except Exception as e:
            self.log_handler.log(f"신청 내역 페이지 확인 중 오류: {str(e)}", allowed_key="ERROR")
        return False

    def check_page_indicators(self, product_id=None):
        """
        현재 페이지의 상태를 확인하고 페이지 인디케이터를 반환

        Returns:
            dict: 페이지 상태 정보를 담은 딕셔너리
                - is_success_page: 성공 페이지 여부
                - is_application_page: 신청 내역 페이지 여부
                - is_inventory_page: 인벤토리 페이지 여부
                - current_url: 현재 URL
        """
        try:
            current_url = self.browser.current_url
            is_success_page = self._check_if_success_page()
            is_application_page = self._check_if_application_page()
            is_inventory_page = False

            # product_id가 제공된 경우에만 인벤토리 페이지 확인
            if product_id:
                is_inventory_page = current_url.startswith(f'https://kream.co.kr/inventory/{product_id}')

            return {
                "is_success_page": is_success_page,
                "is_application_page": is_application_page,
                "is_inventory_page": is_inventory_page,
                "current_url": current_url
            }
        except Exception as e:
            self.log_handler.log(f"페이지 인디케이터 확인 중 오류: {str(e)}", allowed_key="ERROR")
            return {
                "is_success_page": False,
                "is_application_page": False,
                "is_inventory_page": False,
                "current_url": ""
            }
