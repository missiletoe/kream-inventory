"""메인 윈도우 UI 클래스입니다."""

from __future__ import annotations

import logging  # noqa: F401 # 로깅 모듈 임포트 (setup_logger 내부에서 사용될 수 있음)
from datetime import datetime
from typing import Any

# 런타임 시 필요한 모듈 가져오기
import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# logger_setup 임포트
from src.core.logger_setup import setup_logger

from ..core.main_controller import MainController
from ..core.plugin_manager import PluginManager
from .image_assets import (
    get_button_size,
    get_logo_pixmap,
    get_navigation_icons,
    get_window_icon,
)
from .login_popup import LoginPopup

# 전역 로거 설정
logger = setup_logger(__name__)


class MainWindow(QWidget):
    """메인 윈도우 클래스.

    Args:
        plugin_manager: 플러그인 관리자
        main_controller: 메인 컨트롤러
    """

    def __init__(
        self: MainWindow, plugin_manager: PluginManager, main_controller: MainController
    ) -> None:
        """메인 윈도우 초기화."""
        super().__init__()
        # 컨트롤러 초기화
        self.controller = main_controller
        # 브랜드 공식 배송 상품 여부 초기화
        self.current_product_is_official = False
        self.initUI()
        self.connectSignals()

    def initUI(self: MainWindow) -> None:
        """UI를 초기화하고 기본 레이아웃을 설정합니다."""
        self.setWindowTitle("크림 보관판매 매크로 by missiletoe")

        # Set window icon
        QApplication.setWindowIcon(get_window_icon())

        # Set window size and position
        screen = QApplication.primaryScreen()
        button_size_val = 50  # 기본 버튼 크기
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            self.setGeometry(
                0, 0, int(screen_width // 1.5), int((screen_height // 1.5) - 22)
            )
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
            button_size_val = get_button_size(screen)  # screen이 None이 아닐 때만 호출
        else:
            # 기본 창 크기 설정 (스크린을 얻을 수 없는 경우)
            self.setGeometry(100, 100, 1200, 800)

        # Create main layout
        layout = QVBoxLayout()

        # Account section at the top
        account_layout = QHBoxLayout()

        # Account group box
        account_group = QGroupBox("계정")
        account_group_layout = QHBoxLayout()
        self.account_label = QLabel("크림 계정 로그인이 필요합니다.")
        account_group_layout.addWidget(self.account_label, 9)  # 9:1 ratio

        # Login/Logout button inside account group
        self.login_button = QPushButton("로그인", self)
        self.login_button.clicked.connect(self.show_login_popup)
        self.logout_button = QPushButton("로그아웃", self)
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setVisible(False)
        account_group_layout.addWidget(self.login_button, 1)
        account_group_layout.addWidget(self.logout_button, 1)

        account_group.setLayout(account_group_layout)
        account_layout.addWidget(account_group)
        layout.addLayout(account_layout)

        # Search and product info section
        search_product_layout = QHBoxLayout()

        # Search section
        search_group = QGroupBox("검색")
        search_layout = QVBoxLayout()

        # Search input field
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("제품명 입력")
        self.search_input.returnPressed.connect(self.search_product)
        font = self.search_input.font()
        font.setPointSize(font.pointSize() + 4)
        self.search_input.setFont(font)
        search_layout.addWidget(self.search_input)

        # Search buttons layout
        search_input_layout = QHBoxLayout()

        self.search_button = QPushButton("검색", self)
        self.search_button.clicked.connect(self.search_product)
        search_input_layout.addWidget(self.search_button)

        self.search_details_button = QPushButton("상세", self)
        self.search_details_button.setEnabled(False)
        self.search_details_button.clicked.connect(self.product_details)
        search_input_layout.addWidget(self.search_details_button)

        search_layout.addLayout(search_input_layout)
        search_group.setLayout(search_layout)
        search_product_layout.addWidget(search_group, 1)

        # Product info section
        self.product_info = QTextEdit(self)
        self.product_info.setReadOnly(True)
        self.product_info.setPlaceholderText("제품 정보가 여기에 표시됩니다.")
        search_product_layout.addWidget(self.product_info, 3)

        # Detail info section
        self.detail_info = QTextEdit(self)
        self.detail_info.setReadOnly(True)
        self.detail_info.setPlaceholderText("상세 정보가 여기에 표시됩니다.")
        search_product_layout.addWidget(self.detail_info, 2)

        layout.addLayout(search_product_layout)

        # Image and log section with macro settings
        log_image_macro_layout = QHBoxLayout()

        # Image section
        image_layout = QVBoxLayout()

        # Image label
        self.image_label = QLabel()
        self.image_label.setObjectName("image_label")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 화면 크기 참조하기
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            self.image_label.setFixedWidth(screen_width // 3)
            self.image_label.setFixedHeight(screen_width // 3)
        else:
            # 기본 이미지 크기 설정
            self.image_label.setFixedWidth(400)
            self.image_label.setFixedHeight(400)
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(get_logo_pixmap())

        # Navigation buttons
        left_icon, right_icon = get_navigation_icons()
        # button_size = get_button_size(screen) # button_size_val 사용으로 변경

        self.left_button = QPushButton(left_icon, "", self)
        self.left_button.setFixedSize(button_size_val, button_size_val)
        self.left_button.clicked.connect(self.previous_result)
        self.left_button.setEnabled(False)

        self.right_button = QPushButton(right_icon, "", self)
        self.right_button.setFixedSize(button_size_val, button_size_val)
        self.right_button.clicked.connect(self.next_result)
        self.right_button.setEnabled(False)

        # Stack image and navigation buttons
        stacked_layout = QHBoxLayout()
        stacked_layout.addWidget(
            self.left_button,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        stacked_layout.addWidget(self.image_label)
        stacked_layout.addWidget(
            self.right_button,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        image_layout.addLayout(stacked_layout)
        log_image_macro_layout.addLayout(image_layout)

        # Log and macro section
        log_macro_layout = QVBoxLayout()

        # Macro section
        macro_group = QGroupBox("매크로 설정")
        macro_layout = QVBoxLayout()

        # Size, quantity, and start button in horizontal layout
        macro_controls_layout = QHBoxLayout()

        self.macro_status_label = QLabel(
            "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다.", self
        )
        macro_controls_layout.addWidget(self.macro_status_label)

        self.start_button = QPushButton("매크로 시작", self)
        self.start_button.setEnabled(False)
        macro_controls_layout.addWidget(self.start_button)

        macro_layout.addLayout(macro_controls_layout)
        macro_group.setLayout(macro_layout)
        log_macro_layout.addWidget(macro_group)

        user_manual = """프로그램 사용 방법 \n
        1. 우측 상단의 로그인 버튼을 통해 크림 계정에 로그인합니다.\n
        2. 검색창에서 보관판매를 맡길 제품을 검색합니다.\n
        3. 검색 버튼 오른쪽에 있는 상세 버튼을 눌러 상세 정보를 불러옵니다.\n
        4. 매크로 시작 버튼을 누르면 나타나는 팝업창에서 옵션(사이즈, 수량)을 선택합니다.\n
        5. 팝업창의 시작 버튼을 누르면 매크로가 자동으로 실행됩니다."""

        # Log output
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText(user_manual)
        log_macro_layout.addWidget(self.log_output)

        log_image_macro_layout.addLayout(log_macro_layout)
        layout.addLayout(log_image_macro_layout)
        self.setLayout(layout)

    def connectSignals(self: MainWindow) -> None:
        """컨트롤러의 시그널을 UI 요소의 슬롯에 연결합니다."""
        self.controller.login_status_changed.connect(self.handle_login_status)
        self.controller.search_result_received.connect(self.handle_search_result)
        self.controller.details_received.connect(self.handle_details)
        self.controller.sizes_ready.connect(self.update_size_combo)
        try:
            self.controller.log_message.disconnect(self.log_message)
        except TypeError:
            pass
        self.controller.log_message.connect(self.log_message)
        self.controller.macro_status_changed.connect(self.handle_macro_status)
        self.start_button.clicked.connect(self.start_macro)

    def show_login_popup(self: MainWindow) -> None:
        """로그인 팝업을 표시합니다."""
        self.login_popup = LoginPopup(self)
        self.login_popup.login_requested.connect(self.handle_login)
        self.login_popup.exec()

    def handle_login(self: MainWindow, user_email: str, password: str) -> None:
        """로그인 시도를 처리합니다."""
        self.controller.login(user_email, password)

    def handle_logout(self: MainWindow) -> None:
        """로그아웃을 처리합니다."""
        self.controller.logout()

    def update_ui_after_logout(self: MainWindow) -> None:
        """로그아웃 후 UI를 업데이트합니다."""
        self.account_label.setText("크림 계정 로그인이 필요합니다.")
        self.login_button.setVisible(True)
        self.logout_button.setVisible(False)
        self.start_button.setEnabled(False)  # 로그인 안되어있으면 매크로 시작 불가
        self.search_details_button.setEnabled(False)  # 로그인 풀리면 상세정보 조회 불가
        self.macro_status_label.setText(
            "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
        )

    def handle_login_status(self: MainWindow, is_logged_in: bool, message: str) -> None:
        """로그인 상태 변경을 처리하고 UI를 업데이트합니다."""
        self.log_message(message)
        if is_logged_in:
            self.account_label.setText(
                f"현재 로그인된 계정: {self.controller.get_current_email()}"
            )
            self.login_button.setVisible(False)
            self.logout_button.setVisible(True)
            # 로그인 성공 시 매크로 시작 버튼의 활성화 여부는 제품 선택 및 상세 정보 로드 유무에 따라 결정
            self.start_button.setEnabled(bool(self.controller.current_product_id))
            # 로그인 팝업이 열려있으면 닫기
            if hasattr(self, "login_popup") and self.login_popup.isVisible():
                self.login_popup.accept()
        else:
            self.update_ui_after_logout()

    def search_product(self: MainWindow) -> None:
        """제품 검색을 시작합니다."""
        query = self.search_input.text()
        if query:
            logger.debug(f"UI 검색 요청: '{query}'")  # print -> logger.debug

            # UI 초기화
            self.left_button.setEnabled(False)  # 새 검색 시 탐색 버튼 초기화
            self.right_button.setEnabled(False)
            self.search_details_button.setEnabled(False)  # 새 검색 시 상세 버튼 초기화
            self.start_button.setEnabled(False)  # 새 검색 시 매크로 시작 버튼 비활성화
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )
            self.product_info.setPlainText(f"'{query}' 검색 중...")

            # 컨트롤러에 검색 요청
            self.controller.search_product(query)
        else:
            logger.debug("UI 검색어 없음")  # print -> logger.debug
            self.log_message("검색어를 입력해주세요.")

    def next_result(self: MainWindow) -> None:
        """다음 검색 결과를 요청합니다."""
        self.controller.next_result()

    def previous_result(self: MainWindow) -> None:
        """이전 검색 결과를 요청합니다."""
        self.controller.previous_result()

    def product_details(self: MainWindow) -> None:
        """제품 상세 정보를 요청합니다."""
        # 브랜드 공식 배송 상품인 경우 처리
        if (
            hasattr(self, "current_product_is_official")
            and self.current_product_is_official
        ):
            error_message = "브랜드 배송 상품입니다. 보관판매가 불가능합니다."
            self.log_message(error_message)
            self.detail_info.setPlainText(error_message)
            # 매크로 시작 버튼 비활성화
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "브랜드 배송 상품은 매크로 실행이 불가능합니다."
            )
            return

        # 일반 상품 처리
        if self.controller.get_product_details():
            # 상세 정보 요청 성공 시, handle_details에서 start_button 활성화 예정
            pass
        else:
            self.log_message(
                "제품 상세 정보를 가져올 수 없습니다. 먼저 로그인하고 제품을 선택하세요."
            )

    def log_message(self: MainWindow, message: str) -> None:
        """로그 메시지를 UI에 표시합니다."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{current_time}] {message}"
        current_text = self.log_output.toPlainText()

        if not current_text or formatted_message not in current_text:
            self.log_output.append(formatted_message)

    def update_size_combo(self: MainWindow, sizes: list[str]) -> None:
        """제품 사이즈 정보를 받아 콤보박스를 업데이트합니다."""
        # 사이즈 및 수량 선택 UI가 제거되었으므로, 이 함수는 주로 매크로 시작 버튼 활성화 로직을 담당.
        # 단, 현재는 handle_details에서 직접 start_button을 활성화하도록 변경 고려.
        # 여기서는 일단, 상세 정보가 성공적으로 로드되었음을 가정하고 (sizes 인자는 이제 사용 안함)
        # 매크로 시작 버튼을 활성화하고 메시지를 업데이트.
        if self.controller.is_logged_in() and self.controller.current_product_id:
            self.start_button.setEnabled(True)
            self.macro_status_label.setText("매크로 시작이 가능합니다.")
        else:
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )
        # 기존 size_combo, quantity_spin 관련 코드는 제거됨.

    def handle_search_result(self: MainWindow, result: dict[str, Any]) -> None:
        """검색 결과를 처리하고 UI에 표시합니다."""
        if not result:
            self.log_message("검색 결과가 없습니다.")
            self.product_info.setPlainText("검색 결과가 없습니다.")
            self.image_label.setPixmap(get_logo_pixmap())
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)
            self.search_details_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )
            return

        if "error" in result:
            error_msg = result["error"]
            self.log_message(error_msg)
            self.product_info.setPlainText(error_msg)
            self.image_label.setPixmap(get_logo_pixmap())
            self.left_button.setEnabled(result.get("enable_prev", False))
            self.right_button.setEnabled(result.get("enable_next", False))
            self.search_details_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )
            return

        if "info" in result:
            info_msg = result["info"]
            self.log_message(info_msg)
            self.left_button.setEnabled(result.get("enable_prev", False))
            self.right_button.setEnabled(result.get("enable_next", False))
            self.search_details_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )
            return

        name = result.get("name", "이름 없음")
        name_kr = result.get("translated_name", "한국어 이름 없음")
        brand = result.get("brand", "브랜드 없음")
        product_id = result.get("id", "ID 없음")
        wish_figure = result.get("wish_figure")
        review_figure = result.get("review_figure")
        is_brand_official = result.get("is_brand_official", False)

        self.current_product_is_official = is_brand_official

        wish_text = f"관심 {wish_figure}" if wish_figure else ""
        review_text = f"리뷰 {review_figure}" if review_figure else ""

        stats_text = ""
        if wish_text and review_text:
            stats_text = f"{wish_text} · {review_text}"
        elif wish_text:
            stats_text = wish_text
        elif review_text:
            stats_text = review_text

        self.product_info.setPlainText(
            f"{brand}\n{name}\n{name_kr}\n{stats_text}\n[{product_id}]"
        )

        image_url = result.get("image_url")
        if image_url:
            try:
                response = requests.get(image_url, timeout=5)
                image_data = response.content
                pixmap = QPixmap()
                success = pixmap.loadFromData(image_data)

                if success and not pixmap.isNull():
                    self.image_label.setPixmap(pixmap)
                else:
                    self.image_label.setPixmap(get_logo_pixmap())
            except Exception:
                self.image_label.setPixmap(get_logo_pixmap())
        else:
            self.image_label.setPixmap(get_logo_pixmap())

        is_logged_in = self.controller.is_logged_in()
        self.search_details_button.setEnabled(is_logged_in)

        has_previous = result.get("enable_prev", False)
        has_next = result.get("enable_next", False)
        self.left_button.setEnabled(has_previous)
        self.right_button.setEnabled(has_next)

        self.start_button.setEnabled(False)
        self.macro_status_label.setText("상세 버튼을 눌러 제품 상세 정보를 확인하세요.")

    def handle_details(self: MainWindow, details: dict[str, Any]) -> None:
        """제품 상세 정보를 처리하고 UI에 표시합니다."""
        if not details:
            self.log_message("상세 정보를 가져오는데 실패했습니다.")
            self.detail_info.setPlainText("상세 정보를 가져올 수 없습니다.")
            self.start_button.setEnabled(False)
            self.macro_status_label.setText("상세 정보 로드 실패. 매크로 실행 불가.")
            return

        model_no = details.get("model_no", "N/A")
        color = details.get("color", "N/A")

        detail_text = f"{model_no} — {color}\n"
        detail_text += f"최근 거래가: {details.get('recent_price', 'N/A')}원 "
        detail_text += f"{details.get('fluctuation', 'N/A')}\n"
        detail_text += f"발매 정가: {details.get('release_price', 'N/A')}"

        recent_price = details.get("recent_price", "N/A")
        release_price = details.get("release_price", "N/A")

        try:
            if recent_price != "N/A" and release_price != "N/A":
                cleaned_recent = recent_price.replace(",", "").replace("원", "").strip()

                cleaned_release = release_price

                import re

                won_in_parenthesis = re.search(
                    r"\((?:약\s*)?([0-9,]+)원?\)", release_price
                )

                if won_in_parenthesis:
                    cleaned_release = won_in_parenthesis.group(1).replace(",", "")
                else:
                    cleaned_release = (
                        release_price.replace(",", "")
                        .replace("원", "")
                        .replace("$", "")
                        .strip()
                    )

                recent_value = float(cleaned_recent)
                release_value = float(cleaned_release)

                if release_value > 0:
                    premium_percentage = (recent_value / release_value) * 100 - 100
                    detail_text += f"({premium_percentage:.1f}% 프리미엄)\n"
                else:
                    detail_text += "(프리미엄 계산 불가)\n"
            else:
                detail_text += "(프리미엄 정보 없음)\n"
        except (TypeError, ValueError, ZeroDivisionError):
            detail_text += "(프리미엄 계산 불가)\n"

        detail_text += f"발매일: {details.get('release_date', 'N/A')}"
        detail_text += f"{details.get('d_day', '')}\n"

        self.detail_info.setPlainText(detail_text.strip())

        if self.controller.is_logged_in() and self.controller.current_product_id:
            self.start_button.setEnabled(True)
            self.macro_status_label.setText("매크로 시작이 가능합니다.")
        else:
            self.start_button.setEnabled(False)
            self.macro_status_label.setText(
                "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
            )

    def keyPressEvent(self: MainWindow, event: QKeyEvent | None) -> None:
        """키 입력 이벤트를 처리합니다."""
        if event is not None:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if self.search_input.hasFocus():
                    self.search_product()
            super().keyPressEvent(event)
        else:
            # None 인 경우 상위 클래스의 메서드 호출
            super().keyPressEvent(event)

    def start_macro(self: MainWindow) -> None:
        """매크로 시작 버튼 클릭 시 호출됩니다."""
        if not self.controller.is_logged_in():
            self.log_message("로그인이 필요합니다.")
            return

        if self.controller.start_macro():
            self.log_message("매크로 시작 요청됨.")
            self.macro_status_label.setText("매크로 진행 중...")
        else:
            self.log_message("매크로 시작 요청 실패. 컨트롤러 로그를 확인하세요.")
            self.macro_status_label.setText("매크로 시작 실패.")

    def stop_macro(self: MainWindow) -> None:
        """매크로 중지 버튼 클릭 시 호출됩니다."""
        if self.controller.stop_macro():
            self.log_message("매크로 중지 요청됨.")
        else:
            self.log_message("매크로 중지 요청 실패. 컨트롤러 로그를 확인하세요.")
            self.macro_status_label.setText("매크로 중지 실패.")

    def disable_ui_controls(self: MainWindow) -> None:
        """매크로 실행 중 UI 컨트롤을 비활성화합니다."""
        self.search_input.setEnabled(False)
        self.search_button.setEnabled(False)
        self.search_details_button.setEnabled(False)
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)
        self.login_button.setEnabled(False)
        self.logout_button.setEnabled(False)

    def enable_ui_controls(self: MainWindow) -> None:
        """매크로 종료 후 UI 컨트롤을 활성화합니다."""
        self.search_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.login_button.setEnabled(True)
        self.logout_button.setEnabled(
            self.controller.is_logged_in()
        )  # 로그인 상태에 따라 결정
        self.login_button.setVisible(not self.controller.is_logged_in())

    def handle_macro_status(self: MainWindow, status: bool) -> None:
        """매크로 상태 변경을 처리하고 UI를 업데이트합니다."""
        self.macro_running = status
        if status:  # 매크로 시작됨
            self.log_message("매크로가 시작되었습니다.")
            self.start_button.setText("매크로 중지")
            try:
                self.start_button.clicked.disconnect(self.start_macro)
            except TypeError:
                pass
            self.start_button.clicked.connect(self.stop_macro)
            self.disable_ui_controls()
            self.macro_status_label.setText("매크로 진행 중...")
        else:  # 매크로 중지됨
            self.log_message("매크로가 중지되었습니다.")
            self.start_button.setText("매크로 시작")
            try:
                self.start_button.clicked.disconnect(self.stop_macro)
            except TypeError:
                pass
            self.start_button.clicked.connect(self.start_macro)
            self.enable_ui_controls()
            # 매크로 종료 시, 시작 버튼은 현재 제품 및 로그인 상태에 따라 결정
            is_ready_to_start = self.controller.is_logged_in() and bool(
                self.controller.current_product_id
            )
            self.start_button.setEnabled(is_ready_to_start)
            if is_ready_to_start:
                self.macro_status_label.setText("매크로 시작이 가능합니다.")
            else:
                self.macro_status_label.setText(
                    "제품 검색 후 상세버튼을 누르면 매크로 시작이 가능합니다."
                )
