from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from browser_manager import BrowserManager
from webdriver_manager.chrome import ChromeDriverManager

class KreamMacro:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.browser = self.browser_manager.driver  # BrowserManager의 WebDriver 재사용
        self.is_logged_in = False

    def login(self, email, password):
        return self.browser_manager.login(email, password)

    def get_product_details(self, product_id):
        self.browser.get(f'https://kream.co.kr/products/{product_id}')
        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
            details = self.browser.find_elements(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info"]')
            colors = self.browser.find_element(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info color-target"]').text
            return {
                "release_price": details[0].text,
                "model_number": details[1].text,
                "release_date": details[2].text,
                "color": colors
            }
        except Exception as e:
            print(f'제품 정보 조회 실패: {e}')
        return None

    def close(self):
        self.browser_manager.close()
