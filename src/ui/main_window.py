# ui/main_window.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QTextEdit


class MainWindow(QWidget):

    def __init__(self, plugin_manager):

        super().__init__()
        self.setWindowTitle("크림 보관판매 매크로")
        self.plugin_manager = plugin_manager

        # 필요한 플러그인 인스턴스 획득
        self.login_plugin = plugin_manager.get_plugin("login")
        self.search_plugin = plugin_manager.get_plugin("search")
        self.detail_plugin = plugin_manager.get_plugin("detail")
        self.macro_plugin = plugin_manager.get_plugin("macro")

        # 위젯 구성 (간략히 표현)
        self.email_input = QLineEdit(); self.pw_input = QLineEdit()
        self.login_button = QPushButton("로그인")
        self.search_input = QLineEdit(); self.search_button = QPushButton("검색")
        self.detail_button = QPushButton("상세정보검색")
        self.start_macro_button = QPushButton("매크로 시작")
        self.log_output = QTextEdit(); self.log_output.setReadOnly(True)

        # 레이아웃 배치
        layout = QVBoxLayout()

        # ... (Add widgets to layout)
        self.setLayout(layout)

        # 플러그인 시그널 <-> UI 슬롯 연결
        if hasattr(self.login_plugin, 'login_status'):
            self.login_plugin.login_status.connect(self.handle_login_status)
        if hasattr(self.search_plugin, 'search_result'):
            self.search_plugin.search_result.connect(self.handle_search_result)
        if hasattr(self.macro_plugin, 'log_message'):
            self.macro_plugin.log_message.connect(self.append_log)

        # 버튼 이벤트 -> 플러그인 호출 연결
        self.login_button.clicked.connect(lambda:
                                          self.login_plugin.login(self.email_input.text(), self.pw_input.text()))
        self.pw_input.returnPressed.connect(lambda:
                                            self.login_plugin.login(self.email_input.text(), self.pw_input.text()))
        self.search_button.clicked.connect(lambda:
                                           self.search_plugin.search(self.search_input.text()))
        self.detail_button.clicked.connect(lambda:
                                           self.show_detail())  # 상세조회 처리 (별도 메서드 내부에서 detail_plugin 호출)
        self.start_macro_button.clicked.connect(lambda:
                                                self.start_macro())

    def handle_login_status(self, success, message):

        if success:
            self.login_button.setEnabled(False)
            # 로그인 성공 시 검색/매크로 관련 UI 활성화 등

        self.log_output.append(message)

    def handle_search_result(self, result_data: dict):
        # result_data 처리하여 UI에 목록 표시
        ...

    def show_detail(self):

        # 현재 선택된 상품 ID를 가져와 detail_plugin 호출
        product_id = self.get_selected_product_id()
        info = self.detail_plugin.get_details(product_id)

        # info 내용을 UI에 표시 (ex: 메시지박스나 별도 텍스트 출력)
        ...

    def start_macro(self):

        # 사용자 입력값 (예: 상품ID, 수량 등) 가져와 매크로 시작
        product_id = self.get_selected_product_id()
        size = self.get_selected_size()
        quantity = self.get_quantity()
        self.macro_plugin.start(product_id, size, quantity)

    def append_log(self, text: str):

        # 매크로로부터 온 로그 메시지 출력
        self.log_output.append(text)