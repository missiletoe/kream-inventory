import configparser
import os
import sys

class ConfigManager:

    def __init__(self, config_path):
        self.cfg = configparser.ConfigParser()
        self.path = config_path

        if os.path.exists(config_path):
            self.cfg.read(config_path, encoding='utf-8')
        else:
            self._create_default()

    def _create_default(self):
        # Set user-agent based on OS platform
        if sys.platform == 'darwin':
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        elif sys.platform == 'win32':
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        else:
            user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'

        # Default settings
        self.cfg['Browser'] = {
            'user_agent': user_agent,
            'headless': 'yes'
        }

        self.cfg['Macro'] = {
            'min_interval': '8',
            'max_interval': '18'
        }

        # Save default config to file
        with open(self.path, 'w') as f:
            self.cfg.write(f)

    def get(self, section, option, fallback=None):
        return self.cfg.get(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=None):
        return self.cfg.getboolean(section, option, fallback=fallback)