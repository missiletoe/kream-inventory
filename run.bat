@echo off

rem 가상환경 활성화
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo 가상환경이 없습니다. 가상환경을 먼저 생성하세요.
    exit /b 1
)

rem 작업 디렉토리로 변경
cd /d %~dp0

rem 애플리케이션 실행
echo 🚀 크림 인벤토리 애플리케이션 실행 중...
python -m src.main

rem 가상환경 비활성화
if defined VIRTUAL_ENV (
    call deactivate
)

pause 