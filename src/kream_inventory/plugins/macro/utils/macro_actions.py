"""크림 인벤토리 관리 매크로 플러그인을 제공합니다.

이 모듈은 크림 웹사이트에서 인벤토리 작업을 자동화하기 위한 MacroPlugin 클래스와
별도 스레드에서 매크로 작업을 처리하기 위한 MacroWorker 클래스를 포함합니다.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from ..log_tracer import LogTracer
from .selenium_helpers import (
    safe_click,
    wait_for_element,
    wait_for_element_clickable,
    wait_for_elements,
)


def open_inventory_page(
    browser: WebDriver, product_id: str, logger: Optional[LogTracer] = None
) -> bool:
    """인벤토리 페이지를 여는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        product_id: 제품 ID입니다.
        logger: 로그 트레이서 객체입니다.

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
            logger.error(f"인벤토리 페이지 오픈 중 오류: {str(e)}")
        return False


def submit_inventory_form(
    browser: WebDriver,
    size_index: int,
    quantity: int,
    logger: Optional[LogTracer] = None,
) -> bool:
    """인벤토리 폼을 제출하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        size_index: 사이즈 인덱스 (1부터 시작)입니다.
        quantity: 수량입니다.
        logger: 로그 트레이서 객체입니다.

    Returns:
        성공 여부 (True/False)입니다.
    """
    try:
        # 사이즈 선택 입력란 찾기
        input_box = wait_for_element(
            browser,
            By.CSS_SELECTOR,
            f"div.inventory_size_item:nth-child({size_index}) input.counter_quantity_input",
            timeout=10,
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
            browser, By.CSS_SELECTOR, "a.btn.full.solid", timeout=10
        )
        if not complete_button:
            if logger:
                logger.error("완료 버튼을 찾을 수 없음")
            return False

        if not safe_click(complete_button):
            if logger:
                logger.error("완료 버튼 클릭 실패")
            return False

        if logger:
            logger.info(
                f"인벤토리 폼 제출 성공 (사이즈: {size_index}, 수량: {quantity})"
            )

        return True

    except Exception as e:
        if logger:
            logger.error(f"인벤토리 폼 제출 중 오류: {str(e)}")
        return False


def handle_inner_label_popup(
    browser: WebDriver, logger: Optional[LogTracer] = None
) -> bool:
    """안쪽 라벨 사이즈 팝업을 처리하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        logger: 로그 트레이서 객체입니다.

    Returns:
        처리 여부 (True/False)입니다.
    """
    try:
        # 안쪽 라벨 다이얼로그 확인
        layer_container = wait_for_element(
            browser, By.CSS_SELECTOR, "div.layer_container", timeout=5
        )

        if not layer_container:
            return False

        # 안쪽 라벨 사이즈 텍스트 확인
        if "안쪽 라벨 사이즈" not in layer_container.text:
            return False

        # 예시 박스 클릭
        example_boxes = wait_for_elements(
            browser, By.CSS_SELECTOR, "div.example_box.label"
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
            browser, By.CSS_SELECTOR, "button.btn.solid.full.large", timeout=3
        )

        if not confirm_button:
            if logger:
                logger.warning("안쪽 라벨 확인 버튼을 찾을 수 없음")
            return False

        safe_click(confirm_button)

        if logger:
            logger.info("안쪽 라벨 사이즈 팝업 처리 완료")

        return True

    except Exception as e:
        if logger:
            logger.error(f"안쪽 라벨 처리 중 오류: {str(e)}")
        return False


def handle_payment_process(
    browser: WebDriver, logger: Optional[LogTracer] = None
) -> bool | None:
    """보증금 결제 과정을 처리하는 함수입니다.

    Args:
        browser: 웹드라이버 객체입니다.
        logger: 로그 트레이서 객체입니다.

    Returns:
        결제 성공 여부 (True/False/None)입니다.
    """
    try:
        # 신청내역 페이지 확인
        title_element = wait_for_element(
            browser, By.CSS_SELECTOR, "span.title_txt", timeout=10
        )

        if not title_element or title_element.text != "신청내역":
            return None

        # 보증금 결제 버튼 클릭
        if logger:
            logger.info("보증금 결제 진행 중...")

        purchase_button = wait_for_element(
            browser, By.CSS_SELECTOR, "button.display_button", timeout=10
        )

        if not purchase_button:
            if logger:
                logger.warning("보증금 결제 버튼을 찾을 수 없음")
            return None

        # 버튼이 활성화되어 있는지 확인
        button_class = purchase_button.get_attribute("class") or ""
        if "active" not in button_class:
            return None

        # 결제 버튼 클릭
        if not safe_click(purchase_button):
            if logger:
                logger.warning("보증금 결제 버튼 클릭 실패")
            return None

        # 모달 확인
        modal_container = wait_for_element(
            browser, By.CSS_SELECTOR, "div.layer_container", timeout=10
        )

        if not modal_container:
            if logger:
                logger.warning("결제 모달을 찾을 수 없음")
            return None

        # 체크박스 확인 및 클릭
        checkbox_container = wait_for_element(
            browser,
            By.CSS_SELECTOR,
            "div.section-item.display_item.empty_header",
            timeout=10,
        )

        if not checkbox_container:
            if logger:
                logger.warning("체크박스 컨테이너를 찾을 수 없음")
            return None

        # 모든 체크박스 클릭
        checkbox_labels = checkbox_container.find_elements(
            By.CSS_SELECTOR, "div.title-description-checkbox.line label"
        )

        for label in checkbox_labels:
            safe_click(label)

        # 최종 결제 버튼 클릭
        final_button = modal_container.find_element(
            By.CSS_SELECTOR, "div.layer_bottom div.bottom-button button"
        )

        if not final_button:
            if logger:
                logger.warning("최종 결제 버튼을 찾을 수 없음")
            return None

        final_button_class = final_button.get_attribute("class") or ""
        if "active" not in final_button_class:
            if logger:
                logger.warning("최종 결제 버튼이 활성화되지 않음")
            return None

        if not safe_click(final_button):
            if logger:
                logger.warning("최종 결제 버튼 클릭 실패")
            return None

        # 서비스 장애 확인
        service_error = wait_for_element(
            browser, By.CSS_SELECTOR, "div.info_txt", timeout=5
        )

        if service_error and service_error.text == "일시적인 서비스 장애 입니다.":
            if logger:
                logger.warning("일시적인 서비스 장애 발생")
            return False

        # 토스트 팝업 확인
        toast = wait_for_element(
            browser, By.CSS_SELECTOR, "div.toast.sm.show", timeout=5
        )

        if toast:
            if logger:
                logger.warning(f"결제 실패: {toast.text}")
            return False

        # 성공 시
        if logger:
            logger.info("보관판매 신청 성공!")
        return True

    except Exception as e:
        if logger:
            logger.error(f"결제 과정 중 오류: {str(e)}")
        return None
