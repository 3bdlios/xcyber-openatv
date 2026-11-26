"""Unified installed-image, Android and XC recovery boot menu."""
import gettext,os,subprocess
from Components.Language import language
from contextlib import contextmanager
from pathlib import Path
from enigma import eTimer
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop,QUIT_REBOOT
from Plugins.SystemPlugins.XCSlots.boot_state import load_state,save_state

ARABIC = {'Multiboot': 'ملتي بوت', 'Multiboot — Select a boot target': 'ملتي بوت — اختر نظام الإقلاع', 'Android': 'أندرويد', 'XCEnigma Recovery': 'ركفري XCEnigma', 'Slot %s': 'السولت %s', 'Reboot to %s?': 'إعادة التشغيل إلى %s؟', 'Unable to prepare boot:': 'تعذر تجهيز الإقلاع:', 'Image BOOT partition was not found': 'لم أجد قسم BOOT الخاص بالنسخ', 'The selected image is no longer ready to boot': 'النسخة المحددة لم تعد جاهزة للإقلاع', 'Installed images, Android and XCEnigma Recovery': 'النسخ المثبتة وأندرويد وركفري XCEnigma', 'Restart to Android?': 'إعادة التشغيل إلى أندرويد؟', 'Cannot prepare Android boot:': 'تعذر تجهيز الإقلاع إلى أندرويد:', 'Could not stop Avahi safely': 'تعذر إيقاف خدمة Avahi بأمان'}

def _t(text):
    # Resolve on each call so switching the image language updates this menu.
    if language.getLanguage().lower().split('_')[0].split('-')[0]=='ar':
        return ARABIC.get(text,gettext.dgettext('enigma2',text))
    return gettext.dgettext('enigma2',text)

@contextmanager
def boot_directory():
    # Reuse BOOT when the image already mounted it. Never hold a mount across dialogs.
    for path in (Path('/boot'),Path('/flash')):
        if os.path.ismount(path) and (path/'xc').is_dir():
            yield path/'xc'
            return
    device=Path('/run/xc-boot').read_text().strip()
    if not device.startswith('/dev/'):
        raise ValueError(_t('Image BOOT partition was not found'))
    folder=Path('/tmp/xc-multiboot');folder.mkdir(exist_ok=True)
    subprocess.run(['mount','-t','vfat',device,str(folder)],check=True,capture_output=True)
    try:
        yield folder/'xc'
    finally:
        subprocess.run(['umount',str(folder)],check=True,capture_output=True)


def boot_choices(state):
    items=[]
    for slot in state['slots']:
        if slot['status']=='ready':
            name=' '.join(v for v in (slot['image_name'],slot.get('version','')) if v)
            items.append((name+' — '+(_t('Slot %s')%slot['id']),slot['id']))
    items.extend([(_t('Android'),'android'),(_t('XCEnigma Recovery'),'recovery')])
    return items

_pending=[]
def show_error_later(session,error):
    timer=eTimer();entry=[timer,0];_pending.append(entry)
    def show():
        entry[1]+=1
        dialog=getattr(session,'current_dialog',None)
        if getattr(session,'in_exec',False) and dialog is not None and getattr(dialog,'execing',False):
            timer.stop();_pending.remove(entry)
            session.open(MessageBox,_t('Unable to prepare boot:')+'\n'+str(error),type=MessageBox.TYPE_ERROR)
        elif entry[1]<200:timer.start(50,True)
        else:timer.stop();_pending.remove(entry);print('[XCMultiboot]',error)
    timer.callback.append(show);timer.start(50,True)

class ImageRestart(TryQuitMainloop):
    def __init__(self,session,target):
        self.target=target;self.prepared=False
        TryQuitMainloop.__init__(self,session,QUIT_REBOOT)
    def close(self,value):
        if value and not self.prepared:
            try:
                with boot_directory() as folder:
                    state=load_state(folder)
                    target=self.target
                    if target!='recovery':
                        if type(target) is not int or not 1<=target<=len(state['slots']) or state['slots'][target-1]['status']!='ready':
                            raise ValueError(_t('The selected image is no longer ready to boot'))
                    state['selected']=target;save_state(folder,state)
                self.prepared=True
            except Exception as error:
                result=TryQuitMainloop.close(self,False)
                show_error_later(self.session,error)
                return result
        return TryQuitMainloop.close(self,value)


def main(session,**kwargs):
    try:
        with boot_directory() as folder:items=boot_choices(load_state(folder))
    except Exception as error:
        session.open(MessageBox,str(error),type=MessageBox.TYPE_ERROR);return
    def chosen(choice):
        if not choice:return
        target=choice[1]
        if target=='android':
            try:
                from Plugins.SystemPlugins.XCAndroidRestart.plugin import restart
                restart(session)
            except Exception as error:session.open(MessageBox,str(error),type=MessageBox.TYPE_ERROR)
            return
        def confirmed(answer):
            if answer:session.open(ImageRestart,target)
        session.openWithCallback(confirmed,MessageBox,_t('Reboot to %s?')%choice[0],type=MessageBox.TYPE_YESNO,default=False)
    session.openWithCallback(chosen,ChoiceBox,title=_t('Multiboot — Select a boot target'),list=items)


def menu(menuid,**kwargs):
    if menuid=='shutdown':return [(_t('Multiboot'),main,'xc_multiboot',24)]
    return []


def Plugins(**kwargs):
    return [PluginDescriptor(name=_t('Multiboot'),description=_t('Installed images, Android and XCEnigma Recovery'),where=PluginDescriptor.WHERE_MENU,fnc=menu)]
