#!/bin/bash

echo "[INFO] 실행 환경을 설정합니다..."

# 1️⃣ Python 설치 확인
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python이 설치되지 않았습니다. 자동 설치 진행..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "[INFO] MacOS 환경 감지. Homebrew를 이용하여 Python을 설치합니다."
        if ! command -v brew &>/dev/null; then
            echo "[INFO] Homebrew가 설치되지 않음. Homebrew를 설치합니다..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python
    else
        echo "[ERROR] 현재 운영체제에서는 자동 설치를 지원하지 않습니다."
        exit 1
    fi
else
    echo "[INFO] Python이 이미 설치되어 있습니다."
fi

# 2️⃣ 필수 패키지 설치 (pkg-config, cairo, gobject-introspection)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "[INFO] MacOS에서 필수 라이브러리 설치 확인..."
    
    if ! command -v pkg-config &>/dev/null; then
        echo "[INFO] pkg-config가 누락됨. 설치 진행..."
        brew install pkg-config
    fi
    if ! command -v cairo-config &>/dev/null; then
        echo "[INFO] cairo가 누락됨. 설치 진행..."
        brew install cairo
    fi
    if ! pkg-config --exists gobject-introspection-1.0; then
        echo "[INFO] gobject-introspection이 누락됨. 설치 진행..."
        brew install gobject-introspection
    fi
else
    echo "[ERROR] 현재 운영체제에서는 필수 패키지를 자동 설치할 수 없습니다."
    exit 1
fi

# 3️⃣ 기존 가상 환경 삭제 후 재설정 (충돌 방지)
if [ -d "venv" ]; then
    echo "[INFO] 기존 가상 환경(venv)을 삭제합니다..."
    rm -rf venv
fi

echo "[INFO] 새로운 가상 환경을 생성합니다..."
python3 -m venv venv

# 4️⃣ 가상 환경 활성화
source venv/bin/activate

# 5️⃣ pip 및 필수 패키지 업그레이드
echo "[INFO] pip 및 필수 패키지를 업그레이드합니다..."
python3 -m pip install --upgrade pip setuptools wheel

# 6️⃣ 필요한 패키지 설치 (requirements.txt)
if [ -f "requirements.txt" ]; then
    echo "[INFO] requirements.txt 기반으로 패키지를 설치합니다..."
    pip install --no-cache-dir -r requirements.txt
else
    echo "[ERROR] requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# 7️⃣ 설치 확인 및 실행
echo "[INFO] 패키지 설치 확인 중..."
if ! python3 -c "import selenium, PyQt6" &>/dev/null; then
    echo "[ERROR] 필수 패키지 중 일부가 누락되었습니다. 수동 설치가 필요할 수 있습니다."
    exit 1
fi

# 8️⃣ 프로그램 실행
echo "[INFO] 프로그램을 실행합니다..."
python3 main.py