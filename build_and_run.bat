@echo off

:: utf-8 코드페이지 설정 (한글 깨짐 현상 수정)
chcp 65001 >nul

:: REM 스크립트가 있는 디렉토리로 이동
cd /d "%~dp0"

echo Current Directory: %cd%

:: REM Python 설치 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python이 설치되지 않았습니다. https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe 에서 받은 exe파일로 설치 후 다시 시도해주세요.
    exit /b 1
) else (
    echo [INFO] Python이 설치되어 있습니다.
)

:: REM 가상환경(venv) 생성
if not exist "venv" (
    echo [INFO] 가상환경^(venv^) 생성 중...
    python -m venv .venv
)

:: REM 가상환경 활성화
call venv\Scripts\activate

:: REM QT 플러그인 경로 설정
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt6\Qt6\plugins\platforms
set QT_PLUGIN_PATH=venv\Lib\site-packages\PyQt6\Qt6\plugins

:: REM pip 업그레이드
(
    echo [INFO] pip 업그레이드 중...
    python -m pip install --upgrade pip
)

:: REM requirements.txt 기반 패키지 설치
if exist "requirements.txt" (
    echo [INFO] requirements.txt 기반 패키지 설치 중...
    pip install -r requirements.txt
) else (
    echo [ERROR] requirements.txt 파일을 찾지 못했습니다.
    exit /b 1
)

:: REM 프로그램 실행
echo [INFO] 프로그램 실행 중...
python main.py