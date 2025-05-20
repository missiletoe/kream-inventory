@echo off
echo 🔍 가상환경 활성화 중...
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo 가상환경이 없습니다. 가상환경을 먼저 생성하세요.
    exit /b 1
)

echo 📌 현재 사용 중인 Python: %PYTHON%

echo 🔍 프로젝트 루트 디렉토리로 이동 중...
cd /d %~dp0

echo 🔍 패키지 설치 중...
pip install -r requirements.txt

echo 🧹 린트 검사 실행 중...
call lint.bat

echo 🚀 PyInstaller로 빌드 중...
pyinstaller kream_inventory.spec

echo 🎉 빌드 완료! 앱은 dist\kream_inventory.exe에 있습니다.

echo ========================================================
echo 🔍 앱 실행 문제 디버깅을 위한 정보:
echo - 앱을 cmd에서 실행하여 오류 로그 확인: dist\kream_inventory.exe
echo ========================================================

pause 