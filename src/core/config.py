"""설정 파일을 사용하여 애플리케이션 설정을 관리합니다."""

import configparser
import logging  # noqa: F401 # 로깅 모듈 임포트
import os
import sys
from typing import Optional

# logger_setup 임포트
from src.core.logger_setup import setup_logger

# 전역 로거 설정
logger = setup_logger(__name__)


class ConfigManager:
    """애플리케이션 설정 읽기 및 쓰기를 처리합니다."""

    def __init__(self: "ConfigManager", config_path: str) -> None:
        """설정 파일 경로를 사용하여 ConfigManager를 초기화합니다.

        Args:
            config_path: 설정 파일 경로입니다 (예: 'config.ini').
        """
        self.cfg = configparser.ConfigParser()
        self.path = config_path

        # 설정 파일 디렉토리 확인 및 생성
        config_dir = os.path.dirname(config_path)
        if not os.path.exists(config_dir) and config_dir:
            try:
                os.makedirs(config_dir)
                logger.info(f"설정 디렉토리 생성됨: {config_dir}")
            except Exception as e:
                logger.error(f"설정 디렉토리 생성 실패: {e}", exc_info=True)

        # 설정 파일 로딩 또는 생성
        if os.path.exists(config_path):
            try:
                self.cfg.read(config_path, encoding="utf-8")
                logger.info(f"설정 파일 로드 성공: {config_path}")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패, 기본값 사용: {e}", exc_info=True)
                self._create_default()
        else:
            logger.info(f"설정 파일이 존재하지 않습니다. 기본 설정 생성: {config_path}")
            self._create_default()

    def _create_default(self: "ConfigManager") -> None:
        """설정 파일이 없으면 기본 설정 파일을 생성합니다."""
        logger.info("기본 설정 파일 생성을 시작합니다.")
        # Set user-agent based on OS platform
        if sys.platform == "darwin":
            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            )
        elif sys.platform == "win32":
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            )
        else:
            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            )
        logger.debug(f"User-agent 설정: {user_agent}")

        # Default settings
        self.cfg["Browser"] = {"user_agent": user_agent, "headless": "yes"}
        self.cfg["Macro"] = {"min_interval": "8", "max_interval": "18"}
        logger.debug(
            f"기본 설정: Browser={self.cfg['Browser']}, Macro={self.cfg['Macro']}"
        )

        # Save default config to file
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                self.cfg.write(f)
                logger.info(f"기본 설정 파일 생성 성공: {self.path}")
        except Exception as e:
            logger.error(f"기본 설정 파일 생성 실패: {e}", exc_info=True)
            # 기본 설정 파일을 현재 디렉토리에 강제 저장 시도
            try:
                fallback_path = os.path.join(os.getcwd(), "config.ini")
                logger.warning(
                    f"기본 설정 파일을 현재 디렉토리에 저장 시도: {fallback_path}"
                )
                with open(fallback_path, "w", encoding="utf-8") as f:
                    self.cfg.write(f)
                    logger.info(
                        f"기본 설정 파일을 현재 디렉토리에 저장 성공: {fallback_path}"
                    )
                    self.path = fallback_path  # 경로 업데이트
            except Exception as e2:
                logger.error(f"대체 설정 파일 생성도 실패: {e2}", exc_info=True)

    def get(
        self: "ConfigManager", section: str, option: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """설정 값을 문자열로 가져옵니다.

        Args:
            section: 설정 파일의 섹션입니다.
            option: 섹션의 옵션입니다.
            fallback: 옵션을 찾을 수 없는 경우 반환할 값입니다.

        Returns:
            설정 값을 문자열로 반환하거나 fallback 값을 반환합니다.
        """
        return self.cfg.get(section, option, fallback=fallback)

    def getboolean(
        self: "ConfigManager",
        section: str,
        option: str,
        fallback: Optional[bool] = None,
    ) -> bool:
        """부울 설정 값을 가져옵니다.

        Args:
            section: 설정 파일의 섹션입니다.
            option: 섹션의 옵션입니다.
            fallback: 옵션을 찾을 수 없는 경우 반환할 값입니다 (부울 또는 None이어야 함).

        Returns:
            부울 설정 값 또는 fallback 값을 반환합니다.
        """
        try:
            if self.cfg.has_option(section, option):
                return self.cfg.getboolean(section, option)
            if fallback is not None:
                return fallback
        except Exception as e:
            logger.error(
                f"부울 설정 값 가져오기 실패 ({section}.{option}): {e}", exc_info=True
            )
            if fallback is not None:
                return fallback

        # 어떤 경우든 fallback이 None이고 다른 모든 것이 실패한 경우
        raise KeyError(
            f"옵션 {option}이 섹션 {section}에 없고 대체 값이 제공되지 않았습니다."
        )
