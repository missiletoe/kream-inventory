# core/browser.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class BrowserManager:

    def __init__(self, config):
        self.config = config
        self.driver = None

    def get_driver(self):

        if not self.driver:
            options = Options()

            # Apply consistent settings from ConfigManager
            user_agent = self.config.get('Browser', 'user_agent', fallback=None)

            if user_agent:
                options.add_argument(f'user-agent={user_agent}')

            if self.config.getboolean('Browser', 'headless', fallback=False):
                options.add_argument('--headless')

            self.driver = webdriver.Chrome(options=options)

        return self.driver

    def quit(self):

        if self.driver:
            self.driver.quit()
            self.driver = None