from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .macro_log_handler import MacroLogHandler


class MacroErrorHandler:
    def __init__(self, browser, log_callback=None, log_handler=None):
        self.browser = browser

        # Support both direct callback and LogHandler instance
        if log_handler and isinstance(log_handler, MacroLogHandler):
            self.log_handler = log_handler
            self.log = log_handler.log
        else:
            # For backward compatibility
            self.log_handler = None
            self.log = log_callback

    def wait_for_element(self, by, selector, timeout=5):
        """
        요소를 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def wait_for_elements(self, by, selector, timeout=5):
        """
        요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 메서드

        Args:
            by: 요소를 찾는 방법 (By.CSS_SELECTOR, By.XPATH 등)
            selector: 요소를 찾기 위한 선택자
            timeout: 최대 대기 시간 (초)

        Returns:
            찾은 요소들의 리스트
        """
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def check_wrong_page(self, expected_product_id=None, check_type="inventory"):
        """
        현재 페이지가 예상된 페이지가 아닌지 확인합니다.
        """
        result = {
            "status": "unknown_page",
            "message": "알 수 없는 페이지",
            "actual_page": None
        }

        try:
            # 현재 URL 확인
            current_url = self.browser.current_url

            # 1. 올바른 인벤토리/판매 페이지인지 확인
            if check_type == "inventory":
                if f"inventory/{expected_product_id}" in current_url:
                    # 추가 확인 - 이미 완료 페이지인지 체크
                    if 'inventory/detail' in current_url or 'order/complete' in current_url:
                        result["status"] = "success_page"
                        result["message"] = "이미 성공 페이지에 있습니다."
                        return result

                    # 신청 페이지 (인벤토리 판매 페이지)
                    elif 'sale' in current_url or 'inventory_size_item' in self.browser.page_source:
                        result["status"] = "application_page"
                        result["message"] = "보관판매 신청 페이지"
                        return result
                    else:
                        result["status"] = "inventory_page"
                        result["message"] = "인벤토리 페이지"
                        return result

                # 성공 페이지 체크 (더 다양한 방법으로)
                try:
                    # URL로 성공 페이지 확인
                    if 'inventory/detail' in current_url or 'order/complete' in current_url:
                        result["status"] = "success_page"
                        result["message"] = "이미 성공 페이지에 있습니다."
                        return result

                    # 완료 텍스트 확인
                    completion_texts = [
                        "보관 신청이 완료되었습니다",
                        "신청이 완료되었습니다",
                        "보관판매 완료",
                        "보관 신청 완료"
                    ]

                    for text in completion_texts:
                        elements = self.wait_for_elements(By.XPATH, f"//p[contains(text(), '{text}')]")
                        if elements:
                            result["status"] = "success_page"
                            result["message"] = "완료 텍스트 감지됨"
                            return result

                    # 완료 페이지 클래스 확인
                    buy_complete_elements = self.wait_for_elements(By.CSS_SELECTOR,
                                                                   'div.buy_complete, div.inventory_detail, div.order_complete')
                    if buy_complete_elements:
                        result["status"] = "success_page"
                        result["message"] = "완료 페이지 요소 감지됨"
                        return result

                    # 페이지 소스 검사
                    page_source = self.browser.page_source.lower()
                    success_keywords = [
                        "보관 신청이 완료",
                        "신청이 완료",
                        "보관판매 완료",
                        "보관 신청 완료",
                        "inventory_detail",
                        "buy_complete",
                        "order_complete"
                    ]
                    if any(keyword.lower() in page_source for keyword in success_keywords):
                        result["status"] = "success_page"
                        result["message"] = "성공 페이지 내용 감지됨"
                        return result
                except Exception as e:
                    if self.log_handler:
                        self.log_handler.log(f"성공 페이지 확인 중 오류: {str(e)}", allowed_key="ERROR")
        except Exception as e:
            if self.log_handler:
                self.log_handler.log(f"페이지 확인 중 오류: {str(e)}", allowed_key="ERROR")
        return result

    def verify_page_loading(self, selectors):
        """페이지 로딩 확인"""
        for selector in selectors:
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                self.log(f"필수 요소를 찾을 수 없습니다: {selector}")
                return False
        return True

    def check_login_required(self):
        """로그인 필요 여부 확인"""
        if 'login' in self.browser.current_url:
            self.log("로그인이 필요합니다.")
            return True
        return False 
