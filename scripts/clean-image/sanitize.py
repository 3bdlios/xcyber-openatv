from pathlib import Path
import tarfile,shutil,json,os,re,hashlib,time
PROJECT = Path(os.environ.get('XC_PROJECT_ROOT', Path(__file__).resolve().parents[2]))
work=Path(os.environ.get('XC_SNAPSHOT_DIR', PROJECT/'snapshot-20261126'));r=work/'root';b=work/'boot'
stock=Path(os.environ.get('XC_STOCK_ROOTFS', PROJECT/'build-environment/builds/openatv/release/xconn/tmp/deploy/images/xconn/openatv-8.0.1-xconn-20261125.tar.gz'))
def remove(rel):
 p=r/rel
 if p.is_symlink() or p.is_file():p.unlink()
 elif p.is_dir():shutil.rmtree(p)
# Exclude all personal state and caches from the distributable root.
for rel in ['etc/enigma2','home/root','etc/dropbear','etc/ssh','var/log','var/cache','var/lib/connman','var/lib/NetworkManager','var/lib/dhcp','var/lib/dhcpcd','etc/NetworkManager/system-connections','etc/connman','etc/tuxbox/config','etc/epgimport','etc/machine-id','var/lib/dbus/machine-id','etc/resolv.conf','etc/issue.net','etc/xc-timeshift-storage','usr/lib/enigma2/python/Plugins/Extensions/AudioShift','usr/lib/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage']:
 remove(rel)
# Existing Image-specific plugin support used by AudioShift is unnecessary in this image.
for p in list(r.rglob('*')):
 if p.is_symlink():continue
 low=str(p.relative_to(r)).lower()
 if 'audioshift' in low or 'xc-timeshift-storage' in low:
  if p.exists():remove(str(p.relative_to(r)))
# Restore factory defaults only from our own clean OE image, never from another installation.
restore_prefixes=('etc/enigma2/','etc/tuxbox/config/','etc/epgimport/','home/root/','etc/ssh/','var/log/','var/cache/')
restore_exact={'etc/network/interfaces','etc/wpa_supplicant.conf','etc/hostname','etc/hosts','etc/passwd','etc/shadow','etc/group','etc/gshadow','etc/resolv.conf','etc/issue.net','var/log','var/cache'}
with tarfile.open(stock) as t:
 for m in t:
  name=m.name.lstrip('./')
  if name in restore_exact or name.startswith(restore_prefixes):
   if name.startswith('etc/ssh/ssh_host') or 'audioshift' in name.lower():continue
   # Archive is OE-generated and contains trusted package paths.
   dest=r/m.name
   if m.isfile() or m.issym() or m.islnk():
    if dest.exists() or dest.is_symlink():dest.unlink()
   t.extract(m,r)
for rel,mode in [('proc',0o555),('sys',0o555),('dev',0o755),('run',0o755),('tmp',0o1777),('boot',0o755),('flash',0o755),('storage',0o755),('media',0o755),('var/volatile',0o755),('home/root',0o700),('etc/dropbear',0o755),('etc/enigma2',0o755)]:
 p=r/rel;p.mkdir(parents=True,exist_ok=True);p.chmod(mode)
# Empty channel database and bouquets; first-run wizard collects tuner details.
e=r/'etc/enigma2'
for p in list(e.iterdir()):
 if not p.name.startswith('emc-') and p.name!='autotimer.xml':
  if p.is_dir():shutil.rmtree(p)
  else:p.unlink()
(e/'settings').write_text('config.misc.firstrun=true\nconfig.misc.languageselected=false\nconfig.misc.videowizardenabled=true\nconfig.timeshift.startDelay=0\nconfig.timeshift.path=/media/hdd/timeshift/\nconfig.usage.default_path=/media/hdd/movie/\n')
(e/'bouquets.tv').write_text('#NAME Bouquets (TV)\n')
(e/'bouquets.radio').write_text('#NAME Bouquets (Radio)\n')
(e/'lamedb').write_text('eDVB services /4/\ntransponders\nend\nservices\nend\n')
p=e/'bouquetmakerxtream';p.mkdir();(p/'playlists.txt').write_text('');(p/'bmx_playlists.json').write_text('[]\n')
# Keep the installed-package database consistent with removal of AudioShift.
status=r/'var/lib/opkg/status'
blocks=status.read_text().strip().split('\n\n'); removed=[];keep=[]
for block in blocks:
 name=block.split('\n',1)[0].removeprefix('Package: ')
 if 'audioshift' in name.lower() or name=='xc-timeshift-storage':removed.append(name)
 else:keep.append(block)
status.write_text('\n\n'.join(keep)+'\n\n')
for rel in ['var/lib/opkg/info','usr/lib/opkg/info']:
 d=r/rel
 if d.exists():
  for p in d.iterdir():
   if any(p.name.startswith(name+'.') for name in removed):p.unlink()
# Drop cached .pyc only when corresponding source exists, preserving source-less plugins.
for p in r.rglob('*.pyc'):
 if p.with_suffix('.py').exists():p.unlink()
for p in (r/'etc').glob('xc-opkg-backup-*'):remove(str(p.relative_to(r)))
# A new device gets its own SSH host identity and no saved user login state.
for p in (r/'etc/ssh').glob('ssh_host*') if (r/'etc/ssh').exists() else []:p.unlink()
for p in (r/'home/root').glob('.*history'):p.unlink()
for rel in ['home/root/.ssh','home/root/.cache','home/root/.local','home/root/.config']:remove(rel)
# fstab reserves /media/hdd for shared STORAGE; never use an Enigma2 root UUID.
(r/'etc/fstab').write_text('/dev/root / ext4 defaults,noatime 0 1\nLABEL=BOOT /boot vfat defaults,noatime 0 0\nLABEL=STORAGE /storage ext4 defaults,noatime 0 2\n/storage /media/hdd none bind 0 0\nproc /proc proc defaults 0 0\ndevpts /dev/pts devpts mode=0620,gid=5 0 0\ntmpfs /var/volatile tmpfs defaults 0 0\nnone /dev/shm tmpfs defaults,rw 0 0\n')
# Early boot creates shared recording directories after STORAGE has mounted.
init=r/'etc/init.d/xc-storage-defaults'
init.write_text('''#!/bin/sh
case "$1" in start|"")
 if grep -qs ' /storage ' /proc/mounts; then
  mkdir -p /storage/movie /storage/timeshift /media/hdd
  grep -qs ' /media/hdd ' /proc/mounts || mount --bind /storage /media/hdd
 fi
 ;; esac
exit 0
''');init.chmod(0o755)
link=r/'etc/rcS.d/S05xc-storage-defaults';link.parent.mkdir(exist_ok=True)
if link.exists() or link.is_symlink():link.unlink()
link.symlink_to('../init.d/xc-storage-defaults')
# First-boot display remains a widely supported mode before the video wizard.
(b/'resolution.ini').write_text('kernel_hdmimode=1080p60hz\n')
xc=b/'xc';xc.mkdir(exist_ok=True)
(xc/'slots.json').write_text(json.dumps({'schema':1,'model':'XCONN-Forever-X-CYBER','mode':'dynamic-v2','storage_partition':3,'selected':1,'slots':[{'id':1,'partition':2,'label':'Enigma2_1','status':'ready','image_name':'OpenATV XC','version':'8.0.1 clean snapshot'}]},indent=2)+'\n')
(xc/'selected.env').write_text('xc_slot=1\n')
# Do not distribute a shared recovery bearer token. Generate a per-device token at first boot.
# The recovery runtime handles this token; inspect its startup implementation before final packaging.
if (xc/'recovery-token').exists():(xc/'recovery-token').unlink()
report={'removed_packages':removed,'personal_enigma2_state':'reset to clean OE defaults','iptv_playlists':0,'tuner_configuration':'unset; first-run wizard enabled','timeshift_autostart':False,'root_source':'live OpenATV receiver; excluding personal-state directories','audio_shift_present':False,'device_tested_after_packaging':False}
(work/'sanitization-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
