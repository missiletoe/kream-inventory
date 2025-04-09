# plugins/detail_plugin.py

from src.core.plugin_base import PluginBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class DetailPlugin(PluginBase):
    def __init__(self, browser, config, plugin_manager=None):
        super().__init__(name="detail", browser=browser, config=config, plugin_manager=plugin_manager)

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

            details = self.browser.find_elements(By.CSS_SELECTOR, 'dl.detail-product-container > div.detail-box')
            detail_texts = [detail.text.strip() for detail in details[:4]]

            result = {
                "release_price": detail_texts[0] if len(detail_texts) > 0 else None,
                "model_no": detail_texts[1] if len(detail_texts) > 1 else None,
                "release_date": detail_texts[2] if len(detail_texts) > 2 else None,
                "color": detail_texts[3] if len(detail_texts) > 3 else None,
            }

        except Exception as e:
            result = {"error": str(e)}

        finally:
            self.browser.close()
            self.browser.switch_to.window(main_handle)

        return result