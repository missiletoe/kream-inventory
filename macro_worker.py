from PyQt6.QtCore import QObject, pyqtSignal
import time

class MacroWorker(QObject):
    log_message = pyqtSignal(str, bool)

    def __init__(self, kream_macro):
        super().__init__()
        self.kream_macro = kream_macro
        self.is_running = True

    def run(self):
        while self.is_running:
            self.log_message.emit(f"[{time.strftime('%H:%M:%S')}] 매크로 실행 중...", False)
            time.sleep(5)  # 매크로 실행 주기 (5초)
        
        self.log_message.emit(f"[{time.strftime('%H:%M:%S')}] 매크로 중지됨", False)