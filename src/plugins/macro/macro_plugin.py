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
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from src.core.logger_setup import setup_logger
from src.core.plugin_base import PluginBase
from src.core.selenium_helpers import (
    is_url_matching,
    wait_for_element,
    wait_for_elements,
)
from src.plugins.login.login_manager import LoginManager
from src.plugins.macro.macro_actions import (
    handle_inner_label_popup,
    handle_payment_process,
    submit_inventory_form,
)
from src.plugins.macro.macro_toast_handler import MacroToastHandler

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
        self._payment_success_flag = False
        self._count = 0

        self.logger = setup_logger(f"{__name__}.MacroWorker")

        self.toast_handler = MacroToastHandler(
            browser=self.browser, click_term=self.click_term
        )
        self.toast_handler.log_message_signal.connect(self.log_message)

    def _handle_toast(self) -> bool:
        """토스트 메시지 처리 후 루프를 즉시 재시작할지 여부를 반환합니다."""
        return self.toast_handler.handle_toast()

    def _handle_login(self) -> bool:
        """로그인 페이지 감지 및 재로그인 처리 후 루프 재시작 여부 반환."""
        if is_url_matching(self.browser, "login"):
            self.log_message.emit("로그인 페이지 감지. 재로그인합니다.")
            if self.email == "current_session" and self.password == "current_session":
                self.log_message.emit(
                    "오류: 로그인된 세션으로 간주되었으나 로그인 페이지입니다. 새로고침합니다."
                )
                self.browser.refresh()
                time.sleep(2)
                return True
            if not self.login_manager.login(self.email, self.password):
                self.log_message.emit("로그인 실패. 매크로를 중단합니다.")
                self.stop()
                return False
            self.log_message.emit("로그인 성공. 매크로 작업을 계속합니다.")
            return True
        return False

    def _handle_payment_page(self) -> bool:
        """결제 페이지 감지 및 처리 후 루프 재시작 여부 반환."""
        try:
            title_element = wait_for_element(
                self.browser, By.CSS_SELECTOR, "span.title_txt", timeout=1
            )
            if title_element and title_element.text.strip() == "신청 내역":
                self.log_message.emit("신청 내역 페이지입니다. 결제를 시도합니다.")
                result = handle_payment_process(self.browser, self.logger)
                if result:
                    self.log_message.emit("결제 성공!")
                    self._payment_success_flag = True
                    self.stop()
                    return False
                if result is False:
                    self.log_message.emit("결제 실패. 새로고침 후 재시도합니다.")
                    self.browser.refresh()
                    return True
                self.browser.refresh()
                return True
        except TimeoutException:
            pass
        except Exception:
            pass
        return False

    def _handle_inventory_submit(self) -> bool:
        """인벤토리 폼 제출 및 처리 후 루프 재시작 여부 반환."""
        if (
            "inventory" in self.browser.current_url
            and title_text_check(self.browser) != "신청 내역"
        ):
            old_form = None
            try:
                old_form = wait_for_element(
                    self.browser, By.CSS_SELECTOR, "div.inventory_size_list", timeout=5
                )
            except TimeoutException:
                pass
            if submit_inventory_form(
                self.browser, self.size_idx, self.qty, self.logger
            ):
                self._count = getattr(self, "_count", 0) + 1
                self.log_message.emit(f"{self._count}회 시도")
                if self._handle_toast():
                    return True
                if old_form:
                    try:
                        WebDriverWait(self.browser, self.click_term).until(
                            ec.staleness_of(old_form)
                        )
                    except TimeoutException:
                        self.logger.warning("페이지 전환 대기 타임아웃 – 재시도")
                result = handle_payment_process(self.browser, self.logger)
                if result:
                    self.log_message.emit("결제 성공!")
                    self._payment_success_flag = True
                    self.stop()
                    return False
                if result is False:
                    self.log_message.emit(
                        "결제 실패 (폼 제출 후). 새로고침 후 재시도합니다."
                    )
                    self.browser.refresh()
                    return True
                self.browser.refresh()
                return True
            self.log_message.emit("보관 신청 실패. 새로고침 후 재시도합니다.")
            self.browser.refresh()
            return True
        return False

    def _handle_inner_label(self) -> None:
        """안쪽 라벨 팝업 처리."""
        handle_inner_label_popup(self.browser, self.logger)

    def run(self: "MacroWorker") -> None:
        """매크로 실행 루프입니다."""
        self.log_message.emit(f"매크로 시작: {self.size_display_name}, {self.qty}개")
        self.is_running = True

        while self.is_running:
            try:
                if self._handle_toast():
                    continue

                if self._handle_login():
                    continue

                if self._handle_payment_page():
                    continue

                if self._handle_inventory_submit():
                    continue

                self._handle_inner_label()

            except TimeoutException:
                self.log_message.emit("오류 발생 (타임아웃). 새로고침 후 재시도합니다.")
                self.browser.refresh()
                self._count = 0
            except Exception:
                self.log_message.emit(
                    "예상치 못한 오류 발생. 새로고침 후 재시도합니다."
                )
                self.browser.refresh()
                self._count = 0

        if not self._final_log_emitted:
            if self._payment_success_flag:
                self.log_message.emit("매크로 종료: 결제 성공")
            else:
                self.log_message.emit("매크로 종료: 사용자에 의해 중단되었습니다.")
            self._final_log_emitted = True
        self.finished.emit()

    def stop(self: "MacroWorker") -> None:
        """매크로 실행을 중지합니다."""
        if not self.is_running:
            return
        self.is_running = False
        try:
            handle_inner_label_popup(self.browser, self.logger)
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

        new_handle_found = None
        for handle in driver.window_handles:
            if handle not in existing_handles:
                new_handle_found = handle
                break

        if new_handle_found:
            driver.switch_to.window(new_handle_found)
            self.macro_tab_handle = new_handle_found
            self.new_tab_opened_by_macro = True
            if url:
                driver.get(url)
            return driver
        else:
            self.main_controller_log(
                "새 탭을 열지 못했습니다. 팝업 차단 등을 확인해주세요."
            )
            if (
                self.original_tab_handle
                and self.original_tab_handle in driver.window_handles
            ):
                driver.switch_to.window(self.original_tab_handle)
            return None

    def start_macro_dialog(self: "MacroPlugin") -> None:
        """Shows a dialog to configure and start the macro."""
        if self.plugin_manager and self.plugin_manager.main_controller:
            self.main_window = self.plugin_manager.main_controller.main_window
            if not self.main_window:
                self.log_signal.emit("메인 윈도우 참조를 찾을 수 없습니다.")

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

        if self.worker_thread and self.worker_thread.isRunning():
            self.log_signal.emit("매크로가 이미 실행 중입니다. 중복 실행을 방지합니다.")
            return

        login_manager = LoginManager(browser=driver)
        if not login_manager.is_logged_in():
            self.log_signal.emit("로그인이 필요합니다. 로그인을 시도합니다.")
            email_cfg = self.config.get("KREAM", "email", fallback="")
            password_cfg = self.config.get("KREAM", "password", fallback="")

            if not email_cfg or not password_cfg:
                self.log_signal.emit("설정에서 KREAM 이메일과 비밀번호를 입력해주세요.")
                self._close_macro_tab_if_opened(driver)
                return

            if is_url_matching(driver, "kream.co.kr/login"):
                self.log_signal.emit("현재 로그인 페이지에서 로그인을 시도합니다.")
                if login_manager.login(email_cfg, password_cfg):
                    self.log_signal.emit("로그인 성공.")
                    email = "current_session"
                    password = "current_session"
                else:
                    self.log_signal.emit(
                        "로그인 실패. 설정을 확인하거나 수동으로 로그인해주세요."
                    )
                    self._close_macro_tab_if_opened(driver)
                    return
            else:
                self.log_signal.emit("로그인 페이지로 이동하여 로그인을 시도합니다.")
                original_handle_for_login = driver.current_window_handle
                login_attempt_tab_handle: Optional[str] = None
                existing_handles_before_login_tab = set(driver.window_handles)

                try:
                    driver.execute_script("window.open('', '_blank');")
                    for handle in driver.window_handles:
                        if handle not in existing_handles_before_login_tab:
                            login_attempt_tab_handle = handle
                            break

                    if login_attempt_tab_handle:
                        driver.switch_to.window(login_attempt_tab_handle)
                        driver.get("https://kream.co.kr/login")
                        time.sleep(1)

                        if login_manager.login(email_cfg, password_cfg):
                            self.log_signal.emit("로그인 성공.")
                            driver.close()
                            driver.switch_to.window(original_handle_for_login)
                            self.macro_tab_handle = original_handle_for_login
                            email = "current_session"
                            password = "current_session"
                        else:
                            self.log_signal.emit(
                                "로그인 실패. 설정을 확인하거나 수동으로 로그인해주세요."
                            )
                            driver.close()
                            driver.switch_to.window(original_handle_for_login)
                            self._close_macro_tab_if_opened(driver)
                            return
                    else:
                        self.log_signal.emit("로그인을 위한 새 탭을 열지 못했습니다.")
                        self._close_macro_tab_if_opened(driver)
                        return
                except Exception as e_login_tab:
                    self.log_signal.emit(f"로그인 탭 처리 중 오류: {e_login_tab}")
                    if (
                        login_attempt_tab_handle
                        and login_attempt_tab_handle in driver.window_handles
                    ):
                        driver.close()
                    if original_handle_for_login in driver.window_handles:
                        driver.switch_to.window(original_handle_for_login)
                    self._close_macro_tab_if_opened(driver)
                    return
        else:
            email = "current_session"
            password = "current_session"

        if (
            not self.main_window
            and self.plugin_manager
            and self.plugin_manager.main_controller
        ):
            self.main_window = self.plugin_manager.main_controller.main_window

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
        for i in range(1, 100):
            qty_combo.addItem(str(i))
        layout.addWidget(qty_combo)

        click_term_label = QLabel("보관판매 시도 주기 (초):")
        layout.addWidget(click_term_label)

        min_interval_fallback = 8
        max_interval_fallback = 18
        min_interval = self.config.getint(
            "Macro", "min_interval", fallback=min_interval_fallback
        )
        max_interval = self.config.getint(
            "Macro", "max_interval", fallback=max_interval_fallback
        )

        if min_interval > max_interval:
            min_interval, max_interval = min_interval_fallback, max_interval_fallback

        click_term_combo = QComboBox()
        for i in range(min_interval, max_interval + 1):
            click_term_combo.addItem(str(i))

        default_interval = self.config.getint(
            "Macro", "default_interval", fallback=min_interval
        )
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

            try:
                self.macro_worker.log_message.disconnect(self.log_signal.emit)
            except TypeError:
                pass
            self.macro_worker.log_message.connect(self.log_signal.emit)

            self.macro_worker.finished.connect(self._on_macro_finished)
            self.worker_thread.started.connect(self.macro_worker.run)
            self.worker_thread.start()
            self.macro_status_signal.emit(True)

        else:
            self._close_macro_tab_if_opened(driver)

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
                    if original_macro_tab_handle in driver.window_handles:
                        driver.switch_to.window(original_macro_tab_handle)
                        driver.close()
                    else:
                        self.main_controller_log(
                            f"정보: 매크로 탭({original_macro_tab_handle})이 전환 직전에 닫혔습니다."
                        )
                        return
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
            try:
                remaining_handles = driver.window_handles
            except Exception as e_get_handles:
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

            if target_switch_handle:
                try:
                    current_active_handle = driver.current_window_handle
                    needs_switch = current_active_handle != target_switch_handle
                except Exception:
                    needs_switch = True

                if needs_switch:
                    driver.switch_to.window(target_switch_handle)

        except Exception as e_switch:
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
