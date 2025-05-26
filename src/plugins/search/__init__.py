"""검색 처리 모듈.

이 모듈은 상품 검색과 관련된 기능을 제공합니다.
"""

from src.plugins.search.detail_plugin import DetailPlugin
from src.plugins.search.search_plugin import SearchPlugin

__all__ = ["SearchPlugin", "DetailPlugin"]
