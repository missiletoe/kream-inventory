import configparser
import os
import re
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal


class MacroLogHandler:
    def __init__(self, config=None):
        # Inherit from QObject to use signals
        class LogSignalEmitter(QObject):
            log_message = pyqtSignal(str)

        self._emitter = LogSignalEmitter()
        self.log_message = self._emitter.log_message

        # Default allowed display keys
        default_allowed_keys = [
            # 필수 로그만 표시 (매크로 시작/중지, 재시도 횟수, 팝업 메시지, 보관판매 성공)
            "START",  # 매크로 시작
            "STOP",  # 매크로 중지
            "ATTEMPT",  # 매크로 시도 횟수
            "TOAST_CONTENT",  # 토스트 팝업 내용
            "REQUEST_LIMIT",  # 요청 횟수 초과 토스트
            "TOAST_BLOCK",  # 블록 관련 토스트
            "TOAST_RETRY",  # 재시도 관련 토스트
            "TOAST_ERROR",  # 에러 관련 토스트
            "FINAL_SUCCESS",  # 보관판매 신청 성공
            "FINAL_CHECK_SUCCESS",  # 최종 성공 확인
            "WAIT",  # 대기 시간 정보

            # 중요 에러만 표시
            "ERROR"  # 일반 에러
        ]

        # Try to read allowed keys from config
        self._allowed_display_keys = self._read_allowed_keys_from_config(config, default_allowed_keys)

        # Toast message pattern for extraction
        self._toast_pattern = re.compile(r'토스트(?:\s+메시지)?\s*(?:내용|감지|확인)?(?:\s*:\s*|\()([^)]+)(?:\)|$)')

        # Deduplication mechanism
        self._recent_messages = {}  # Message -> timestamp
        self._dedup_timeout = 3  # seconds to deduplicate

    def log(self, message, allowed_key=None):
        """
        로그 메시지를 기록하고 필터링된 메시지만 표시
        """
        # Check if this is a duplicate message within the deduplication timeout
        current_time = datetime.now().timestamp()

        # Clean up old messages from the deduplication history
        self._cleanup_old_messages(current_time)

        # Check if this is a duplicate message (for toast and error messages)
        is_duplicate = False
        if "토스트" in message or "오류" in message or "실패" in message or "error" in message.lower():
            # Get simple version of message for comparison (remove timestamps, slight variations)
            simple_message = self._simplify_message(message)

            # Check if we've seen this simplified message recently
            if simple_message in self._recent_messages:
                last_time = self._recent_messages[simple_message]
                if current_time - last_time < self._dedup_timeout:
                    is_duplicate = True

            # Update the timestamp for this message
            if not is_duplicate:
                self._recent_messages[simple_message] = current_time

        # If it's a duplicate, don't emit it
        if is_duplicate:
            return message

        # If 'ALL' is in allowed keys, show all logs
        if 'ALL' in self._allowed_display_keys:
            self._emitter.log_message.emit(message)
            return message

        # Show logs for allowed keys
        if allowed_key in self._allowed_display_keys:
            self._emitter.log_message.emit(message)
        # Show logs containing error/exception keywords
        elif "오류" in message or "예외" in message or "실패" in message or "exception" in message.lower() or "error" in message.lower():
            self._emitter.log_message.emit(message)
        # Special handling for toast popup content from other logs
        elif "토스트" in message and ":" in message:
            match = self._toast_pattern.search(message)
            if match:
                toast_content = match.group(1).strip()
                self._emitter.log_message.emit(f"토스트 메시지: {toast_content}")

        # Always return the original message for internal use
        return message

    def _simplify_message(self, message):
        """Remove variable parts from message for comparison"""
        # Remove any timestamps, numbers, or variable parts
        simplified = re.sub(r'\d+[초분]', 'XX초', message)
        simplified = re.sub(r'\d+회', 'XX회', simplified)
        simplified = re.sub(r'\d+원', 'XX원', simplified)
        simplified = re.sub(r'\([^)]+\)', '', simplified)

        # Remove specific variable details from error messages
        simplified = re.sub(r': .*$', '', simplified)

        return simplified.strip()

    def _cleanup_old_messages(self, current_time):
        """Remove old messages from the deduplication history"""
        to_remove = []
        for msg, timestamp in self._recent_messages.items():
            if current_time - timestamp > 30:  # Remove after 30 seconds
                to_remove.append(msg)

        for msg in to_remove:
            del self._recent_messages[msg]

    # direct_log 메소드 제거 

    def _read_allowed_keys_from_config(self, config, default_keys):
        """
        Read allowed log keys from config.ini
        """
        if config is None:
            # Try to load config from default location
            config = configparser.ConfigParser()
            config_path = os.path.join(os.getcwd(), 'config.ini')
            if os.path.exists(config_path):
                config.read(config_path)

        try:
            # Try to get the allowed_keys using ConfigManager's get method
            # This works if config is a ConfigManager instance
            keys_str = config.get('Logging', 'allowed_keys', fallback=None)
            if keys_str:
                if keys_str.strip().upper() == 'ALL':
                    # Special case: ALL means show all logs
                    return ['ALL']
                else:
                    # Parse comma-separated list
                    return [key.strip() for key in keys_str.split(',') if key.strip()]
        except (AttributeError, TypeError):
            # If config is a configparser.ConfigParser instance, use has_section and has_option
            try:
                # If config is available and has Logging section
                if config and config.has_section('Logging'):
                    # Check if allowed_keys is specified
                    if config.has_option('Logging', 'allowed_keys'):
                        # Get comma-separated list of keys
                        keys_str = config.get('Logging', 'allowed_keys')
                        if keys_str.strip().upper() == 'ALL':
                            # Special case: ALL means show all logs
                            return ['ALL']
                        else:
                            # Parse comma-separated list
                            return [key.strip() for key in keys_str.split(',') if key.strip()]
            except Exception:
                # Ignore any other exceptions and return default keys
                pass

        # Return default keys if no config is available or no keys are specified
        return default_keys
