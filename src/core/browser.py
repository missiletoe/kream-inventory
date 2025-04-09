# core/browser.py
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

class BrowserManager:

    def __init__(self, config):

        options = webdriver.ChromeOptions()

        # 설정에서 user_agent와 headless 옵션 불러오기
        ua = config.get('Browser', 'user_agent', fallback=True)
        headless = config.getboolean('Browser', 'headless', fallback=True)
        options.add_argument(f"user-agent={ua}")

        if headless:
            options.add_argument("--headless")

        # 기타 옵션 설정
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver_path = chromedriver_autoinstaller.install()
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_driver(self):
        return self.driver

    def quit(self):
        self.driver.quit()
