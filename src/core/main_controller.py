"""애플리케이션의 메인 컨트롤러 모듈입니다.

UI와 플러그인 간의 상호작용을 관리합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

# logger_setup 임포트
from src.core.logger_setup import setup_logger

from ..plugins import DetailPlugin, LoginPlugin, MacroPlugin, SearchPlugin
from .plugin_manager import PluginManager

if TYPE_CHECKING:
    from ..ui.main_window import MainWindow

# 전역 로거 설정
logger = setup_logger(__name__)


class MainController(QObject):
    """애플리케이션의 메인 컨트롤러 클래스입니다.

    UI와 플러그인 간의 상호작용을 관리합니다.
    """

    login_status_changed = pyqtSignal(bool, str)
    search_result_received = pyqtSignal(dict)
    details_received = pyqtSignal(dict)
    sizes_ready = pyqtSignal(list)
    log_message = pyqtSignal(str)  # UI 로깅용
    macro_status_changed = pyqtSignal(bool)

    def __init__(
        self: MainController,
        plugin_manager: PluginManager,
        main_window: Optional["MainWindow"] = None,
    ) -> None:
        """MainController를 초기화합니다.

        Args:
            plugin_manager: 플러그인 매니저 객체입니다.
            main_window: 메인 윈도우 객체입니다. (선택 사항)
        """
        super().__init__()
        self.plugin_manager: PluginManager = plugin_manager
        self.main_window: Optional["MainWindow"] = main_window
        self.browser: Any = plugin_manager.browser

        logger.debug(  # print -> logger.debug
            f"Debug MainController: Available plugins: {list(plugin_manager.plugins.keys())}"
        )

        # 플러그인 참조 가져오기
        self.login_plugin: Optional[LoginPlugin] = plugin_manager.get_plugin("login")
        self.search_plugin: Optional[SearchPlugin] = plugin_manager.get_plugin("search")
        self.detail_plugin: Optional[DetailPlugin] = plugin_manager.get_plugin("detail")
        self.macro_plugin: Optional[MacroPlugin] = plugin_manager.get_plugin("macro")

        logger.debug(
            f"Debug MainController: login_plugin = {self.login_plugin}"
        )  # print -> logger.debug
        logger.debug(
            f"Debug MainController: search_plugin = {self.search_plugin}"
        )  # print -> logger.debug
        logger.debug(
            f"Debug MainController: detail_plugin = {self.detail_plugin}"
        )  # print -> logger.debug
        logger.debug(
            f"Debug MainController: macro_plugin = {self.macro_plugin}"
        )  # print -> logger.debug

        self.logged_in: bool = False
        self.macro_running: bool = False
        self.current_product_id: Optional[str] = None
        self._current_email: Optional[str] = None

        # 플러그인 시그널 연결
        self._connect_plugin_signals()

    def _connect_plugin_signals(self: MainController) -> None:
        """플러그인의 시그널을 컨트롤러의 슬롯에 연결합니다."""
        # 플러그인이 없는 경우 다시 참조 업데이트 시도
        if not all(
            [
                self.login_plugin,
                self.search_plugin,
                self.detail_plugin,
                self.macro_plugin,
            ]
        ):
            logger.info(
                "Some plugins not found, attempting to update references."
            )  # 로깅 추가
            self.update_plugin_references()

        if self.login_plugin and hasattr(self.login_plugin, "login_status"):
            self.login_plugin.login_status.connect(self._handle_login_status)
        else:  # 로깅 추가
            logger.warning("Login plugin or login_status signal not found.")

        if self.search_plugin and hasattr(self.search_plugin, "search_result"):
            self.search_plugin.search_result.connect(self._handle_search_result)
        else:  # 로깅 추가
            logger.warning("Search plugin or search_result signal not found.")

        if self.detail_plugin and hasattr(self.detail_plugin, "sizes_ready"):
            self.detail_plugin.sizes_ready.connect(self._handle_sizes_ready)
        else:  # 로깅 추가
            logger.warning("Detail plugin or sizes_ready signal not found.")

        if self.detail_plugin and hasattr(self.detail_plugin, "details_ready"):
            self.detail_plugin.details_ready.connect(self._handle_details_ready)
        else:  # 로깅 추가
            logger.warning("Detail plugin or details_ready signal not found.")

        if self.macro_plugin and hasattr(self.macro_plugin, "log_signal"):
            self.macro_plugin.log_signal.connect(
                self.log_message.emit
            )  # UI 로깅용이므로 유지
        else:  # 로깅 추가
            logger.warning("Macro plugin or log_signal signal not found.")

        if self.macro_plugin and hasattr(self.macro_plugin, "macro_status_signal"):
            self.macro_plugin.macro_status_signal.connect(self._handle_macro_status)
        else:  # 로깅 추가
            logger.warning("Macro plugin or macro_status_signal signal not found.")

    def _handle_login_status(
        self: MainController, is_logged_in: bool, message: str
    ) -> None:
        """로그인 상태 변경 시그널을 처리합니다.

        Args:
            is_logged_in: 로그인 상태입니다.
            message: 관련 메시지입니다.
        """
        self.logged_in = is_logged_in
        self.login_status_changed.emit(is_logged_in, message)
        logger.info(
            f"Login status changed: {is_logged_in}, Message: {message}"
        )  # 로깅 추가

    def _handle_search_result(self: MainController, result: Dict[str, Any]) -> None:
        """검색 결과 수신 시그널을 처리합니다.

        Args:
            result: 검색 결과 딕셔너리입니다.
        """
        logger.debug(
            f"[DEBUG CONTROLLER] 검색 결과 수신: {list(result.keys()) if isinstance(result, dict) else 'Invalid result type'}"
        )  # print -> logger.debug, 내용 상세화

        if isinstance(result, dict) and "error" in result:
            logger.error(
                f"[DEBUG CONTROLLER] 검색 결과 오류: {result['error']}"
            )  # print -> logger.error
            self.current_product_id = None
        elif isinstance(result, dict):
            self.current_product_id = result.get("id")
            logger.debug(
                f"[DEBUG CONTROLLER] 제품 ID 설정: {self.current_product_id}"
            )  # print -> logger.debug
        else:
            logger.error(
                f"[DEBUG CONTROLLER] 수신된 검색 결과의 타입이 올바르지 않습니다: {type(result)}"
            )
            self.current_product_id = None

        # 검색 결과를 UI로 전달
        self.search_result_received.emit(result)

    def _handle_macro_status(self: MainController, status: bool) -> None:
        """매크로 상태 변경 시그널을 처리합니다.

        Args:
            status: 매크로 실행 상태입니다.
        """
        self.macro_running = status
        self.macro_status_changed.emit(status)
        logger.info(f"Macro status changed: {status}")  # 로깅 추가

    def _handle_sizes_ready(self: MainController, sizes: List[str]) -> None:
        """사이즈 정보 준비 완료 시그널을 처리합니다.

        Args:
            sizes: 사용 가능한 사이즈 목록입니다.
        """
        self.sizes_ready.emit(sizes)

    def _handle_details_ready(self: MainController, details: Dict[str, Any]) -> None:
        """제품 상세 정보 준비 완료 시그널을 처리합니다.

        Args:
            details: 제품 상세 정보 딕셔너리입니다.
        """
        self.details_received.emit(details)

    def login(self: MainController, username: str, password: str) -> None:
        """로그인을 시도합니다.

        Args:
            username: 사용자 아이디입니다.
            password: 사용자 비밀번호입니다.
        """
        if self.login_plugin:
            self._current_email = username
            self.login_plugin.login(username, password)
        else:
            self.log_message.emit("로그인 플러그인이 로드되지 않았습니다.")

    def logout(self: MainController) -> None:
        """로그아웃을 시도합니다."""
        try:
            if self.login_plugin:
                self.login_plugin.logout()
            else:
                self.log_message.emit("로그인 플러그인이 로드되지 않았습니다.")
        except Exception as e:
            self.log_message.emit(f"웹 로그아웃 중 오류 발생: {e}")
        finally:
            self.logged_in = False
            self.log_message.emit("로그아웃되었습니다.")
            self.login_status_changed.emit(False, "로그아웃되었습니다.")

    def search_product(self: MainController, query: str) -> None:
        """제품을 검색합니다.

        Args:
            query: 검색어입니다.
        """
        if self.search_plugin:
            self.search_plugin.search(query)
        else:
            self.log_message.emit("검색 플러그인이 로드되지 않았습니다.")

    def next_result(self: MainController) -> None:
        """다음 검색 결과를 가져옵니다."""
        try:
            if self.search_plugin:
                self.search_plugin.next_result()
            else:
                self.log_message.emit("검색 플러그인이 로드되지 않았습니다.")
        except Exception as e:
            self.log_message.emit(f"오류 발생: {e}")

    def previous_result(self: MainController) -> None:
        """이전 검색 결과를 가져옵니다."""
        if self.search_plugin:
            self.search_plugin.previous_result()
        else:
            self.log_message.emit("검색 플러그인이 로드되지 않았습니다.")

    def get_product_details(self: MainController) -> bool:
        """선택된 제품의 상세 정보를 가져옵니다.

        Returns:
            상세 정보 요청 성공 여부입니다.
        """
        if not self.logged_in:
            self.log_message.emit("로그인이 필요합니다. 로그인해주세요.")
            return False

        if not self.current_product_id:
            self.log_message.emit("제품을 먼저 선택해주세요.")
            return False

        if self.detail_plugin:
            self.detail_plugin.get_details(self.current_product_id)
            return True
        else:
            self.log_message.emit("상세 정보 플러그인이 로드되지 않았습니다.")
            return False

    def start_macro(self: MainController) -> bool:
        """매크로를 시작합니다.

        매크로 실행에 필요한 정보(size, quantity)는 MacroPlugin 내부에서 UI를 통해 입력받습니다.

        Returns:
            매크로 시작 요청 성공 여부입니다.
        """
        if not self.current_product_id:
            self.log_message.emit("제품을 먼저 선택해주세요.")
            return False

        if self.macro_running:
            self.log_message.emit("매크로가 이미 실행 중입니다.")
            return False

        if self.macro_plugin:
            try:
                self.macro_plugin.start_macro_dialog()
                self.log_message.emit("매크로 시작을 요청했습니다.")
                return True
            except Exception as e:
                self.log_message.emit(f"매크로 시작 요청 중 오류: {str(e)}")
                return False
        else:
            self.log_message.emit("매크로 플러그인이 로드되지 않았습니다.")
            return False

    def stop_macro(self: MainController) -> bool:
        """매크로를 중지합니다.

        Returns:
            매크로 중지 요청 성공 여부입니다.
        """
        if not self.macro_running:
            self.log_message.emit("실행 중인 매크로가 없습니다.")
            return False

        if self.macro_plugin:
            try:
                self.macro_plugin.stop_macro()
                self.log_message.emit("매크로 중지를 요청했습니다.")
                return True
            except Exception as e:
                self.log_message.emit(f"매크로 중지 요청 중 오류: {str(e)}")
                return False
        else:
            self.log_message.emit("매크로 플러그인이 로드되지 않았습니다.")
            return False

    def is_logged_in(self: MainController) -> bool:
        """현재 로그인 상태를 반환합니다.

        Returns:
            로그인 되어 있으면 True, 아니면 False를 반환합니다.
        """
        return self.logged_in

    def is_macro_running(self: MainController) -> bool:
        """현재 매크로 실행 상태를 반환합니다.

        (주의: 이 상태는 MacroPlugin의 실제 상태와 동기화되어야 합니다.)

        Returns:
            매크로가 실행 중이면 True, 아니면 False를 반환합니다.
        """
        return self.macro_running

    def mask_email(self: MainController, email: str) -> str:
        """이메일 주소의 일부를 마스킹 처리합니다.

        예시: "user@example.com" -> "us**@******.com"

        Args:
            email: 마스킹할 이메일 주소입니다.

        Returns:
            마스킹 처리된 이메일 주소입니다.
        """
        if "@" not in email:
            return email  # 유효하지 않은 이메일 형식

        local_part, domain_part = email.split("@", 1)
        domain_name, domain_suffix = (
            domain_part.split(".", 1) if "." in domain_part else (domain_part, "")
        )

        masked_local = local_part[:2] + "**" if len(local_part) > 2 else local_part
        masked_domain_name = "******" if len(domain_name) > 0 else ""

        if domain_suffix:
            return f"{masked_local}@{masked_domain_name}.{domain_suffix}"
        return f"{masked_local}@{masked_domain_name}"

    def get_current_email(self: MainController) -> str:
        """현재 로그인된 계정의 이메일(마스킹 적용)을 반환합니다.

        Returns:
            마스킹된 이메일 문자열입니다. 로그인되어 있지 않으면 빈 문자열을 반환합니다.
        """
        if self._current_email:
            return self.mask_email(self._current_email)
        return ""

    def update_plugin_references(self: MainController) -> None:
        """플러그인 참조를 업데이트합니다."""
        self.login_plugin = self.plugin_manager.get_plugin("login")
        self.search_plugin = self.plugin_manager.get_plugin("search")
        self.detail_plugin = self.plugin_manager.get_plugin("detail")
        self.macro_plugin = self.plugin_manager.get_plugin("macro")

        logger.info("플러그인 참조가 업데이트되었습니다:")
        logger.info(f"login_plugin = {self.login_plugin}")
        logger.info(f"search_plugin = {self.search_plugin}")
        logger.info(f"detail_plugin = {self.detail_plugin}")
        logger.info(f"macro_plugin = {self.macro_plugin}")

        # 시그널 다시 연결
        self._connect_plugin_signals()
