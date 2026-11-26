"""Close native discovery before Twisted unregisters its poll descriptors."""
import ctypes
from Plugins.Plugin import PluginDescriptor

_runtime=None
_closed=False
_trigger=None


def close_discovery():
    global _closed
    if _closed or _runtime is None:
        return
    _runtime._Z16done_servicepeerv()
    _runtime._Z13e2avahi_closev()
    _closed=True
    print('[XCAvahiShutdownEarly] native discovery closed before reactor teardown')


def autostart(reason,**kwargs):
    global _runtime,_trigger
    if reason == 0 and _trigger is None:
        from twisted.internet import reactor
        _runtime=ctypes.PyDLL(None)
        for name in ('_Z16done_servicepeerv','_Z13e2avahi_closev'):
            function=getattr(_runtime,name)
            function.argtypes=[]
            function.restype=None
        _trigger=reactor.addSystemEventTrigger('before','shutdown',close_discovery)
        print('[XCAvahiShutdownEarly] before-shutdown reactor trigger armed')
    # Deliberately no late plugin-shutdown fallback: that point is too late
    # in OpenBH, after Twisted has already recycled registered descriptors.


def Plugins(**kwargs):
    return [PluginDescriptor(name='XC Avahi early shutdown',where=PluginDescriptor.WHERE_AUTOSTART,fnc=autostart,needsRestart=False)]
