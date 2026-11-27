# -*- coding: utf-8 -*-
"""Video enhancement on XC (Amlogic) receivers.

Enigma2's Video Enhancement plugin drives the Broadcom picture engine (/proc/stb/vmpeg/0/pep_*) and
hides itself where that is missing, as on these boxes. The Amlogic picture engine (amvecm) has the
same basic controls for the video layer; this plugin puts them in the same place (Setup > AV). Every
value stands at 0 = the receiver's own setting and goes up or down from there, shown as a number.
The menus (OSD) are never changed.
"""
import os
import subprocess
from os.path import exists

from enigma import eTimer, iPlayableService
from Components.ActionMap import HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigSelectionNumber, ConfigSelection
from Plugins.Plugin import PluginDescriptor
from Screens.Setup import Setup

VECM = '/sys/class/amvecm/'
SR0_GAIN = 0x3e22		# SRSHARP0_PK_FINALGAIN_HP_BP on G12A/SM1: high pass << 8 | band pass
SR0_GAIN_DEFAULT = 0x14		# the driver's own gain for both
SR0_GAIN_MAX = 0x80


def write(name, value):
	try:
		with open(VECM + name, 'w') as f:
			f.write(value)
	except OSError as e:
		print('[XCVideoEnhancement] %s: %s' % (name, e))


def number(low, high, step):
	return ConfigSelectionNumber(min=low, max=high, stepwidth=step, default=0, wraparound=False)


def val(item):
	# a value saved by an older version (e.g. "off") counts as 0
	try:
		return int(item.value)
	except (TypeError, ValueError):
		return 0


config.plugins.XCVideoEnhancement = ConfigSubsection()
cfg = config.plugins.XCVideoEnhancement
cfg.contrast = number(-100, 100, 5)
cfg.saturation = number(-100, 100, 5)
cfg.hue = number(-25, 25, 1)
cfg.brightness = number(-100, 100, 5)
cfg.sharpness = number(-100, 100, 5)
cfg.colorspace = ConfigSelection(default='auto', choices=[('auto', _('auto')), ('rgb', 'RGB'), ('444', 'YCbCr 4:4:4')])
# an older version saved words here ("off", "on", "default"), which a number list reads as its first
# entry (-100 = sharpness off): start such values at 0
for _item in (cfg.contrast, cfg.saturation, cfg.hue, cfg.brightness, cfg.sharpness):
	try:
		int(_item.saved_value) if _item.saved_value is not None else 0
	except ValueError:
		_item.value = _item.default
		_item.save()


# amvecm ranges: brightness -1024..1024, contrast -1024..1023 (video layer 1), saturation -128..128 and
# hue -25..25 ("sat hue"); +-100 uses up to +-400 of the first two
def set_brightness(*args):
	write('brightness', '%d' % (val(cfg.brightness) * 4))


def set_contrast(*args):
	write('contrast', '%d' % (val(cfg.contrast) * 4))


def set_saturation_hue(*args):
	write('saturation_hue_pre', '%d %d' % (val(cfg.saturation) * 128 // 100, val(cfg.hue)))


def set_sharpness(*args):
	# scaler peaking: -100 off, 0 the driver's gain, +100 a strong gain
	v = val(cfg.sharpness)
	if v <= -100:
		write('pq_user_set', 'sr0_pk_dis')
		return
	if v < 0:
		gain = SR0_GAIN_DEFAULT * (100 + v) // 100
	else:
		gain = SR0_GAIN_DEFAULT + (SR0_GAIN_MAX - SR0_GAIN_DEFAULT) * v // 100
	write('pq_user_set', 'sr0_pk_en')
	write('pq_reg_rw', 'w %x %x' % (SR0_GAIN, gain << 8 | gain))


COLOR_CHOICE = '/etc/xc/colorspace'	# read by xc-display-fix at every modeset


def set_colorspace(*args):
	want = '' if cfg.colorspace.value == 'auto' else cfg.colorspace.value
	try:
		with open(COLOR_CHOICE) as f:
			if f.read().strip() == want:
				return
	except OSError:
		if not want:
			return
	try:
		os.makedirs(os.path.dirname(COLOR_CHOICE), exist_ok=True)
		with open(COLOR_CHOICE, 'w') as f:
			f.write(want + '\n')
		subprocess.Popen(['/usr/sbin/xc-display-fix', '--force'], close_fds=True)
	except OSError as e:
		print('[XCVideoEnhancement] colour space: %s' % e)


colorspace_timer = eTimer()		# a modeset per choice would blink the screen while scrolling
colorspace_timer.callback.append(set_colorspace)
cfg.colorspace.addNotifier(lambda item: colorspace_timer.start(1500, True), initial_call=False, immediate_feedback=True)

SETTERS = [(cfg.contrast, set_contrast), (cfg.saturation, set_saturation_hue), (cfg.hue, set_saturation_hue),
	(cfg.brightness, set_brightness), (cfg.sharpness, set_sharpness)]
for item, fn in SETTERS:
	item.addNotifier(fn, initial_call=False, immediate_feedback=True)


def apply_all():
	for item, fn in SETTERS:
		try:
			fn()
		except Exception as e:
			print('[XCVideoEnhancement] %s: %r' % (fn.__name__, e))
	print('[XCVideoEnhancement] applied: contrast %s saturation %s hue %s brightness %s sharpness %s' % tuple(
		repr(i.value) for i in (cfg.contrast, cfg.saturation, cfg.hue, cfg.brightness, cfg.sharpness)))


class XCVideoEnhancementSetup(Setup):
	"""Laid out like Enigma2's own Video enhancement setup: red Cancel, green OK, yellow Last config, blue Default."""
	def __init__(self, session):
		Setup.__init__(self, session, 'xcvideoenhancement', plugin='SystemPlugins/XCVideoEnhancement')
		self['key_yellow'] = StaticText(_('Last config'))
		self['key_blue'] = StaticText(_('Default'))
		self['xcColourActions'] = HelpableActionMap(self, ['ColorActions'], {
			'yellow': (self.last_config, _('Back to the values saved last')),
			'blue': (self.defaults, _('Set all values to their defaults')),
		}, prio=-2)
		if 'key_green' in self:
			self['key_green'].setText(_('OK'))

	def ve_items(self):
		return [item for item, fn in SETTERS] + [cfg.colorspace]

	def last_config(self):
		for item in self.ve_items():
			item.cancel()
		self.createSetup()

	def defaults(self):
		for item in self.ve_items():
			item.value = item.default
		self.createSetup()


class Reapply:
	"""The scaler settings can be reset when a new video starts: apply them again shortly after."""
	def __init__(self, session):
		self.timer = eTimer()
		self.timer.callback.append(set_sharpness)
		session.nav.event.append(self.event)

	def event(self, ev):
		if ev in (iPlayableService.evStart, iPlayableService.evVideoSizeChanged):
			self.timer.start(800, True)


reapply = None


def main(session, **kwargs):
	session.open(XCVideoEnhancementSetup)


def startSetup(menuid):
	if menuid != 'video_menu':
		return []
	return [(_('Video enhancement setup'), main, 'videoenhancement_setup', 5)]


def sessionstart(reason, session=None, **kwargs):
	global reapply
	if reason == 0:
		apply_all()
		if session and reapply is None:
			reapply = Reapply(session)


def Plugins(**kwargs):
	if exists('/proc/stb/vmpeg/0/pep_apply') or not exists(VECM + 'brightness'):
		return []
	return [
		PluginDescriptor(name=_('Video enhancement'), description=_('Picture contrast, colour, brightness and sharpness'),
			where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, needsRestart=False, fnc=sessionstart),
	]
