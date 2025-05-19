"""매크로 처리 모듈.

이 모듈은 반복 작업 자동화와 관련된 기능을 제공합니다.
"""

from .macro_plugin import MacroPlugin
from .macro_toast_handler import MacroToastHandler

__all__ = ["MacroPlugin", "MacroToastHandler"]
