from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel, QTextEdit, QHBoxLayout, QMessageBox
)
from PyQt6.QtGui import QTextCursor, QPixmap, QIcon
from PyQt6.QtCore import pyqtSignal, Qt
import requests
import sys
import os

class UI(QWidget):
    search_signal = pyqtSignal(str)
    next_signal = pyqtSignal()
    prev_signal = pyqtSignal()
    login_signal = pyqtSignal(str, str)
    macro_signal = pyqtSignal(str, str, str)
    details_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

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
        self.pw_input.returnPressed.connect(self.login_button_clicked)
        self.login_button.clicked.connect(self.login_button_clicked)
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

        self.search_details_button = QPushButton('제품 상세정보', self)
        self.search_details_button.setEnabled(False)
        self.search_details_button.clicked.connect(self.product_details)
        horizontal_layout.addWidget(self.search_details_button, 1)

        horizontal_layout.addSpacing(20)
        screen = QApplication.primaryScreen()

        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            horizontal_layout.addSpacing(20)

        self.start_button = QPushButton('매크로 시작', self)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_macro)
        horizontal_layout.addWidget(self.start_button, 2)

        layout.addLayout(horizontal_layout)

        log_image_layout = QHBoxLayout()

        image_label = QLabel()
        image_label.setObjectName("image_label")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        image_label.setFixedWidth(screen_width // 3)
        image_label.setFixedHeight(screen_width // 3)
        image_label.setScaledContents(True)
        image_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')))

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
        stacked_layout.addWidget(image_label)
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

    def emit_login(self):
        self.login_signal.emit(self.email_input.text(), self.pw_input.text())

    def login_button_clicked(self):
        email = self.email_input.text()
        pw = self.pw_input.text()
        if self.is_valid_email(email):
            if self.is_valid_password(pw):
                self.emit_login()
            else:
                QMessageBox.warning(self, "비밀번호 오류", "영문, 숫자, 특수문자를 조합해서 입력해주세요. (8-16자)")
        else:
            QMessageBox.warning(self, "이메일 오류", "이메일 주소를 정확히 입력해주세요.")

    def is_valid_email(self, email):
        import re
        regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.match(regex, email)

    def is_valid_password(self, password):
        import re
        has_valid_length = 8 <= len(password) <= 16
        has_letter = re.search(r'[A-Za-z]', password)
        has_number = re.search(r'[0-9]', password)
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>+-]', password)
        return all([has_valid_length, has_letter, has_number, has_special])

    def emit_macro(self):
        product_id = self.product_info.toPlainText().split('\n')[0].split(':')[-1].strip()
        self.macro_signal.emit(self.email_input.text(), self.pw_input.text(), product_id)

    def start_macro(self):
        self.emit_macro()

    def search_product(self):
        self.emit_search()

    def next_result(self):
        self.next_signal.emit()
    
    def previous_result(self):
        self.prev_signal.emit()
    
    def product_details(self):
        self.details_signal.emit()

    def update_product_info(self, product_data):
        if "error" in product_data:
            self.product_info.setText(product_data["error"])
            return
        
        product_text = f"제품 ID: {product_data['product_id']}\n제품명: {product_data['product_name']}\n한글명: {product_data['translated_name']}\n가격: {product_data['amount']}"
        self.product_info.setText(product_text)
        
        image_data = product_data['image_data']
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)
        
        self.search_details_button.setEnabled(True)
    
    def update_log(self, message):
        self.log_output.append(message)
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)