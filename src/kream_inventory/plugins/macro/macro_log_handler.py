from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal


class MacroLogHandler(QObject):
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    def direct_log(self, message):
        """Logs a message directly without filtering, intended for critical messages like toasts."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_message.emit(log_message)

    def log(self, message, allowed_key=None):
        """로그 메시지를 생성하고 필터링하여 발신"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # Define allowed log messages/patterns (keys can be used for easier identification)
        allowed_logs = {
            "START": "매크로 구동 시작",
            "STOP": "매크로 구동 정지",
            "ATTEMPT_FAIL": "보관판매 신청 시도 {attempt}회 — 실패", # Placeholder for attempt number
            "RELOGIN_SUCCESS": "재로그인 성공",
            "PAGE_ENTRY_SUCCESS": "{page_name} 페이지 진입 성공", # Placeholder for page name
            "FINAL_SUCCESS": "보관판매 신청 완료. 매크로 정지"
            # Toast messages are handled by direct_log via ToastHandler
        }

        # Check if the message matches an allowed pattern or if an allowed_key is provided
        should_log = False
        if allowed_key and allowed_key in allowed_logs:
             # Format message if necessary (e.g., for attempt number, page name)
             # This part needs refinement based on how parameters are passed
             formatted_message_template = allowed_logs[allowed_key]
             # Simple placeholder replacement for now
             if "{attempt}" in formatted_message_template:
                 # Requires attempt number passed somehow, maybe as part of the message string itself initially?
                 # Example: self.log(f"ATTEMPT_FAIL:{attempt}", allowed_key="ATTEMPT_FAIL")
                 # Or pass parameters: self.log("some internal detail", allowed_key="ATTEMPT_FAIL", attempt=attempt)
                 # Let's assume the message itself contains the final string for now
                 log_message = f"[{timestamp}] {message}" # Use the pre-formatted message
                 should_log = True
             elif "{page_name}" in formatted_message_template:
                 log_message = f"[{timestamp}] {message}" # Use the pre-formatted message
                 should_log = True
             else:
                 # For exact matches like START, STOP, RELOGIN_SUCCESS, FINAL_SUCCESS
                 if message == formatted_message_template:
                      should_log = True

        # Fallback: Check if the raw message matches any allowed message (useful if allowed_key isn't used)
        if not should_log:
            for key, allowed_msg_template in allowed_logs.items():
                # Handle templates vs exact matches
                if "{attempt}" in allowed_msg_template or "{page_name}" in allowed_msg_template:
                     # Check if the message starts with the non-placeholder part
                     base_msg = allowed_msg_template.split("{")[0]
                     if message.startswith(base_msg):
                          log_message = f"[{timestamp}] {message}" # Log the full message passed in
                          should_log = True
                          break
                elif message == allowed_msg_template:
                     should_log = True
                     break

        if should_log:
            self.log_message.emit(log_message)
        # Else: Do nothing, filter out the log 