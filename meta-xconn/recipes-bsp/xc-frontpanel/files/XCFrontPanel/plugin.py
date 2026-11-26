"""XC front panel: channel name/number, menu names and clock on the 4-digit display via xc-fpd."""
import socket
import time

from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from enigma import iPlayableService, eServiceReference, eServiceCenter

SOCK = '/run/xc-fp.sock'

config.plugins.xcfrontpanel = ConfigSubsection()
config.plugins.xcfrontpanel.channel = ConfigSelection(default='clock', choices=[
    ('clock', _('Clock only')), ('name', _('Channel name')), ('number', _('Channel number')), ('both', _('Number, then name'))])
config.plugins.xcfrontpanel.menus = ConfigYesNo(default=False)
config.plugins.xcfrontpanel.standby = ConfigSelection(default='clock', choices=[('clock', _('Clock')), ('off', _('Off'))])
config.plugins.xcfrontpanel.scroll = ConfigSelection(default='words', choices=[
    ('words', _('Word by word')), ('once', _('Scroll once')), ('loop', _('Scroll continuously')),
    ('none', _('First four characters only'))])
config.plugins.xcfrontpanel.brightness = ConfigSelection(default='4', choices=[(str(n), str(n)) for n in range(1, 8)])

# Short 7-segment friendly labels for common screens; anything else uses the screen title.
LABELS = {
    'MainMenu': 'MENU', 'Menu': 'MENU', 'ChannelSelection': 'CHAN', 'ChannelSelectionRadio': 'RADIO',
    'MovieSelection': 'REC', 'MoviePlayer': 'PLAY', 'EPGSelection': 'EPG', 'GraphMultiEPG': 'EPG',
    'PluginBrowser': 'PLUG', 'TimerEditList': 'TIMER', 'About': 'INFO', 'Setup': 'SETUP',
    'NimSetup': 'TUNER', 'NimSelection': 'TUNER', 'ServiceScan': 'SCAN', 'ScanSetup': 'SCAN',
    'AudioSelection': 'AUDIO', 'Subtitles': 'SUB', 'QuickSubtitlesConfigMenu': 'SUB',
    'NetworkAdapterSelection': 'NET', 'AdapterSetup': 'NET', 'VideoSetup': 'VIDEO', 'VideoMode': 'VIDEO',
    'HarddiskSelection': 'HDD', 'TimeshiftState': 'TS', 'Timeshift': 'TS',
    'XCSlotsScreen': 'BOOT', 'XCFrontPanelSetup': 'PANEL', 'SoftwareUpdate': 'UPD', 'BpBlue': 'BLUE',
}
VIEWING = ('InfoBar', 'MoviePlayer', 'SimpleMoviePlayer', 'DVDPlayer')
IGNORE = ('MessageBox', 'ChoiceBox', 'InputBox', 'Console', 'PinInput', 'TryQuitMainloop',
          'EventView', 'EventViewSimple', 'ServiceInfo', 'ServiceList')
STANDBY = ('Standby', 'Standby2')


def send(*parts):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            s.sendto(' '.join(str(p) for p in parts).encode('utf-8'), SOCK)
        finally:
            s.close()
    except OSError as error:
        print('[XCFrontPanel] send failed:', error)


def displayable(text):
    return ''.join(c for c in text if c.isascii() and (c.isalnum() or c in ' -_.')).strip()


class Controller:
    def __init__(self, session):
        self.session = session
        self.original_begin = session.execBegin
        self.standby = False
        session.execBegin = self.exec_begin
        session.nav.event.append(self.on_event)
        self.apply_settings()
        self.show_channel()

    def apply_settings(self):
        send('BRIGHT', config.plugins.xcfrontpanel.brightness.value)
        send('SCROLLMODE', 'loop' if config.plugins.xcfrontpanel.scroll.value == 'loop' else 'once')

    def text(self, label):
        label = displayable(label)
        if not label:
            return
        mode = config.plugins.xcfrontpanel.scroll.value
        if mode == 'none':
            send('TEXT', label[:4])
        elif mode == 'words':
            send('WORDS', label)
        else:
            send('SCROLL', label)

    def channel_name_number(self):
        ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
        if ref is None:
            return '', 0
        name = ''
        try:
            info = eServiceCenter.getInstance().info(ref)
            name = info and info.getName(ref) or ''
        except Exception:
            pass
        try:
            number = ref.getChannelNum()
        except Exception:
            number = 0
        return name, number

    def show_channel(self):
        if self.standby:
            return
        mode = config.plugins.xcfrontpanel.channel.value
        if mode == 'clock':
            send('CLOCK')
            return
        name, number = self.channel_name_number()
        shown = displayable(name)
        if mode == 'number' and number:
            send('TEXT', '%4d' % number)
        elif mode == 'both' and number and shown:
            send('WORDS' if config.plugins.xcfrontpanel.scroll.value == 'words' else 'SCROLL', '%d %s' % (number, shown))
        elif shown:
            self.text(shown)
        elif number:
            send('TEXT', '%4d' % number)
        else:
            send('CLOCK')

    def on_event(self, event):
        if event == iPlayableService.evStart:
            self.show_channel()

    def exec_begin(self, *args, **kwargs):
        result = self.original_begin(*args, **kwargs)
        try:
            self.update_for_dialog()
        except Exception as error:
            print('[XCFrontPanel]', error)
        return result

    def update_for_dialog(self):
        dialog = getattr(self.session, 'current_dialog', None)
        kind = type(dialog).__name__
        if kind in STANDBY:
            self.standby = True
            send('CLOCK' if config.plugins.xcfrontpanel.standby.value == 'clock' else 'OFF')
            return
        if self.standby:
            self.standby = False
        if kind in VIEWING:
            self.show_channel()
            return
        if kind in IGNORE or not config.plugins.xcfrontpanel.menus.value or config.plugins.xcfrontpanel.channel.value == 'clock':
            return
        label = LABELS.get(kind)
        if label is None:
            try:
                label = dialog.getTitle() if hasattr(dialog, 'getTitle') else ''
            except Exception:
                label = ''
            if not displayable(label or ''):
                label = kind
        self.text(label)

    def close(self):
        try:
            self.session.nav.event.remove(self.on_event)
        except ValueError:
            pass
        self.session.execBegin = self.original_begin


class XCFrontPanelSetup(Screen, ConfigListScreen):
    skin = """
    <screen name="XCFrontPanelSetup" position="center,center" size="720,420" title="XC Front Panel">
      <widget name="config" position="20,20" size="680,300" scrollbarMode="showOnDemand" />
      <widget name="key_red" position="20,360" size="200,40" font="Regular;22" halign="center" valign="center" backgroundColor="#9f1313" />
      <widget name="key_green" position="260,360" size="200,40" font="Regular;22" halign="center" valign="center" backgroundColor="#1f771f" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(_('XC Front Panel'))
        self['key_red'] = Label(_('Cancel'))
        self['key_green'] = Label(_('Save'))
        entries = [
            getConfigListEntry(_('Show on channel change'), config.plugins.xcfrontpanel.channel),
            getConfigListEntry(_('Show menu names'), config.plugins.xcfrontpanel.menus),
            getConfigListEntry(_('In standby'), config.plugins.xcfrontpanel.standby),
            getConfigListEntry(_('Long text'), config.plugins.xcfrontpanel.scroll),
            getConfigListEntry(_('Brightness'), config.plugins.xcfrontpanel.brightness),
        ]
        ConfigListScreen.__init__(self, entries, session=session)
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {
            'ok': self.save, 'green': self.save, 'save': self.save,
            'cancel': self.cancel, 'red': self.cancel}, -2)

    def save(self):
        for entry in self['config'].list:
            entry[1].save()
        config.plugins.xcfrontpanel.save()
        if _controller is not None:
            _controller.apply_settings()
        self.close()

    def cancel(self):
        for entry in self['config'].list:
            entry[1].cancel()
        self.close()


_controller = None


def sessionstart(reason, session=None, **kwargs):
    global _controller
    if reason == 0 and session is not None and _controller is None:
        try:
            _controller = Controller(session)
        except Exception as error:
            print('[XCFrontPanel] start failed:', error)
    elif reason != 0 and _controller is not None:
        _controller.close()
        _controller = None
        send('BOOT')   # GUI restarting: show the counter until the GUI is back


def open_setup(session, **kwargs):
    session.open(XCFrontPanelSetup)


def Plugins(**kwargs):
    return [
        PluginDescriptor(name='XC Front Panel', description=_('Front panel display: channel, menus, clock'),
                         where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
        PluginDescriptor(name=_('XC Front Panel'), description=_('Front panel display settings'),
                         where=PluginDescriptor.WHERE_PLUGINMENU, icon='plugin.png', fnc=open_setup),
    ]
