from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging
from config import Config

class BrowserManager:
    def __init__(self):
        options = Options()
        options.add_argument("--headless")  # UI 없이 실행
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(Config.CHROME_DRIVER_PATH)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self, email, password):
        """ 크림 로그인 """
        self.driver.get(Config.LOGIN_URL)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))).send_keys(email)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))).send_keys(password)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()
        logging.info("로그인 완료")

    def go_to_inventory(self, product_id):
        """ 인벤토리 페이지 이동 """
        url = Config.INVENTORY_URL(product_id)
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        logging.info(f"인벤토리 페이지 이동: {url}")

    def click_element(self, css_selector):
        """ 특정 요소 클릭 """
        element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))
        element.click()
        logging.info(f"클릭: {css_selector}")

    def close(self):
        """ 브라우저 종료 """
        self.driver.quit()
        logging.info("브라우저 종료")