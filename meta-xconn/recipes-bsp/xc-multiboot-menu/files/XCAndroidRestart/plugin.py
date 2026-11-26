"""GT Combo Android restart: retain native shutdown checks and defer error dialogs."""
import subprocess

def _t(text):
    from Plugins.SystemPlugins.XCSlots.plugin import _t as translate
    return translate(text)

from enigma import eTimer
from Plugins.Plugin import PluginDescriptor
from Screens.Standby import TryQuitMainloop, QUIT_REBOOT
from Screens.MessageBox import MessageBox

_pending_errors=[]
def run_helper(mode):
    try:
        result=subprocess.run(['/usr/bin/python3','/usr/lib/xcenigma/reboot-android.py',mode],capture_output=True,text=True,timeout=30)
        if result.returncode:
            return (result.stderr or result.stdout or 'Android helper failed').strip()[-2000:]
        return None
    except Exception as error:
        return str(error)

def error_later(session,message):
    # A TryQuitMainloop constructor can invoke close(True) before becoming modal.
    # Wait for Session to restore an executable screen before opening a dialog.
    timer=eTimer();entry=[timer,0];_pending_errors.append(entry)
    def display():
        entry[1]+=1
        dialog=getattr(session,'current_dialog',None)
        if getattr(session,'in_exec',False) and dialog is not None and getattr(dialog,'execing',False):
            timer.stop();_pending_errors.remove(entry)
            session.open(MessageBox,_t('Cannot prepare Android boot:')+'\n'+message,type=MessageBox.TYPE_ERROR)
        elif entry[1]<200:
            timer.start(50,True)
        else:
            timer.stop();_pending_errors.remove(entry)
            print('[XCAndroidRestart] Cannot display Android boot error:',message)
    timer.callback.append(display);timer.start(50,True)

class AndroidRestart(TryQuitMainloop):
    def close(self,value):
        if not value:
            subprocess.Popen(['/etc/init.d/avahi-daemon','start'])
        if value:
            error=run_helper('--arm')
            if error:
                result=TryQuitMainloop.close(self,False)
                subprocess.Popen(['/etc/init.d/avahi-daemon','start'])
                error_later(self.session,error)
                return result
        return TryQuitMainloop.close(self,value)

def restart(session,**kwargs):
    error=run_helper('--check')
    if error:
        session.open(MessageBox,_t('Cannot prepare Android boot:')+'\n'+error,type=MessageBox.TYPE_ERROR)
        return
    def confirmed(answer):
        if not answer:return
        try:
            result=subprocess.run(['/etc/init.d/avahi-daemon','stop'],capture_output=True,text=True,timeout=10)
            if result.returncode:raise RuntimeError(_t('Could not stop Avahi safely'))
        except Exception as exc:
            error_later(session,str(exc));return
        timer=eTimer();_restart_timers.append(timer)
        def proceed():
            timer.stop();_restart_timers.remove(timer)
            session.open(AndroidRestart,QUIT_REBOOT)
        timer.callback.append(proceed);timer.start(1000,True)
    session.openWithCallback(confirmed,MessageBox,_t('Restart to Android?'),type=MessageBox.TYPE_YESNO,default=False)

_restart_timers=[]

def menu(menuid,**kwargs):
    if menuid=='shutdown':return [('Restart to Android',restart,'xc_android_restart',45)]
    return []

def Plugins(**kwargs):
    # Kept importable for unified Multiboot; no separate Android menu entry.
    return []
