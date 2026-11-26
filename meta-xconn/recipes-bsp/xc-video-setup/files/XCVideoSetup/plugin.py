"""Apply the XC HDR output setting at every GUI start and whenever it changes."""
from Plugins.Plugin import PluginDescriptor


def autostart(reason, **kwargs):
	if reason != 0:
		return
	try:
		from Components import XCVideo
		if XCVideo.available():
			from Components.config import config
			config.av.xc_hdr.addNotifier(XCVideo.apply_hdr)
	except Exception as error:
		print("[XCVideoSetup]", error)


def Plugins(**kwargs):
	return [PluginDescriptor(name="XC Video Setup", where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart)]
