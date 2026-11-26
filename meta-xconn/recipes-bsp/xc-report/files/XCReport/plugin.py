# -*- coding: utf-8 -*-
"""XC support report: send a diagnostic report (xc-report) to the support repository.

- "Send support report": collects and uploads.
- "Screenshot + support report": meant for a hotkey (Setup > Hotkey). Grabs the screen
  first, so the picture shows the problem, then sends it with the report.
- After an Enigma2 crash, the next start sends the new crash log on its own.
- Problem recording: turns on the Enigma2 debug log and the tuner/DiSEqC driver trace,
  snapshots the settings at the start and at every boot, and on "stop" sends it all
  (with what changed in the settings). It survives reboots and stops by itself after 24 h.
"""
import glob
import os
import subprocess
import threading

import time

from enigma import getDesktop
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config, configfile
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools import Notifications

TOOL = '/usr/bin/xc-report'
CONF = '/etc/xc/report.conf'
SHOT = '/tmp/xc-report-shot.png'
SENT = '/etc/xc/report.crash-sent'	# newest crash log already sent
PREV_DEBUG = '/etc/xc/report-rec/debug-before'	# Enigma2 debug log setting before the recording
LAST = '/etc/xc/report.last'		# "name|time" of the last report sent from this box
HERE = os.path.dirname(__file__)
NICE = ['nice', '-n', '19']		# collecting and uploading never compete with playback
CRASHES = ('/home/root/logs/Enigma2_crash_*.log', '/media/hdd/logs/Enigma2_crash_*.log')
FEED = 'https://raw.githubusercontent.com/3bdlios/xcyber-openatv/main/feeds/openatv-8.0.1/xconn/cortexa55'
PKG = 'xc-report'
busy = threading.Lock()


def configured():
	try:
		conf = dict(l.strip().split('=', 1) for l in open(CONF) if '=' in l and not l.startswith('#'))
		return bool(conf.get('repo') and (conf.get('token') or conf.get('blob')))
	except OSError:
		return False


def popup(text, kind=MessageBox.TYPE_INFO, timeout=8):
	# like Notifications.AddPopup, with our own title (Enigma2's is in the box language)
	Notifications.AddNotification(MessageBox, text=text, type=kind, timeout=timeout, close_on_any_key=True, title=tr('box_title'))


def yes_no():
	"""Title and buttons in the plugin's language, not Enigma2's."""
	return dict(title=tr('box_title'), list=[(tr('yes'), True), (tr('no'), False)])


def send(reason, shot=None, quiet=False):
	"""Collect and upload in a thread; report back with a popup."""
	if not busy.acquire(False):
		if not quiet:
			popup(tr('busy'))
		return

	def work():
		try:
			cmd = NICE + [TOOL, 'upload', '--reason', reason]
			if shot:
				cmd += ['--shot', shot]
			r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
			if r.returncode == 0 and r.stdout.strip():
				name = os.path.basename(r.stdout.strip())
				remember(name)
				if not quiet:
					popup(tr('sent', name), timeout=3)
			elif not quiet:
				popup(tr('failed', (r.stderr.strip().splitlines() or ['?'])[-1]), MessageBox.TYPE_ERROR, 15)
		except Exception as e:
			if not quiet:
				popup(tr('failed', e), MessageBox.TYPE_ERROR, 15)
		finally:
			if shot and os.path.exists(shot):
				os.remove(shot)
			busy.release()
	threading.Thread(target=work, daemon=True).start()


def grab():
	"""Screen as it is now (video + OSD), via OpenWebif's grab (XC capture)."""
	try:
		subprocess.run(['wget', '-qO', SHOT, 'http://127.0.0.1/grab?format=png&mode=all&r=1280'], timeout=20)
		return SHOT if os.path.getsize(SHOT) > 1000 else None
	except (OSError, subprocess.TimeoutExpired):
		return None


def installed_version():
	try:
		out = subprocess.run(['opkg', 'status', PKG], capture_output=True, text=True, timeout=30).stdout
	except (OSError, subprocess.TimeoutExpired):
		return ''
	return next((l.split(':', 1)[1].strip() for l in out.splitlines() if l.startswith('Version:')), '')


def latest_package():
	"""(version, filename) of xc-report in the XC feed, read straight from its index."""
	try:
		out = subprocess.run(NICE + ['sh', '-c', 'wget -qO- "%s/Packages.gz" | gunzip -c' % FEED],
			capture_output=True, text=True, timeout=60).stdout
	except (OSError, subprocess.TimeoutExpired):
		return None
	for block in out.split('\n\n'):
		fields = dict(l.split(': ', 1) for l in block.splitlines() if ': ' in l and not l.startswith(' '))
		if fields.get('Package') == PKG and fields.get('Filename'):
			return fields.get('Version', ''), fields['Filename']
	return None


def newer(latest, current):
	if not current:
		return True
	return subprocess.run(['opkg', 'compare-versions', latest, '>>', current]).returncode == 0


def remember(name):
	try:
		with open(LAST, 'w') as f:
			f.write('%s|%s' % (name, time.strftime('%Y-%m-%d %H:%M')))
	except OSError:
		pass


def last_report():
	try:
		name, when = open(LAST).read().strip().split('|', 1)
		return name, when
	except (OSError, ValueError):
		return None, None


def tool(*args):
	try:
		return subprocess.run(NICE + [TOOL] + list(args), capture_output=True, text=True, timeout=300).stdout.strip()
	except (OSError, subprocess.TimeoutExpired):
		return ''


def recording():
	return os.path.exists('/etc/xc/report-rec/state.json')


def set_debug(on):
	config.crash.enabledebug.value = on
	config.crash.enabledebug.save()
	configfile.save()


def restore_debug():
	try:
		before = open(PREV_DEBUG).read().strip() == 'True'
	except OSError:
		before = False
	set_debug(before)


def stop_recording(quiet=False):
	"""Upload the recording in a thread, then put the debug log setting back."""
	if not busy.acquire(False):
		return

	def work():
		try:
			dest = tool('record', 'stop')
			if dest.startswith('reports/'):
				remember(os.path.basename(dest))
			if not quiet:
				if dest.startswith('reports/'):
					popup(tr('rec_sent', os.path.basename(dest)), timeout=15)
				else:
					popup(tr('rec_failed'), MessageBox.TYPE_ERROR, 15)
		finally:
			busy.release()
	restore_debug()
	threading.Thread(target=work, daemon=True).start()


def box_id():
	"""Same id as in the report names on GitHub (xc-report box_identity)."""
	import hashlib
	import socket
	try:
		mac = open('/sys/class/net/eth0/address').read().strip()
	except OSError:
		mac = socket.gethostname()
	return hashlib.sha1(mac.encode()).hexdigest()[:8]


def recording_since():
	try:
		import json
		return time.strftime('%Y-%m-%d %H:%M', time.localtime(json.load(open('/etc/xc/report-rec/state.json'))['start']))
	except Exception:
		return ''


FHD = getDesktop(0).size().width() >= 1920


def scale(v):
	return v if FHD else v * 2 // 3


def skin():
	w, h = scale(1320), scale(780)
	f = scale
	bw = (w - f(80) - 3 * f(16)) // 4
	keys = ''.join("""
	<eLabel position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="1" />
	<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;%d" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="%s" zPosition="2" />""" % (
		f(40) + i * (bw + f(16)), h - f(96), bw, f(64), color, name, f(40) + i * (bw + f(16)), h - f(96), bw, f(64), f(28), color)
		for i, (name, color) in enumerate((("key_red", "#00a82a2a"), ("key_green", "#00217a3c"), ("key_yellow", "#00a8820e"), ("key_blue", "#001e4f9c"))))
	return """<screen name="XCReportScreen" position="center,center" size="%(w)d,%(h)d" title="XC support report" flags="wfNoBorder" backgroundColor="#1a0d1626">
	<eLabel position="0,0" size="%(w)d,%(hdr)d" backgroundColor="#1a12305a" zPosition="0" />
	<widget name="icon" position="%(m)d,%(im)d" size="%(isz)d,%(isz)d" alphatest="blend" scale="1" zPosition="1" />
	<widget name="headline" position="%(tx)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00ffffff" backgroundColor="#1a12305a" transparent="1" zPosition="1" />
	<widget name="subtitle" position="%(tx)d,%(sy)d" size="%(tw)d,%(sh)d" font="Regular;%(sf)d" foregroundColor="#00a8c8f0" backgroundColor="#1a12305a" transparent="1" zPosition="1" />
	<eLabel position="%(m)d,%(ly)d" size="%(lw)d,2" backgroundColor="#00375a8c" zPosition="1" />
	<widget name="status" position="%(m)d,%(sty)d" size="%(lw)d,%(sth)d" font="Regular;%(bf)d" foregroundColor="#00e6eef8" backgroundColor="#1a0d1626" transparent="1" zPosition="1" />
	<widget name="detail" position="%(m)d,%(dty)d" size="%(lw)d,%(sth)d" font="Regular;%(df)d" foregroundColor="#00a8c8f0" backgroundColor="#1a0d1626" transparent="1" zPosition="1" />
	<widget name="boxid" position="%(m)d,%(dty)d" size="%(lw)d,%(sth)d" font="Regular;%(bf)d" foregroundColor="#00ffd45a" backgroundColor="#1a0d1626" transparent="1" zPosition="1" />
	<widget name="help" position="%(m)d,%(hy)d" size="%(lw)d,%(hh)d" font="Regular;%(hf)d" foregroundColor="#008ea6c4" backgroundColor="#1a0d1626" transparent="1" zPosition="1" />
	<widget name="option" position="%(m)d,%(oy)d" size="%(lw)d,%(oh)d" font="Regular;%(bf)d" foregroundColor="#00ffd45a" backgroundColor="#1a0d1626" transparent="1" zPosition="1" />
	<widget name="key_menu" position="%(mx)d,%(my)d" size="%(mw)d,%(mh)d" font="Regular;%(hf)d" halign="right" foregroundColor="#00a8c8f0" backgroundColor="#1a12305a" transparent="1" zPosition="1" />%(keys)s
</screen>""" % dict(w=w, h=h, hdr=f(200), m=f(40), im=f(20), isz=f(160), tx=f(230), ty=f(36), tw=w - f(270), th=f(64), tf=f(44),
		sy=f(112), sh=f(80), sf=f(28), ly=f(214), lw=w - f(80), sty=f(232), sth=f(80), bf=f(30), dty=f(310), df=f(24), hy=f(396), hh=f(212), hf=f(26), oy=f(616), oh=f(42), keys=keys,
		mx=w - f(300), my=f(150), mw=f(260), mh=f(40))


LANG_FILE = '/etc/xc/report.lang'	# 'ar' or 'en' once switched with MENU; else the box language
TEXT = {
	'headline': ("تقرير الدعم XC", "XC support report"),
	'subtitle': ("يرسل حالة الجهاز وسجلاته للدعم لتشخيص المشكلة", "Sends the state and logs of this receiver to support"),
	'red': ("إغلاق", "Close"),
	'shot_name': ("لقطة الشاشة للدعم", "Screenshot + support report"),
	'shot_desc': ("يصور الشاشة الآن ويرسلها مع تقرير، اربطه بزر", "Capture the screen now and send it with a report (assign to a hotkey)"),
	'green': ("إرسال تقرير الآن", "Send report now"),
	'yellow': ("بدء تسجيل المشكلة", "Start recording"),
	'blue': ("إيقاف التسجيل وإرساله", "Stop and send"),
	'menu': ("MENU: اللغة والتحديث", "MENU: Language, update"),
	'box_title': ("تقارير الدعم", "Support report"),
	'yes': ("نعم", "Yes"),
	'no': ("لا", "No"),
	'menu_title': ("الخيارات", "Options"),
	'update': ("تحديث البلجن", "Update the plugin"),
	'checking': ("جاري البحث عن تحديث للبلجن...", "Checking for a plugin update..."),
	'up_to_date': ("البلجن محدّث، هذا آخر إصدار.", "The plugin is up to date."),
	'check_fail': ("تعذر الاتصال بسيرفر التحديثات. تأكد من الإنترنت.", "Could not reach the update server. Check the internet connection."),
	'update_ask': ("فيه إصدار جديد من بلجن تقارير الدعم. تحدّثه الآن؟", "A new version of the support report plugin is available. Update now?"),
	'updating': ("جاري تحديث البلجن...", "Updating the plugin..."),
	'update_fail': ("فشل تحديث البلجن.", "The plugin update failed."),
	'updated': ("تم تحديث البلجن. لازم إعادة تشغيل الواجهة علشان يشتغل الإصدار الجديد. أعيد تشغيلها الآن؟",
		"The plugin was updated. Restart the GUI now to load the new version?"),
	'last': ("آخر تقرير: %s", "Last report: %s"),
	'none': ("لا يوجد", "none yet"),
	'rec_on': ("تسجيل المشكلة: شغّال منذ %s", "Problem recording: ON since %s"),
	'rec_off': ("تسجيل المشكلة: متوقف", "Problem recording: off"),
	'help': ("أولاً: الزر الأخضر يرسل تقرير عن الجهاز الآن.\n"
		"ثانياً: لمشكلة تحتاج متابعة، اضغط الأصفر ليبدأ التسجيل.\n"
		"ثالثاً: أعد المشكلة: بحث، ضبط الدايزك، إعادة تشغيل الجهاز.\n"
		"رابعاً: ارجع هنا واضغط الأزرق ليتوقف التسجيل ويرسل.\n"
		"الأعطال ترسل تلقائياً، والتسجيل يتوقف وحده بعد يوم كامل.\n"
		"للقطة شاشة وقت المشكلة: من إعدادات الأزرار اربط زراً بخيار لقطة الشاشة المكتوب تحت.",
		"1. Green sends a report about this receiver now.\n"
		"2. For a problem that needs a trace, press yellow to start recording.\n"
		"3. Reproduce it: scan, set up the DiSEqC, reboot the receiver.\n"
		"4. Come back here and press blue to stop and send the recording.\n"
		"Crashes are sent automatically; a recording stops by itself after 24 hours.\n"
		"Screenshot of a problem: in Hotkey setup, assign a key to the screenshot option below."),
	'busy': ("يوجد تقرير قيد الإرسال الآن.", "A support report is already being sent."),
	'sent': ("تم إرسال التقرير.\nرقم التقرير: %s", "Support report sent.\nReport: %s"),
	'failed': ("تعذر إرسال التقرير:\n%s", "The support report could not be sent:\n%s"),
	'rec_sent': ("تم إرسال تسجيل المشكلة.\nرقم التقرير: %s", "Problem recording sent.\nReport: %s"),
	'rec_failed': ("تعذر إرسال تسجيل المشكلة.", "The problem recording could not be sent."),
	'shot_taken': ("تم تصوير الشاشة، جاري إرسال التقرير...", "Screenshot taken. Sending the support report..."),
	'rec_reminder': ("تسجيل المشكلة شغال. افتح تقرير الدعم واضغط الأزرق لإيقافه وإرساله.", "Problem recording is on. Open the XC support report and press blue to stop and send it."),
	'not_conf': ("التقارير غير مفعّلة في هذا الجهاز.", "Support reports are not configured on this receiver."),
	'sending': ("جاري جمع التقرير وإرساله.", "Collecting and sending the report."),
	'no_rec': ("ما فيه تسجيل شغّال. ابدأ التسجيل بالزر الأصفر.", "No problem recording is running. Start one with yellow."),
	'sending_rec': ("جاري إرسال تسجيل المشكلة.", "Sending the problem recording."),
	'already': ("التسجيل شغّال من قبل. أعد المشكلة ثم اضغط الأزرق.", "A recording is already running. Reproduce the problem, then press blue."),
	'start_fail': ("تعذر بدء التسجيل.", "The problem recording could not be started."),
	'started': ("بدأ التسجيل.\nأعد المشكلة الآن (بحث، تغيير إعدادات التيونر، إعادة تشغيل...) ثم ارجع واضغط الأزرق.\n"
		"السجل التفصيلي يبدأ بعد إعادة تشغيل الواجهة. أعيد تشغيلها الآن؟",
		"Recording started.\nNow reproduce the problem (scan, tuner settings, reboot...), then come back and press blue.\n"
		"The detailed log starts after a GUI restart. Restart the GUI now?"),
}


def lang():
	try:
		value = open(LANG_FILE).read().strip()
		if value in ('ar', 'en'):
			return value
	except OSError:
		pass
	return 'ar' if config.osd.language.value.startswith('ar') else 'en'


def tr(key, *args):
	text = TEXT[key][0 if lang() == 'ar' else 1]
	return text % args if args else text


class XCReportScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = skin()
		self["icon"] = Pixmap()
		for name in ("headline", "subtitle", "status", "detail", "boxid", "help", "option", "key_red", "key_green", "key_yellow", "key_blue", "key_menu"):
			self[name] = Label()
		self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "MenuActions"], {
			"red": self.close, "cancel": self.close,
			"green": self.send_now, "ok": self.send_now,
			"yellow": self.start_recording, "blue": self.stop_recording,
			"menu": self.switch_language}, -1)
		self.onLayoutFinish.append(self.layout)

	def layout(self):
		from enigma import ePicLoad
		self.picload = ePicLoad()
		size = self["icon"].instance.size()
		self.picload.setPara((size.width(), size.height(), 1, 1, False, 1, "#00000000"))
		if self.picload.startDecode(os.path.join(HERE, 'xcreport.png'), 0, 0, False) == 0:
			self["icon"].instance.setPixmap(self.picload.getData())
		self.refresh()
		check_update(self.session, auto=True)	# says something only when there is a newer version

	def switch_language(self):
		# The XC remote sends one press as a burst of MENU events; a choice box opened on
		# the first one simply ignores the rest.
		if getattr(self, 'choosing', False):
			return
		self.choosing = True
		from Screens.ChoiceBox import ChoiceBox
		self.session.openWithCallback(self.language_chosen, ChoiceBox, title=tr('menu_title'),
			list=[("العربية", 'ar'), ("English", 'en'), (tr('update'), 'update')], selection=0 if lang() == 'ar' else 1)

	def language_chosen(self, choice):
		self.choosing = False
		if choice and choice[1] == 'update':
			check_update(self.session)
		elif choice:
			try:
				with open(LANG_FILE, 'w') as f:
					f.write(choice[1])
			except OSError:
				pass
			self.refresh()

	def refresh(self):
		for name, key in (("headline", "headline"), ("subtitle", "subtitle"), ("key_red", "red"), ("key_green", "green"),
				("key_yellow", "yellow"), ("key_blue", "blue"), ("key_menu", "menu"), ("help", "help")):
			self[name].setText(tr(key))
		rec = recording()
		self["status"].setText(tr('rec_on', '').rstrip() if rec else tr('rec_off'))
		# Latin text (names, dates, the hotkey option) never shares a label with Arabic:
		# Enigma2's bidi reorders mixed lines
		self["detail"].setText(recording_since() if rec else '')
		self["option"].setText("XC Screenshot Report")
		self["boxid"].setText("ID: " + box_id())
		from enigma import eLabel
		align = eLabel.alignRight if lang() == 'ar' else eLabel.alignLeft
		for name in ("headline", "subtitle", "status", "help", "detail", "option"):
			if self[name].instance:
				self[name].instance.setHAlign(align)
		# the id sits on the recording-time row, on the other side
		if self["boxid"].instance:
			self["boxid"].instance.setHAlign(eLabel.alignLeft if lang() == 'ar' else eLabel.alignRight)

	def check(self):
		if configured():
			return True
		self.session.open(MessageBox, tr('not_conf'), MessageBox.TYPE_ERROR, title=tr('box_title'))
		return False

	def send_now(self):
		if not self.check():
			return
		# the picture should show the TV, not this screen: hide it for the grab
		from enigma import eTimer
		self.hide()
		self.shot_timer = eTimer()
		self.shot_timer.callback.append(self.send_with_shot)
		self.shot_timer.start(600, True)

	def send_with_shot(self):
		# OpenWebif serves the grab from this same main loop: wait for it from a thread,
		# never block here (that froze the GUI with the busy spinner until the timeout)
		self.shot = []
		threading.Thread(target=lambda: self.shot.append(grab()), daemon=True).start()
		self.shot_timer.callback.remove(self.send_with_shot)
		self.shot_timer.callback.append(self.shot_done)
		self.shot_timer.start(200, False)

	def shot_done(self):
		if not self.shot:
			return
		self.shot_timer.stop()
		self.show()
		send('manual', self.shot[0])
		self.session.open(MessageBox, tr('sending'), MessageBox.TYPE_INFO, timeout=6, title=tr('box_title'))

	def stop_recording(self):
		if not self.check():
			return
		if not recording():
			self.session.open(MessageBox, tr('no_rec'), MessageBox.TYPE_INFO, timeout=6, title=tr('box_title'))
			return
		stop_recording()
		self.session.open(MessageBox, tr('sending_rec'), MessageBox.TYPE_INFO, timeout=6, title=tr('box_title'))
		self.refresh()

	def start_recording(self):
		if not self.check():
			return
		if recording():
			self.session.open(MessageBox, tr('already'), MessageBox.TYPE_INFO, timeout=8, title=tr('box_title'))
			return
		if tool('record', 'start') != 'recording':
			self.session.open(MessageBox, tr('start_fail'), MessageBox.TYPE_ERROR, title=tr('box_title'))
			return
		try:
			os.makedirs(os.path.dirname(PREV_DEBUG), exist_ok=True)
			with open(PREV_DEBUG, 'w') as f:
				f.write(str(config.crash.enabledebug.value))
		except OSError:
			pass
		set_debug(True)
		self.refresh()
		self.session.openWithCallback(self.restart, MessageBox, tr('started'), MessageBox.TYPE_YESNO, **yes_no())

	def restart(self, answer):
		if answer:
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 3)


def ask(session, callback, text):
	"""Yes/no from a worker thread, opened on the GUI thread over whatever screen is showing
	(a queued notification would wait until the user is back on the TV picture)."""
	from twisted.internet import reactor
	reactor.callFromThread(lambda: session.openWithCallback(callback, MessageBox, text, MessageBox.TYPE_YESNO, **yes_no()))


def check_update(session, auto=False):
	"""Compare with the XC feed in a thread; ask, install the new ipk, offer a GUI restart.
	auto: the quiet check when the plugin is opened, which only speaks up when there is an update."""
	if not auto:
		popup(tr('checking'), timeout=4)

	def ask_restart(answer):
		if answer:
			from Screens.Standby import TryQuitMainloop
			session.open(TryQuitMainloop, 3)

	def install(answer, filename):
		if not answer:
			return
		popup(tr('updating'), timeout=5)

		def work():
			ipk = '/tmp/xc-report-update.ipk'
			try:
				ok = subprocess.run(NICE + ['wget', '-qO', ipk, '%s/%s' % (FEED, filename)], timeout=120).returncode == 0 \
					and subprocess.run(['opkg', 'install', ipk], capture_output=True, timeout=300).returncode == 0
			except (OSError, subprocess.TimeoutExpired):
				ok = False
			finally:
				if os.path.exists(ipk):
					os.remove(ipk)
			if ok:
				ask(session, ask_restart, tr('updated'))
			else:
				popup(tr('update_fail'), MessageBox.TYPE_ERROR, 10)
		threading.Thread(target=work, daemon=True).start()

	def work():
		latest = latest_package()
		if not latest:
			if not auto:
				popup(tr('check_fail'), MessageBox.TYPE_ERROR, 10)
		elif not newer(latest[0], installed_version()):
			if not auto:
				popup(tr('up_to_date'), timeout=6)
		else:
			ask(session, lambda answer: install(answer, latest[1]), tr('update_ask'))
	threading.Thread(target=work, daemon=True).start()


def report(session, **kwargs):
	session.open(XCReportScreen)


def screenshot_report(session, **kwargs):
	if not configured():
		session.open(MessageBox, tr('not_conf'), MessageBox.TYPE_ERROR, title=tr('box_title'))
		return
	# grab from a thread (OpenWebif answers from this main loop), before anything else is drawn
	def work():
		shot = grab()
		popup(tr('shot_taken'), timeout=5)	# only now, so it is not in the picture
		send('screenshot', shot)
	threading.Thread(target=work, daemon=True).start()


def newest_crash():
	logs = [p for pattern in CRASHES for p in glob.glob(pattern)]
	return max(logs, key=os.path.getmtime) if logs else None


def autostart(reason, session=None, **kwargs):
	"""Problem recording: snapshot at every boot, stop and send when it expired.
	Crash: send the report once for a crash log that has not been sent yet."""
	if reason != 0 or session is None or not configured():
		return
	state = tool('record', 'boot')
	if state == 'expired':
		stop_recording(quiet=True)
	elif state == 'recording':
		popup(tr('rec_reminder'), timeout=10)
	crash = newest_crash()
	if not crash:
		return
	try:
		sent = open(SENT).read().strip()
	except OSError:
		sent = ''
	if os.path.basename(crash) == sent:
		return
	try:
		os.makedirs(os.path.dirname(SENT), exist_ok=True)
		with open(SENT, 'w') as f:
			f.write(os.path.basename(crash))
	except OSError:
		return
	send('crash', quiet=True)


def Plugins(**kwargs):
	return [
		PluginDescriptor(name='XC Support Report', description=tr('subtitle'),
			where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU], icon='plugin.png', fnc=report),
		PluginDescriptor(name='XC Screenshot Report', description=tr('shot_desc'),
			where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=screenshot_report),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=autostart),
	]
