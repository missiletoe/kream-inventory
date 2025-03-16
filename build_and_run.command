#!/bin/bash

# 스크립트가 있는 디렉토리로 이동
cd "$(dirname "$0")"

# 현재 디렉토리 출력 (디버깅용)
echo "Current Directory: $(pwd)"

# 1️⃣ Python이 설치되어 있는지 확인
if ! command -v python3 &>/dev/null; then
    echo "[INFO] Python이 설치되지 않았습니다. 자동 설치 진행..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "[INFO] MacOS 환경 감지. Homebrew를 이용하여 Python 설치."
        if ! command -v brew &>/dev/null; then
            echo "[INFO] Homebrew가 설치되지 않음. Homebrew 설치 중..."
            /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"
        fi
        brew install python
    else
        echo "[ERROR] 현재 운영체제에서 자동 설치를 지원하지 않습니다."
        exit 1
    fi
else
    echo "[INFO] Python이 이미 설치되어 있습니다."
fi

# 2️⃣ 가상 환경 생성
if [ ! -d "venv" ]; then
    echo "[INFO] 가상 환경(venv) 생성 중..."
    python3 -m venv .venv
fi

# 3️⃣ 가상 환경 활성화
source venv/bin/activate
PYTHON_VER=$(python3 -c "import sys; print('python{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
export QT_QPA_PLATFORM_PLUGIN_PATH="venv/lib/${PYTHON_VER}/site-packages/PyQt6/Qt6/plugins/platforms"
export QT_PLUGIN_PATH="venv/lib/${PYTHON_VER}/site-packages/PyQt6/Qt6/plugins"

# 4️⃣ pip 업그레이드
echo "[INFO] pip 업그레이드 중..."
python3 -m pip install --upgrade pip

# 5️⃣ 필요한 패키지 설치
if [ -f "requirements.txt" ]; then
    echo "[INFO] requirements.txt 기반 패키지 설치 중..."
    pip install -r requirements.txt
else
    echo "[ERROR] requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# 6️⃣ UI 프로그램 실행
echo "[INFO] 프로그램 실행 중..."
python3 main.py