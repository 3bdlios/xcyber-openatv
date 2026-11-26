#!/usr/bin/env python3
from pathlib import Path
import json,os,time,datetime
root=Path(__file__).resolve().parent
log=root/'build.log'; status=root/'build-status.json'
try:
 data=log.read_text(errors='replace') if log.exists() else ''
 marker=data.rfind('BUILD TARGET:')
 print(data[marker:] if marker>=0 else data[-4000:],end='',flush=True)
 with log.open(errors='replace') as stream:
  stream.seek(0,2); last=time.monotonic()
  while True:
   chunk=stream.read()
   if chunk:
    print(chunk,end='',flush=True);last=time.monotonic()
   state=json.loads(status.read_text())
   if state.get('status') in ('failed','built-awaiting-device-test'):
    chunk=stream.read()
    if chunk: print(chunk,end='',flush=True)
    print('\n'+('توقف البناء بخطأ؛ أرسل آخر السطور.' if state['status']=='failed' else 'اكتمل البناء؛ الصورة تحتاج اختباراً على الجهاز.'),flush=True)
    break
   try: os.kill(int(state['pid']),0)
   except (ProcessLookupError,KeyError):
    print('\nعملية البناء غير موجودة؛ أرسل هذه النتيجة للفحص.',flush=True);break
   if time.monotonic()-last>=15:
    started=datetime.datetime.fromisoformat(state['started'])
    seconds=int((datetime.datetime.now(datetime.timezone.utc)-started).total_seconds())
    print(f'\n[العملية تعمل | المدة {seconds//60:02d}:{seconds%60:02d} | انتظار أسطر جديدة]',flush=True)
    last=time.monotonic()
   time.sleep(1)
except KeyboardInterrupt:
 print('\nأُغلقت المتابعة فقط؛ لم يُوقف البناء.')
