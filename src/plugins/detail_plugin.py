# plugins/detail_plugin.py

from src.core.plugin_base import PluginBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyQt6.QtCore import pyqtSignal, QObject
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, date
import re

class DetailPlugin(PluginBase, QObject):
    details_ready = pyqtSignal(dict)
    sizes_ready = pyqtSignal(list)

    def __init__(self, browser, config, plugin_manager=None):
        PluginBase.__init__(self, name="detail", browser=browser, config=config, plugin_manager=plugin_manager)
        QObject.__init__(self)

    def get_days_difference(self, release_date_str):
        """
        출시일로부터 경과일/남은일 계산 (D-day 형식)
        """
        try:
            # 날짜 포맷 확인 (YY/MM/DD 또는 YYYY-MM-DD 등)
            if '/' in release_date_str:
                # YY/MM/DD 형식 처리
                parts = release_date_str.split('/')
                if len(parts) == 3:
                    year = int(parts[0])
                    if year < 100:  # 2자리 연도인 경우 앞에 20 추가
                        year += 2000
                    month = int(parts[1])
                    day = int(parts[2])
                    release_date = date(year, month, day)
                else:
                    return ""
            elif '-' in release_date_str:
                # YYYY-MM-DD 형식 처리
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
            else:
                return ""
            
            # 현재 날짜와 비교
            today = date.today()
            days_diff = (release_date - today).days
            
            if days_diff > 0:
                return f" (D-{days_diff})"
            elif days_diff == 0:
                return " (D-DAY)"
            else:
                return f" (D+{abs(days_diff)})"
        except Exception:
            return ""

    def get_details(self, product_id: str) -> dict:
        detail_url = f"https://kream.co.kr/products/{product_id}"

        main_handle = self.browser.current_window_handle
        self.browser.execute_script("window.open(arguments[0], '_blank');", detail_url)

        new_handle = self.browser.window_handles[-1]
        self.browser.switch_to.window(new_handle)

        try:
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'dl.detail-product-container'))
            )

            # Get recent price and fluctuation
            try:
                recent_price = self.browser.find_element(By.CSS_SELECTOR, 'div.detail-price div.amount span.price-info').text
                fluctuation = self.browser.find_element(By.CSS_SELECTOR, 'div.detail-price div.fluctuation').text
                fluctuation_type = self.browser.find_element(By.CSS_SELECTOR, 'div.detail-price div.fluctuation').get_attribute('class').split()[-1]
            except NoSuchElementException:
                recent_price = "N/A"
                fluctuation = "N/A"
                fluctuation_type = ""

            # Get product details
            details = self.browser.find_elements(By.CSS_SELECTOR, 'div.detail-box')
            detail_info = {}
            
            for detail in details:
                try:
                    title = detail.find_element(By.CSS_SELECTOR, 'div.product_title').text.strip()
                    info = detail.find_element(By.CSS_SELECTOR, 'div.product_info').text.strip()
                    detail_info[title] = info
                except:
                    continue

            # 출시일 정보 추출 및 D-day 계산
            release_date = detail_info.get('출시일', 'N/A')
            d_day_text = ""
            if release_date != 'N/A' and release_date != '-':
                d_day_text = self.get_days_difference(release_date)
            
            result = {
                "recent_price": recent_price,
                "fluctuation": fluctuation,
                "fluctuation_type": fluctuation_type,
                "release_price": detail_info.get('발매가', 'N/A'),
                "model_no": detail_info.get('모델번호', 'N/A'),
                "release_date": release_date,
                "d_day": d_day_text,  # D-day 정보 추가
                "color": detail_info.get('대표 색상', 'N/A')
            }

            # Get available sizes
            try:
                # Click the sell button to open the layer container
                sell_button = self.browser.find_element(By.CSS_SELECTOR, 'button.btn_action[style*="background-color: rgb(65, 185, 121)"]')
                sell_button.click()
                WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'))
                )
                
                # Get all size options from the layer container
                size_elements = self.browser.find_elements(By.CSS_SELECTOR, 'div.select_item')
                sizes = []
                
                for element in size_elements:
                    try:
                        # Get the size text from the text-lookup element
                        size_text = element.find_element(By.CSS_SELECTOR, 'p.text-lookup').text.strip()
                        if size_text:
                            sizes.append(size_text)
                    except:
                        continue
                
                # If no sizes found in dropdown, check if it's ONE SIZE
                if not sizes:
                    try:
                        # Check the current selected size text
                        current_size = self.browser.find_element(By.CSS_SELECTOR, 'div.detail-size span.text').text.strip()
                        if current_size and current_size.upper() == "ONE SIZE":
                            sizes = ["ONE SIZE"]
                    except:
                        pass
                
                # Close the layer container
                try:
                    close_button = self.browser.find_element(By.CSS_SELECTOR, 'a.btn_layer_close')
                    close_button.click()
                except:
                    pass
                
                # If we have multiple sizes, sort them numerically
                if len(sizes) > 1 and all(size.replace('(US ', '').replace(')', '').replace('.', '').isdigit() for size in sizes):
                    sizes.sort(key=lambda x: float(x.split('(')[0].strip()))
                
                result["sizes"] = sizes
                self.sizes_ready.emit(sizes)
            except Exception as e:
                result["sizes"] = []
                self.sizes_ready.emit([])

            self.details_ready.emit(result)
            return result

        except Exception as e:
            result = {"error": str(e)}
            self.details_ready.emit(result)
            return result

        finally:
            self.browser.close()
            self.browser.switch_to.window(main_handle)