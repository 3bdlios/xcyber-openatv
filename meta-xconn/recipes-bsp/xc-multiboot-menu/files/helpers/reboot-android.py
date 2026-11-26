#!/usr/bin/env python3
"""XCEnigma Android restart v1.1: verified environment one-shot, no boot UI changes."""
import argparse, importlib.util, os, subprocess, sys
from pathlib import Path
TOOL=Path('/usr/lib/xcenigma/android-env-once.py')
def module():
    local=Path(__file__).parent/'android-env-once.py'
    p=local if local.exists() else TOOL
    s=importlib.util.spec_from_file_location('android_env',str(p));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    m.verify_host()
    return m

def cancel(m):
    print(m.cancel())
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group()
    for mode in ('check','arm','android','cancel'):g.add_argument('--'+mode,action='store_true')
    args=p.parse_args();m=module()
    if args.cancel:cancel(m);return
    raw=m.read_env();m.plan(raw)
    if not (args.arm or args.android):print('COMPATIBLE_VERIFIED_BOOT_PROFILE; CHECK_ONLY');return
    subprocess.run(['/usr/bin/python3',str(TOOL),'--arm','--expect-sha256',m.sha(raw)],check=True)
    if args.android:
        subprocess.run(['/etc/init.d/avahi-daemon','stop'],check=True)
        subprocess.run(['/sbin/reboot'],check=True)
if __name__=='__main__':
    try:main()
    except Exception as e:print('STOP:',e,file=sys.stderr);sys.exit(1)
