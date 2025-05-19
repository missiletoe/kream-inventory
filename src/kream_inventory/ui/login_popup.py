"""크림 로그인 팝업 UI를 정의합니다."""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LoginPopup(QDialog):
    """로그인 정보를 입력받는 팝업창 클래스입니다."""

    login_requested = pyqtSignal(str, str)

    def __init__(self: "LoginPopup", parent: Optional[QWidget] = None) -> None:
        """Login Popup 인스턴스를 초기화합니다.

        Args:
            parent: 부모 위젯입니다.
        """
        super().__init__(parent)
        self.setWindowTitle("크림 로그인")
        self.setModal(True)
        self.initUI()

    def initUI(self: "LoginPopup") -> None:
        """로그인 팝업의 UI를 초기화하고 구성합니다."""
        layout = QVBoxLayout()

        # Email input
        email_layout = QHBoxLayout()
        email_label = QLabel("이메일:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("크림 계정 이메일 입력")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Password input
        password_layout = QHBoxLayout()
        password_label = QLabel("비밀번호:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("비밀번호 입력")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # Status message
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Login button
        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def handle_login(self: "LoginPopup") -> None:
        """로그인 버튼 클릭 또는 Enter 키 입력 시 호출됩니다.

        입력된 이메일과 비밀번호로 login_requested 시그널을 발생시킵니다.
        """
        email = self.email_input.text()
        password = self.password_input.text()

        # Clear any previous error messages
        self.status_label.setVisible(False)
        self.status_label.setText("")

        # Disable the login button during the login attempt
        self.login_button.setEnabled(False)

        # Emit the login request signal
        self.login_requested.emit(email, password)
        # Don't close the popup automatically, wait for login status

    def handle_login_status(
        self: "LoginPopup", is_logged_in: bool, message: str
    ) -> None:
        """로그인 시도 결과를 처리합니다.

        로그인 성공 시 팝업을 닫고, 실패 시 에러 메시지를 표시합니다.

        Args:
            is_logged_in: 로그인 성공 여부입니다.
            message: 로그인 결과 메시지입니다.
        """
        # Only close the popup if login was successful
        if is_logged_in:
            self.accept()
        else:
            # Display error message and keep the popup open for retry
            self.status_label.setText(message)
            self.status_label.setVisible(True)
            # Re-enable the login button
            self.login_button.setEnabled(True)
