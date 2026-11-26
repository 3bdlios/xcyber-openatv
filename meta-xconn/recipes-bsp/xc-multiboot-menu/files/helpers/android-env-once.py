#!/usr/bin/env python3
"""Verified one-shot boot flag. Default --check is read-only. Never reboots."""
import argparse, hashlib, json, os, re, stat, struct, tempfile, zlib
from pathlib import Path
SIZE=65536
BOOT_SHA='b6f01df81e74a83a52179b7cfdbaf5466833dae47c5b9a8202d9d66861ead36c'
BOOTCMD=b'if test ${bootfromnand} = 1; then setenv bootfromnand 0; saveenv; else run bootfromsd; run bootfromusb; run bootfromemmc; fi; run storeboot'

PROFILE_COMMANDS={b'storeboot': 'cd7998f3d24bf739916bf51a6598458c54cffb8ab3162063f2dbcf10d121b2a6', b'storeargs': '771a246cf40ed563a0d86600da381435a919bbe131cabb93617ff01cd8041b26', b'bootfromsd': 'bd0026c3dec0c8c346c1b6c6e05d2f5c82fcdfcbd85adab09e3607dbf335b127', b'bootfromusb': 'f6794667642283bdb9184ca72d71e00bbc8f5cfbc6ac680164ac3b2427affc0d', b'bootfromemmc': '076357eb4c5e0c13a14447032cfee704f1208899371acdd10181194f73edb146'}

def sha(b): return hashlib.sha256(b).hexdigest()

def parse(raw):
    if len(raw)!=SIZE or struct.unpack('<I',raw[:4])[0] != zlib.crc32(raw[4:])&0xffffffff:
        raise RuntimeError('Invalid 64KiB environment CRC')
    end=raw.find(b'\0\0',4)
    if end<0: raise RuntimeError('No environment terminator')
    result={}
    for entry in raw[4:end].split(b'\0'):
        if b'=' not in entry: raise RuntimeError('Invalid environment record')
        key,value=entry.split(b'=',1)
        if key in result: raise RuntimeError('Duplicate environment key')
        result[key]=value
    return result

def plan(raw):
    env=parse(raw)
    if env.get(b'bootcmd')!=BOOTCMD: raise RuntimeError('Boot command changed; stop for review')
    if env.get(b'bootfromnand')!=b'0': raise RuntimeError('One-shot flag is already set or unknown')
    needle=b'\0bootfromnand=0\0'
    if raw.count(needle)!=1: raise RuntimeError('Ambiguous flag location')
    patched=bytearray(raw)
    offset=raw.index(needle)+len(b'\0bootfromnand=')
    patched[offset]=ord('1')
    patched[:4]=struct.pack('<I',zlib.crc32(patched[4:])&0xffffffff)
    after=bytes(patched); expected=dict(env); expected[b'bootfromnand']=b'1'
    if parse(after)!=expected: raise RuntimeError('Unexpected variable change')
    if any(raw[i]!=after[i] for i in range(4,SIZE) if i!=offset): raise RuntimeError('Unexpected byte change')
    return after,offset

def verify_host():
    model=Path('/proc/device-tree/model').read_bytes().rstrip(b'\0\r\n ')
    expected_boot_sha={b'GTMedia GT Combo':BOOT_SHA,b'XCONN':'9788581f8fba433a68daf425db45f887b9c88f3190aa585f0ad1acbbb84a7e3d'}.get(model)
    if expected_boot_sha is None: raise RuntimeError('Unexpected hardware')
    if Path('/proc/device-tree/coreelec-dt-id').read_bytes().rstrip(b'\0\r\n ')!=b'sm1_s905x3_gtcombo':raise RuntimeError('Unexpected DT identity')
    if model==b'XCONN':
        if Path('/proc/device-tree/coreelec-dt-id').read_bytes().rstrip(b'\0\r\n ')!=b'sm1_s905x3_gtcombo': raise RuntimeError('Unexpected XCONN DT identity')
        if parse(read_env()).get(b'aml_dt')!=b'sm1_ac213_4g': raise RuntimeError('Unexpected XCONN Android identity')
    for name in ('/dev/bootloader','/dev/env'):
        # Identify the eMMC partition by name, not by minor number: with an SD
        # card inserted the card can enumerate first and shift eMMC minors.
        s=os.stat(name)
        if not stat.S_ISBLK(s.st_mode) or os.major(s.st_rdev)!=179:
            raise RuntimeError('Unexpected block device mapping: '+name)
        node=Path('/sys/dev/block/%d:%d'%(os.major(s.st_rdev),os.minor(s.st_rdev))).resolve()
        uevent=dict(l.split('=',1) for l in (node/'uevent').read_text().splitlines() if '=' in l)
        try:disk_type=(node.parent/'device'/'type').read_text().strip()
        except OSError:disk_type=''
        if uevent.get('PARTNAME')!=name[5:] or disk_type!='MMC':
            raise RuntimeError('Unexpected block device mapping: '+name)
    with open('/dev/bootloader','rb',buffering=0) as f:
        observed_boot_sha=sha(f.read(4194304))
        allowed={expected_boot_sha}
        if model==b'GTMedia GT Combo':allowed.add('c20d2a095ec2a4c2b11cc59825849835b81788ceb50012145258b48cf070ed41')
        if observed_boot_sha not in allowed:
            # Other firmware builds of the same receiver ship a different
            # bootloader binary. Accept them only when the U-Boot routing that
            # the one-byte flag relies on is exactly the audited profile.
            env=parse(read_env())
            routing=(b'storeboot',b'bootfromsd',b'bootfromusb',b'bootfromemmc')
            if any(sha(env.get(key,b''))!=PROFILE_COMMANDS[key] for key in routing):
                raise RuntimeError('Unsupported bootloader; no changes')
    if observed_boot_sha=='c20d2a095ec2a4c2b11cc59825849835b81788ceb50012145258b48cf070ed41':
        env=parse(read_env())
        if env.get(b'aml_dt')!=b'sm1_ac213_2g':raise RuntimeError('Unexpected Android DT identity')
        for key,expected in PROFILE_COMMANDS.items():
            if sha(env.get(key,b''))!=expected:raise RuntimeError('Unexpected boot command: '+key.decode())
    return verify_boot_mount()

def verify_boot_mount():
    """Match BOOT and the running slot by kernel device IDs, never path text."""
    def unescape(value):
        return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), value)

    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        try:
            sep = fields.index('-')
            mounts.append((fields[2], unescape(fields[4]), fields[sep + 1]))
        except (ValueError, IndexError):
            raise RuntimeError('Invalid kernel mount information')
    roots = [m for m in mounts if m[1] == '/']
    if not roots:
        raise RuntimeError('Cannot identify the running root filesystem')
    root = roots[-1]
    recovery = root[2] in ('tmpfs', 'rootfs', 'ramfs')
    root_node = None
    root_partition = None
    if not recovery:
        root_node = Path('/sys/dev/block/' + root[0]).resolve(strict=True)
        try:
            root_partition = int((root_node / 'partition').read_text())
        except (OSError, ValueError):
            raise RuntimeError('Running root is not an identifiable slot partition: ' + root[0])

    candidates = {}
    rejected = []
    for dev, mountpoint, filesystem in mounts:
        if filesystem != 'vfat':
            continue
        folder = Path(mountpoint) / 'xc'
        try:
            node = Path('/sys/dev/block/' + dev).resolve(strict=True)
            if int((node / 'partition').read_text()) != 1:
                continue
            # An SD card may enumerate before eMMC. The immutable kernel node,
            # rather than mmcblk numbering, identifies the parent disk.
            if not re.fullmatch(r'sd[a-z]+|mmcblk[0-9]+', node.parent.name):
                continue
            if node.parent.name.startswith('mmcblk'):
                if (node.parent / 'device/type').read_text().strip() != 'SD':
                    continue
            if not recovery and node.parent != root_node.parent:
                continue
            state = json.loads((folder / 'slots.json').read_text())
            if state.get('model') != 'XCONN-Forever-X-CYBER' or state.get('mode') != 'dynamic-v2':
                rejected.append(mountpoint + ': incompatible slot metadata')
                continue
            if not (folder / 'bridge-enabled').is_file():
                rejected.append(mountpoint + ': missing bridge marker')
                continue
            parts = set()
            for slot in state['slots']:
                value = slot.get('partition')
                if isinstance(value, bool) or not str(value).isdigit() or int(value) < 2:
                    raise ValueError('invalid slot partition')
                parts.add(int(value))
            if not parts or (not recovery and root_partition not in parts):
                rejected.append(mountpoint + ': running partition absent from slot metadata')
                continue
            # /boot and /flash can be aliases of the same partition. Count the
            # block device once and prefer the standard image mountpoint.
            if dev not in candidates or mountpoint == '/boot':
                candidates[dev] = folder
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            if mountpoint in ('/boot', '/flash'):
                rejected.append(mountpoint + ': unreadable BOOT identity or slot metadata')
    if len(candidates) != 1:
        detail = '; '.join(rejected) or 'no matching mounted FAT BOOT on the running slot disk'
        raise RuntimeError('Cannot identify a unique verified BOOT: root=%s candidates=%d; %s'
                           % (root[0], len(candidates), detail))
    return next(iter(candidates.values()))

def check():
    folder=verify_host();raw=read_env();plan(raw)
    return folder,raw

def arm(expected):
    folder,before=check()
    if os.geteuid()!=0 or sha(before)!=expected:raise RuntimeError('Root and matching environment checksum required')
    after,offset=plan(before)
    backup=Path(tempfile.mkdtemp(prefix='android-env-',dir=folder))
    for name,data in [('env-before.bin',before),('env-armed.bin',after)]:
        with (backup/name).open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
        if (backup/name).read_bytes()!=data:raise RuntimeError('Backup verification failed')
    with (backup/'metadata.json').open('x') as out:
        json.dump({'original_sha256':sha(before),'armed_sha256':sha(after),'changed_flag_offset':offset},out);out.flush();os.fsync(out.fileno())
    os.sync()
    fd=os.open('/dev/env',os.O_RDWR|os.O_SYNC)
    try:
        if os.pread(fd,SIZE,0)!=before:raise RuntimeError('Environment changed; refusing write')
        try:
            write_exact(fd,after)
            if os.pread(fd,SIZE,0)!=after:raise RuntimeError('Environment readback failed')
        except Exception:
            write_exact(fd,before)
            if os.pread(fd,SIZE,0)!=before:raise RuntimeError('Restore failed; do not reboot')
            raise
    finally:os.close(fd)
    return str(backup)

def cancel():
    folder=verify_host();raw=read_env()
    if parse(raw).get(b'bootfromnand')==b'0':return 'NOT_ARMED'
    for backup in sorted(folder.glob('android-env-*'),reverse=True):
        try:
            before=(backup/'env-before.bin').read_bytes();after=(backup/'env-armed.bin').read_bytes()
            if raw!=after or plan(before)[0]!=raw:continue
        except (OSError,RuntimeError):continue
        fd=os.open('/dev/env',os.O_RDWR|os.O_SYNC)
        try:
            if os.pread(fd,SIZE,0)!=raw:raise RuntimeError('Environment changed; refusing cancel')
            write_exact(fd,before)
            if os.pread(fd,SIZE,0)!=before:raise RuntimeError('Cancel readback failed; do not reboot')
        finally:os.close(fd)
        return 'REQUEST_CANCELLED'
    raise RuntimeError('No matching verified backup; refusing environment write')

def read_env():
    with open('/dev/env','rb',buffering=0) as f: return f.read(SIZE)

def write_exact(fd,data):
    off=0
    while off<len(data):
        n=os.pwrite(fd,data[off:],off)
        if n<=0: raise RuntimeError('Short device write')
        off+=n
    os.fsync(fd)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--arm',action='store_true',help='Writes internal environment after verified backup')
    ap.add_argument('--expect-sha256',help='Exact original environment hash from the read-only check')
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    if args.arm and args.check: raise RuntimeError('Select check or arm')
    folder,before=check()
    if not args.arm:
        print('COMPATIBLE_VERIFIED_BOOT_PROFILE; CHECK_ONLY');return
    print('ARMED AND READBACK VERIFIED; backup:',arm(args.expect_sha256))

if __name__=='__main__':
    try: main()
    except Exception as e: print('STOP:',e); raise SystemExit(1)
