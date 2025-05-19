#!/bin/bash
set -e  # 오류 발생 시 즉시 중단

# 필요한 환경 변수 설정
# export PYTHONPATH=$PWD:$PYTHONPATH

# 가상환경 활성화
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 작업 디렉토리로 변경
cd "$(dirname "$0")"

# 애플리케이션 실행
echo "🚀 크림 인벤토리 애플리케이션 실행 중..."
python -m src.main

# 가상환경 비활성화
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 