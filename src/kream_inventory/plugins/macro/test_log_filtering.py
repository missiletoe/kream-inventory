#!/usr/bin/env python3
"""
로그 필터링 테스트 스크립트
"""

from src.kream_inventory.plugins.macro.macro_log_handler import MacroLogHandler


def test_log_filtering():
    """로그 필터링 테스트"""
    # Setup log handler
    log_handler = MacroLogHandler()

    # Connect to log signal to see output
    def print_log(message):
        print(f"Log: {message}")

    log_handler.log_message.connect(print_log)

    # Test different log types
    print("\n=== 다음 로그들은 표시되어야 함 ===")
    log_handler.log("보관판매 신청 시도 1회", allowed_key="ATTEMPT")
    log_handler.log("토스트 메시지: 요청 횟수 초과", allowed_key="TOAST_CONTENT")
    log_handler.log("요청 횟수 초과, 30초 대기", allowed_key="REQUEST_LIMIT")
    log_handler.log("토스트 메시지 감지: 잠시 후 다시 시도해주세요", allowed_key="TOAST_BLOCK")

    # 에러 로그 테스트
    print("\n=== 에러 로그 테스트 (표시되어야 함) ===")
    log_handler.log("결제 처리 중 오류: Connection refused", allowed_key="PAYMENT_PROCESS_ERROR")
    log_handler.log("결제 버튼 클릭 중 오류: Element not clickable", allowed_key="PAYMENT_CLICK_ERROR")
    log_handler.log("성공 페이지 확인 중 오류: No such element", allowed_key="SUCCESS_CHECK_ERROR")

    # 키워드로 에러 로그 감지 테스트
    print("\n=== 에러 키워드 감지 테스트 (표시되어야 함) ===")
    log_handler.log("버튼 클릭 실패: Element is not clickable", allowed_key="UNKNOWN")
    log_handler.log("예외 발생: IndexError: list index out of range", allowed_key="UNKNOWN")
    log_handler.log("페이지 로딩 중 오류 발생", allowed_key="UNKNOWN")
    log_handler.log("Exception occurred: NoSuchElementException", allowed_key="UNKNOWN")

    print("\n=== 다음 로그들은 표시되지 않아야 함 ===")
    log_handler.log("매크로 구동 시작", allowed_key="START")
    log_handler.log("보관판매 페이지 이동", allowed_key="NAVIGATE")
    log_handler.log("결제 버튼 클릭 성공", allowed_key="PAYMENT_CLICK")

    print("\n=== 토스트 내용 추출 테스트 ===")
    log_handler.log("토스트 메시지: 잠시 후 다시 시도해주세요", allowed_key="UNKNOWN")
    log_handler.log("토스트 메시지 확인됨: 요청 횟수 초과", allowed_key="UNKNOWN")
    log_handler.log("토스트(일시적인 서비스 장애 입니다.)", allowed_key="UNKNOWN")


if __name__ == "__main__":
    test_log_filtering()
