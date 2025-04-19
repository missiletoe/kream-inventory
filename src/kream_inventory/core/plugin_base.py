class PluginBase:

    def __init__(self, name, browser, config, plugin_manager=None):

        self.name = name
        self.browser = browser
        self.config = config
        self.plugin_manager = plugin_manager