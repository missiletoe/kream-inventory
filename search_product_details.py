from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class SearchProductDetails:
    def __init__(self, browser, product_id):
        self.browser = browser
        self.product_id = product_id

    def execute(self):
        detail_url = f"https://kream.co.kr/products/{self.product_id}"
        # 새 탭으로 상세정보 페이지 열고 전환
        self.browser.execute_script("window.open(arguments[0], '_blank');", detail_url)
        self.browser.switch_to.window(self.browser.window_handles[-1])
        
        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
            details = self.browser.find_elements(By.CSS_SELECTOR, 'dl.detail-product-container > div.detail-box')
            additional_info = [detail.text.replace("\n", ": ") for detail in details[:4]]
        except Exception as e:
            additional_info = [f"상세정보 로드 에러: {e}"]
        finally:
            # 새 탭 닫고 원래 탭으로 복귀
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            
        return additional_info

def main():
    # 크롬드라이버가 PATH에 있어야 함
    browser = webdriver.Chrome()
    product_id = input("상품 ID 입력: ")
    spd = SearchProductDetails(browser, product_id)
    additional_info = spd.execute()
    print("추가 상세정보:", additional_info)
    time.sleep(5)
    browser.quit()

if __name__ == '__main__':
    main()