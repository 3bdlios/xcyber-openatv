#!/usr/bin/python3
"""Runlevel 0 only: hand the front panel and IR receiver to BL30 like Android does.

1. Panel: ask xc-fpd (which owns the FD650 GPIO lines) to blank the digits and light
   only the red standby LED (FD650 DIG2 bit 0x80, confirmed on hardware 2026-11-04).
2. IR: swap upstream meson-ir for the vendor meson-remote driver. Its probe sends
   ir_wakeup_key (incl. XCONN/GT Combo power, present in the XC dtb) to BL30 over
   mbox and programs the hardware NEC decoder that BL30 polls while the SoC is off.
Every step is best-effort; poweroff must never be blocked.
"""
import json, os, subprocess, sys, time
from pathlib import Path

MODDIR = Path('/usr/lib/xc/ir-wake')
LOGS = (Path('/boot/xc/last-poweroff-handoff.json'), Path('/tmp/last-poweroff-handoff.json'))
out = {'time': time.time()}


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return {'cmd': ' '.join(cmd), 'rc': r.returncode, 'out': (r.stdout + r.stderr).strip()[-400:]}


def panel_off():
    # Through the daemon when it runs, directly on the FD650 otherwise.
    return [run('/usr/sbin/xc-fpd', 'standby')]


def ir_handoff():
    steps = []
    if Path('/sys/module/meson_ir').exists():
        steps.append(run('rmmod', 'meson_ir'))
    if not Path('/sys/module/amlogic_gkitool').exists():
        steps.append(run('insmod', str(MODDIR / 'amlogic-gkitool.ko')))
    if not Path('/sys/module/meson_remote').exists():
        steps.append(run('insmod', str(MODDIR / 'meson-remote.ko')))
    bound = Path('/sys/bus/platform/devices/ff808040.meson-remote/driver').exists()
    if not bound and Path('/sys/bus/platform/drivers/bl30_manager/bl30_manager').exists():
        # The shared BL30 mailbox channel may be held; release it and retry the bind.
        Path('/sys/bus/platform/drivers/bl30_manager/unbind').write_text('bl30_manager')
        Path('/sys/bus/platform/drivers/meson-remote/bind').write_text('ff808040.meson-remote')
        bound = Path('/sys/bus/platform/devices/ff808040.meson-remote/driver').exists()
        steps.append({'bl30_manager_unbound_retry': bound})
    dmesg = subprocess.run(['dmesg'], capture_output=True, text=True).stdout.splitlines()
    return {'steps': steps, 'bound': bound,
            'dmesg': [l for l in dmesg if 'meson-remote' in l or 'mbox' in l.lower()][-15:]}


only = sys.argv[1] if len(sys.argv) > 1 else None
for name, fn in (('panel', panel_off), ('ir', ir_handoff)):
    if only and only != name:
        continue
    try:
        out[name] = fn() or 'ok'
    except Exception as e:
        out[name] = 'error: %r' % (e,)

for log in LOGS:
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps(out, indent=1))
        os.sync()
        break
    except OSError:
        continue
print(json.dumps(out))
