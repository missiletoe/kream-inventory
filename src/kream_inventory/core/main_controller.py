from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal


class MainController(QObject):
    """
    컨트롤러 클래스: UI와 플러그인 간의 상호작용을 관리
    UI로부터 요청을 받아 적절한 플러그인에 전달하고 결과를 다시 UI에 전달합니다.
    """
    # 시그널 정의
    login_status_changed = pyqtSignal(bool, str)
    search_result_received = pyqtSignal(dict)
    details_received = pyqtSignal(dict)
    sizes_ready = pyqtSignal(list)
    log_message = pyqtSignal(str)
    macro_status_changed = pyqtSignal(bool)

    def __init__(self, plugin_manager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.browser = plugin_manager.browser
        self.login_plugin = plugin_manager.get_plugin("login")
        self.search_plugin = plugin_manager.get_plugin("search")
        self.detail_plugin = plugin_manager.get_plugin("detail")
        self.macro_plugin = plugin_manager.get_plugin("macro")
        self.logged_in = False
        self.macro_running = False
        self.current_product_id = None
        
        # 플러그인 시그널 연결
        self._connect_plugin_signals()
    
    def _connect_plugin_signals(self):
        """플러그인의 시그널을 컨트롤러 시그널에 연결"""
        if hasattr(self.login_plugin, 'login_status'):
            self.login_plugin.login_status.connect(self._handle_login_status)
        if hasattr(self.search_plugin, 'search_result'):
            self.search_plugin.search_result.connect(self._handle_search_result)
        if hasattr(self.macro_plugin, 'log_message'):
            self.macro_plugin.log_message.connect(self._handle_log_message)
        if hasattr(self.macro_plugin, 'macro_status_changed'):
            self.macro_plugin.macro_status_changed.connect(self._handle_macro_status)
        if hasattr(self.detail_plugin, 'sizes_ready'):
            self.detail_plugin.sizes_ready.connect(self._handle_sizes_ready)
        if hasattr(self.detail_plugin, 'details_ready'):
            self.detail_plugin.details_ready.connect(self._handle_details_ready)
    
    # 플러그인 시그널 핸들러
    def _handle_login_status(self, is_logged_in, message):
        self.logged_in = is_logged_in
        self.login_status_changed.emit(is_logged_in, message)
    
    def _handle_search_result(self, result):
        self.current_product_id = result.get('id', '')
        self.search_result_received.emit(result)
    
    def _handle_log_message(self, message):
        self.log_message.emit(message)
    
    def _handle_macro_status(self, status):
        self.macro_running = status
        self.macro_status_changed.emit(status)
    
    def _handle_sizes_ready(self, sizes):
        self.sizes_ready.emit(sizes)
    
    def _handle_details_ready(self, details):
        self.details_received.emit(details)
    
    # UI 요청을 처리하는 메서드
    def login(self, username, password):
        """로그인 처리"""
        self.login_plugin.login(username, password)
    
    def logout(self):
        """로그아웃 처리"""
        self.logged_in = False
        self.log_message.emit("로그아웃되었습니다.")
        self.login_status_changed.emit(False, "로그아웃되었습니다.")
    
    def search_product(self, query):
        """제품 검색"""
        self.search_plugin.search(query)
    
    def next_result(self):
        """다음 검색 결과로 이동"""
        try:
            self.search_plugin.next_result()
        except Exception as e:
            self.log_message.emit(f"오류 발생: {e}")
    
    def previous_result(self):
        """이전 검색 결과로 이동"""
        self.search_plugin.previous_result()
    
    def get_product_details(self):
        """현재 제품의 상세 정보 요청"""
        if not self.logged_in:
            self.log_message.emit("로그인이 필요합니다. 로그인해주세요.")
            return False
            
        if self.current_product_id:
            self.detail_plugin.get_details(self.current_product_id)
            return True
        else:
            self.log_message.emit("제품을 먼저 선택해주세요.")
            return False
    
    def start_macro(self, size, quantity):
        """매크로 시작"""
        if not self.current_product_id:
            self.log_message.emit("제품을 먼저 선택해주세요.")
            return False

        if self.macro_running:
            self.log_message.emit("매크로가 이미 실행 중입니다.")
            return False

        try:
            self.macro_plugin.start_macro(self.current_product_id, size, str(quantity))
            return True
        except Exception as e:
            self.log_message.emit(f"매크로 시작 실패: {str(e)}")
            return False
    
    def stop_macro(self):
        """매크로 중지"""
        if not self.macro_running:
            self.log_message.emit("실행 중인 매크로가 없습니다.")
            return False
            
        try:
            self.macro_plugin.stop()
            return True
        except Exception as e:
            self.log_message.emit(f"매크로 중지 실패: {str(e)}")
            return False
    
    def is_logged_in(self):
        """로그인 상태 반환"""
        return self.logged_in
    
    def is_macro_running(self):
        """매크로 실행 상태 반환"""
        return self.macro_running
    
    def mask_email(self, email):
        """이메일 주소 마스킹"""
        if '@' not in email:
            return email
            
        username, domain = email.split('@')
        if len(username) <= 2:
            masked_username = username[0] + '*' * (len(username) - 1)
        else:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
            
        return f"{masked_username}@{domain}" 