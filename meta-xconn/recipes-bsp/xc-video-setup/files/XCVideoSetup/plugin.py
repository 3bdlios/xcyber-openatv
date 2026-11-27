"""Apply the XC HDR output setting at every GUI start and whenever it changes."""
from Plugins.Plugin import PluginDescriptor


def autostart(reason, **kwargs):
	if reason != 0:
		return
	try:
		from Components import XCVideo
		if XCVideo.available():
			from Components.config import config
			config.av.xc_hdr.addNotifier(XCVideo.apply_hdr, immediate_feedback=True)
			install_video_settings()
	except Exception as error:
		print("[XCVideoSetup]", error)


def Plugins(**kwargs):
	return [PluginDescriptor(name="XC Video Setup", where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart)]


def install_video_settings():
    """Add native XC HDR policy to the standard Video Settings screen."""
    from Screens.VideoMode import VideoSettings
    from Components.config import config
    if getattr(VideoSettings, '_xc_hdr_entry', False):
        return
    original = VideoSettings.createSetup

    def createSetup(self, appendItems=None, prependItems=None):
        original(self, appendItems=appendItems, prependItems=prependItems)
        if config.av.videoport.value != 'HDMI':
            return
        if not any(len(entry) > 1 and entry[1] is config.av.xc_hdr for entry in self.list):
            entry = (_('HDR / SDR output'), config.av.xc_hdr,
                _('Auto follows the programme and TV capabilities: HDR10 or HLG for supported HDR content, SDR for normal channels. SDR only disables HDR output.'))
            self.list.insert(1, entry)
            self['config'].setList(self.list)
    VideoSettings.createSetup = createSetup
    VideoSettings._xc_hdr_entry = True
