from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
import sys
import os

class BrowserManager:
    def __init__(self):
        options = webdriver.ChromeOptions()

        # user-agent 설정 (25년 3월 기준 크롬 134 버전 / CSR 페이지 크롤링 시 설정필수)
        if sys.platform == 'darwin':
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36' 
        elif sys.platform == 'win32':
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            # 윈도우에서 크롬 실행파일 경로 지정
            chrome_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            if not os.path.exists(chrome_path):
                chrome_path = r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            options.binary_location = chrome_path

        options.add_argument(f'user-agent={user_agent}')
        options.add_argument("--headless")  # 크롬 창 숨기기
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver_path = chromedriver_autoinstaller.install()
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_browser(self):
        return self.driver