from pathlib import Path
import subprocess,json,time,os
root=Path(__file__).resolve().parent
status=root/'build-status.json'
def update(**values):
 data=json.loads(status.read_text()) if status.exists() else {}
 
 if values.get('status') == 'building':
  data.pop('exit_code',None); data.pop('finished',None)
 data.update(values); status.write_text(json.dumps(data,indent=2)+'\n')
update(status='building',log=str(root/'build.log'),pid=os.getpid(),started=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
with (root/'build.log').open('a',buffering=1) as log:
 for targets in [['oea-image'],['package-index']]:
  log.write('\nBUILD TARGET: '+' '.join(targets)+'\n')
  process=subprocess.Popen([str(root/'build-image.sh'),*targets],cwd=root,stdout=log,stderr=subprocess.STDOUT)
  update(target=' '.join(targets),worker_pid=process.pid)
  result=process.wait()
  if result:
   update(status='failed',exit_code=result,finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
   raise SystemExit(result)
update(status='built-awaiting-device-test',finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
