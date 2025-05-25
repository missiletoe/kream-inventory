"""로깅 설정 모듈입니다."""

import datetime
import logging
import os

LOG_DIR = "logs"


def setup_logger(name: str) -> logging.Logger:
    """지정된 이름으로 로거를 설정하고 반환합니다.

    로그는 'logs' 디렉토리 아래에 타임스탬프 형식의 파일로 저장되며,
    콘솔에는 출력되지 않습니다. 로그 레벨은 DEBUG로 설정됩니다.

    Args:
        name: 로거의 이름입니다. 일반적으로 __name__을 사용합니다.

    Returns:
        설정된 logging.Logger 객체입니다.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 로그 디렉토리가 없으면 생성
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 파일 핸들러 설정 (타임스탬프 기반 파일명)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file = os.path.join(LOG_DIR, f"{timestamp}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # 로그 포맷 설정
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
    )
    file_handler.setFormatter(formatter)

    # 핸들러 추가 (기존 핸들러가 있다면 중복 추가 방지)
    if not logger.handlers:
        logger.addHandler(file_handler)

    # 콘솔 전파 방지
    logger.propagate = False

    return logger


def log_input(prompt: str) -> str | None:
    """input() 함수를 대체하여 사용자 입력을 로깅하고 None을 반환합니다.

    실제 사용자 입력이 필요한 경우 이 함수의 동작을 수정해야 합니다.

    Args:
        prompt: 사용자에게 보여줄 프롬프트 메시지입니다.

    Returns:
        항상 None을 반환하거나, 필요한 경우 기본값을 반환하도록 수정할 수 있습니다.
    """
    # 이 로거는 src.core.logger_setup 로거를 사용하게 됩니다.
    # 호출한 모듈의 로거를 사용하려면, 해당 로거를 인자로 받아야 합니다.
    # 현재 요구사항은 콘솔 출력을 막고 파일로만 로깅하는 것이므로,
    # 어떤 로거를 사용하든 파일로만 기록되면 됩니다.
    # setup_logger에서 propagate=False로 설정했으므로 콘솔 출력은 없습니다.
    logger = logging.getLogger(__name__)  # src.core.logger_setup 로거
    if not logger.hasHandlers():
        logger.warning(f"사용자 입력 요청 (실제 입력 없음, 핸들러 부재): {prompt}")
    else:
        logger.info(f"사용자 입력 요청 (프롬프트): {prompt}")

    return None


# 통합된 LogTracer 기능
LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

TOAST_KEYS: dict[str, str] = {
    "TOAST_CONTENT": "INFO",
    "TOAST_ERROR": "ERROR",
    "TOAST_BLOCK": "WARNING",
    "TOAST_RETRY": "WARNING",
    "REQUEST_LIMIT": "WARNING",
    "ERROR": "ERROR",
}


def trace_log(
    logger: logging.Logger,
    message: str,
    level: str = "INFO",
    allowed_key: str | None = None,
) -> None:
    """토스트 키에 따라 로그 수준을 매핑하여 메시지를 기록합니다.

    Args:
        logger: 로그를 기록할 Logger 객체입니다.
        message: 기록할 메시지입니다.
        level: 기본 로그 수준입니다 (예: "INFO").
        allowed_key: TOAST_KEYS에 정의된 키입니다.
    """
    log_level_str = level.upper()
    if allowed_key and allowed_key in TOAST_KEYS:
        log_level_str = TOAST_KEYS[allowed_key].upper()
    level_num = LEVELS.get(log_level_str, logging.INFO)
    logger.log(level_num, message)
