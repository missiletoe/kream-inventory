"""크림 인벤토리 애플리케이션의 제품 검색 플러그인입니다."""

from __future__ import annotations

import logging  # noqa: F401 # 로깅 모듈 임포트
import time
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.browser import BrowserManager

# logger_setup 임포트
from src.core.logger_setup import setup_logger
from src.core.plugin_base import PluginBase

if TYPE_CHECKING:
    from configparser import ConfigParser

    from src.core.plugin_manager import PluginManager as CorePluginManager

# 전역 로거 설정
logger = setup_logger(__name__)


class SearchPlugin(PluginBase, QObject):
    """제품 검색 및 결과 표시를 처리하는 플러그인입니다."""

    search_result = pyqtSignal(dict)

    def __init__(
        self: "SearchPlugin",
        name: str,
        browser: BrowserManager,
        config: "ConfigParser",
        plugin_manager: Optional[CorePluginManager] = None,
    ) -> None:
        """SearchPlugin을 초기화합니다.

        Args:
            name: 플러그인 이름입니다.
            browser: 브라우저 관리자 인스턴스입니다.
            config: 설정 파서 인스턴스입니다.
            plugin_manager: 플러그인 관리자 인스턴스입니다.
        """
        PluginBase.__init__(
            self,
            name=name,
            browser=browser,
            config=config,  # ConfigParser 객체 직접 전달
            plugin_manager=plugin_manager,
        )
        QObject.__init__(self)
        self.products: List[WebElement] = []
        self.current_index: int = 0
        self.max_retries: int = 3
        self.timeout: int = 15
        self.last_keyword: str = ""
        self.driver: Optional[WebDriver] = None

    def _get_driver(self: "SearchPlugin") -> WebDriver:
        """Webdriver 인스턴스를 가져오거나, 없으면 초기화합니다.

        Returns:
            Webdriver 인스턴스입니다.
        """
        if self.driver is not None:
            try:
                _ = self.driver.current_url  # Check if driver is still responsive
                return self.driver
            except WebDriverException:
                logger.warning("기존 WebDriver 세션이 유효하지 않아 새로 초기화합니다.")
                self.driver = None

        if isinstance(self.browser, BrowserManager):
            try:
                active_driver = self.browser.get_driver()
                if active_driver:
                    self.driver = active_driver
                    return self.driver
                logger.error("BrowserManager.get_driver()가 None을 반환했습니다.")
            except Exception as e:
                logger.error(
                    f"BrowserManager.get_driver() 호출 중 오류 발생: {e}", exc_info=True
                )

        if (
            hasattr(self, "plugin_manager")
            and self.plugin_manager
            and self.plugin_manager.browser
        ):
            logger.debug("플러그인 매니저를 통해 브라우저 재시도")
            # plugin_manager.browser가 BrowserManager 인스턴스인지 확인
            if isinstance(self.plugin_manager.browser, BrowserManager):
                self.browser = self.plugin_manager.browser  # self.browser 업데이트
                try:
                    active_driver = self.browser.get_driver()
                    if active_driver:
                        self.driver = active_driver
                        return self.driver
                    logger.error(
                        "플러그인 매니저 통해 BrowserManager.get_driver() 호출 시 None 반환"
                    )
                except Exception as e:
                    logger.error(
                        f"플러그인 매니저 통해 BrowserManager.get_driver() 호출 중 오류: {e}",
                        exc_info=True,
                    )
            else:
                logger.error("plugin_manager.browser가 BrowserManager 타입이 아닙니다.")

        logger.critical(
            "WebDriver 인스턴스를 가져올 수 없습니다. BrowserManager 또는 PluginManager 설정을 확인하세요."
        )
        raise TypeError(
            "SearchPlugin에는 BrowserManager 인스턴스가 필요합니다. 브라우저 초기화에 실패했습니다."
        )

    def wait_for_element(
        self: "SearchPlugin", by: str, selector: str, timeout: int = 5
    ) -> Optional[WebElement]:
        """지정된 선택자를 사용하여 웹 요소를 찾을 때까지 대기합니다.

        Args:
            by: 요소를 찾는 방법 (예: "css selector", "xpath" 등)입니다.
            selector: 요소를 찾기 위한 선택자입니다.
            timeout: 최대 대기 시간 (초)입니다.

        Returns:
            찾은 WebElement 또는 None입니다.
        """
        driver = self._get_driver()
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            return None

    def wait_for_elements(
        self: "SearchPlugin", by: str, selector: str, timeout: int = 5
    ) -> List[WebElement]:
        """요소들을 찾을 때까지 최대 timeout 초 동안 대기하는 메서드입니다.

        Args:
            by: 요소를 찾는 방법 (예: "css selector", "xpath" 등)입니다.
            selector: 요소를 찾기 위한 선택자입니다.
            timeout: 최대 대기 시간 (초)입니다.

        Returns:
            찾은 WebElement 목록입니다.
        """
        driver = self._get_driver()
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def search(self: "SearchPlugin", keyword: str) -> None:
        """주어진 키워드로 제품을 검색하고 첫 번째 결과를 반환합니다."""
        if not keyword.strip():
            self.search_result.emit({"error": "검색어를 입력해주세요."})
            return

        logger.debug(f"검색 시작: 키워드 '{keyword}'")
        self.last_keyword = keyword.strip()
        encoded_keyword = urllib.parse.quote(self.last_keyword)
        search_url = f"https://kream.co.kr/search?keyword={encoded_keyword}&tab=products&sort=popular_score"
        driver = self._get_driver()

        # 현재 URL 상태 확인
        logger.debug(f"현재 URL: {driver.current_url}")

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"검색 URL 접속 시도 ({attempt + 1} / {self.max_retries}): {search_url}"
                )
                driver.get(search_url)

                # 페이지 로딩 확인
                logger.debug(f"페이지 로딩 완료: {driver.current_url}")

                # 가능한 여러 선택자를 시도하여 검색 결과나 결과 없음 메시지 확인
                selectors_to_try = [
                    "div.search_result_item.product",
                    ".search_result_item",
                    ".product_card",
                    "div.product_card",
                    ".product_item",
                    "div.product_item",
                ]

                # 결과가 없을 때 나타나는 메시지 선택자
                no_result_selectors = [
                    "div.search_content p.nodata_main",
                    ".nodata_main",
                    ".search_no_result",
                    ".no_result",
                ]

                # 페이지 로딩을 기다림 (제품 카드 또는 "결과 없음" 메시지 중 하나가 나타날 때까지)
                logger.debug("검색 결과 또는 결과 없음 메시지 대기 중...")

                try:
                    # lambda를 명명된 함수로 변경하여 타입 추론 문제 해결
                    def check_elements_exist(driver: WebDriver) -> bool:
                        for selector in selectors_to_try + no_result_selectors:
                            logger.debug(f"요소 존재 확인: {selector}")
                            elements = driver.find_elements("css selector", selector)
                            if len(elements) > 0:
                                return True
                        return False

                    WebDriverWait(driver, self.timeout).until(check_elements_exist)
                except TimeoutException:
                    logger.warning("요소 대기 시간 초과. 페이지 구조 확인 필요")

                # 웹페이지 HTML 구조 확인 (디버깅용)
                logger.debug(f"HTML 제목: {driver.title}")

                # 검색 결과 선택자를 순차적으로 시도
                products = []
                for selector in selectors_to_try:
                    products = driver.find_elements("css selector", selector)
                    if products:
                        logger.debug(
                            f"검색 결과 찾음: 선택자 '{selector}'로 {len(products)}개 제품"
                        )
                        break

                if products:
                    logger.debug(f"검색 결과 찾음: {len(products)}개 제품")
                    self.products = products
                    self.current_index = 0
                    self._emit_current_product()
                    return

                # 결과 없음 메시지 선택자를 순차적으로 시도
                no_data_elements = []
                for selector in no_result_selectors:
                    no_data_elements = driver.find_elements("css selector", selector)
                    if no_data_elements:
                        logger.debug(f"검색 결과 없음 메시지 발견: 선택자 '{selector}'")
                        break

                if no_data_elements and len(no_data_elements) > 0:
                    logger.debug("검색 결과 없음 메시지 발견")
                    try:
                        no_data_text = no_data_elements[0].text.strip()
                        if not no_data_text:
                            no_data_text = "검색 결과가 없습니다."
                    except Exception:
                        no_data_text = "검색 결과가 없습니다."

                    self.search_result.emit({"error": no_data_text})
                    return

                # 페이지 소스 출력 (디버깅용)
                logger.debug("검색 결과를 찾을 수 없음, 페이지 소스 일부:")
                page_source = driver.page_source
                logger.debug(
                    page_source[:500] + "..." if len(page_source) > 500 else page_source
                )

                # 페이지가 로드되었지만 제품을 찾을 수 없는 경우
                self.search_result.emit(
                    {
                        "error": "검색 결과를 찾을 수 없습니다. 웹사이트 구조가 변경되었을 수 있습니다."
                    }
                )
                return
            except TimeoutException:
                logger.warning(f"검색 시간 초과 ({attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.search_result.emit(
                        {"error": "검색 시간이 초과되었습니다. 다시 시도해주세요."}
                    )
                else:
                    time.sleep(1)
            except WebDriverException as e:
                logger.warning(
                    f"브라우저 오류 ({attempt + 1}/{self.max_retries}): {str(e)}"
                )
                if attempt == self.max_retries - 1:
                    self.search_result.emit(
                        {"error": f"브라우저 오류로 검색에 실패했습니다: {str(e)}"}
                    )
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"예상치 못한 오류: {str(e)}", exc_info=True)
                self.search_result.emit(
                    {"error": f"검색 중 예상치 못한 오류가 발생했습니다: {str(e)}"}
                )
                return

    def _emit_current_product(self: "SearchPlugin") -> None:
        """현재 제품 정보를 추출하여 신호로 방출합니다."""
        logger.debug(
            f"_emit_current_product 호출: 인덱스 {self.current_index}, 총 {len(self.products)}개 제품"
        )

        if not self.products:
            logger.debug("제품 목록이 비어 있음")
            self.search_result.emit({"error": "검색 결과가 없습니다."})
            return

        try:
            if self.current_index < 0 or self.current_index >= len(self.products):
                logger.warning(f"인덱스가 범위를 벗어남: {self.current_index}")
                self.search_result.emit({"error": "유효하지 않은 제품 인덱스입니다."})
                return

            current_product = self.products[self.current_index]

            # 현재 제품이 아직 DOM에 존재하는지 확인
            try:
                # ID나 클래스 속성을 확인하여 DOM에 여전히 존재하는지 검증
                _ = current_product.get_attribute("class")
            except Exception as e:
                logger.warning(f"DOM 참조 오류 발생, 제품 목록 새로고침 시도: {str(e)}")
                # 탐색을 다시 실행하려 시도
                self.search(self.last_keyword)
                return

            # 현재 제품 정보 가져오기
            product_info = self.get_product_info(current_product)

            if not product_info:
                logger.warning("제품 정보를 가져올 수 없음")
                self.search_result.emit({"error": "제품 정보를 가져올 수 없습니다."})
                return

            logger.debug(f"가져온 제품 정보: {product_info}")

            # 제품의 링크를 가져오려고 시도
            try:
                product_link_element = current_product.find_element("css selector", "a")
                product_url = product_link_element.get_attribute("href")

                # /products/ URL에서 제품 ID 추출
                if product_url and "/products/" in product_url:
                    product_id = (
                        product_url.split("/products/")[1].split("/")[0].split("?")[0]
                    )
                    logger.debug(f"추출된 제품 ID: {product_id}")
                    product_info["id"] = product_id
                else:
                    logger.warning(f"제품 URL에서 ID를 추출할 수 없음: {product_url}")
                    # ID를 추출할 수 없을 경우에도 고유 식별자를 제공하기 위한 임시 ID 생성
                    product_info["id"] = f"temp_{self.current_index}"
            except Exception as e:
                logger.warning(f"제품 URL 또는 ID 추출 중 오류: {str(e)}")
                product_info["id"] = f"temp_{self.current_index}"

            # 네비게이션 버튼 상태
            product_info["enable_prev"] = self.current_index > 0
            product_info["enable_next"] = self.current_index < len(self.products) - 1

            # 최종 검색 결과 시그널 발생
            self.search_result.emit(product_info)

        except Exception as e:
            logger.error(
                f"_emit_current_product 에서 예외 발생: {str(e)}", exc_info=True
            )
            self.search_result.emit(
                {
                    "error": "제품 정보를 처리하는 중 오류가 발생했습니다.",
                    "enable_prev": self.current_index > 0 and bool(self.products),
                    "enable_next": (
                        self.current_index < len(self.products) - 1
                        if self.products
                        else False
                    ),
                }
            )

    def next_result(self: "SearchPlugin") -> None:
        """다음 검색 결과를 표시합니다."""
        if self.products and self.current_index < len(self.products) - 1:
            self.current_index += 1
            self._emit_current_product()
        elif self.products and self.current_index == len(self.products) - 1:
            self.search_result.emit(
                {
                    "info": "마지막 제품입니다.",
                    "enable_prev": True,
                    "enable_next": False,
                }
            )
        else:
            self.search_result.emit(
                {
                    "error": "다음 제품 정보를 가져올 수 없습니다.",
                    "enable_prev": False,
                    "enable_next": False,
                }
            )

    def previous_result(self: "SearchPlugin") -> None:
        """이전 검색 결과를 표시합니다."""
        if self.products and self.current_index > 0:
            self.current_index -= 1
            self._emit_current_product()
        elif self.products and self.current_index == 0:
            self.search_result.emit(
                {
                    "info": "첫 번째 제품입니다.",
                    "enable_prev": False,
                    "enable_next": True,
                }
            )
        else:
            self.search_result.emit(
                {
                    "error": "이전 제품 정보를 가져올 수 없습니다.",
                    "enable_prev": False,
                    "enable_next": False,
                }
            )

    def get_product_info(
        self: "SearchPlugin", current_product: WebElement
    ) -> Optional[Dict[str, Any]]:
        """WebElement에서 제품 정보를 추출합니다.

        Args:
            current_product: 정보를 추출할 WebElement입니다.

        Returns:
            제품 정보를 담은 딕셔너리 또는 None입니다.
        """
        if current_product is None:
            logger.warning("get_product_info: current_product가 None입니다.")
            return None

        try:
            logger.debug("제품 정보 추출 시작")

            # 안전하게 HTML 출력
            try:
                html_preview = current_product.get_attribute("outerHTML")
                if html_preview:
                    html_preview = html_preview[:200] + "..."
                else:
                    html_preview = "(HTML을 가져올 수 없음)"
                logger.debug(f"현재 제품 요소 HTML: {html_preview}")
            except Exception as e:
                logger.warning(f"HTML 가져오기 실패: {str(e)}")

            # 다양한 CSS 선택자 시도
            title_selectors = [
                "p.item_title",
                ".item_title",
                ".product_title",
                ".name",
                "h3",
                ".product_name",
                "div.product_info_product_name p.name",
            ]

            translated_name_selectors = [
                ".translated_name",
                "div.product_info_product_name p.translated_name",
                "p.translated_name",
            ]

            brand_selectors = [
                "p.item_brand",
                ".item_brand",
                ".product_brand",
                ".brand",
                ".brand_name",
                "span.brand-name",
                "p.product_info_brand span.brand-name",
            ]

            # 브랜드 공식 배송 아이콘 선택자
            brand_official_selectors = [
                ".ico-brand-official",
                "svg.ico-brand-official",
                ".product_info_brand svg",
            ]

            price_selectors = [
                "div.price_area .amount",
                ".amount",
                ".price",
                ".product_price",
                ".product_amount",
            ]
            image_selectors = [
                "img.product_img",
                "img",
                ".product_img",
                ".thumbnail img",
                ".product_image img",
            ]

            # 관심수 및 리뷰수 선택자
            wish_figure_selectors = [
                ".wish_figure",
                "span.wish_figure",
                "span.wish_figure span",
            ]

            review_figure_selectors = [
                ".review_figure",
                "span.review_figure span:last-child",
                "span.review_figure span",
            ]

            # 제품명 찾기
            name = "이름 없음"
            for selector in title_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    name = elements[0].text.strip()
                    logger.debug(f"제품명 찾음: '{name}' (선택자: {selector})")
                    break

            # 한국어 이름(번역된 이름) 찾기
            translated_name = ""
            for selector in translated_name_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    translated_name = elements[0].text.strip()
                    logger.debug(
                        f"한국어 이름 찾음: '{translated_name}' (선택자: {selector})"
                    )
                    break

            # 브랜드 찾기
            brand = "브랜드 없음"
            for selector in brand_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    brand = elements[0].text.strip()
                    logger.debug(f"브랜드 찾음: '{brand}' (선택자: {selector})")
                    break

            # 브랜드 공식 배송 아이콘 확인
            is_brand_official = False
            for selector in brand_official_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    is_brand_official = True
                    logger.debug(f"브랜드 공식 배송 아이콘 찾음 (선택자: {selector})")
                    break

            # 가격 찾기
            price = "가격 없음"
            for selector in price_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    price = elements[0].text.strip()
                    logger.debug(f"가격 찾음: '{price}' (선택자: {selector})")
                    break

            # 이미지 URL 찾기
            img_url = None
            for selector in image_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    img_url = elements[0].get_attribute("src")
                    logger.debug(f"이미지 URL 찾음: '{img_url}' (선택자: {selector})")
                    break

            # 관심수 찾기
            wish_figure = ""
            for selector in wish_figure_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    wish_text = elements[0].text.strip()
                    if wish_text:
                        # "관심 1,087" 형식에서 숫자만 추출
                        if "관심" in wish_text:
                            wish_figure = wish_text.split("관심")[-1].strip()
                        else:
                            wish_figure = wish_text
                        logger.debug(
                            f"관심수 찾음: '{wish_figure}' (선택자: {selector})"
                        )
                        break

            # 리뷰수 찾기
            review_figure = ""
            for selector in review_figure_selectors:
                elements = current_product.find_elements("css selector", selector)
                if elements:
                    review_text = elements[0].text.strip()
                    if review_text:
                        # "리뷰 76" 형식에서 숫자만 추출
                        if "리뷰" in review_text:
                            review_figure = review_text.split("리뷰")[-1].strip()
                        else:
                            review_figure = review_text
                        logger.debug(
                            f"리뷰수 찾음: '{review_figure}' (선택자: {selector})"
                        )
                        break

            logger.debug(
                f"제품 정보 추출 완료: {name}, {brand}, {price}, "
                f"이미지URL: {img_url is not None}, 관심수: {wish_figure}, 리뷰수: {review_figure}"
            )

            # 기본 정보는 항상 반환, 값이 누락되어도 기본값으로 대체
            return {
                "name": name or "이름 없음",
                "translated_name": translated_name or "",
                "brand": brand or "브랜드 없음",
                "price": price or "가격 없음",
                "image_url": img_url,
                "wish_figure": wish_figure,
                "review_figure": review_figure,
                "is_brand_official": is_brand_official,
            }
        except NoSuchElementException as e:
            logger.error(f"NoSuchElementException: {str(e)}", exc_info=True)
            # 오류 발생해도, 기본 정보를 담은 결과 반환
            return {
                "name": "이름 없음",
                "translated_name": "이름 없음",
                "brand": "브랜드 없음",
                "price": "가격 없음",
                "image_url": None,
                "wish_figure": "",
                "review_figure": "",
                "is_brand_official": False,
            }
        except StaleElementReferenceException as e:
            logger.error(f"StaleElementReferenceException: {str(e)}", exc_info=True)
            # 기본 정보 반환
            return {
                "name": "이름 없음 (페이지 변경됨)",
                "translated_name": "이름 없음 (페이지 변경됨)",
                "brand": "브랜드 없음",
                "price": "가격 없음",
                "image_url": None,
                "wish_figure": "",
                "review_figure": "",
                "is_brand_official": False,
            }
        except Exception as e:
            logger.error(f"제품 정보 추출 중 오류: {str(e)}", exc_info=True)
            # 기본 정보 반환
            return {
                "name": "이름 없음 (오류)",
                "translated_name": "",
                "brand": "브랜드 없음",
                "price": "가격 없음",
                "image_url": None,
                "wish_figure": "",
                "review_figure": "",
                "is_brand_official": False,
            }
