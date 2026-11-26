from pathlib import Path
import shutil,json,hashlib,re,os
PROJECT = Path(os.environ.get('XC_PROJECT_ROOT', Path(__file__).resolve().parents[2]))
w=Path(os.environ.get('XC_SNAPSHOT_DIR', PROJECT/'snapshot-20261126'));r=w/'root'
for rel in ['etc/enigma2/autotimer.xml','var/lib/opkg/status-old','var/lib/opkg/status.bak']:
 p=r/rel
 if p.exists():p.unlink()
for name in ['CCcam.cfg','oscam.server']:
 p=r/'etc/tuxbox/config'/name
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# No subscription accounts included.\n');p.chmod(0o600)
p=r/'var/local'
if p.exists():
 if p.is_symlink():p.unlink()
 else:shutil.rmtree(p)
p.mkdir(parents=True,exist_ok=True)
p=r/'usr/lib/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage'
if p.exists():shutil.rmtree(p)
for pattern in ['etc/udhcpc.last.*','etc/network/*.bak','etc/fstab.before-*','etc/udev/rules.d/70-persistent-net.rules']:
 for old in r.glob(pattern):
  if old.is_file() or old.is_symlink():old.unlink()
for rel in ['var/lib/urandom/random-seed','var/lib/nfs/rmtab','var/lib/nfs/etab']:
 old=r/rel
 if old.exists():old.unlink()
# Assert installed plugins and post-build fixes are retained.
required=['usr/lib/enigma2/python/Plugins/Extensions/AddRemote/plugin.py','usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/plugin.py','usr/lib/enigma2/python/Plugins/Extensions/XCUpdateTest/plugin.py','usr/lib/enigma2/python/Plugins/SystemPlugins/XCScreenshot/plugin.py','usr/lib/enigma2/python/Plugins/SystemPlugins/XCSlots/plugin.py','usr/lib/enigma2/python/Components/AVSwitch.py','usr/lib/enigma2/python/Screens/WizardStart.py','usr/lib/python3.14/multiprocessing/pool.pyc','lib/modules/5.15.196/modules.dep','usr/bin/enigma2']
for rel in required:assert (r/rel).is_file(),rel
bad=[str(p.relative_to(r)) for p in r.rglob('*') if 'audioshift' in str(p).lower() or 'xc-timeshift-storage' in str(p).lower() or 'xctimeshiftstorage' in str(p).lower()]
assert not bad,bad
assert 'Package: enigma2-plugin-extensions-audioshift\n' not in (r/'var/lib/opkg/status').read_text()
settings=(r/'etc/enigma2/settings').read_text();assert 'config.Nims.' not in settings and 'config.misc.firstrun=true' in settings
assert (r/'etc/enigma2/bouquetmakerxtream/playlists.txt').stat().st_size==0
assert json.loads((r/'etc/enigma2/bouquetmakerxtream/bmx_playlists.json').read_text())==[]
assert 'UUID=' not in (r/'etc/fstab').read_text()
# Personal-data exclusions are checked before generating any distributable image.
for rel in ['etc/dropbear','home/root/.ssh']:
 p=r/rel
 assert not p.exists() or not list(p.iterdir()),rel
print('Clean-root checks passed; required plugins, kernel modules, and fixes retained.')
(w/'retained-files.json').write_text(json.dumps({rel:hashlib.sha256((r/rel).read_bytes()).hexdigest() for rel in required},indent=2)+'\n')
