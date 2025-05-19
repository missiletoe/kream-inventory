"""크림 인벤토리 애플리케이션의 검색 관련 플러그인입니다."""

from .detail_plugin import DetailPlugin
from .search_plugin import SearchPlugin

__all__ = ["SearchPlugin", "DetailPlugin"]
