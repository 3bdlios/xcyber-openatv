"""Keep passive subtitle windows from occluding active receiver menus."""
from Plugins.Plugin import PluginDescriptor
import time

_installed=False


def viewing(session):
    dialog=getattr(session,'current_dialog',None)
    return type(dialog).__name__ in ('InfoBar','MoviePlayer','SimpleMoviePlayer','DVDPlayer')


def start(reason,session=None,**kwargs):
    global _installed
    if reason or session is None or _installed:
        return
    try:
        from Plugins.Extensions.ChannelLingo.skin.captions import CaptionOverlay
        from Plugins.Extensions.ChannelLingo.plugin import get_controller
    except ImportError:
        return
    original_show=CaptionOverlay.show
    original_begin=session.execBegin

    def show(overlay,*args,**kwargs):
        if viewing(overlay.session):
            return original_show(overlay,*args,**kwargs)
        return overlay.hide()

    def exec_begin(*args,**kwargs):
        result=original_begin(*args,**kwargs)
        controller=get_controller(session)
        overlay=getattr(controller,'overlay',None)
        if overlay is not None:
            if not viewing(session):
                overlay.hide()
            elif getattr(controller,'visible_until',0)>time.monotonic():
                overlay.show()
        return result

    CaptionOverlay.show=show
    session.execBegin=exec_begin
    _installed=True


def Plugins(**kwargs):
    return [PluginDescriptor(name='XC subtitle overlay compatibility',where=PluginDescriptor.WHERE_SESSIONSTART,fnc=start)]
