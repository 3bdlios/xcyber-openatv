from pathlib import Path
import os,subprocess,struct,hashlib,json,gzip,shutil,tarfile,io,importlib.util,time
PROJECT = Path(os.environ.get('XC_PROJECT_ROOT', Path(__file__).resolve().parents[2]))
W=Path(os.environ.get('XC_SNAPSHOT_DIR', PROJECT/'snapshot-20261126'));R=W/'root';B=W/'boot';O=PROJECT/'release';O.mkdir(exist_ok=True)
os.environ['PATH']='/usr/sbin:/sbin:'+os.environ['PATH']
M=1024**2;G=1024**3;OFFSET=4*M;BOOTSIZE=G;ROOTSIZE=4*G;STORESIZE=256*M
NAME='OpenATV-8.0.1-X-CYBER-CLEAN-NoAudioShift-20261126'
def run(*args,**kw):
 print('+',' '.join(map(str,args)),flush=True);return subprocess.run(list(map(str,args)),check=True,**kw)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*M),b''):h.update(b)
 return h.hexdigest()
# The boot/runtime is captured from the receiver's currently working XC chain.
runtime=B/'xc/recovery-runtime-4g-d08c6c6f22e4.tar.gz'
assert hashlib.md5(runtime.read_bytes()).hexdigest()=='7d968bd6eb4ab7298643d9c9698036de'
with tarfile.open(runtime) as t:
 source=t.extractfile('xc/slots.py').read();p=W/'runtime-slots.py';p.write_bytes(source)
 spec=importlib.util.spec_from_file_location('xc_runtime_slots',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.validate(json.loads((B/'xc/slots.json').read_text()))
 assert t.getmember('xc/manager.py').isfile() and t.getmember('xc/recovery.py').isfile()
assert sha(B/'kernel.img')==sha((PROJECT/'build-environment/builds/openatv/release/xconn/tmp/deploy/images/xconn/kernel.img'))
rootimg=W/'clean-root.ext4';rootimg.unlink(missing_ok=True);run('truncate','-s',ROOTSIZE,rootimg)
run('mkfs.ext4','-q','-F','-m','0','-O','^orphan_file,^metadata_csum_seed','-L','Enigma2_1','-d',R,rootimg)
run('e2fsck','-f','-p',rootimg)
# Check preserved root ownership and critical file modes in the generated filesystem.
for path in ['/usr/bin/enigma2','/etc/shadow','/etc/enigma2/settings','/etc/init.d/xc-storage-defaults']:
 v=run('debugfs','-R','stat '+path,rootimg,capture_output=True,text=True).stdout
 assert 'Inode:' in v and 'User:     0' in v,(path,v)
 if path=='/etc/shadow':assert '0400' in v or '0600' in v,v
for absent in ['/usr/lib/enigma2/python/Plugins/Extensions/AudioShift','/usr/lib/enigma2/python/Plugins/SystemPlugins/XCTimeshiftStorage','/etc/enigma2/audioshift']:
 v=run('debugfs','-R','stat '+absent,rootimg,capture_output=True,text=True)
 assert 'Inode:' not in v.stdout,absent
v=run('debugfs','-R','cat /etc/enigma2/settings',rootimg,capture_output=True,text=True).stdout
assert 'config.misc.firstrun=true' in v and 'config.Nims.' not in v
v=run('debugfs','-R','cat /etc/enigma2/bouquetmakerxtream/bmx_playlists.json',rootimg,capture_output=True,text=True).stdout
assert json.loads(v)==[]
bootimg=W/'clean-boot.fat';bootimg.unlink(missing_ok=True);run('truncate','-s',BOOTSIZE,bootimg);run('mkfs.vfat','-F','32','-n','BOOT',bootimg,stdout=subprocess.DEVNULL)
for p in sorted(B.iterdir()):run('mcopy','-s','-i',bootimg,p,'::')
sroot=W/'empty-storage';sroot.mkdir(exist_ok=True)
for name in ['movie','timeshift','picon']:(sroot/name).mkdir(exist_ok=True)
storeimg=W/'clean-storage.ext4';storeimg.unlink(missing_ok=True);run('truncate','-s',STORESIZE,storeimg);run('mkfs.ext4','-q','-F','-m','0','-O','^orphan_file,^metadata_csum_seed','-L','STORAGE','-d',sroot,storeimg)
raw=O/(NAME+'.img');raw.unlink(missing_ok=True);total=OFFSET+BOOTSIZE+ROOTSIZE+STORESIZE+4*M;run('truncate','-s',total,raw)
table='label: gpt\nunit: sectors\n\n'
parts=[(OFFSET,BOOTSIZE,'EBD0A0A2-B9E5-4433-87C0-68B6B72699C7','BOOT'),(OFFSET+BOOTSIZE,ROOTSIZE,'0FC63DAF-8483-4772-8E79-3D69D8477DE4','Enigma2_1'),(OFFSET+BOOTSIZE+ROOTSIZE,STORESIZE,'0FC63DAF-8483-4772-8E79-3D69D8477DE4','STORAGE')]
for start,size,kind,label in parts:table+=f'start={start//512}, size={size//512}, type={kind}, name="{label}"\n'
run('sfdisk',raw,input=table,text=True,stdout=subprocess.DEVNULL)
# XC U-Boot uses FAT in MBR entry 1; GPT continues describing the full layout.
with raw.open('r+b') as f:
 mbr=bytearray(f.read(512));mbr[446:510]=b'\0'*64
 mbr[446:462]=struct.pack('<B3sB3sII',0,b'\xfe\xff\xff',0x0c,b'\xfe\xff\xff',OFFSET//512,BOOTSIZE//512)
 mbr[462:478]=struct.pack('<B3sB3sII',0,b'\x00\x02\x00',0xee,b'\xfe\xff\xff',1,OFFSET//512-1)
 mbr[510:512]=b'\x55\xaa';f.seek(0);f.write(mbr)
# Insert only allocated extents so the raw disk image remains sparse.
with raw.open('r+b') as dst:
 for src,offset in [(bootimg,OFFSET),(rootimg,OFFSET+BOOTSIZE),(storeimg,OFFSET+BOOTSIZE+ROOTSIZE)]:
  with src.open('rb') as f:
   pos=0;size=src.stat().st_size
   while pos<size:
    try:start=os.lseek(f.fileno(),pos,os.SEEK_DATA)
    except OSError as e:
     if e.errno==6:break
     raise
    end=min(os.lseek(f.fileno(),start,os.SEEK_HOLE),size);f.seek(start);dst.seek(offset+start)
    left=end-start
    while left:
     block=f.read(min(left,4*M));assert block;dst.write(block);left-=len(block)
    pos=end
run('sgdisk','-v',raw)
# Verify each filesystem's bytes in the composed IMG against its source.
with raw.open('rb') as disk:
 for src,offset in [(bootimg,OFFSET),(rootimg,OFFSET+BOOTSIZE),(storeimg,OFFSET+BOOTSIZE+ROOTSIZE)]:
  disk.seek(offset);h=hashlib.sha256();left=src.stat().st_size
  while left:block=disk.read(min(left,4*M));assert block;h.update(block);left-=len(block)
  assert h.hexdigest()==sha(src),src
rawsha=sha(raw);gz=O/(NAME+'.img.gz')
with raw.open('rb') as f,gz.open('wb') as out:
 with gzip.GzipFile(filename='',fileobj=out,mode='wb',compresslevel=6,mtime=0) as z:shutil.copyfileobj(f,z,4*M)
h=hashlib.sha256();count=0
with gzip.open(gz,'rb') as z:
 for block in iter(lambda:z.read(4*M),b''):h.update(block);count+=len(block)
assert count==total and h.hexdigest()==rawsha
report={'file':gz.name,'raw_file':raw.name,'raw_bytes':total,'compressed_bytes':gz.stat().st_size,'sha256':sha(gz),'raw_sha256':rawsha,'includes_recovery':True,'kernel_version':'5.15.196','kernel_sha256':sha(B/'kernel.img'),'boot_files_sha256':{str(p.relative_to(B)):sha(p) for p in B.rglob('*') if p.is_file()},'rootfs_sha256':sha(rootimg),'source':'snapshot of running OpenATV with locally applied fixes and installed plugins; personal state removed offline','first_run_wizard':True,'iptv_subscriptions':0,'tuner_settings':'factory unset','channel_database':'empty','AudioShift':'removed, including installed-package metadata and all settings','github_update_test':'0.1 -> 0.2 received and installed from GitHub','minimum_media':'8 GB USB/SD','image_hardware_boot_tested':False,'original_receiver_settings_modified':False,'sanitization':json.loads((W/'sanitization-report.json').read_text())}
(O/(NAME+'-report.json')).write_text(json.dumps(report,indent=2)+'\n');(O/(NAME+'.img.gz.sha256')).write_text(report['sha256']+'  '+gz.name+'\n')
print(json.dumps(report,indent=2),flush=True)
