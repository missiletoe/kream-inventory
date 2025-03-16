# setup_win.py = 윈도우 exe 빌드 스크립트
# 
# KNOWN ISSUES
# 윈도우 Python 3.12 이상 버전에서 cx_Freeze import 시 import msilib 오류남 
# 윈도우 환경에서 cx_Freeze를 ModuleError 없이 구동시키려면 시스템에 Python 3.11 설치 후 venv 설치
# venv 설정 후 terminal에서 python setup_win.py build_exe 실행하면 build 파일 아래 exe가 만들어짐

from cx_Freeze import setup, Executable
import os

# QT 플러그인 경로 처리
build_exe_options = {
    "packages": ["os", "sys"],
    "includes": ["PyQt6"],
    "include_files": [
        # Qt 플랫폼 플러그인 복사
        (
            os.path.join(".venv", "Lib", "site-packages", "PyQt6", "Qt6", "plugins", "platforms"),
            os.path.join("platforms")
        )
    ],
    "excludes": [],
}

base = None

setup(
    name="KreamInventory",
    version="1.0",
    description="Kream Inventory Tool",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, target_name="kream_inventory.exe")]
)
