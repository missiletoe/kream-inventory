#!/usr/bin/env python3
"""
로그 중복 제거 테스트 스크립트
"""
import time

from src.kream_inventory.plugins.macro.macro_log_handler import MacroLogHandler


def test_deduplication():
    """로그 중복 제거 테스트"""
    # Setup log handler
    log_handler = MacroLogHandler()

    # Connect to log signal to see output
    log_outputs = []

    def capture_log(message):
        print(f"Log: {message}")
        log_outputs.append(message)

    log_handler.log_message.connect(capture_log)

    print("\n=== 중복 토스트 메시지 테스트 ===")
    # Send the same toast message multiple times in quick succession
    log_handler.log("토스트 메시지: 요청 횟수 초과", allowed_key="TOAST_CONTENT")
    log_handler.log("토스트 메시지: 요청 횟수 초과", allowed_key="TOAST_CONTENT")
    log_handler.log("토스트 메시지: 요청 횟수 초과", allowed_key="TOAST_CONTENT")
    log_handler.log("토스트(요청 횟수 초과)", allowed_key="UNKNOWN")

    # Check if only one message was output
    print(f"출력된 메시지 수: {len(log_outputs)}")
    log_outputs.clear()

    print("\n=== 중복 오류 메시지 테스트 ===")
    # Send similar error messages
    log_handler.log("버튼 클릭 실패: Element not clickable", allowed_key="ERROR")
    log_handler.log("버튼 클릭 실패: Element not clickable at point (123,456)", allowed_key="ERROR")
    log_handler.log("버튼 클릭 실패: 다른 오류", allowed_key="ERROR")

    # Check outputs
    print(f"출력된 메시지 수: {len(log_outputs)}")
    log_outputs.clear()

    print("\n=== 시간 경과 후 중복 메시지 테스트 ===")
    log_handler.log("토스트 메시지: 시간 테스트", allowed_key="TOAST_CONTENT")
    print("3초 대기...")
    time.sleep(3.5)  # Wait longer than the deduplication timeout
    log_handler.log("토스트 메시지: 시간 테스트", allowed_key="TOAST_CONTENT")

    # Check if both messages were output after waiting
    print(f"출력된 메시지 수: {len(log_outputs)}")


if __name__ == "__main__":
    test_deduplication()
