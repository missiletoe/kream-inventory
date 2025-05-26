"""크림 인벤토리 관리 매크로 플러그인을 제공합니다.

이 모듈은 크림 웹사이트에서 인벤토리 작업을 자동화하기 위한 MacroPlugin 클래스와
별도 스레드에서 매크로 작업을 처리하기 위한 MacroWorker 클래스를 포함합니다.
"""

from __future__ import annotations

import logging
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from src.core.selenium_helpers import (
    safe_click,
    wait_for_element,
    wait_for_element_clickable,
    wait_for_elements,
)


def open_inventory_page(
    browser: WebDriver, product_id: str, logger: Optional[logging.Logger] = None
) -> bool:
    """인벤토리 페이지를 여는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        product_id: 제품 ID입니다.
        logger: 표준 logging.Logger 객체입니다.

    Returns:
        성공 여부 (True/False)입니다.
    """
    inventory_url = f"https://kream.co.kr/inventory/{product_id}"
    try:
        browser.get(inventory_url)

        # 인벤토리 페이지 로딩 대기
        inventory_list = wait_for_element(
            browser, By.CSS_SELECTOR, "div.inventory_size_list", timeout=15
        )

        if inventory_list:
            if logger:
                logger.info(f"인벤토리 페이지 로드 성공: {inventory_url}")
            return True
        else:
            if logger:
                logger.error("인벤토리 페이지 로딩 실패")
            return False

    except Exception as e:
        if logger:
            logger.error(f"인벤토리 페이지 오픈 중 오류: {str(e)}", exc_info=True)
        return False


def submit_inventory_form(
    browser: WebDriver,
    size_index: int,
    quantity: int,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """인벤토리 폼을 제출하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        size_index: 사이즈 인덱스 (1부터 시작)입니다.
        quantity: 수량입니다.
        logger: 표준 logging.Logger 객체입니다.

    Returns:
        성공 여부 (True/False)입니다.
    """
    try:
        # 사이즈 선택 입력란 찾기
        input_box = wait_for_element(
            browser,
            By.CSS_SELECTOR,
            f"div.inventory_size_item:nth-child({size_index}) input.counter_quantity_input",
            timeout=3,  # 10초에서 3초로 단축
        )

        if not input_box:
            if logger:
                logger.error(f"사이즈 입력란을 찾을 수 없음 (인덱스: {size_index})")
            return False

        # 수량 입력
        input_box.clear()
        input_box.send_keys(str(quantity))

        # 완료 버튼 클릭
        complete_button = wait_for_element_clickable(
            browser,
            By.CSS_SELECTOR,
            "a.btn.full.solid",
            timeout=3,  # 10초에서 3초로 단축
        )
        if not complete_button:
            if logger:
                logger.error("완료 버튼을 찾을 수 없음")
            return False

        if not safe_click(complete_button):
            if logger:
                logger.error("완료 버튼 클릭 실패, JavaScript로 클릭 시도")
            try:
                # JavaScript로 강제 클릭 시도
                browser.execute_script("arguments[0].click();", complete_button)
                if logger:
                    logger.info("JavaScript로 완료 버튼 클릭 시도")
            except Exception as js_click_error:
                if logger:
                    logger.error(
                        f"JavaScript 클릭도 실패: {str(js_click_error)}", exc_info=True
                    )
                return False

        if logger:
            logger.info(
                f"인벤토리 폼 제출 성공 (사이즈: {size_index}, 수량: {quantity})"
            )

        return True

    except Exception as e:
        if logger:
            logger.error(f"인벤토리 폼 제출 중 오류: {str(e)}", exc_info=True)
        return False


def handle_inner_label_popup(
    browser: WebDriver, logger: Optional[logging.Logger] = None
) -> bool:
    """안쪽 라벨 사이즈 팝업을 처리하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        logger: 표준 logging.Logger 객체입니다.

    Returns:
        처리 여부 (True/False)입니다.
    """
    try:
        # 안쪽 라벨 다이얼로그 확인
        layer_container = wait_for_element(
            browser,
            By.CSS_SELECTOR,
            "div.layer_container",
            timeout=2,  # 5초에서 2초로 단축
        )

        if not layer_container:
            return False

        # 안쪽 라벨 사이즈 텍스트 확인
        if "안쪽 라벨 사이즈" not in layer_container.text:
            return False

        if logger:
            logger.info("안쪽 라벨 사이즈 팝업 감지")

        # 예시 박스 클릭
        example_boxes = wait_for_elements(
            browser,
            By.CSS_SELECTOR,
            "div.example_box.label",
            timeout=2,  # 타임아웃 단축
        )

        if not example_boxes:
            if logger:
                logger.warning("안쪽 라벨 예시 박스를 찾을 수 없음")
            return False

        # 모든 예시 박스 클릭
        for label in example_boxes:
            safe_click(label)

        # 확인 버튼 클릭
        confirm_button = wait_for_element_clickable(
            browser,
            By.CSS_SELECTOR,
            "button.btn.solid.full.large",
            timeout=2,  # 3초에서 2초로 단축
        )

        if not confirm_button:
            if logger:
                logger.warning("안쪽 라벨 확인 버튼을 찾을 수 없음")
            return False

        if not safe_click(confirm_button):
            if logger:
                logger.info("JavaScript로 안쪽 라벨 확인 버튼 클릭 시도")
            try:
                browser.execute_script("arguments[0].click();", confirm_button)
            except Exception as js_click_error:
                if logger:
                    logger.error(
                        f"JavaScript 클릭도 실패: {str(js_click_error)}", exc_info=True
                    )

        if logger:
            logger.info("안쪽 라벨 사이즈 팝업 처리 완료")

        return True

    except Exception as e:
        if logger:
            logger.error(f"안쪽 라벨 처리 중 오류: {str(e)}", exc_info=True)
        return False


def handle_payment_process(
    browser: WebDriver, logger: Optional[logging.Logger] = None
) -> bool | None:
    """보증금 결제 과정을 처리하는 함수입니다."""
    try:
        if logger:
            logger.info(
                f"handle_payment_process 호출됨. 현재 URL: {browser.current_url}"
            )

        title_element = wait_for_element(
            browser, By.CSS_SELECTOR, "span.title_txt", timeout=3  # 10초에서 3초로 단축
        )

        if not title_element:
            if logger:
                logger.warning(
                    "신청 내역 페이지 타이틀(span.title_txt)을 찾을 수 없습니다."
                )
            return None  # 페이지 구조가 예상과 다르면 None 반환하여 루프 계속

        title_text = title_element.text.strip()  # strip() 추가하여 앞뒤 공백 제거
        if logger:
            logger.info(f"페이지 타이틀 발견: '{title_text}'")

        if title_text != "신청 내역":
            if logger:
                logger.info(
                    f"현재 페이지 타이틀이 '신청 내역'이 아님 ('{title_text}'). 결제 프로세스 건너뜀."
                )
            return None  # 현재 페이지가 신청내역이 아니면 None 반환

        if logger:
            logger.info("신청 내역 페이지 확인 완료. 결제 프로세스 시작.")

        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        if logger:
            logger.info("페이지 하단으로 스크롤 완료.")

        first_payment_button_selector = (
            "div.order-agreements-button button.display_button"
        )
        if logger:
            logger.info(
                f"첫번째 '보증금 결제하기' 버튼 탐색 시작: {first_payment_button_selector}"
            )

        purchase_button = wait_for_element_clickable(
            browser,
            By.CSS_SELECTOR,
            first_payment_button_selector,
            timeout=5,  # 15초에서 5초로 단축
        )

        if not purchase_button:
            if logger:
                logger.warning(
                    f"첫번째 '보증금 결제하기' 버튼({first_payment_button_selector})을 찾을 수 없거나 클릭할 수 없습니다."
                )
            # JavaScript로 직접 버튼 찾아 클릭 시도
            try:
                js_button = browser.execute_script(
                    f"return document.querySelector('{first_payment_button_selector}')"
                )
                if js_button:
                    browser.execute_script("arguments[0].click();", js_button)
                    if logger:
                        logger.info("JavaScript로 첫번째 결제 버튼 클릭 시도")
                else:
                    return False
            except Exception:
                return False
            # 이후 로직 실행을 위해 구매 버튼 상태 확인하지 않고 진행
            if logger:
                logger.info("JavaScript 클릭 후 계속 진행")
        else:
            # purchase_button이 None이 아닌 경우에만 속성 확인
            button_class = purchase_button.get_attribute("class") or ""
            if logger:
                logger.info(f"첫번째 결제 버튼 클래스: '{button_class}'")
            if "active" not in button_class:
                if logger:
                    logger.warning(
                        "첫번째 '보증금 결제하기' 버튼이 활성화되지 않았습니다. (클래스에 'active' 없음)"
                    )
                return False  # 비활성화 시 False

            if logger:
                logger.info("첫번째 '보증금 결제하기' 버튼 클릭 시도...")
            if not safe_click(purchase_button):  # purchase_button은 여기서 None이 아님
                if logger:
                    logger.warning(
                        "첫번째 '보증금 결제하기' 버튼 클릭 실패 (safe_click 결과 False)"
                    )
                # JavaScript로 클릭 시도
                try:
                    browser.execute_script("arguments[0].click();", purchase_button)
                    if logger:
                        logger.info(
                            "JavaScript로 첫번째 결제 버튼 클릭 시도 (safe_click 실패 후)"
                        )
                except Exception:
                    return False

        if logger:
            logger.info("첫번째 '보증금 결제하기' 버튼 클릭 성공.")

        modal_container_selector = "div.layer_container"
        if logger:
            logger.info(f"판매조건 확인 팝업 탐색 시작: {modal_container_selector}")
        modal_container = wait_for_element(
            browser,
            By.CSS_SELECTOR,
            modal_container_selector,
            timeout=5,  # 10초에서 5초로 단축
        )

        if not modal_container:
            if logger:
                logger.warning(
                    f"판매조건 확인 팝업({modal_container_selector})을 찾을 수 없습니다."
                )
            return False  # 팝업 못찾으면 False

        if logger:
            logger.info("판매조건 확인 팝업이 나타났습니다.")

        checkbox_labels_selector = (
            "div.layer_content div.title-description-checkbox label"
        )
        if logger:
            logger.info(f"팝업 내 체크박스 탐색 시작: {checkbox_labels_selector}")
        checkbox_labels = wait_for_elements(
            browser,
            By.CSS_SELECTOR,
            checkbox_labels_selector,
            timeout=5,  # 10초에서 5초로 단축
        )

        if not checkbox_labels:
            if logger:
                logger.warning(
                    f"판매조건 확인 팝업 내 체크박스({checkbox_labels_selector})를 찾을 수 없습니다."
                )
            return False

        if logger:
            logger.info(f"{len(checkbox_labels)}개의 체크박스를 클릭합니다.")
        all_checkboxes_clicked = True
        for i, label in enumerate(checkbox_labels):
            try:
                checkbox_input = label.find_element(
                    By.CSS_SELECTOR, "input[type='checkbox']"
                )
                if not checkbox_input.is_selected():
                    if logger:
                        logger.info(f"{i + 1}번째 체크박스 클릭 시도...")
                    if not safe_click(label):
                        if logger:
                            logger.warning(
                                f"{i + 1}번째 체크박스 클릭 실패 (safe_click 결과 False). JavaScript 클릭 시도"
                            )
                        # JavaScript로 클릭 시도
                        try:
                            browser.execute_script("arguments[0].click();", label)
                            if logger:
                                logger.info(
                                    f"{i + 1}번째 체크박스 JavaScript 클릭 시도"
                                )
                        except Exception as e_js:
                            if logger:
                                logger.error(
                                    f"JavaScript 클릭도 실패: {str(e_js)}",
                                    exc_info=True,
                                )
                            all_checkboxes_clicked = False
                    else:
                        if logger:
                            logger.info(f"{i + 1}번째 체크박스 클릭 성공.")
                else:
                    if logger:
                        logger.info(f"{i + 1}번째 체크박스는 이미 선택되어 있습니다.")
            except Exception as e_checkbox:
                if logger:
                    logger.error(
                        f"{i + 1}번째 체크박스 처리 중 오류: {str(e_checkbox)}",
                        exc_info=True,
                    )
                all_checkboxes_clicked = False

        if not all_checkboxes_clicked:
            if logger:
                logger.error("일부 체크박스 클릭에 실패하여 결제를 진행할 수 없습니다.")
            return False

        final_payment_button_selector = "div.layer_bottom button.display_button"
        if logger:
            logger.info(
                f"팝업 내 최종 '보증금 결제하기' 버튼 활성화 대기 시작: {final_payment_button_selector}"
            )

        try:
            final_purchase_button = WebDriverWait(
                browser, 5
            ).until(  # 20초에서 5초로 단축
                ec.element_to_be_clickable(
                    (By.CSS_SELECTOR, final_payment_button_selector)
                )
            )
            if logger:
                logger.info("팝업 내 최종 '보증금 결제하기' 버튼이 활성화되었습니다.")
        except TimeoutException:
            if logger:
                logger.error(
                    f"팝업 내 최종 '보증금 결제하기' 버튼({final_payment_button_selector})이 시간 내에 활성화되지 않았습니다.",
                    exc_info=True,
                )
            # JavaScript로 버튼 직접 찾기 시도
            try:
                js_final_button = browser.find_element(
                    By.CSS_SELECTOR, final_payment_button_selector
                )
                final_purchase_button = (
                    js_final_button  # WebElement | None -> WebElement로 취급
                )
                if logger:
                    logger.info("타임아웃 후 직접 버튼 찾기 시도")
            except Exception:
                return False

        # WebDriverWait 또는 직접 요소 찾기로 final_purchase_button 설정 후 안전 검사
        if not final_purchase_button:
            if logger:
                logger.warning(
                    f"팝업 내 최종 '보증금 결제하기' 버튼({final_payment_button_selector})을 찾을 수 없습니다.",
                    exc_info=True,
                )
            return False

        if logger:
            logger.info("팝업 내 최종 '보증금 결제하기' 버튼 클릭 시도...")
        if not safe_click(final_purchase_button):
            if logger:
                logger.warning(
                    "팝업 내 최종 '보증금 결제하기' 버튼 클릭 실패 (safe_click 결과 False)",
                    exc_info=True,
                )
            # JavaScript로 클릭 시도
            try:
                browser.execute_script("arguments[0].click();", final_purchase_button)
                if logger:
                    logger.info("JavaScript로 최종 결제 버튼 클릭 시도")
            except Exception:
                return False

        if logger:
            logger.info(
                "팝업 내 최종 '보증금 결제하기' 버튼 클릭 성공. 결제 완료 확인 대기..."
            )

        import time

        time.sleep(1)  # 결제 처리 및 페이지 전환 대기 시간 - 5초에서 1초로 단축

        # 결제 성공 후 예상 URL (예시: 마이페이지의 판매 내역 등)
        # 실제 성공 시 리디렉션되는 URL 패턴으로 변경해야 합니다.
        expected_url_after_payment = "/my/selling"  # 예시

        if expected_url_after_payment in browser.current_url:
            if logger:
                logger.info(
                    f"결제 성공 후 예상 URL({expected_url_after_payment})로 이동 확인. 최종 성공."
                )
            return True
        else:
            # 토스트 메시지 등 다른 성공 지표 확인
            success_toast_selector = (
                "div.toast.success"  # 실제 성공 토스트 선택자로 변경
            )
            success_toast = wait_for_element(
                browser, By.CSS_SELECTOR, success_toast_selector, timeout=3
            )
            if success_toast and success_toast.is_displayed():
                if logger:
                    logger.info(f"결제 성공 토스트 메시지 확인: {success_toast.text}")
                return True

            if logger:
                logger.warning(
                    f"결제 완료 후 예상 URL({expected_url_after_payment})로 이동하지 않았고, "
                    f"성공 토스트도 없음. 현재 URL: {browser.current_url}",
                    exc_info=True,
                )
            # 페이지에 "신청 완료", "결제 완료" 등의 텍스트가 있는지 확인하는 것도 방법
            body_text = browser.find_element(By.TAG_NAME, "body").text
            if (
                "신청이 완료되었습니다" in body_text
                or "결제가 완료되었습니다" in body_text
            ):  # 예시 문구
                if logger:
                    logger.info(
                        "결제/신청 완료 관련 텍스트를 페이지에서 확인. 최종 성공."
                    )
                return True

            if logger:
                logger.error(
                    "결제 성공 여부를 명확히 확인할 수 없습니다.", exc_info=True
                )
            return False  # 명확한 성공 지표가 없으면 실패로 처리

    except TimeoutException as e_timeout:
        if logger:
            logger.error(f"결제 과정 중 타임아웃 오류: {str(e_timeout)}", exc_info=True)
        return False
    except Exception as e_general:
        if logger:
            logger.error(
                f"결제 과정 중 예측하지 못한 오류: {str(e_general)}", exc_info=True
            )
        return False
