from selenium import webdriver
import chromedriver_autoinstaller

class BrowserManager:
    def __init__(self):
        options = webdriver.ChromeOptions()
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'  # 사용자 에이전트 설정
        options.add_argument(f'user-agent={user_agent}')  # 사용자 에이전트 옵션 추가
        options.add_argument("--headless")  # UI 없이 실행
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        chromedriver_autoinstaller.install()
        self.driver = webdriver.Chrome(options=options)

    def get_browser(self):
        return self.driver