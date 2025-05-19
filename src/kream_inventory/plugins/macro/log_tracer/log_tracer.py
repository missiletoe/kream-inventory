"""로그 메시지를 관리하고 기록하기 위한 스레드 안전 로거를 제공합니다.

이 모듈은 LogTracer 클래스를 정의하며, 이 클래스를 사용하면 다양한 수준(DEBUG, INFO,
WARNING, ERROR, CRITICAL)의 로그 메시지를 콘솔과 지정된 로그 파일 모두에 기록할 수
있습니다. 스레드 안전 작업을 지원하며 최소 로그 수준에 따라 메시지를 필터링할 수 있습니다.
"""

import os
import threading
from datetime import datetime
from typing import Callable, Dict, Optional


class LogTracer:
    """다양한 수준의 로그 메시지를 스레드 안전하게 관리하고 기록합니다."""

    LEVELS: Dict[str, int] = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    TOAST_KEYS: Dict[str, str] = {
        "TOAST_CONTENT": "INFO",
        "TOAST_ERROR": "ERROR",
        "TOAST_BLOCK": "WARNING",
        "TOAST_RETRY": "WARNING",
        "REQUEST_LIMIT": "WARNING",
        "ERROR": "ERROR",  # General error key
    }

    def __init__(
        self: "LogTracer",
        log_path: Optional[str] = None,
        console_handler: Optional[Callable[[str], None]] = None,
        min_level: str = "INFO",
    ) -> None:
        """LogTracer를 초기화합니다.

        Args:
            log_path: 로그 파일의 선택적 경로입니다.
            console_handler: 콘솔 출력을 처리하는 선택적 함수입니다.
            min_level: 기록할 최소 로그 수준입니다 (예: "INFO").
        """
        self.lock = threading.Lock()
        self.console_handler = console_handler
        self.min_level_str = min_level  # Store original string for reference if needed
        self.min_level_val: int = self.LEVELS.get(
            min_level.upper(), self.LEVELS["INFO"]
        )
        self.log_path = log_path

        if log_path:
            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    def _format_message(self: "LogTracer", message: str, level: str) -> str:
        """타임스탬프와 수준으로 로그 메시지 형식을 지정합니다."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level.upper()}] {message}"

    def log(
        self: "LogTracer",
        message: str,
        level: str = "INFO",
        allowed_key: Optional[str] = None,
    ) -> None:
        """수준이 최소 수준 이상인 경우 로그 메시지를 기록합니다.

        Args:
            message: 기록할 로그 메시지입니다.
            level: 로그 수준 문자열입니다 (예: "INFO", "ERROR").
            allowed_key: TOAST_KEYS에서 로그 수준을 결정하는 선택적 키입니다.
        """
        log_level_str = level.upper()
        if allowed_key and allowed_key in self.TOAST_KEYS:
            log_level_str = self.TOAST_KEYS[allowed_key].upper()

        level_num = self.LEVELS.get(log_level_str, self.LEVELS["INFO"])

        if level_num < self.min_level_val:
            return

        formatted_msg = self._format_message(message, log_level_str)

        with self.lock:
            if self.console_handler:
                self.console_handler(formatted_msg)

            if self.log_path:
                try:
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(formatted_msg + "\n")
                except IOError as e:  # More specific exception
                    if self.console_handler:
                        error_log_msg = self._format_message(
                            f"Log file write error: {str(e)}", "ERROR"
                        )
                        self.console_handler(error_log_msg)
                except Exception as e:  # Catch other potential errors
                    if self.console_handler:
                        generic_error_msg = self._format_message(
                            f"Unexpected error during log writing: {str(e)}", "ERROR"
                        )
                        self.console_handler(generic_error_msg)

    def debug(self: "LogTracer", message: str) -> None:
        """DEBUG 수준으로 메시지를 기록합니다."""
        self.log(message, level="DEBUG")

    def info(self: "LogTracer", message: str) -> None:
        """INFO 수준으로 메시지를 기록합니다."""
        self.log(message, level="INFO")

    def warning(self: "LogTracer", message: str) -> None:
        """WARNING 수준으로 메시지를 기록합니다."""
        self.log(message, level="WARNING")

    def error(self: "LogTracer", message: str) -> None:
        """ERROR 수준으로 메시지를 기록합니다."""
        self.log(message, level="ERROR")

    def critical(self: "LogTracer", message: str) -> None:
        """CRITICAL 수준으로 메시지를 기록합니다."""
        self.log(message, level="CRITICAL")
