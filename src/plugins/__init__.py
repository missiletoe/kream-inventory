"""플러그인 모듈.

이 모듈은 애플리케이션의 각종 플러그인을 포함합니다.
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
