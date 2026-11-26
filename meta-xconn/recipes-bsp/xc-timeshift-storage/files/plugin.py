"""Keep XC timeshift on mounted storage when the default root path is unusable."""
import os
from Plugins.Plugin import PluginDescriptor
from Components.config import config,configfile

def start(reason,session=None,**kwargs):
    if reason != 0 or session is None or not os.path.ismount('/storage'):
        return
    try:
        item=config.usage.timeshift_path
        old=item.value
        try:
            current=os.statvfs(old)
            if current.f_bavail*current.f_frsize >= 1024**3 and os.stat(old).st_dev != os.stat('/').st_dev:
                return
        except OSError:
            pass
        target='/storage/timeshift/'
        os.makedirs(target,exist_ok=True)
        free=os.statvfs(target)
        if free.f_bavail*free.f_frsize < 1024**3:
            return
        choices=list(item.choices)
        if target not in choices:
            choices.append(target)
        item.setChoices(choices,default=item.default)
        item.value=target;item.save()
        bookmarks=config.usage.allowed_timeshift_paths
        if target not in bookmarks.value:
            bookmarks.value=list(bookmarks.value)+[target];bookmarks.save()
        configfile.save()
        print('[XC] Timeshift storage restored:',target)
    except Exception as e:
        print('[XC] Timeshift storage check failed:',e)
def Plugins(**kwargs):
    return [PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART,fnc=start)]
