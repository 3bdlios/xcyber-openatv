from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
VERSION = "0.2"
def main(session, **kwargs):
    session.open(MessageBox, "XC GitHub update test\nInstalled version: " + VERSION + "\nFeed: xcyber-openatv", MessageBox.TYPE_INFO)
def Plugins(**kwargs):
    return [PluginDescriptor(name="XC Update Test", description="GitHub update test " + VERSION, where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
