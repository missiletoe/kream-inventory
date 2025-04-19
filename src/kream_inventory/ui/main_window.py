from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QComboBox, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QTextEdit, QVBoxLayout, QWidget)

from src.kream_inventory.core.main_controller import MainController
from .image_assets import (get_button_size, get_logo_pixmap,
                           get_navigation_icons, get_window_icon)
from .login_popup import LoginPopup


class MainWindow(QWidget):
    def __init__(self, plugin_manager):
        super().__init__()
        # 컨트롤러 초기화
        self.controller = MainController(plugin_manager)
        self.initUI()
        self.connectSignals()

    def initUI(self):
        self.setWindowTitle('크림 보관판매 매크로 by missiletoe')

        # Set window icon
        QApplication.setWindowIcon(get_window_icon())

        # Set window size and position
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        self.setGeometry(0, 0, int(screen_width // 1.5), int((screen_height // 1.5) - 22))
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

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
        self.login_button = QPushButton('로그인', self)
        self.login_button.clicked.connect(self.show_login_popup)
        self.logout_button = QPushButton('로그아웃', self)
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
        self.search_input.setPlaceholderText('제품명 입력')
        self.search_input.returnPressed.connect(self.search_product)
        font = self.search_input.font()
        font.setPointSize(font.pointSize() + 4)
        self.search_input.setFont(font)
        search_layout.addWidget(self.search_input)
        
        # Search buttons layout
        search_input_layout = QHBoxLayout()
        
        self.search_button = QPushButton('검색', self)
        self.search_button.clicked.connect(self.search_product)
        search_input_layout.addWidget(self.search_button)

        self.search_details_button = QPushButton('상세', self)
        self.search_details_button.setEnabled(False)
        self.search_details_button.clicked.connect(self.product_details)
        search_input_layout.addWidget(self.search_details_button)
        
        search_layout.addLayout(search_input_layout)
        search_group.setLayout(search_layout)
        search_product_layout.addWidget(search_group, 1)

        # Product info section
        self.product_info = QTextEdit(self)
        self.product_info.setReadOnly(True)
        self.product_info.setPlaceholderText('제품 정보가 여기에 표시됩니다.')
        search_product_layout.addWidget(self.product_info, 3)

        # Detail info section
        self.detail_info = QTextEdit(self)
        self.detail_info.setReadOnly(True)
        self.detail_info.setPlaceholderText('상세 정보가 여기에 표시됩니다.')
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
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        self.image_label.setFixedWidth(screen_width // 3)
        self.image_label.setFixedHeight(screen_width // 3)
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(get_logo_pixmap())

        # Navigation buttons
        left_icon, right_icon = get_navigation_icons()
        button_size = get_button_size(screen)

        self.left_button = QPushButton(left_icon, '', self)
        self.left_button.setFixedSize(button_size, button_size)
        self.left_button.clicked.connect(self.previous_result)
        self.left_button.setEnabled(False)

        self.right_button = QPushButton(right_icon, '', self)
        self.right_button.setFixedSize(button_size, button_size)
        self.right_button.clicked.connect(self.next_result)
        self.right_button.setEnabled(False)

        # Stack image and navigation buttons
        stacked_layout = QHBoxLayout()
        stacked_layout.addWidget(self.left_button, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stacked_layout.addWidget(self.image_label)
        stacked_layout.addWidget(self.right_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        image_layout.addLayout(stacked_layout)
        log_image_macro_layout.addLayout(image_layout)

        # Log and macro section
        log_macro_layout = QVBoxLayout()

        # Macro section
        macro_group = QGroupBox("매크로 설정")
        macro_layout = QVBoxLayout()

        # Size, quantity, and start button in horizontal layout
        macro_controls_layout = QHBoxLayout()

        self.size_combo = QComboBox(self)
        self.size_combo.setEnabled(False)
        macro_controls_layout.addWidget(QLabel("사이즈:"))
        macro_controls_layout.addWidget(self.size_combo)

        self.quantity_spin = QSpinBox(self)
        self.quantity_spin.setRange(1, 10)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setEnabled(False)
        macro_controls_layout.addWidget(QLabel("수량:"))
        macro_controls_layout.addWidget(self.quantity_spin)

        self.start_button = QPushButton('매크로 시작', self)
        self.start_button.setEnabled(False)
        macro_controls_layout.addWidget(self.start_button)

        macro_layout.addLayout(macro_controls_layout)
        macro_group.setLayout(macro_layout)
        log_macro_layout.addWidget(macro_group)

        user_manual = """프로그램 사용 방법 \n
        1. 우측 상단에 로그인 버튼을 통해 크림 계정에 로그인합니다.\n
        2. 보관판매를 맡길 제품을 검색합니다.\n
        3. 검색 버튼 오른쪽에 상세 버튼을 눌러 상세 정보를 불러옵니다.\n
        4. 매크로 설정 박스에서 옵션을 선택합니다.\n
        5. 매크로 시작 버튼을 누르면 매크로가 실행됩니다."""

        # Log output
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText(user_manual)
        log_macro_layout.addWidget(self.log_output)

        log_image_macro_layout.addLayout(log_macro_layout)
        layout.addLayout(log_image_macro_layout)
        self.setLayout(layout)

    def connectSignals(self):
        """컨트롤러와 UI 사이의 시그널 연결"""
        # 컨트롤러로부터 UI로의 시그널 연결
        self.controller.login_status_changed.connect(self.handle_login_status)
        self.controller.search_result_received.connect(self.handle_search_result)
        self.controller.details_received.connect(self.handle_details)
        self.controller.sizes_ready.connect(self.update_size_combo)
        self.controller.log_message.connect(self.append_log)
        self.controller.macro_status_changed.connect(self.handle_macro_status)
        
        # UI 액션 버튼 연결
        self.start_button.clicked.connect(self.start_macro)

        # 키보드 이벤트 핸들러 추가
        self.keyPressEvent = self.handle_key_press

    def show_login_popup(self):
        popup = LoginPopup(self)
        popup.login_requested.connect(self.handle_login)
        popup.exec()

    def handle_login(self, email, password):
        self.controller.login(email, password)

    def handle_logout(self):
        self.controller.logout()
        self.update_ui_after_logout()

    def update_ui_after_logout(self):
        self.login_button.setVisible(True)
        self.logout_button.setVisible(False)
        self.account_label.setText("크림 계정 로그인이 필요합니다.")
        self.start_button.setEnabled(False)

    def handle_login_status(self, is_logged_in, message):
        if is_logged_in:
            self.login_button.setVisible(False)
            self.logout_button.setVisible(True)
            
            # Extract email from message and mask it
            email = message.split("크림에 ")[1].split(" 계정으로")[0] if "크림에 " in message else ""
            masked_email = self.controller.mask_email(email)
            self.account_label.setText(f"계정: {masked_email}")
            self.log_output.append(f"{masked_email} 계정으로 로그인 되었습니다.")

            # 로그인 성공 후 상세 정보 조회 기능 활성화
            if self.search_details_button.isEnabled():
                self.product_details()
        else:
            self.update_ui_after_logout()

    def search_product(self):
        query = self.search_input.text()
        if query:
            self.controller.search_product(query)
            # Reset macro settings when new search is performed
            self.size_combo.setEnabled(False)
            self.quantity_spin.setEnabled(False)
            self.start_button.setEnabled(False)
            # Re-enable the detail button when a new search is performed
            self.search_details_button.setEnabled(True)

    def next_result(self):
        self.controller.next_result()
        # Enable the detail button when navigating to a different result
        self.search_details_button.setEnabled(True)

    def previous_result(self):
        self.controller.previous_result()
        # Enable the detail button when navigating to a different result
        self.search_details_button.setEnabled(True)

    def product_details(self):
        if not self.controller.is_logged_in():
            self.log_output.append("로그인이 필요합니다. 로그인해주세요.")
            self.show_login_popup()
            return
        
        # Disable the detail button to prevent multiple clicks
        self.search_details_button.setEnabled(False)
        self.controller.get_product_details()

    def append_log(self, text: str):
        # 매크로로부터 온 로그 메시지 출력
        self.log_output.append(text)

    def update_size_combo(self, sizes):
        self.size_combo.clear()
        if sizes:
            self.size_combo.addItems(sizes)
            self.size_combo.setEnabled(True)
            self.quantity_spin.setEnabled(True)
            if self.controller.is_logged_in():
                self.start_button.setEnabled(True)
        else:
            self.size_combo.setEnabled(False)
            self.quantity_spin.setEnabled(False)
            self.start_button.setEnabled(False)

    def handle_search_result(self, result):
        if "error" in result:
            self.product_info.setText(result["error"])
            # 이전/다음 버튼 활성화 상태 업데이트
            self.left_button.setEnabled(result.get("enable_prev", False))
            self.right_button.setEnabled(result.get("enable_next", False))
            return
            
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
        product_text = ""
        
        # 브랜드배송 메시지를 먼저 추가
        if result.get('is_brand'):
            product_text += "보관판매가 불가능한 브랜드배송 제품입니다.\n\n"
            self.search_details_button.setEnabled(False)
        else:
            # Only enable the detail button if it's not a brand product and we're in a new search
            self.search_details_button.setEnabled(True)
        
        product_text += f"{result.get('name', '')}\n"
        product_text += f"{result.get('translated_name', '')}\n"
        product_text += f"[{current_time} 기준]\n"
        product_text += f"최저구매가: {result.get('price', '')}\n"
        product_text += f"누적거래량: {result.get('status_value', '').strip()}건"

        # 이전/다음 버튼 활성화 상태 업데이트
        self.left_button.setEnabled(result.get("enable_prev", False))
        self.right_button.setEnabled(result.get("enable_next", False))

        # Reset detail info and macro settings when changing products
        self.detail_info.clear()
        self.size_combo.setEnabled(False)
        self.quantity_spin.setValue(1)
        self.start_button.setEnabled(False)  # Always disable macro button after search

        if result.get('additional_info'):
            product_text += f"\n{result.get('additional_info')}"
            self.search_details_button.setEnabled(False)
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)

        self.product_info.setText(product_text)

        if result.get('image'):
            self.image_label.setPixmap(result['image'])
            self.image_label.setScaledContents(True)

    def handle_details(self, details):
        if "error" in details:
            self.detail_info.append(f"상세 정보 조회 실패: {details['error']}")
            self.size_combo.setEnabled(False)
            self.quantity_spin.setEnabled(False)
            self.start_button.setEnabled(False)
            return

        info_text = ""
        
        # Model number and color line
        model_no = details.get('model_no', 'N/A').strip()
        color = details.get('color', 'N/A').strip()
        if model_no != '-' and color != '-':
            info_text += f"{model_no} — {color}<br>"
        elif model_no != '-' or color != '-':
            info_text += f"{model_no if model_no != '-' else ''}{color if color != '-' else ''}<br>"
        
        # Release date with D-day
        release_date = details.get('release_date', 'N/A').strip()
        d_day = details.get('d_day', '')
        
        if release_date != 'N/A' and release_date != '-':
            try:
                year, month, day = release_date.split('/')
                # D-day 정보 추가
                d_day_color = "black"
                if d_day.startswith(" (D-") and not d_day.startswith(" (D-DAY"):
                    d_day_color = "blue"  # 앞으로 다가올 출시일은 파란색
                elif d_day.startswith(" (D+"):
                    d_day_color = "green"  # 이미 지난 출시일은 초록색
                elif d_day.startswith(" (D-DAY"):
                    d_day_color = "red"  # 당일 출시는 빨간색
                
                info_text += f"20{year}년 {month}월 {day}일 출시<span style='color: {d_day_color};'>{d_day}</span><br>"
            except:
                info_text += f"{release_date} 출시<span style='color: black;'>{d_day}</span><br>"
        
        # Release price
        release_price = details.get('release_price', 'N/A').strip()
        if release_price != 'N/A':
            info_text += f"발매 정가    {release_price}<br>"
        
        # Recent price
        recent_price = details.get('recent_price', 'N/A')
        if recent_price != 'N/A':
            info_text += f"최근 거래가 {recent_price}원<br>"
        
        # Price fluctuation
        fluctuation = details.get('fluctuation', 'N/A')
        if fluctuation != 'N/A':
            fluctuation_type = details.get('fluctuation_type', '')
            if fluctuation_type == 'increase':
                info_text += f"<span style='color: red;'>{fluctuation}</span>"
            elif fluctuation_type == 'decrease':
                info_text += f"<span style='color: green;'>{fluctuation}</span>"
            else:
                info_text += fluctuation
        
        self.detail_info.setHtml(info_text)
        
        # Update size combo box with available sizes
        if 'sizes' in details and details['sizes']:
            self.size_combo.clear()
            self.size_combo.addItems(details['sizes'])
            self.size_combo.setEnabled(True)
            self.quantity_spin.setEnabled(True)
            if self.controller.is_logged_in():
                # 매크로 시작 버튼 활성화 및 연결
                self.start_button.setEnabled(True)
                try:
                    self.start_button.clicked.disconnect()
                except TypeError:
                    pass
                self.start_button.clicked.connect(self.start_macro)
                self.start_button.setText('매크로 시작')
        else:
            self.size_combo.setEnabled(False)
            self.quantity_spin.setEnabled(False)
            self.start_button.setEnabled(False)

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.previous_result()
        elif event.key() == Qt.Key.Key_Right:
            self.next_result()

    def start_macro(self):
        """매크로 시작 UI 핸들러"""
        size = self.size_combo.currentText()
        quantity = self.quantity_spin.value()
        
        if self.controller.start_macro(size, quantity):
            # 버튼 상태 변경
            self.start_button.setText("매크로 중지")
            try:
                self.start_button.clicked.disconnect()
            except TypeError:
                pass
            self.start_button.clicked.connect(self.stop_macro)

    def stop_macro(self):
        """매크로 중지 UI 핸들러"""
        if self.controller.stop_macro():
            # 버튼 상태는 매크로 상태 변경 핸들러(handle_macro_status)에서 처리됨
            pass

    def handle_macro_status(self, status):
        if status:
            self.start_button.setText('매크로 중지')
            try:
                self.start_button.clicked.disconnect()
            except TypeError:
                pass
            self.start_button.clicked.connect(self.stop_macro)
        else:
            self.start_button.setText('매크로 시작')
            try:
                self.start_button.clicked.disconnect()
            except TypeError:
                pass
            self.start_button.clicked.connect(self.start_macro)
        self.start_button.setEnabled(True)