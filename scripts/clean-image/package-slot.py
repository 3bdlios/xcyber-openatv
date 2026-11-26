from pathlib import Path
import hashlib,json,gzip,tarfile,io,struct
import os
root=Path(os.environ.get('XC_PROJECT_ROOT', Path(__file__).resolve().parents[2]));w=root/'snapshot-20261126';out=root/'release';fs=Path(os.environ.get('XC_SLOT_ROOTFS', w/'clean-slot.ext4'));boot=w/'boot'
name='OpenATV-8.0.1-X-CYBER-SLOT-CLEAN-NoAudioShift-20261126-r2.tar.gz'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
with fs.open('rb') as f:f.seek(1024);sb=f.read(1024)
assert sb[56:58]==b'\x53\xef'
assert struct.unpack_from('<I',sb,4)[0]*(1024<<struct.unpack_from('<I',sb,24)[0])==fs.stat().st_size
manifest={'format':'XCEnigma-slot-v2','model':'XCONN-Forever-X-CYBER','image_name':'OpenATV','version':'8.0.1 Clean r2 NoAudioShift','architecture':'aarch64','base_kernel_sha256':sha(boot/'kernel.img'),'base_dtb_sha256':sha(boot/'dtb.img'),'filesystem':'ext4','expand_to_slot':True,'hardware_boot_tested':False,'files':{'rootfs.img':{'size':fs.stat().st_size,'sha256':sha(fs)}}}
p=out/name
with p.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|',format=tarfile.GNU_FORMAT) as t:
 data=(json.dumps(manifest,indent=2)+'\n').encode();m=tarfile.TarInfo('manifest.json');m.mode=0o644;m.size=len(data);t.addfile(m,io.BytesIO(data))
 m=tarfile.TarInfo('rootfs.img');m.mode=0o644;m.size=fs.stat().st_size
 with fs.open('rb') as f:t.addfile(m,f)
with tarfile.open(p,'r:gz') as t:
 assert t.getnames()==['manifest.json','rootfs.img']
 assert json.load(t.extractfile('manifest.json'))==manifest
 h=hashlib.sha256()
 with t.extractfile('rootfs.img') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 assert h.hexdigest()==manifest['files']['rootfs.img']['sha256']
report={'package':str(p),'format':'XCEnigma-slot-v2','compressed_bytes':p.stat().st_size,'compressed_MiB':round(p.stat().st_size/1024**2,2),'rootfs_bytes':fs.stat().st_size,'sha256':sha(p),'contents':['manifest.json','rootfs.img'],'includes_boot':False,'includes_recovery':False,'requires_existing_matching_XC_recovery':True,'AudioShift_removed':True,'IPTV_subscriptions_removed':True,'channels_and_tuner_reset':True,'first_run_wizard':True,'hardware_install_tested':False,'password_pam_fix':'xc-password-pam-fix 1.0-r0; isolated password-change test passed'}
(out/(name+'.sha256')).write_text(report['sha256']+'  '+name+'\n');(out/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
(out/'OpenATV-8.0.1-X-CYBER-SLOT-CLEAN-README-ar.txt').write_text('حزمة سلوت للملتي بوت XC وليست صورة قرص كامل.\nثبت ملف tar.gz كما هو من خيار تثبيت صورة في ركفري الملتي بوت، واختر السلوت المطلوب. لا تفك ضغطه ولا تحرقه ببرنامج صور الأقراص.\nمتوافقة مع نواة XC 5.15.196 والركفري الحالي المطابق. يوسع المثبت النظام ويعدل تسمية القسم تلقائياً للسلوت المختار.\nتشمل الإصلاحات والبلجنات المثبتة حديثاً، مع إصلاح تغيير كلمة المرور PAM في الإصدار r2. AudioShift ومساعده واشتراكاته محذوفة، وIPTV بلا اشتراك والقنوات والتيونر بلا إعدادات شخصية. يبدأ معالج الإعداد الأول.\nفحوص الحزمة وEXT4 والبصمات نجحت؛ لم تثبت هذه الحزمة فعلياً على جهاز.\n')
(root/'clean-slot-status.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
