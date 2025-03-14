import time
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from macro_worker import MacroWorker
from config import Config
from ui import UI

def create_dummy_inventory_page():
    html_content = """
    <html>
      <head><title>Inventory Test</title></head>
      <body>
        <!-- 인벤토리 페이지 조건 충족 요소 -->
        <div class="inventory_size_list">
          <div class="inventory_size_item"><input type="text" value=""></div>
        </div>
        <div class="complete_btn_box" style="cursor:pointer;">Complete</div>
        <!-- toast 요소: show 클래스와 테스트 텍스트 -->
        <div class="toast show" style="display:block;">신규 보관신청이 제한된 카테고리의 상품입니다.</div>
        <div class="layer_container"></div>
        <span class="title_txt">신청내역</span>
      </body>
    </html>
    """
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp_file.write(html_content.encode('utf-8'))
    tmp_file.close()
    return tmp_file.name

def integration_test():
    # dummy 인벤토리 페이지 생성 및 파일 URL 구성
    inventory_page_path = create_dummy_inventory_page()
    file_url = "file://" + inventory_page_path

    # ChromeDriver 설정 (Config의 CHROME_DRIVER_PATH 사용)
    service = ChromeService(executable_path=Config.CHROME_DRIVER_PATH)
    browser = webdriver.Chrome(service=service)

    # dummy 페이지 로드
    browser.get(file_url)
    time.sleep(1)  # 페이지 로드 대기

    # MacroWorker 인스턴스 생성 (테스트용 dummy 인자 사용)
    worker = MacroWorker(browser, "test@example.com", "password", size=1, qty=1, click_term=5)

    logs = []
    def log_slot(message):
        print("LOG:", message)
        logs.append(message)

    # 로그 슬롯 연결
    worker.log_message.connect(log_slot)

    # 매크로 실행 (run() 메서드 내에서 조건에 따라 return)
    worker.run()

    # 매크로 실행 결과 로그 확인
    if any("신규 보관신청이 제한된 카테고리의 상품입니다." in log for log in logs):
        print("매크로가 정상 작동함.")
    else:
        print("매크로 실행 결과 예상과 다름.")

    # 정리: 브라우저 종료 및 임시 파일 삭제
    browser.quit()
    os.unlink(inventory_page_path)

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    from ui import UI
    from macro_worker import MacroWorker
    from unittest.mock import MagicMock
    import sys

    app = QApplication(sys.argv)
    
    # Create a mocked MacroWorker instance using MagicMock (mockito style)
    mock_macro_worker = MagicMock(spec=MacroWorker)
    # Define behavior for the run() method
    mock_macro_worker.run.side_effect = lambda: print('Mock macro worker run executed')
    
    # Initialize the UI and inject the mocked MacroWorker
    ui = UI()
    ui.macro_worker = mock_macro_worker
    ui.show()
    
    sys.exit(app.exec())