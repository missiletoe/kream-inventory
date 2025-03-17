@echo off

:: 윈도우에서 배치파일 실행 시 cmd가 순간적으로 떴다가 사라지는 문제 해결방법
:: 1. 한글 깨짐 현상 해결 -> CP949나 UTF-8로 된 인코딩을 UTF-8 with BOM 으로 설정
:: 2. 개행 오류 현상 해결 -> LF로 된 개행형식을 CRLF 로 설정
:: 3. git commit & push 할 때 crlf를 자동으로 lf 로 변환해주는 설정값 변경:
::    git config --global core.autocrlf false

:: utf-8 코드페이지 설정 (한글 깨짐 현상 수정)
chcp 65001 >nul

:: 스크립트가 있는 디렉터리로 이동
cd /d "%~dp0"
echo Current Directory: %cd%

:: 시스템에 Python 설치 여부 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 시스템에 Python이 없습니다. winget으로 설치 중...
    winget install --id Python.Python.3.9 --silent
    if %errorlevel% neq 0 (
         echo [ERROR] Python 설치 실패.
         exit /b 1
    ) else (
         echo [INFO] Python 설치 완료.
    )
) else (
    echo [INFO] 시스템에 Python이 이미 설치되어 있습니다.
)

:: 가상환경 생성
if not exist ".venv" (
    echo [INFO] 가상환경 생성 중...
    python -m venv .venv
    if %errorlevel% neq 0 (
         echo [ERROR] 가상환경 생성 실패.
         exit /b 1
    )
)
if not exist ".venv" (
    echo [ERROR] 가상환경이 존재하지 않습니다.
    exit /b 1
)

:: 가상환경 활성화
if not exist ".venv\Scripts\activate" (
    echo [ERROR] 가상환경 스크립트 없음.
    exit /b 1
)
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] 가상환경 활성화 실패.
    exit /b 1
)

:: QT 플러그인 경로 설정
set QT_QPA_PLATFORM_PLUGIN_PATH=.venv\Lib\site-packages\PyQt6\Qt6\plugins\platforms
set QT_PLUGIN_PATH=.venv\Lib\site-packages\PyQt6\Qt6\plugins

:: Qt 개발 도구(qmake) 설치 여부 확인 및 PATH 추가
where qmake >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] qmake가 설치되어 있지 않습니다. pip로 PyQt6 개발 도구 설치 중...
    winget install --id=Qt.QtDesigner --silent
)

:: requirements.txt 기반 패키지 설치
if exist "requirements.txt" (
    echo [INFO] 필수 패키지 설치중...
    pip install -r requirements.txt
)

:: 프로그램 실행
echo [INFO] 프로그램 실행...
python main.py
if %errorlevel% neq 0 (
    echo [ERROR] 프로그램 에러 발생.
    exit /b 1
)