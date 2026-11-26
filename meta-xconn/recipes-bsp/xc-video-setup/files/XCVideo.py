"""XC (Amlogic DRM) video output helpers for Enigma2's Video Setup.

The XC kernel has no /proc/stb/video: the DRM driver owns the output mode and refuses
live changes from /sys/class/display/mode. A resolution change is applied live with one
atomic DRM modeset (xc-display-fix; the 1080p OSD is scaled to the new mode), confirmed
by the user or reverted after 15 s, and saved to resolution.ini (kernel_hdmimode=...),
which the boot scripts on the BOOT partition read to start the kernel in that mode. When
the live modeset fails the change is applied by a restart, as before. HDR output is the HDMI transmitter's
hdr_priority (0 = TV capabilities, 1 = no Dolby Vision, 2 = SDR only) and applies live.
"""
import os
from Components.config import config, ConfigSelection, ConfigSubsection

DRM_MODES = "/sys/class/drm/card0-HDMI-A-1/modes"
DRM_STATUS = "/sys/class/drm/card0-HDMI-A-1/status"
DISP_CAP = "/sys/class/amhdmitx/amhdmitx0/disp_cap"
DISPLAY_FIX = "/usr/sbin/xc-display-fix"
DISPLAY_MODE = "/sys/class/display/mode"
RESOLUTION_INI = "/boot/resolution.ini"
HDR_PRIORITY = "/sys/class/amhdmitx/amhdmitx0/hdr_priority_mode"
HDR_CAP = "/sys/class/amhdmitx/amhdmitx0/hdr_cap"
BOOT_DEFAULT = "1080p60hz"   # cfgload_env default when resolution.ini is absent

ORDER = [
	("2160p60hz", "2160p 60Hz (4K)"), ("2160p50hz", "2160p 50Hz (4K)"), ("2160p30hz", "2160p 30Hz (4K)"),
	("2160p25hz", "2160p 25Hz (4K)"), ("2160p24hz", "2160p 24Hz (4K)"),
	("1080p60hz", "1080p 60Hz"), ("1080p50hz", "1080p 50Hz"), ("1080p30hz", "1080p 30Hz"),
	("1080p25hz", "1080p 25Hz"), ("1080p24hz", "1080p 24Hz"),
	("1080i60hz", "1080i 60Hz"), ("1080i50hz", "1080i 50Hz"),
	("720p60hz", "720p 60Hz"), ("720p50hz", "720p 50Hz"),
	("576p50hz", "576p 50Hz"), ("480p60hz", "480p 60Hz"),
]
HDR_CHOICES = [
	("0", _("Auto (HDR10 / HLG when the TV supports it)")),
	("1", _("Auto without Dolby Vision")),
	("2", _("Off (SDR only)")),
]


def _read(path, default=""):
	try:
		with open(path) as f:
			return f.read()
	except OSError:
		return default


def available():
	return os.path.exists(DRM_MODES) and os.path.exists(DISPLAY_MODE) and not os.path.exists("/proc/stb/video/videomode")


def tv_modes():
	"""The TV's modes. DRM can probe the connector before the EDID is ready and keep only
	"dummy_l" until the next hotplug, so ask it to probe again, then add the HDMI TX's list."""
	present = set(_read(DRM_MODES).split())
	if not any(m in present for m, _l in ORDER):
		try:
			with open(DRM_STATUS, "w") as f:
				f.write("detect")
		except OSError as error:
			print("[XCVideo] drm detect:", error)
		present = set(_read(DRM_MODES).split())
	present |= set(_read(DISP_CAP).split())
	return [(m, label) for m, label in ORDER if m in present]


def saved_mode():
	for line in _read(RESOLUTION_INI).splitlines():
		key, _sep, value = line.partition("=")
		if key.strip() == "kernel_hdmimode" and value.strip():
			return value.strip().strip("'\"")
	return BOOT_DEFAULT


def current_mode():
	return _read(DISPLAY_MODE).strip() or BOOT_DEFAULT


def tv_hdr():
	cap = _read(HDR_CAP)
	return {"hdr10": "SMPTE ST 2084: 1" in cap, "hlg": "Hybrid Log-Gamma: 1" in cap}


config.av.xc_hdr = ConfigSelection(default="0", choices=HDR_CHOICES)


def apply_hdr(element=None):
	value = (element or config.av.xc_hdr).value
	try:
		with open(HDR_PRIORITY, "w") as f:
			f.write(value)
	except OSError as error:
		print("[XCVideo] hdr_priority:", error)


def resolution_element():
	"""A fresh selection each time the screen opens: the truth is resolution.ini."""
	modes = tv_modes()
	saved = saved_mode()
	if saved not in [m for m, _l in modes]:
		label = dict(ORDER).get(saved, saved)
		modes.insert(0, (saved, label + " " + _("(not reported by this TV)")))
	if not modes:
		modes = [(BOOT_DEFAULT, dict(ORDER)[BOOT_DEFAULT])]
	return ConfigSelection(default=saved, choices=modes)


def entries(resolution):
	hdr = tv_hdr()
	if hdr["hdr10"] or hdr["hlg"]:
		hdr_info = _("This TV reports: %s.") % ", ".join(n for n, ok in (("HDR10", hdr["hdr10"]), ("HLG", hdr["hlg"])) if ok)
	else:
		hdr_info = _("This TV reports no HDR support, so the output stays SDR.")
	from Components.config import getConfigListEntry
	return [
		getConfigListEntry(_("Resolution"), resolution,
			_("Output resolution, from the modes your TV reports. Current output: %s. A change is applied at once and kept when you confirm it.") % current_mode()),
		getConfigListEntry(_("HDR output"), config.av.xc_hdr,
			_("HDR10 and HLG are sent only when both the programme and the TV support them.") + " " + hdr_info),
	]


def write_resolution(mode):
	try:
		with open(RESOLUTION_INI + ".tmp", "w") as f:
			f.write("kernel_hdmimode=%s\n" % mode)
			f.flush()
			os.fsync(f.fileno())
		os.rename(RESOLUTION_INI + ".tmp", RESOLUTION_INI)
		os.sync()
		return True
	except OSError as error:
		print("[XCVideo] resolution.ini:", error)
		return False


def set_mode_live(mode):
	"""One atomic DRM modeset to mode (OSD plane scaled to it); True when the output is mode."""
	try:
		import importlib.machinery
		import importlib.util
		loader = importlib.machinery.SourceFileLoader("xc_display_fix", DISPLAY_FIX)
		fix = importlib.util.module_from_spec(importlib.util.spec_from_loader("xc_display_fix", loader))
		loader.exec_module(fix)
		fix.wanted_mode = lambda: mode
		result = fix.fix(force=True)
		# The modeset unblank can reset plane scaling; repair it after the driver settles.
		if result and result.startswith("modeset "):
			from time import sleep
			sleep(0.1)
			fix.fix()
		print("[XCVideo] live mode:", result)
		return bool(result) and result.startswith("modeset " + mode + ":")
	except Exception as error:
		print("[XCVideo] live mode %s: %s" % (mode, error))
		return False


_confirm = []


def _ask_keep(mode, previous, previous_saved):
	from Screens.InfoBar import InfoBar
	from Screens.MessageBox import MessageBox

	def answer(keep):
		if not keep:
			set_mode_live(previous)
			write_resolution(previous_saved)
	if InfoBar.instance is None:
		return
	InfoBar.instance.session.openWithCallback(answer, MessageBox,
		_("Is the picture shown correctly at %s?\nThe previous resolution returns in 15 seconds.") % dict(ORDER).get(mode, mode),
		MessageBox.TYPE_YESNO, timeout=15, default=False, timeout_default=False)


def save_resolution(resolution):
	"""Save resolution.ini and switch the output live; True when a restart is still needed."""
	mode, previous, previous_saved = resolution.value, current_mode(), saved_mode()
	if mode == previous_saved and mode == previous:
		return False
	if not write_resolution(mode):
		return False
	if mode == previous:
		return False
	if not set_mode_live(mode):
		return mode != current_mode()
	# Ask once the setup screen has closed, from the screen below it.
	from enigma import eTimer
	timer = eTimer()
	timer.callback.append(lambda: (_confirm.remove(timer), _ask_keep(mode, previous, previous_saved)))
	_confirm.append(timer)
	timer.start(500, True)
	return False
