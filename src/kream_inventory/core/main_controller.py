from PyQt6.QtCore import QObject, pyqtSignal


class MainController(QObject):

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
        
        self._connect_plugin_signals()
    
    def _connect_plugin_signals(self):
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
    
    def login(self, username, password):
        self.login_plugin.login(username, password)
    
    def logout(self):
        try:
            # Attempt web logout via the login plugin
            self.login_plugin.logout() 
            self.log_message.emit("크림 웹사이트에서 로그아웃을 시도했습니다.")
        except Exception as e:
            self.log_message.emit(f"웹 로그아웃 중 오류 발생: {e}")
        finally:
            # Update internal state and notify UI regardless of web logout success
            self.logged_in = False
            self.log_message.emit("로그아웃되었습니다.")
            self.login_status_changed.emit(False, "로그아웃되었습니다.")
    
    def search_product(self, query):
        self.search_plugin.search(query)
    
    def next_result(self):
        try:
            self.search_plugin.next_result()
        except Exception as e:
            self.log_message.emit(f"오류 발생: {e}")
    
    def previous_result(self):
        self.search_plugin.previous_result()
    
    def get_product_details(self):
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
        return self.logged_in
    
    def is_macro_running(self):
        return self.macro_running
    
    def mask_email(self, email):
        if '@' not in email:
            return email
            
        username, domain = email.split('@')
        if len(username) <= 2:
            masked_username = username[0] + '*' * (len(username) - 1)
        else:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
            
        return f"{masked_username}@{domain}" 