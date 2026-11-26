"""A direct, accessible menu for the original IPAudioPlus delay controls."""
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
import os
_INSTALLED=False

class DelaySeconds(Screen):
    skin='''<screen name="XCIPADelaySeconds" position="center,center" size="760,380" flags="wfNoBorder" backgroundColor="#ff000000">
      <eLabel position="0,0" size="760,380" zPosition="-1" backgroundColor="#252b37" cornerRadius="28" />
      <widget zPosition="1" name="brand" position="30,25" size="700,45" font="Regular;30" foregroundColor="#dce4ef" backgroundColor="#252b37" transparent="1" />
      <widget zPosition="1" name="video" position="30,95" size="700,65" font="Regular;30" halign="center" foregroundColor="#dce4ef" backgroundColor="#303844" cornerRadius="16" />
      <widget zPosition="1" name="audio" position="30,170" size="700,65" font="Regular;30" halign="center" foregroundColor="#dce4ef" backgroundColor="#303844" cornerRadius="16" />
      <widget zPosition="1" name="help" position="30,255" size="700,35" font="Regular;22" halign="center" foregroundColor="#95a6bf" backgroundColor="#252b37" transparent="1" />
      <widget zPosition="1" name="status" position="30,305" size="700,45" font="Regular;22" halign="center" foregroundColor="#36dba0" backgroundColor="#252b37" transparent="1" />
    </screen>'''
    def __init__(self,session,owner):
        Screen.__init__(self,session)
        self.owner=owner
        self.mode='video'
        self.delay_values={'video':float(getattr(owner,'delay_seconds',0) or 0),'audio':float(getattr(owner,'audio_delay_seconds',0) or 0)}
        self['brand']=Label('IP AUDIO +   |   المزامنة')
        self['video']=Label('');self['audio']=Label('')
        self['help']=Label('فوق / تحت: اختيار     يمين / يسار: نصف ثانية')
        self['status']=Label('OK: تطبيق التأخير     EXIT: إغلاق')
        self['actions']=ActionMap(['OkCancelActions','DirectionActions'],{
            'left':lambda:self.step(-0.5),'right':lambda:self.step(0.5),
            'up':self.select,'down':self.select,
            'ok':self.apply,'cancel':self.cancel},-30)
        self.refresh()
    def refresh(self):
        for mode,label in [('video','تأخير الصورة'),('audio','تأخير الصوت')]:
            self[mode].setText('%s   %.1f s   %s' % ('◀' if self.mode==mode else ' ',self.delay_values[mode],label))
    def select(self):self.mode='audio' if self.mode=='video' else 'video';self.refresh()
    def step(self,delta):
        self.delay_values[self.mode]=round(max(0.0,min(120.0,self.delay_values[self.mode]+delta)),1)
        self.refresh()
    def apply(self):self.close((self.mode,self.delay_values[self.mode]))
    def cancel(self):self.close(None)

class DelayMenu:
    def __init__(self,screen):self.screen=screen
    def open(self):
        self.screen.session.openWithCallback(self.apply,DelaySeconds,self.screen)
        return 1
    def apply(self,result):
        if result is None:return
        mode,value=result
        self.screen.start_inline_edit(mode)
        self.screen.inline_edit_value=float(value)
        self.screen._inline_edit_apply()
        print('[XC IPA delay applied]',mode,value)


def bind(screen,active=False):
    if getattr(screen,'_xc_delay_menu_version',0)==5:return
    old=screen['xc_delay_controls'] if 'xc_delay_controls' in screen else None
    if old:
        old.setEnabled(False)
        if active:old.execEnd()
    menu=DelayMenu(screen)
    screen._xc_delay_menu=menu
    screen._xc_delay_menu_version=5
    def reset():
        from Plugins.Extensions.IPAudioPlus import core_plugin as core
        core.stop_ipaudio_clean(screen.session)
        # Re-open the native PCM without blocking Enigma's event loop.
        import subprocess
        subprocess.Popen(['/usr/sbin/xc-audio-reopen'],stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,start_new_session=True)
        screen.delay_seconds=0.0
        screen.audio_delay_seconds=0.0
        screen._restore_delay_rows_display()
        print('[XC IPA Reset] external audio stopped; native restore requested')
        return 1
    actions=ActionMap(['XCIPADelayControls'],{'menu':menu.open,'reset':reset,'ignore':lambda:1},-30)
    screen['xc_delay_controls']=actions
    if active:actions.execBegin()

def install(reason,**kwargs):
    global _INSTALLED
    if reason!=0 or _INSTALLED:return
    try:
        from Plugins.Extensions.IPAudioPlus import core_plugin as core
        from keymapparser import readKeymap,removeKeymap
        from Components.config import config,configfile
        cfg=config.plugins.IPAudioPlus
        choices=list(cfg.timeshift_storage.choices)
        custom=next((v for v in choices if 'custom' in str(v).lower()),None)
        if custom is not None and os.path.ismount('/storage'):
            os.makedirs('/storage/timeshift',exist_ok=True)
            cfg.timeshift_storage.value=custom
            cfg.timeshift_custom_path.value='/storage/timeshift/'
            cfg.timeshift_storage.save();cfg.timeshift_custom_path.save()
            core.apply_timeshift_storage();configfile.save()
        print('[XC IPA storage]',choices,core.get_effective_timeshift_path())
        path=os.path.join(os.path.dirname(__file__),'keymap.xml')
        removeKeymap(path);readKeymap(path)
        cls=core.IPAudioPlusScreen
        if not getattr(cls,'_xc_delay_menu_hook',False):
            original=cls.__init__
            def init(self,*args,**kw):
                original(self,*args,**kw)
                bind(self)
            cls.__init__=init
            cls._xc_delay_menu_hook=True
        _INSTALLED=True
        from Screens.InfoBar import InfoBar
        session=InfoBar.instance and InfoBar.instance.session
        if session:
            dialogs=[session.current_dialog]+[x[0] for x in session.dialog_stack]
            for d in dialogs:
                if isinstance(d,cls):bind(d,d is session.current_dialog)
    except Exception as e:
        import traceback
        print('[XC IPA delay menu]',traceback.format_exc())

def Plugins(**kwargs):return [PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART,fnc=install)]
