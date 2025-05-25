#!/bin/bash
set -e  # 에러 발생 시 즉시 중단

echo "🔍 가상환경 활성화 중..."
source .venv/bin/activate
echo "📌 현재 사용 중인 Python: $(which python)"

echo "🔍 프로젝트 루트 디렉토리로 이동 중..."
cd "$(dirname "$0")"

echo "🔍 패키지 설치 중..."
pip install -r requirements.txt

echo "🧹 린트 검사 실행 중..."
./lint.sh

echo "🚀 PyInstaller로 빌드 중..."
pyinstaller --noconfirm kream_inventory.spec

echo "🔏 보안 속성 해제 및 앱 서명 중..."
sudo xattr -rd com.apple.quarantine dist/kream_inventory.app
sudo /usr/bin/codesign --force --deep --sign - dist/kream_inventory.app

echo "🎉 빌드 완료! 앱은 dist/kream_inventory.app에 있습니다."
echo "🔑 앱 서명 완료! 앱을 실행할 수 있습니다."

echo "========================================================"
echo "🔍 앱 실행 문제 디버깅을 위한 정보:"
echo "- 앱을 터미널에서 실행하여 오류 로그 확인: open -a Terminal dist/kream_inventory.app/Contents/MacOS/kream_inventory"
echo "- 또는 로그 파일 확인: cat ~/Library/Logs/DiagnosticReports/kream_inventory_*.crash"
echo "========================================================"