# core/config.py
import configparser, os

from setuptools.package_index import user_agent


class ConfigManager:

    def __init__(self, config_path):

        self.cfg = configparser.ConfigParser()
        self.path = config_path

        if os.path.exists(config_path):
            self.cfg.read(config_path, encoding='utf-8')

        else:
            self._create_default()

    def _create_default(self):

        # 기본 설정값 작성
        self.cfg['Browser'] = {
            'user_agent': user_agent,
            'headless': 'yes'
        }

        self.cfg['Macro'] = {
            'min_interval': '8',
            'max_interval': '18'
        }

        # etc...
        with open(self.path, 'w') as f:
            self.cfg.write(f)

    def get(self, section, option, fallback=None):
        return self.cfg.get(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=None):
        return self.cfg.getboolean(section, option, fallback=fallback)
    # 필요 시 set() 및 save() 메서드 구현