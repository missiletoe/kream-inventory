"""크림 인벤토리 애플리케이션을 위한 플러그인입니다.

이 패키지는 로그인, 상품 검색, 매크로 작업 등 애플리케이션의 기능을 확장하는 다양한 플러그인을 포함합니다.
"""

from .login import LoginManager, LoginPlugin
from .macro import MacroPlugin, MacroToastHandler

# Import search plugins
from .search import DetailPlugin, SearchPlugin

__all__ = [
    "LoginManager",
    "LoginPlugin",
    "MacroPlugin",
    "MacroToastHandler",
    "SearchPlugin",
    "DetailPlugin",
]
