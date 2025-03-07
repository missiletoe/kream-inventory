from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
from PyQt6.QtCore import pyqtSignal, QObject

class SearchProduct(QObject):
    search_result_signal = pyqtSignal(dict)
    
    def __init__(self, browser_manager):
        super().__init__()
        self.browser_manager = browser_manager
        self.browser = browser_manager.driver
        self.search_results = []
        self.current_index = 0
    
    def search(self, keyword):
        search_url = f'https://kream.co.kr/search?keyword={keyword}&tab=products&sort=popular_score'
        self.browser.get(search_url)
        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="search_result_item product"]')))
            self.search_results = self.browser.find_elements(By.CSS_SELECTOR, 'div[class="search_result_item product"]')
            self.current_index = 0
            self.emit_search_result()
        except TimeoutException:
            self.search_result_signal.emit({"error": "검색 결과가 없습니다."})
    
    def next_result(self):
        if self.search_results and self.current_index < len(self.search_results) - 1:
            self.current_index += 1
            self.emit_search_result()
    
    def prev_result(self):
        if self.search_results and self.current_index > 0:
            self.current_index -= 1
            self.emit_search_result()
    
    def emit_search_result(self):
        try:
            result = self.search_results[self.current_index]
            product_name = result.find_element(By.CSS_SELECTOR, 'p[class="name"]').text
            product_translated_name = result.find_element(By.CSS_SELECTOR, 'p[class="translated_name"]').text
            product_id = result.get_attribute("data-product-id")
            amount = result.find_element(By.CSS_SELECTOR, 'p[class="amount"]').text
            image_link = result.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
            image_data = requests.get(image_link).content
            
            self.search_result_signal.emit({
                "product_name": product_name,
                "translated_name": product_translated_name,
                "product_id": product_id,
                "amount": amount,
                "image_data": image_data
            })
        except NoSuchElementException:
            self.search_result_signal.emit({"error": "검색 결과를 불러올 수 없습니다."})