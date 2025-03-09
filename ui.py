from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QLabel
)
from PyQt6.QtGui import QPixmap, QIcon, QTextCursor
from PyQt6.QtCore import pyqtSignal, Qt
import requests
import sys
import os
from login import LoginManager
from search_product import SearchProduct
from search_product_details import SearchProductDetails
from browser_manager import BrowserManager
from macro_worker import start_macro

class UI(QWidget):
    browser_instance = None
    search_signal = pyqtSignal(str)
    next_signal = pyqtSignal()
    prev_signal = pyqtSignal()
    login_signal = pyqtSignal(str, str)
    macro_signal = pyqtSignal(str, str, str)
    details_signal = pyqtSignal()

    def __init__(self, browser=None):
        super().__init__()
        self.initUI()
        self.browser = BrowserManager().get_browser()
        self.login_manager = LoginManager(browser=self.browser)
        self.logged_in = False
        self.login_manager.login_status.connect(self.handle_login_status)
        self.search_product_handler = SearchProduct(browser=self.browser)
        self.search_signal.connect(self.search_product_handler.search_product)
        self.search_product_handler.search_result.connect(self.handle_search_result)
        self.next_signal.connect(lambda: self.safe_next_result())
        self.prev_signal.connect(self.search_product_handler.previous_result)

    def initUI(self):
        self.setWindowTitle('크림 보관판매 매크로 by missiletoe')

        # 아이콘 경로 설정
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.icns")

        # MacOS의 경우 QGuiApplication을 사용하여 독 아이콘 설정
        if sys.platform == "darwin":
            from PyQt6.QtGui import QGuiApplication
            QGuiApplication.setWindowIcon(QIcon(icon_path))

        # 윈도우 & 리눅스의 경우 일반 창 아이콘 설정
        else:
            QApplication.setWindowIcon(QIcon(icon_path))

        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        self.setGeometry(0, 0, int(screen_width // 1.5), int((screen_height // 1.5) - 22)) # 창 크기를 화면의 절반으로 설정

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout()
        horizontal_layout = QHBoxLayout()

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText('크림 계정 이메일 입력')
        self.email_input.setClearButtonEnabled(True)
        horizontal_layout.addWidget(self.email_input, 3)

        self.pw_input = QLineEdit(self)
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.setPlaceholderText('비밀번호 입력')
        self.pw_input.setClearButtonEnabled(True)
        horizontal_layout.addWidget(self.pw_input, 2)

        self.login_button = QPushButton('로그인', self)
        self.pw_input.returnPressed.connect(lambda: self.login_manager.login(self.email_input.text(), self.pw_input.text()))
        self.login_button.clicked.connect(lambda: self.login_manager.login(self.email_input.text(), self.pw_input.text()))
        horizontal_layout.addWidget(self.login_button, 1)

        horizontal_layout.addSpacing(20)

        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            horizontal_layout.addSpacing(20)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText('제품명 입력')
        self.search_input.returnPressed.connect(self.search_product)
        horizontal_layout.addWidget(self.search_input, 3)

        self.search_button = QPushButton('검색', self)
        self.search_button.clicked.connect(self.search_product)
        horizontal_layout.addWidget(self.search_button, 1)

        self.search_details_button = QPushButton('상세정보검색', self)
        self.search_details_button.setEnabled(False)
        self.search_details_button.clicked.connect(self.product_details)
        horizontal_layout.addWidget(self.search_details_button, 1)

        horizontal_layout.addSpacing(20)
        screen = QApplication.primaryScreen()

        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            horizontal_layout.addSpacing(20)

        # 매크로는 click_term 초마다 반복 실행됨 (while loop 사용)
        self.start_button = QPushButton('매크로 시작', self)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(lambda: start_macro(self))
        horizontal_layout.addWidget(self.start_button, 2)

        layout.addLayout(horizontal_layout)
        self.product_info = QTextEdit(self)
        self.product_info.setReadOnly(True)
        self.product_info.setPlaceholderText('제품 정보를 여기에 표시합니다.')
        layout.addWidget(self.product_info)

        log_image_layout = QHBoxLayout()

        self.image_label = QLabel()
        self.image_label.setObjectName("image_label")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        self.image_label.setFixedWidth(screen_width // 3)
        self.image_label.setFixedHeight(screen_width // 3)
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')))

        left_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271220.png'
        left_icon = QIcon()
        left_icon_data = requests.get(left_icon_url).content
        left_icon_pixmap = QPixmap()
        left_icon_pixmap.loadFromData(left_icon_data)
        left_icon.addPixmap(left_icon_pixmap)
        self.left_button = QPushButton(left_icon, '', self)
        self.left_button.setFixedSize(50, 50)

        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            self.left_button.setFixedSize(100, 100)

        self.left_button.clicked.connect(self.previous_result)
        self.left_button.setEnabled(False)

        right_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271228.png'
        right_icon = QIcon()
        right_icon_data = requests.get(right_icon_url).content
        right_icon_pixmap = QPixmap()
        right_icon_pixmap.loadFromData(right_icon_data)
        right_icon.addPixmap(right_icon_pixmap)
        self.right_button = QPushButton(right_icon, '', self)
        self.right_button.setFixedSize(50, 50)

        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            self.right_button.setFixedSize(100, 100)
        self.right_button.clicked.connect(self.next_result)
        self.right_button.setEnabled(False)
        
        stacked_layout = QHBoxLayout()
        stacked_layout.addWidget(self.left_button, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stacked_layout.addWidget(self.image_label)
        stacked_layout.addWidget(self.right_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        image_layout = QVBoxLayout()
        image_layout.addLayout(stacked_layout)
        
        log_image_layout.addLayout(image_layout)

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText('제품 정보와 매크로 활동 기록이 여기에 표시됩니다.')
        log_image_layout.addWidget(self.log_output)

        layout.addLayout(log_image_layout)

        self.setLayout(layout)
    
    def emit_search(self):
        self.search_signal.emit(self.search_input.text())

    def emit_login(self, username, password):
        self.login_signal.emit(username, password)

    def search_product(self):
        self.emit_search()

    def next_result(self):
        self.next_signal.emit()

    def safe_next_result(self):
        try:
            self.search_product_handler.next_result()
        except Exception as e:
            self.log_output.append(f"오류 발생: {e}")
    
    def previous_result(self):
        self.prev_signal.emit()
    
    def product_details(self):
        self.details_signal.emit()

    def update_log(self, message, html=False):
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)
        if html:
            self.log_output.insertHtml(message + '<br>')
        else:
            self.log_output.insertPlainText(message + '\n')

    def handle_search_result(self, result):

        # 검색 결과가 없을 경우 버튼 비활성화
        if not result:
            product_text = "검색 결과 없음"
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)
            self.search_details_button.setEnabled(False)
            self.start_button.setEnabled(False)
            return
        
        product_text = f"[{result.get('id', '')}] {result.get('name', '')}"
        product_text += f"  |  {result.get('translated_name', '')}"
        product_text += f"\n{result.get('price', '')}"
        product_text += f"  |  {result.get('status_value', '')}"

        self.search_details_button.setEnabled(True)
        self.current_product_id = result.get('id', '')
        self.left_button.setEnabled(True)
        self.right_button.setEnabled(True)

        # 로그인 상태일 경우 매크로 시작 버튼 활성화
        if self.logged_in:
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)

        # 브랜드배송 제품인 경우
        if result.get('is_brand'):
            product_text += "\n보관판매가 불가능한 브랜드배송 제품입니다."
            self.search_details_button.setEnabled(False)
        
        # 상세정보 추가 (발매가 | 모델번호 | 출시일 | 대표색상)
        if result.get('additional_info'):
            product_text += f"\n{result.get('additional_info')}"
            self.search_details_button.setEnabled(False)
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)

        self.product_info.setText(product_text)
        if result.get('image'):
            self.image_label.setPixmap(result['image'])
            self.image_label.setScaledContents(True)

    def handle_login_status(self, is_logged_in, message):
        if is_logged_in:
            self.logged_in = True
            self.email_input.setEnabled(False)
            self.pw_input.setEnabled(False)
            self.login_button.setEnabled(False)
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)
            self.search_details_button.setEnabled(False)
            self.log_output.append(message)

            # 로그인 성공 시 제품 ID 정보가 있을 경우 매크로 시작 버튼 활성화
            if hasattr(self, 'current_product_id') and self.current_product_id:
                self.start_button.setEnabled(True)

        else:
            self.logged_in = False
            self.login_button.setEnabled(True)
            self.log_output.append(message)
            self.start_button.setEnabled(False)

    # 상세정보검색 버튼을 눌렀을 때 실행됨
    def product_details(self):
        if not hasattr(self, 'current_product_id') or not self.current_product_id:
            product_text = "제품 ID 정보가 없습니다."
            return
        spd = SearchProductDetails(self.browser, self.current_product_id)
        additional_info = spd.execute()
        self.product_info.append(" | ".join(additional_info))
