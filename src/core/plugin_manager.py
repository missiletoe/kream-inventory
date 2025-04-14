# core/plugin_manager.py

from ..plugins import detail_plugin
from ..plugins import search_plugin, macro_plugin, login_plugin


class PluginManager:

    def __init__(self, browser, config):
        self.browser = browser
        self.config = config
        self.plugins = {}

    def load_plugins(self):

        # 방법1: 수동 등록
        plugin_classes = [
            login_plugin.LoginPlugin,
            search_plugin.SearchPlugin,
            detail_plugin.DetailPlugin,
            macro_plugin.MacroPlugin
        ]

        for cls in plugin_classes:
            self._init_plugin(cls)

        # 방법2 (대안): 자동 검색 로딩
        # for module_name in ['login_plugin','search_plugin','detail_plugin','macro_plugin']:
        #     module = importlib.import_module(f'kream_inv.plugins.{module_name}')
        #     for _, obj in inspect.getmembers(module, inspect.isclass):
        #         if issubclass(obj, PluginBase) and obj is not PluginBase:
        #             self._init_plugin(obj)

    def _init_plugin(self, PluginClass):

        # 각 플러그인 인스턴스 생성 시 필요한 공용 객체를 주입
        plugin_instance = PluginClass(browser=self.browser, config=self.config, plugin_manager=self)
        self.plugins[plugin_instance.name] = plugin_instance

    def get_plugin(self, name):
        return self.plugins.get(name)