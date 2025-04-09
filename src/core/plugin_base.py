# core/plugin_base.py

class PluginBase:

    def __init__(self, name, browser, config, plugin_manager=None):

        self.name = name
        self.browser = browser            # Selenium WebDriver 객체 공유
        self.config = config              # 설정 관리자 공유
        self.plugin_manager = plugin_manager  # 필요 시 다른 플러그인 접근 가능