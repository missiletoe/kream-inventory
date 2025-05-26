"""애플리케이션에서 사용되는 이미지 에셋(아이콘, 로고 등)을 로드하는 유틸리티 함수들을 제공합니다."""

import os
import sys

import requests
from PyQt6.QtGui import QIcon, QPixmap, QScreen


def get_window_icon() -> QIcon:
    """운영체제에 맞는 윈도우 아이콘을 반환합니다."""
    if sys.platform == "darwin":
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets",
            "icon.icns",
        )
        return QIcon(icon_path)
    else:
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets",
            "icon.png",
        )
        return QIcon(icon_path)


def get_logo_pixmap(image_path: str | None = None) -> QPixmap:
    """애플리케이션 로고 이미지를 QPixmap 객체로 반환합니다."""
    # 이미지 경로가 유효한지 확인
    if image_path and os.path.exists(image_path) and os.path.isfile(image_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            return pixmap

    # 기본 로고 이미지 경로
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "assets",
        "logo.png",
    )

    # 기본 로고 파일이 존재하는지 확인
    if os.path.exists(logo_path) and os.path.isfile(logo_path):
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            return pixmap

    # 기본 빈 이미지 생성 및 반환
    empty_pixmap = QPixmap(256, 256)
    empty_pixmap.fill()
    return empty_pixmap


def get_navigation_icons() -> tuple[QIcon, QIcon]:
    """네비게이션 버튼(좌, 우) 아이콘을 QIcon 객체 튜플로 반환합니다."""
    left_icon_url = "https://cdn-icons-png.flaticon.com/512/271/271220.png"
    right_icon_url = "https://cdn-icons-png.flaticon.com/512/271/271228.png"

    # Left icon
    left_icon = QIcon()
    left_icon_data = requests.get(left_icon_url).content
    left_icon_pixmap = QPixmap()
    left_icon_pixmap.loadFromData(left_icon_data)
    left_icon.addPixmap(left_icon_pixmap)

    # Right icon
    right_icon = QIcon()
    right_icon_data = requests.get(right_icon_url).content
    right_icon_pixmap = QPixmap()
    right_icon_pixmap.loadFromData(right_icon_data)
    right_icon.addPixmap(right_icon_pixmap)

    return left_icon, right_icon


def get_button_size(screen: QScreen) -> int:
    """화면 DPI에 따라 버튼 크기를 반환합니다.

    Args:
        screen: 현재 화면 정보를 담고 있는 QScreen 객체입니다.

    Returns:
        버튼 크기를 정수값으로 반환합니다.
    """
    if sys.platform == "win32" and screen.logicalDotsPerInch() > 96:
        return 100
    return 50
