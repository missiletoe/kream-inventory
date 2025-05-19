"""제품 상세 정보 조회 플러그인."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.kream_inventory.core.browser import BrowserManager
from src.kream_inventory.core.plugin_base import PluginBase

if TYPE_CHECKING:
    from configparser import ConfigParser

    from src.kream_inventory.core.plugin_manager import (
        PluginManager as CorePluginManager,
    )


class DetailPlugin(PluginBase, QObject):
    """제품 상세 정보 및 사이즈 정보를 가져오는 플러그인입니다."""

    details_ready = pyqtSignal(dict)
    sizes_ready = pyqtSignal(list)

    def __init__(
        self: "DetailPlugin",
        name: str,
        browser: BrowserManager,
        config: "ConfigParser",
        plugin_manager: Optional[CorePluginManager] = None,
    ) -> None:
        """DetailPlugin을 초기화합니다.

        Args:
            name: 플러그인 이름입니다.
            browser: BrowserManager 인스턴스입니다.
            config: 설정 파서 인스턴스입니다.
            plugin_manager: CorePluginManager 인스턴스입니다.
        """
        PluginBase.__init__(
            self,
            name=name,
            browser=browser,
            config=config,  # ConfigParser 객체 직접 전달
            plugin_manager=plugin_manager,
        )
        QObject.__init__(self)

    def get_days_difference(self: "DetailPlugin", release_date_str: str) -> str:
        """출시일로부터 경과일/남은일을 D-day 형식으로 계산합니다.

        Args:
            release_date_str: 출시일 문자열 (YY/MM/DD 또는 YYYY-MM-DD 형식).

        Returns:
            D-day 형식의 문자열 (예: " (D-7)", " (D+10)", " (D-DAY)") 또는 빈 문자열.
        """
        try:
            # 날짜 포맷 확인 (YY/MM/DD 또는 YYYY-MM-DD 등)
            if "/" in release_date_str:
                # YY/MM/DD 형식 처리
                parts = release_date_str.split("/")
                if len(parts) == 3:
                    year = int(parts[0])
                    if year < 100:  # 2자리 연도인 경우 앞에 20 추가
                        year += 2000
                    month = int(parts[1])
                    day = int(parts[2])
                    release_date = date(year, month, day)
                else:
                    return ""
            elif "-" in release_date_str:
                # YYYY-MM-DD 형식 처리
                release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
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

    def get_details(self: "DetailPlugin", product_id: str) -> Dict[str, Any]:
        """주어진 제품 ID에 대한 상세 정보와 사용 가능한 사이즈를 가져옵니다.

        새 탭에서 제품 상세 페이지를 열고 정보를 파싱한 후, 결과를 시그널로 보내고 반환합니다.

        Args:
            product_id: 상세 정보를 가져올 제품의 ID입니다.

        Returns:
            제품 상세 정보와 사이즈를 포함하는 딕셔너리입니다. 오류 발생 시 오류 메시지를 포함합니다.
        """
        detail_url = f"https://kream.co.kr/products/{product_id}"
        driver = self.browser.get_driver()

        main_handle = driver.current_window_handle
        driver.execute_script("window.open(arguments[0], '_blank');", detail_url)

        new_handle = driver.window_handles[-1]
        driver.switch_to.window(new_handle)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "dl.detail-product-container")
                )
            )

            # Get recent price and fluctuation
            try:
                recent_price = driver.find_element(
                    By.CSS_SELECTOR, "div.detail-price div.amount span.price-info"
                ).text
                fluctuation = driver.find_element(
                    By.CSS_SELECTOR, "div.detail-price div.fluctuation"
                ).text
                fluctuation_class = driver.find_element(
                    By.CSS_SELECTOR, "div.detail-price div.fluctuation"
                ).get_attribute("class")
                fluctuation_type = (
                    fluctuation_class.split()[-1] if fluctuation_class else ""
                )
            except NoSuchElementException:
                recent_price = "N/A"
                fluctuation = "N/A"
                fluctuation_type = ""

            # Get product details
            details = driver.find_elements(By.CSS_SELECTOR, "div.detail-box")
            detail_info: Dict[str, str] = {}

            for detail in details:
                try:
                    title = detail.find_element(
                        By.CSS_SELECTOR, "div.product_title"
                    ).text.strip()
                    info = detail.find_element(
                        By.CSS_SELECTOR, "div.product_info"
                    ).text.strip()
                    detail_info[title] = info
                except Exception:
                    continue

            # 출시일 정보 추출 및 D-day 계산
            release_date_str_val = detail_info.get("출시일", "N/A")
            d_day_text = ""
            if release_date_str_val != "N/A" and release_date_str_val != "-":
                d_day_text = self.get_days_difference(release_date_str_val)

            result: Dict[str, Any] = {
                "recent_price": recent_price,
                "fluctuation": fluctuation,
                "fluctuation_type": fluctuation_type,
                "release_price": detail_info.get("발매가", "N/A"),
                "model_no": detail_info.get("모델번호", "N/A"),
                "release_date": release_date_str_val,
                "d_day": d_day_text,  # D-day 정보 추가
                "color": detail_info.get("대표 색상", "N/A"),
            }

            # Get available sizes
            try:
                # Click the sell button to open the layer container
                sell_button = driver.find_element(
                    By.CSS_SELECTOR,
                    'button.btn_action[style*="background-color: rgb(65, 185, 121)"]',
                )
                sell_button.click()
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.layer_container")
                    )
                )

                # Get all size options from the layer container
                size_elements = driver.find_elements(By.CSS_SELECTOR, "div.select_item")
                sizes: List[str] = []

                for element in size_elements:
                    try:
                        # Get the size text from the text-lookup element
                        size_text = element.find_element(
                            By.CSS_SELECTOR, "p.text-lookup"
                        ).text.strip()
                        if size_text:
                            sizes.append(size_text)
                    except Exception:
                        continue

                # If no sizes found in dropdown, check if it's ONE SIZE
                if not sizes:
                    try:
                        # Check the current selected size text
                        current_size = driver.find_element(
                            By.CSS_SELECTOR, "div.detail-size span.text"
                        ).text.strip()
                        if current_size and current_size.upper() == "ONE SIZE":
                            sizes = ["ONE SIZE"]
                    except Exception:
                        pass

                # Close the layer container
                try:
                    close_button = driver.find_element(
                        By.CSS_SELECTOR, "a.btn_layer_close"
                    )
                    close_button.click()
                except Exception:
                    pass

                # If we have multiple sizes, sort them numerically
                if len(sizes) > 1 and all(
                    size.replace("(US ", "").replace(")", "").replace(".", "").isdigit()
                    for size in sizes
                ):
                    sizes.sort(key=lambda x: float(x.split("(")[0].strip()))

                result["sizes"] = sizes
                self.sizes_ready.emit(sizes)
            except Exception:
                result["sizes"] = []
                self.sizes_ready.emit([])

            self.details_ready.emit(result)
            return result

        except Exception as e_main:
            result = {"error": str(e_main)}
            self.details_ready.emit(result)
            return result

        finally:
            driver.close()
            driver.switch_to.window(main_handle)
