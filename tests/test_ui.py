import sys
import time
import tempfile
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from macro_worker import MacroWorker
from config import Config

class TestUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macro Test UI")
        self.resize(600, 400)
        self.text_edit = QTextEdit(self)
        self.run_button = QPushButton("Run Macro", self)
        self.run_button.clicked.connect(self.run_macro)
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.run_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        # Setup dummy inventory page and browser
        self.browser = self.setup_browser()
        # MacroWorker 생성 (dummy 인자 사용)
        self.worker = MacroWorker(self.browser, "test@example.com", "password", size=1, qty=1, click_term=5)
        self.worker.log_message.connect(self.log_message)
    
    def setup_browser(self):
        html_content = """
        <html>
          <head><title>Inventory Test</title></head>
          <body>
            <div class="inventory_size_list">
              <div class="inventory_size_item"><input type="text" value=""></div>
            </div>
            <div class="complete_btn_box" style="cursor:pointer;">Complete</div>
            <div class="toast show" style="display:block;">신규 보관신청이 제한된 카테고리의 상품입니다.</div>
            <div class="layer_container"></div>
            <span class="title_txt">신청내역</span>
          </body>
        </html>
        """
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_file.write(html_content.encode("utf-8"))
        tmp_file.close()
        file_url = "file://" + tmp_file.name
        
        service = ChromeService(executable_path=Config.CHROME_DRIVER_PATH)
        browser = webdriver.Chrome(service=service)
        browser.get(file_url)
        time.sleep(1)
        return browser
    
    def log_message(self, message):
        self.text_edit.append(message)
    
    def run_macro(self):
        self.text_edit.append("Starting Macro...")
        self.worker.run()
    
    def closeEvent(self, event):
        # UI 종료 시 브라우저 종료
        self.worker.browser.quit()
        super().closeEvent(event)

def main_ui():
    app = QApplication(sys.argv)
    window = TestUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main_ui()