"""kream_inventory 패키지 설정 스크립트."""

import os

from setuptools import find_packages, setup

# 프로젝트 루트 디렉토리 내 readme.md 파일이 있으면 긴 설명으로 사용
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="kream_inventory",
    version="0.2.1",
    author="missiletoe",
    description="KREAM 보관판매 매크로 애플리케이션",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    # 패키지 데이터 포함 (예: 이미지, 아이콘 등)
    include_package_data=True,
    # 필수 패키지 의존성
    install_requires=[
        "PyQt6>=6.7.0",
        "selenium>=4.15.2",
        "requests>=2.31.0",
        "chromedriver-autoinstaller>=0.6.4",
        "webdriver-manager>=4.0.1",
    ],
    # 진입점 정의
    entry_points={
        "console_scripts": [
            "kream_inventory = kream_inventory:main",
        ],
        "gui_scripts": [
            "kream_inventory_gui = kream_inventory:main",  # Windows에서 콘솔 창 없이 실행
        ],
    },
    # 파이썬 버전 요구사항
    python_requires=">=3.8",
    # 분류 태그 (선택 사항)
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Private :: Do Not Upload",  # PyPI에 업로드하지 않음
    ],
)
