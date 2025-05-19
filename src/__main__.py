"""애플리케이션의 시작점입니다."""

import logging
import sys

from src import main

# 디버깅을 위한 로그 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logging.getLogger().setLevel(logging.DEBUG)
print("디버그 모드로 실행합니다.")

if __name__ == "__main__":
    main()
