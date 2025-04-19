from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton


class LoginPopup(QDialog):
    login_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("크림 로그인")
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Email input
        email_layout = QHBoxLayout()
        email_label = QLabel("이메일:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('크림 계정 이메일 입력')
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Password input
        password_layout = QHBoxLayout()
        password_label = QLabel("비밀번호:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText('비밀번호 입력')
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # Login button
        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def handle_login(self):
        email = self.email_input.text()
        password = self.password_input.text()
        self.login_requested.emit(email, password)
        self.accept() 