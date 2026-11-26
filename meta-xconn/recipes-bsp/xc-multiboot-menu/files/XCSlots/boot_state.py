#!/usr/bin/env python3
"""Offline XCEnigma layout and boot-selection metadata. Never accesses devices."""
import argparse
import json
import os
from pathlib import Path
import tempfile

GIB = 1024 ** 3
MIB = 1024 ** 2
MODEL = 'XCONN-Forever-X-CYBER'


def layout(slots=1):
    if not 1 <= slots <= 8:
        raise ValueError('slot count must be between 1 and 8')
    # GPT is needed when BOOT + roots + STORAGE exceeds four partitions.
    # U-Boot GPT support must be checked on the receiver before deployment.
    return {
        'schema': 1, 'model': MODEL, 'partition_table': 'gpt',
        'hardware_verified': False,
        'distribution': {'format': 'compressed raw IMG',
                         'storage_initial_bytes': 256 * MIB,
                         'slot_policy': 'create six-GiB slots on demand in recovery'},
        'partitions': [
            {'number': 1, 'label': 'BOOT', 'filesystem': 'vfat', 'size_bytes': GIB},
            {'number': 2, 'slot': 1, 'label': 'Enigma2_1', 'filesystem': 'ext4', 'size_bytes': 6 * GIB},
            {'number': 3, 'label': 'STORAGE', 'filesystem': 'ext4', 'size_bytes': 'remaining',
             'minimum_bytes': 256 * MIB, 'directories': ['movie', 'timeshift', 'picon']},
            *[{'number': i + 2, 'slot': i, 'label': f'Enigma2_{i}',
               'filesystem': 'ext4', 'size_bytes': 6 * GIB} for i in range(2, slots + 1)],
        ],
        'minimum_disk_bytes': (1 + 6 * slots) * GIB + 256 * MIB + 8 * MIB,
    }


def initial_state(slots=1):
    layout(slots)
    return {'schema': 1, 'model': MODEL, 'mode': 'dynamic-v2', 'storage_partition': 3, 'selected': 'recovery', 'slots': [
        {'id': i, 'partition': 2 if i == 1 else i + 2, 'label': f'Enigma2_{i}', 'status': 'empty',
         'image_name': '', 'version': ''} for i in range(1, slots + 1)]}


def validate(state):
    if state.get('schema') != 1 or state.get('model') != MODEL:
        raise ValueError('unsupported state schema or model')
    slots = state.get('slots', [])
    layout(len(slots))
    for i, slot in enumerate(slots, 1):
        if slot.get('id') != i or slot.get('label') != f'Enigma2_{i}':
            raise ValueError('slot IDs and partition labels must be stable')
        if slot.get('status') not in ('empty', 'installing', 'ready', 'failed'):
            raise ValueError('invalid slot status')
        for key in ('image_name', 'version'):
            text = slot.get(key)
            if not isinstance(text, str) or len(text) > 80 or any(ord(c) < 32 for c in text):
                raise ValueError('invalid display text')
        if slot['status'] == 'ready' and not slot['image_name'].strip():
            raise ValueError('ready slot needs an image name')
    if state.get('mode') == 'dynamic-v2':
        if state.get('storage_partition') != 3:
            raise ValueError('invalid STORAGE partition')
        if any(s.get('partition') != (2 if s['id'] == 1 else s['id'] + 2) for s in slots):
            raise ValueError('invalid dynamic slot partition mapping')
    selected = state.get('selected')
    if selected != 'recovery':
        if type(selected) is not int or not 1 <= selected <= len(slots):
            raise ValueError('invalid selection')
        if slots[selected - 1]['status'] != 'ready':
            raise ValueError('selected slot is not ready')
    return state


def display_name(slot):
    if slot['status'] == 'empty':
        return f"Empty Slot {slot['id']}"
    name = ' '.join(x for x in (slot['image_name'], slot['version']) if x)
    return f"{name or slot['status']} (Slot {slot['id']})"


def atomic_write(path, data):
    path = Path(path)
    # Restrict this desktop utility to ordinary local directories, not /dev.
    if str(path.resolve()).startswith('/dev/'):
        raise ValueError('device paths are forbidden')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.xc-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_state(folder):
    folder=Path(folder)
    errors=[]
    for name in ('slots.json','slots.json.bak'):
        try:
            value=validate(json.loads((folder/name).read_text()))
            if name.endswith('.bak'):
                atomic_write(folder/'slots.json',json.dumps(value,indent=2)+'\n')
            return value
        except (OSError,ValueError,KeyError,TypeError) as error:
            errors.append(name+': '+str(error))
    raise ValueError('No valid slot configuration: '+'; '.join(errors))

def save_state(folder,state):
    folder=Path(folder)
    data=json.dumps(validate(state),indent=2)+'\n'
    atomic_write(folder/'slots.json.bak',data)
    atomic_write(folder/'slots.json',data)
    atomic_write(folder/'selected.env','xc_slot='+str(state['selected'])+'\n')
    os.sync()


def select(state, target):
    state = json.loads(json.dumps(validate(state)))
    state['selected'] = 'recovery' if target == 'recovery' else int(target)
    return validate(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan'); p.add_argument('--slots', type=int, default=1)
    p = sub.add_parser('init'); p.add_argument('state', type=Path); p.add_argument('--slots', type=int, default=1)
    p = sub.add_parser('list'); p.add_argument('state', type=Path)
    p = sub.add_parser('select'); p.add_argument('state', type=Path); p.add_argument('target')
    args = parser.parse_args()
    if args.command == 'plan':
        print(json.dumps(layout(args.slots), indent=2))
    elif args.command == 'init':
        if args.state.exists():
            raise ValueError('state already exists')
        atomic_write(args.state, json.dumps(initial_state(args.slots), indent=2) + '\n')
    else:
        state = validate(json.loads(args.state.read_text()))
        if args.command == 'list':
            for slot in state['slots']:
                print(display_name(slot))
        else:
            atomic_write(args.state, json.dumps(select(state, args.target), indent=2) + '\n')


if __name__ == '__main__':
    main()
