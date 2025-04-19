from ..plugins import detail_plugin
from ..plugins import search_plugin, macro_plugin, login_plugin


class PluginManager:

    def __init__(self, browser, config):
        self.browser = browser
        self.config = config
        self.plugins = {}

    def load_plugins(self):

        plugin_classes = [
            login_plugin.LoginPlugin,
            search_plugin.SearchPlugin,
            detail_plugin.DetailPlugin,
            macro_plugin.MacroPlugin
        ]

        for cls in plugin_classes:
            self._init_plugin(cls)

    def _init_plugin(self, PluginClass):

        plugin_instance = PluginClass(browser=self.browser, config=self.config, plugin_manager=self)
        self.plugins[plugin_instance.name] = plugin_instance

    def get_plugin(self, name):
        return self.plugins.get(name)