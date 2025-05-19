"""설정 파일을 사용하여 애플리케이션 설정을 관리합니다."""

import configparser
import os
import sys
from typing import Optional


class ConfigManager:
    """애플리케이션 설정 읽기 및 쓰기를 처리합니다."""

    def __init__(self: "ConfigManager", config_path: str) -> None:
        """설정 파일 경로를 사용하여 ConfigManager를 초기화합니다.

        Args:
            config_path: 설정 파일 경로입니다 (예: 'config.ini').
        """
        self.cfg = configparser.ConfigParser()
        self.path = config_path

        if os.path.exists(config_path):
            self.cfg.read(config_path, encoding="utf-8")
        else:
            self._create_default()

    def _create_default(self: "ConfigManager") -> None:
        """설정 파일이 없으면 기본 설정 파일을 생성합니다."""
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

        # Default settings
        self.cfg["Browser"] = {"user_agent": user_agent, "headless": "yes"}

        self.cfg["Macro"] = {"min_interval": "8", "max_interval": "18"}

        # Save default config to file
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

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
        # configparser.getboolean은 fallback이 부울 문자열이 아니고 옵션을 찾을 수 없는 경우
        # ValueError를 발생시킬 수 있습니다. 따라서 fallback 로직을 더 명시적으로 처리합니다.
        if self.cfg.has_option(section, option):
            return self.cfg.getboolean(section, option)
        if fallback is not None:
            return fallback
        # This case should ideally not be reached if fallback has a default or is always provided.
        # Raising an error or returning a default boolean might be options.
        raise KeyError(
            f"Option {option} not found in section {section} and no fallback provided."
        )
