"""Bridge standard softcam services to OpenATV without changing their config."""
from pathlib import Path
import os
import re
import shlex

MARKER = '# XC managed softcam bridge v1'

def _syncCams(root='/'):
    root = Path(root)
    init = root / 'etc/init.d'
    cams = root / 'usr/camscript'
    cams.mkdir(parents=True, exist_ok=True)
    native = list(cams.glob('Ncam_*.sh'))
    wanted = set()
    for service in sorted(init.glob('softcam.*')):
        name = service.name[len('softcam.'):]
        if name.lower() in ('none', 'ci') or not re.fullmatch(r'[A-Za-z0-9_.+-]+', name):
            continue
        if not service.is_file() or not os.access(service, os.X_OK):
            continue
        target = '/etc/init.d/' + service.name
        # Respect package-provided and existing native integrations.
        if any(MARKER not in p.read_text(errors='replace') and
               target in p.read_text(errors='replace') for p in native):
            continue
        out = cams / ('Ncam_XC_' + name + '.sh')
        wanted.add(out)
        if out.exists() and MARKER not in out.read_text(errors='replace'):
            continue
        text = ('#!/bin/sh\n' + MARKER + '\nCAMNAME="' + name + '"\n'
                'case "$1" in\n start|stop|restart) exec ' + shlex.quote(target) +
                ' "$1" ;;\n *) exit 1 ;;\nesac\n')
        if not out.exists() or out.read_text() != text:
            tmp = out.with_suffix('.sh.new')
            tmp.write_text(text)
            tmp.chmod(0o755)
            tmp.replace(out)
    for p in cams.glob('Ncam_XC_*.sh'):
        if p not in wanted and MARKER in p.read_text(errors='replace'):
            p.unlink()

def syncCams(root="/"):
    try:
        _syncCams(root)
    except OSError as error:
        print("[XC CAM] Discovery deferred:", error)
