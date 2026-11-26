"""OpenWebif screenshots on XC: Amlogic video capture (/dev/amvideocap0) plus OSD framebuffer.
The stock aio-grab knows no Amlogic video path and refuses to write a frame."""
import os
from Plugins.Plugin import PluginDescriptor


def sessionstart(reason, session=None, **kwargs):
    if reason != 0 or session is None:
        return
    try:
        if not os.path.exists('/dev/amvideocap0'):
            return
        from Plugins.Extensions.OpenWebif.controllers.models import grab
        grab.GRAB_PATH = os.path.join(os.path.dirname(__file__), 'capture.py')
        print('[XCScreenshot] OpenWebif grab redirected to Amlogic video + OSD capture')
    except Exception as error:
        print('[XCScreenshot] stock grab retained: %s' % error)


def Plugins(**kwargs):
    return [PluginDescriptor(name='XC Screenshot', description='Amlogic video and OSD capture for OpenWebif',
                             where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)]
