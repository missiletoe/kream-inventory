# plugins/search_plugin.py

from PyQt6.QtCore import QObject, pyqtSignal
import urllib.parse
import requests
from PyQt6.QtGui import QPixmap
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException
)
from src.core.plugin_base import PluginBase
import time

class SearchPlugin(PluginBase, QObject):
    search_result = pyqtSignal(dict)

    def __init__(self, browser, config, plugin_manager=None):
        PluginBase.__init__(self, name="search", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)
        self.products = []
        self.current_index = 0
        self.max_retries = 3
        self.timeout = 15
        self.last_keyword = ""

    def search(self, keyword: str):
        if not keyword.strip():
            self.search_result.emit({"error": "검색어를 입력해주세요."})
            return

        self.last_keyword = keyword.strip()  # 마지막 검색어 저장
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f'https://kream.co.kr/search?keyword={encoded_keyword}&tab=products&sort=popular_score'
        
        for attempt in range(self.max_retries):
            try:
                self.browser.get(search_url)
                # Wait for either search results or "no results" message
                WebDriverWait(self.browser, self.timeout).until(
                    lambda driver: (
                        len(driver.find_elements(By.CSS_SELECTOR, 'div.search_result_item.product')) > 0 or
                        len(driver.find_elements(By.CSS_SELECTOR, 'div.search_content p.nodata_main')) > 0
                    )
                )
                
                # Get products first
                products = self.browser.find_elements(By.CSS_SELECTOR, 'div.search_result_item.product')
                if products:
                    self.products = products
                    self.current_index = 0
                    self._emit_current_product()
                    return
                
                # If no products found, check for no results message
                no_data_elements = self.browser.find_elements(By.CSS_SELECTOR, 'div.search_content p.nodata_main')
                if no_data_elements:
                    no_data_text = no_data_elements[0].text
                    self.search_result.emit({"error": no_data_text})
                    return
                
                # If neither products nor no results message found
                self.search_result.emit({"error": "검색 결과를 가져오는데 실패했습니다."})
                return
                
            except TimeoutException:
                if attempt == self.max_retries - 1:
                    self.search_result.emit({"error": "검색 시간이 초과되었습니다. 다시 시도해주세요."})
                else:
                    time.sleep(1)  # Wait before retry
            except WebDriverException as e:
                if attempt == self.max_retries - 1:
                    self.search_result.emit({"error": f"검색 중 오류가 발생했습니다: {str(e)}"})
                else:
                    time.sleep(1)
            except Exception as e:
                self.search_result.emit({"error": f"예상치 못한 오류가 발생했습니다: {str(e)}"})
                return

    def _emit_current_product(self):
        try:
            # 로그인 후 검색 결과 페이지 유지
            if not self.browser.current_url.startswith('https://kream.co.kr/search'):
                self.browser.get(f'https://kream.co.kr/search?keyword={urllib.parse.quote(self.last_keyword)}&tab=products&sort=popular_score')
                WebDriverWait(self.browser, self.timeout).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, 'div.search_result_item.product')) > 0
                )
                self.products = self.browser.find_elements(By.CSS_SELECTOR, 'div.search_result_item.product')

            current_product = self.products[self.current_index]
            product_info = self.get_product_info(current_product)
            if product_info:
                product_id = current_product.get_attribute("data-product-id")
                product_info["id"] = product_id
                # 현재 인덱스 정보 추가
                product_info["current_index"] = self.current_index
                product_info["total_products"] = len(self.products)
                
                # 이전/다음 버튼 활성화 상태 정보 추가
                product_info["enable_prev"] = self.current_index > 0
                product_info["enable_next"] = self.current_index < len(self.products) - 1
                
                self.search_result.emit(product_info)
        except StaleElementReferenceException:
            self.search_result.emit({
                "error": "검색 결과가 만료되었습니다. 다시 검색해주세요.",
                "enable_prev": False,
                "enable_next": False
            })
        except Exception as e:
            self.search_result.emit({
                "error": f"제품 정보를 가져오는데 실패했습니다: {str(e)}",
                "enable_prev": False,
                "enable_next": False
            })

    def next_result(self):
        if self.products and self.current_index < len(self.products) - 1:
            self.current_index += 1
            self._emit_current_product()
        else:
            # 이전 결과로 돌아갈 수 있도록 이전 버튼만 활성화
            self.search_result.emit({
                "error": "더 이상 다음 결과가 없습니다.", 
                "enable_prev": self.current_index > 0,
                "enable_next": False
            })

    def previous_result(self):
        if self.products and self.current_index > 0:
            self.current_index -= 1
            self._emit_current_product()
        else:
            # 다음 결과로 돌아갈 수 있도록 다음 버튼만 활성화
            self.search_result.emit({
                "error": "더 이상 이전 결과가 없습니다.", 
                "enable_prev": False,
                "enable_next": self.current_index < len(self.products) - 1
            })

    def get_product_info(self, current_product):
        try:
            # Wait for product elements to be present
            WebDriverWait(self.browser, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'p.name, p.translated_name, p.amount, img'))
            )
            
            product_name = current_product.find_element(By.CSS_SELECTOR, 'p.name').text
            translated_name = current_product.find_element(By.CSS_SELECTOR, 'p.translated_name').text
            price = current_product.find_element(By.CSS_SELECTOR, 'p.amount').text
            
            # Get image with retry
            img_url = None
            for attempt in range(3):
                try:
                    img_url = current_product.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    if img_url:
                        break
                except StaleElementReferenceException:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)
            
            if not img_url:
                raise NoSuchElementException("이미지 URL을 찾을 수 없습니다.")
            
            img_data = requests.get(img_url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            # Get status value with fallback
            try:
                status_value = current_product.find_element(By.CSS_SELECTOR, 'div.status_value').text.strip().replace('거래', '').strip()
            except NoSuchElementException:
                status_value = '0'
            
            # Check if brand product
            is_brand = False
            try:
                current_product.find_element(By.CSS_SELECTOR, 'svg[class="ico-brand-official icon sprite-icons"]')
                is_brand = True
            except NoSuchElementException:
                pass
            
            return {
                "name": product_name,
                "translated_name": translated_name,
                "price": price,
                "image": pixmap,
                "status_value": status_value,
                "is_brand": is_brand
            }
            
        except Exception as e:
            raise Exception(f"제품 정보 추출 중 오류 발생: {str(e)}")