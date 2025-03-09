from PyQt6.QtCore import QObject, pyqtSignal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import urllib.parse
import requests
from PyQt6.QtGui import QPixmap

class SearchProduct(QObject):
    search_result = pyqtSignal(dict)

    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    def search_product(self, keyword):
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f'https://kream.co.kr/search?keyword={encoded_keyword}&tab=products&sort=popular_score'
        self.browser.get(search_url)

        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.search_result_item.product')))
            products = self.browser.find_elements(By.CSS_SELECTOR, 'div.search_result_item.product')

            if not products:
                self.search_result.emit({})
                return

            self.products = products
            self.current_index = 0
            self._emit_current_product()
        except Exception as e:
            print(e)
            self.search_result.emit({})

    def _emit_current_product(self):
        current_product = self.products[self.current_index]
        product_info = self.get_product_info(current_product)
        if product_info:
            product_id = current_product.get_attribute("data-product-id")
            product_info["id"] = product_id
            self.search_result.emit(product_info)

    def emit_search_result(self, result_data):
        self.search_result.emit(result_data)

    def product_update_info(self):
        if hasattr(self, 'products') and self.products:
            self._emit_current_product()

    def next_result(self):
        if hasattr(self, 'products') and self.products:
            if self.current_index < len(self.products) - 1:
                self.current_index += 1
                self._emit_current_product()
            else:
                print("더 이상 다음 결과가 없습니다.")

    def previous_result(self):
        if hasattr(self, 'products') and self.products:
            if self.current_index > 0:
                self.current_index -= 1
                self._emit_current_product()
            else:
                print("더 이상 이전 결과가 없습니다.")

    def get_product_info(self, current_product):

        is_brand = False # 브랜드배송 여부 초기화

        # 검색 에러 처리
        try:
            current_product.find_element(By.CSS_SELECTOR, 'p.name')

        except StaleElementReferenceException:
            raise Exception("검색버튼을 다시 눌러주세요.")


        product_name = current_product.find_element(By.CSS_SELECTOR, 'p.name').text
        translated_name = current_product.find_element(By.CSS_SELECTOR, 'p.translated_name').text
        price = current_product.find_element(By.CSS_SELECTOR, 'p.amount').text
        img_url = current_product.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
        img_data = requests.get(img_url).content
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)

        # 거래 건수 확인
        try:
            status_value = current_product.find_element(By.CSS_SELECTOR, 'div.status_value').text
        except NoSuchElementException:
            status_value = ' 거래 0 '

        # 브랜드배송 여부 확인
        try:
            current_product.find_element(By.CSS_SELECTOR, 'svg[class="ico-brand-official icon sprite-icons"]')
            is_brand = True
        except NoSuchElementException: # 요소 없음 예외 발생 시
            pass

        return {
            "name": product_name,
            "translated_name": translated_name,
            "price": price,
            "image": pixmap,
            "status_value": status_value,
            "is_brand": is_brand
        }