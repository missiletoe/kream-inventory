@echo off
setlocal

:: 1️⃣ Python이 설치되어 있는지 확인
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Python이 설치되지 않았습니다.
    echo [INFO] Python을 설치해야 합니다: https://www.python.org/downloads/windows/
    pause
    exit /b
)

:: 2️⃣ 가상 환경 생성
if not exist venv (
    echo [INFO] 가상 환경(venv) 생성 중...
    python -m venv venv
)

:: 3️⃣ 가상 환경 활성화
call venv\Scripts\activate

:: 4️⃣ pip 업그레이드
echo [INFO] pip 업그레이드 중...
python -m pip install --upgrade pip

:: 5️⃣ 패키지 설치
pip install -r requirements.txt

:: 6️⃣ UI 프로그램 실행
python main.py