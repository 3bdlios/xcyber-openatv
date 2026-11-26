#!/usr/bin/env python3
"""Normalize only the current OpenATV slot's display name; never select a slot."""
from pathlib import Path
import json,os,re,tempfile

def atomic(path,data):
    fd,temp=tempfile.mkstemp(prefix='.xc-name-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def main():
    info=dict(line.split('=',1) for line in Path('/etc/image-version').read_text().splitlines() if '=' in line)
    if info.get('distro')!='openatv':return
    version=info.get('imageversion',info.get('version',''))
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*',version):raise ValueError('Invalid OpenATV version')
    match=re.search(r'(?:^|\s)xc.slot=([0-9]+)(?:\s|$)',Path('/proc/cmdline').read_text())
    if not match:return
    slotid=int(match.group(1))
    folder=next((p/'xc' for p in (Path('/boot'),Path('/flash')) if os.path.ismount(p) and (p/'xc/slots.json').is_file()),None)
    if folder is None:return
    state=json.loads((folder/'slots.json').read_text())
    if state.get('model')!='XCONN-Forever-X-CYBER':raise ValueError('Wrong model')
    slot=next((s for s in state.get('slots',[]) if s.get('id')==slotid),None)
    if slot is None or slot.get('status')!='ready' or 'openatv' not in slot.get('image_name','').lower():return
    if slot.get('image_name')=='OpenATV' and slot.get('version')==version:return
    before=json.loads(json.dumps(state));selected=(folder/'selected.env').read_bytes()
    slot['image_name']='OpenATV';slot['version']=version
    assert state.get('selected')==before.get('selected')
    assert [s for s in state['slots'] if s['id']!=slotid]==[s for s in before['slots'] if s['id']!=slotid]
    data=json.dumps(state,indent=2)+'\n'
    backup=folder/'slots.json.before-openatv-name'
    if not backup.exists():atomic(backup,json.dumps(before,indent=2)+'\n')
    atomic(folder/'slots.json.bak',data);atomic(folder/'slots.json',data)
    assert (folder/'selected.env').read_bytes()==selected
    print('OpenATV slot name: OpenATV '+version)
if __name__=='__main__':main()
