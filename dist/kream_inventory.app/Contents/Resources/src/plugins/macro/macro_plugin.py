"""크림 인벤토리 매크로 플러그인입니다.

이 모듈은 KREAM 웹사이트에서 인벤토리 작업을 자동화하는 매크로 플러그인을 포함합니다.
매크로 작업을 별도의 스레드에서 처리하는 MacroWorker 클래스를 포함합니다.
"""

from __future__ import annotations

import time
from configparser import ConfigParser
from typing import TYPE_CHECKING, List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.core.plugin_base import PluginBase
from src.plugins.login.login_manager import LoginManager

from .macro_toast_handler import MacroToastHandler
from .utils import (
    handle_inner_label_popup,
    handle_payment_process,
    is_url_matching,
    submit_inventory_form,
    wait_for_element,
    wait_for_elements,
)

if TYPE_CHECKING:
    from src.core.browser import BrowserManager
    from src.core.plugin_manager import PluginManager
    from src.ui.main_window import MainWindow


class MacroWorker(QObject):
    """매크로 작업을 별도의 스레드에서 처리하는 클래스입니다."""

    log_message = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self: "MacroWorker",
        browser_driver: WebDriver,
        email: str,
        password: str,
        size_index: int,
        qty: int,
        click_term: int,
        size_display_name: str,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initializes the MacroWorker."""
        super().__init__(parent)
        self.browser = browser_driver
        self.email = email
        self.password = password
        self.size_idx = size_index
        self.qty = qty
        self.click_term = click_term
        self.size_display_name = size_display_name
        self.is_running = True
        self.login_manager = LoginManager(browser=self.browser)
        self._final_log_emitted = False

        # MacroToastHandler 초기화 및 시그널 연결
        self.toast_handler = MacroToastHandler(
            browser=self.browser, click_term=self.click_term
        )
        self.toast_handler.log_message_signal.connect(self.log_message)

        # 로거 초기화 부분 비활성화
        self.logger = None

    def run(self: "MacroWorker") -> None:
        """매크로 실행 루프입니다."""
        self.log_message.emit(f"매크로 시작: {self.size_display_name}, {self.qty}개")

        self.is_running = True
        _payment_success_flag = False
        count = 0

        while self.is_running:
            try:
                current_url = self.browser.current_url

                # 루프 시작 시 토스트 메시지 확인 (예: 이전 작업의 결과로 나타난 토스트)
                if self.toast_handler.handle_toast():
                    # 토스트 핸들러가 True를 반환하면 페이지 상태가 변경되었을 수 있으므로 즉시 다음 루프로
                    continue

                if is_url_matching(self.browser, "login"):
                    self.log_message.emit("로그인 페이지 감지. 재로그인합니다.")

                    if (
                        self.email == "current_session"
                        and self.password == "current_session"
                    ):
                        self.browser.refresh()
                        time.sleep(1)  # 2초에서 1초로 감소
                        continue

                    if not self.login_manager.relogin(self.email, self.password):
                        self.log_message.emit("재로그인 실패. 매크로를 중단합니다.")
                        self.stop()
                        break
                    continue

                # 신청 내역 페이지 직접 결제 시도
                try:
                    payment_page_title_element = wait_for_element(
                        self.browser,
                        By.CSS_SELECTOR,
                        "span.title_txt",
                        timeout=1,  # 2초에서 1초로 감소
                    )
                    if (
                        payment_page_title_element
                        and payment_page_title_element.text.strip() == "신청 내역"
                    ):
                        self.log_message.emit(
                            "신청 내역 페이지입니다. 결제를 시도합니다."
                        )
                        payment_successful = handle_payment_process(
                            self.browser,
                            self.logger,
                        )
                        if payment_successful:
                            self.log_message.emit("결제 성공!")
                            _payment_success_flag = True
                            self.stop()
                            break
                        elif payment_successful is False:
                            self.log_message.emit(
                                "결제 실패. 새로고침 후 재시도합니다."
                            )
                            if (
                                self.toast_handler.handle_toast()
                            ):  # 결제 실패 후 토스트 확인
                                continue
                            self.browser.refresh()
                            time.sleep(1)  # 더 짧은 대기 시간
                            continue
                        else:  # None
                            if (
                                self.toast_handler.handle_toast()
                            ):  # 결제 프로세스 None 후 토스트 확인
                                continue
                            self.browser.refresh()
                            time.sleep(1)  # 더 짧은 대기 시간
                            continue
                except TimeoutException:
                    pass
                except Exception:
                    pass

                current_url = self.browser.current_url  # URL 다시 가져오기

                # 인벤토리 페이지에서 폼 제출 로직
                if (
                    "inventory" in current_url
                    and not title_text_check(self.browser)
                    == "신청 내역"  # 신청내역 페이지가 아닐 때만
                ):
                    # 즉시 폼 제출 시도
                    if submit_inventory_form(
                        self.browser, self.size_idx, self.qty, None
                    ):
                        # 폼 제출 후 토스트 확인 (최소한의 대기)
                        time.sleep(0.1)  # 0.3초에서 0.1초로 최소화
                        if self.toast_handler.handle_toast():
                            continue  # 여기가 중요: 토스트 처리 후 바로 다음 루프로

                        count += 1
                        self.log_message.emit(
                            f"[{count}회차] 보관 신청 완료. 결제 페이지로 이동합니다."
                        )

                        time.sleep(0.1)  # 결제 페이지 전환 대기 시간 최소화

                        payment_successful_after_submit = handle_payment_process(
                            self.browser, None
                        )
                        if payment_successful_after_submit:
                            self.log_message.emit("결제 성공!")
                            _payment_success_flag = True
                            self.stop()
                            break
                        elif payment_successful_after_submit is False:
                            self.log_message.emit(
                                "결제 실패 (폼 제출 후). 새로고침 후 재시도합니다."
                            )
                            if self.toast_handler.handle_toast():
                                continue
                            self.browser.refresh()
                            time.sleep(1)  # 더 짧은 대기 시간
                            continue
                        else:  # None
                            if self.toast_handler.handle_toast():
                                continue
                            self.browser.refresh()
                            time.sleep(1)  # 더 짧은 대기 시간
                            continue
                    else:  # submit_inventory_form 실패
                        self.log_message.emit(
                            "보관 신청 실패. 새로고침 후 재시도합니다."
                        )
                        self.browser.refresh()
                        time.sleep(1)  # 더 짧은 대기 시간
                        continue

                handle_inner_label_popup(self.browser, self.logger)  # 내부 팝업 처리

                current_url_final_check = self.browser.current_url
                if not any(
                    pattern in current_url_final_check
                    for pattern in ["/login", "/inventory/"]
                ):
                    # title_text_check는 이미 위에서 수행했으므로, 여기서는 URL 기반으로만 판단
                    # 혹은 더욱 명확한 "알 수 없는 상태" 정의 필요
                    if title_text_check(self.browser) != "신청 내역":  # 한번 더 확인
                        self.log_message.emit(
                            f"알 수 없는 페이지({current_url_final_check}). 이전 페이지로 이동 후 재시도합니다."
                        )
                        self.browser.back()
                        time.sleep(1)  # 더 짧은 대기 시간
                        # 이전 페이지로 돌아간 후에는 토스트를 다시 확인하고 루프를 처음부터 시작
                        if self.toast_handler.handle_toast():
                            continue
                        continue

                # 루프 마지막에 일반적인 토스트 메시지 확인 (최후의 방어선)
                if self.toast_handler.handle_toast():
                    continue

            except TimeoutException:
                self.log_message.emit("오류 발생 (타임아웃). 새로고침 후 재시도합니다.")
                self.browser.refresh()
                count = 0
                time.sleep(1)  # 더 짧은 대기 시간
            except Exception:
                self.log_message.emit(
                    "예상치 못한 오류 발생. 새로고침 후 재시도합니다."
                )
                self.browser.refresh()
                count = 0
                time.sleep(1)  # 더 짧은 대기 시간

        # 종료 메시지 표시
        if not self._final_log_emitted:
            if _payment_success_flag:
                self.log_message.emit("매크로 종료: 결제 성공")
            else:
                self.log_message.emit("매크로 종료: 사용자에 의해 중단되었습니다.")
            self._final_log_emitted = True

        self.finished.emit()

    def stop(self: "MacroWorker") -> None:
        """매크로 실행을 중지합니다."""
        if not self.is_running:
            return

        # 로그 남김
        self.log_message.emit("매크로 중지 요청됨.")

        # 실행 상태 업데이트
        self.is_running = False

        # 매크로가 종료될 때 토스트 메시지 처리가 필요할 수 있음
        try:
            handle_inner_label_popup(self.browser, None)
        except Exception:
            pass


class MacroPlugin(PluginBase):
    """Plugin for automating KREAM inventory tasks."""

    log_signal = pyqtSignal(str)
    macro_status_signal = pyqtSignal(bool)

    def __init__(
        self: "MacroPlugin",
        name: str,
        browser: "BrowserManager",
        config: "ConfigParser",
        plugin_manager: Optional["PluginManager"] = None,
    ) -> None:
        """Initializes the MacroPlugin."""
        super().__init__(
            name=name,
            browser=browser,
            config=config,
            plugin_manager=plugin_manager,
        )
        self.description = "보관판매 매크로 기능"
        self.worker_thread: Optional[QThread] = None
        self.macro_worker: Optional[MacroWorker] = None
        self.main_window: Optional["MainWindow"] = None

        self.original_tab_handle: Optional[str] = None
        self.macro_tab_handle: Optional[str] = None
        self.new_tab_opened_by_macro: bool = False
        # _log_signal_connected 및 관련 시그널 연결/해제 로직 완전히 제거

        if self.plugin_manager and self.plugin_manager.main_controller:
            if hasattr(self.plugin_manager.main_controller, "main_window"):
                self.main_window = self.plugin_manager.main_controller.main_window
                # MainController에서 시그널 연결을 담당하므로 여기서는 삭제

    def _open_new_tab_and_go_to_url(
        self: "MacroPlugin", url: str
    ) -> Optional[WebDriver]:
        """Opens a new browser tab and navigates to the given URL."""
        driver = self.browser.get_driver()
        if not driver:
            self.main_controller_log("WebDriver가 초기화되지 않았습니다.")
            return None

        self.original_tab_handle = driver.current_window_handle
        existing_handles = set(driver.window_handles)

        driver.execute_script("window.open('', '_blank');")

        # 새 탭 핸들 찾기
        new_handle_found = None
        for handle in driver.window_handles:
            if handle not in existing_handles:
                new_handle_found = handle
                break

        if new_handle_found:
            driver.switch_to.window(new_handle_found)
            self.macro_tab_handle = new_handle_found
            self.new_tab_opened_by_macro = True  # 새 탭을 열었음을 표시
            if url:
                driver.get(url)
            return driver
        else:
            self.main_controller_log(
                "새 탭을 열지 못했습니다. 팝업 차단 등을 확인해주세요."
            )
            # 원래 탭으로 돌아가기
            if (
                self.original_tab_handle
                and self.original_tab_handle in driver.window_handles
            ):
                driver.switch_to.window(self.original_tab_handle)
            return None

    def start_macro_dialog(self: "MacroPlugin") -> None:
        """Shows a dialog to configure and start the macro."""
        driver = self.browser.get_driver()
        if not driver:
            self.log_signal.emit(
                "브라우저가 준비되지 않았습니다. 먼저 브라우저를 실행해주세요."
            )
            return

        product_id = self._get_product_id_from_ui()
        if not product_id:
            self.log_signal.emit("상품 ID를 입력해주세요.")
            return

        current_url = driver.current_url
        self.original_tab_handle = driver.current_window_handle

        if "inventory" not in current_url or product_id not in current_url:
            target_url = f"https://kream.co.kr/inventory/{product_id}/"
            if not self._open_new_tab_and_go_to_url(target_url):
                self.main_controller_log(
                    "상품 인벤토리 페이지로 이동하는데 실패했습니다."
                )
                return
        else:
            self.macro_tab_handle = driver.current_window_handle
            self.new_tab_opened_by_macro = False

        try:
            size_elements = wait_for_elements(
                driver,
                By.CSS_SELECTOR,
                "div.inventory_size_item",
                timeout=10,
            )
            size_options = [
                elem.text.strip() for elem in size_elements if elem.text.strip()
            ]
            if not size_options:
                self.log_signal.emit(
                    "현재 페이지에서 사이즈 옵션을 찾을 수 없습니다. 상품 상세 페이지로 이동해주세요."
                )
                self._close_macro_tab_if_opened()
                return
        except TimeoutException:
            self.log_signal.emit("사이즈 옵션을 가져오는 데 실패했습니다.")
            self._close_macro_tab_if_opened()
            return
        except Exception as e:
            self.log_signal.emit(f"사이즈 옵션 가져오기 오류: {str(e)}")
            self._close_macro_tab_if_opened()
            return

        self._show_settings_dialog_and_start(size_options, product_id, driver)

    def _get_product_id_from_ui(self: "MacroPlugin") -> Optional[str]:
        """UI에서 현재 선택된 제품 ID를 가져옵니다."""
        if self.plugin_manager and self.plugin_manager.main_controller:
            return self.plugin_manager.main_controller.current_product_id
        return None

    def _show_settings_dialog_and_start(
        self: "MacroPlugin", size_options: List[str], product_id: str, driver: WebDriver
    ) -> None:
        """Shows the settings dialog and starts the macro worker if confirmed."""
        if not driver:
            self.log_signal.emit("브라우저 드라이버가 유효하지 않습니다.")
            self._close_macro_tab_if_opened()
            return

        # 이미 매크로 워커가 실행 중인지 확인
        if self.worker_thread and self.worker_thread.isRunning():
            self.log_signal.emit("매크로가 이미 실행 중입니다. 중복 실행을 방지합니다.")
            return

        login_manager = LoginManager(browser=driver)
        if login_manager.is_logged_in():
            email = "current_session"
            password = "current_session"
        else:
            email = self.config.get("KREAM", "email", fallback="")
            password = self.config.get("KREAM", "password", fallback="")

            if not email or not password:
                self.log_signal.emit("설정에서 KREAM 이메일과 비밀번호를 입력해주세요.")
                self._close_macro_tab_if_opened()
                return

        if not self.main_window:
            self.log_signal.emit(
                "메인 윈도우를 찾을 수 없어 매크로 설정을 표시할 수 없습니다."
            )
            self._close_macro_tab_if_opened()
            return

        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("매크로 설정")
        layout = QVBoxLayout(dialog)

        size_label = QLabel("사이즈:")
        layout.addWidget(size_label)
        size_combo = QComboBox()
        size_combo.addItems(size_options)
        layout.addWidget(size_combo)

        qty_label = QLabel("수량:")
        layout.addWidget(qty_label)
        qty_combo = QComboBox()
        for i in range(1, 100):  # 1부터 99까지
            qty_combo.addItem(str(i))
        layout.addWidget(qty_combo)

        click_term_label = QLabel("보관판매 시도 주기 (초):")
        layout.addWidget(click_term_label)

        # config.ini에서 min_interval과 max_interval 값을 불러옴
        min_interval_fallback = 8
        max_interval_fallback = 18
        min_interval = self.config.getint(
            "Macro", "min_interval", fallback=min_interval_fallback
        )
        max_interval = self.config.getint(
            "Macro", "max_interval", fallback=max_interval_fallback
        )

        # 범위 유효성 검사
        if min_interval > max_interval:
            min_interval, max_interval = min_interval_fallback, max_interval_fallback

        click_term_combo = QComboBox()
        for i in range(min_interval, max_interval + 1):
            click_term_combo.addItem(str(i))

        # 기본값 설정 (config에서 기본 주기 값)
        default_interval = self.config.getint(
            "Macro", "default_interval", fallback=min_interval
        )
        # 기본값이 범위 내에 있는지 확인
        if min_interval <= default_interval <= max_interval:
            click_term_combo.setCurrentText(str(default_interval))

        layout.addWidget(click_term_combo)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_size_text = size_combo.currentText()
            selected_size_index = size_combo.currentIndex() + 1
            selected_qty = int(qty_combo.currentText())
            selected_click_term = int(click_term_combo.currentText())

            self.macro_worker = MacroWorker(
                browser_driver=driver,
                email=email,
                password=password,
                size_index=selected_size_index,
                qty=selected_qty,
                click_term=selected_click_term,
                size_display_name=selected_size_text,
                parent=None,
            )
            self.worker_thread = QThread(parent=self)
            self.macro_worker.moveToThread(self.worker_thread)

            # MacroWorker의 log_message 시그널을 MacroPlugin의 log_signal에 연결
            # 이 연결은 UI로 로그를 전달하는 주 경로
            try:
                self.macro_worker.log_message.disconnect(self.log_signal.emit)
            except TypeError:
                pass  # 연결되지 않은 경우
            self.macro_worker.log_message.connect(self.log_signal.emit)

            self.macro_worker.finished.connect(self._on_macro_finished)
            self.worker_thread.started.connect(self.macro_worker.run)
            self.worker_thread.start()
            self.macro_status_signal.emit(True)
            # 시작 로그는 Worker.run()에서 emit

        else:
            self._close_macro_tab_if_opened(driver)  # driver 전달

    def _close_macro_tab_if_opened(
        self: "MacroPlugin", driver_arg: Optional[WebDriver] = None
    ) -> None:
        """매크로가 새 탭을 열었다면 해당 탭을 닫고, 원래 탭으로 돌아갑니다."""
        driver = driver_arg if driver_arg else self.browser.get_driver()

        if not driver:
            if self.new_tab_opened_by_macro:
                self.main_controller_log(
                    "정보: 매크로 탭을 닫으려 했으나, WebDriver가 유효하지 않습니다."
                )
            self.new_tab_opened_by_macro = False
            self.macro_tab_handle = None
            return

        if not self.new_tab_opened_by_macro or not self.macro_tab_handle:
            self.new_tab_opened_by_macro = False
            self.macro_tab_handle = None
            return

        original_macro_tab_handle = self.macro_tab_handle

        try:
            current_handles_before_close = driver.window_handles
            if original_macro_tab_handle in current_handles_before_close:
                if driver.current_window_handle == original_macro_tab_handle:
                    driver.close()
                else:
                    # 탭 전환 전에 해당 탭이 아직 열려 있는지 다시 확인
                    if (
                        original_macro_tab_handle in driver.window_handles
                    ):  # 이 확인 추가
                        driver.switch_to.window(original_macro_tab_handle)
                        driver.close()
                    else:
                        # 전환하려던 탭이 그 사이에 닫힌 경우
                        self.main_controller_log(
                            f"정보: 매크로 탭({original_macro_tab_handle})이 전환 직전에 닫혔습니다."
                        )
                        return  # 탭 전환 및 닫기 로직 종료
            else:
                self.main_controller_log(
                    f"정보: 매크로 탭({original_macro_tab_handle})은 이미 닫혀있었습니다."
                )
        except Exception as e:
            self.main_controller_log(
                f"오류: 매크로 탭({original_macro_tab_handle}) 닫기 실패 - {type(e).__name__}: {e}"
            )
        finally:
            self.macro_tab_handle = None
            self.new_tab_opened_by_macro = False

        try:
            # 드라이버 세션 유효성 검사 (window_handles 호출 자체가 예외를 던질 수 있음)
            try:  # 이 try-except는 window_handles 접근 자체의 오류를 잡기 위함
                remaining_handles = driver.window_handles
            except Exception as e_get_handles:  # 예: invalid session id
                self.main_controller_log(
                    f"정보: 브라우저 세션이 유효하지 않아 탭 전환을 스킵합니다 - {type(e_get_handles).__name__}"
                )
                return

            if not remaining_handles:
                self.main_controller_log("정보: 모든 브라우저 탭이 닫혔습니다.")
                return

            target_switch_handle = None
            if (
                self.original_tab_handle
                and self.original_tab_handle in remaining_handles
            ):
                target_switch_handle = self.original_tab_handle
            elif remaining_handles:
                target_switch_handle = remaining_handles[0]

            if target_switch_handle:  # 전환할 대상 핸들이 있다면
                # 현재 활성 탭과 전환 대상이 다른 경우에만 switch 시도
                try:  # current_window_handle 접근 시 예외 발생 가능성 고려
                    current_active_handle = driver.current_window_handle
                    needs_switch = current_active_handle != target_switch_handle
                except (
                    Exception
                ):  # current_window_handle 접근 실패 시 (예: 팝업만 남은 상태 등)
                    needs_switch = True  # 일단 전환 시도

                if needs_switch:
                    driver.switch_to.window(target_switch_handle)

        except Exception as e_switch:
            # 여기서 발생하는 예외는 주로 switch_to.window 실패
            if (
                "no such window" not in str(e_switch).lower()
                and "target window already closed" not in str(e_switch).lower()
                and "invalid session id" not in str(e_switch).lower()
            ):
                self.main_controller_log(
                    f"오류: 탭 전환 중 예기치 않은 문제 발생 후 - {type(e_switch).__name__}: {e_switch}"
                )

    def _on_macro_finished(self: "MacroPlugin") -> None:
        """매크로 종료 시 탭 닫기 및 스레드 종료 처리 로직입니다."""
        driver = self.browser.get_driver()
        self._close_macro_tab_if_opened(driver)

        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.macro_worker = None
        self.macro_status_signal.emit(False)

    def stop_macro(self: "MacroPlugin") -> None:
        """매크로를 중지합니다."""
        if self.macro_worker:
            self.macro_worker.stop()

        driver = self.browser.get_driver()
        self._close_macro_tab_if_opened(driver)

        if self.worker_thread:
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                pass
            self.worker_thread = None
            self.macro_worker = None

        self.macro_status_signal.emit(False)

    def main_controller_log(self: "MacroPlugin", message: str) -> None:
        """메인 컨트롤러를 통해 로그 메시지를 UI로 전송합니다."""
        self.log_signal.emit(message)


def title_text_check(browser: WebDriver) -> str | None:
    """현재 페이지의 제목 텍스트('span.title_txt')를 확인합니다.

    Args:
        browser: WebDriver 인스턴스입니다.

    Returns:
        제목 텍스트 문자열 또는 None을 반환합니다.
    """
    try:
        el = wait_for_element(browser, By.CSS_SELECTOR, "span.title_txt", timeout=1)
        return el.text.strip() if el else None
    except TimeoutException:
        return None
