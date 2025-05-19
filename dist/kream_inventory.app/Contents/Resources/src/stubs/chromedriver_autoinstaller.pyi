"""chromedriver_autoinstaller 모듈에 대한 타입 스텁."""

from typing import Optional, Union

def install(cwd: bool = False, path: Optional[str] = None) -> str:
    """크롬 드라이버를 설치하고 드라이버 경로를 반환합니다.

    Args:
        cwd: 현재 작업 디렉토리에 드라이버를 설치할지 여부입니다.
        path: 드라이버를 설치할 경로입니다. 기본값은 None입니다.

    Returns:
        설치된 드라이버의 경로입니다.
    """
    ...

def get_chrome_version() -> Union[str, None]:
    """설치된 크롬 브라우저 버전을 반환합니다.

    Returns:
        설치된 크롬 브라우저의 버전 또는 None입니다.
    """
    ...
