#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only inspection of a dedicated finishing-build mount and its consumers."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mount')
args = parser.parse_args()
root = Path(args.mount).resolve(strict=True)
assert re.fullmatch(r'/var/tmp/dagric-finishing-build-mount\.[A-Za-z0-9]+', str(root))
assert root.is_mount() and root.stat().st_uid == os.getuid() == 0
mounts = json.loads(subprocess.check_output(['findmnt', '--json', '-R', str(root)], text=True))
consumers = []
for process in Path('/proc').iterdir():
    if not process.name.isdigit() or int(process.name) == os.getpid(): continue
    links = [process / 'root', process / 'cwd']
    try: links.extend((process / 'fd').iterdir())
    except (FileNotFoundError, PermissionError, ProcessLookupError): pass
    for link in links:
        try: target = str(link.readlink())
        except (OSError, PermissionError): continue
        if target == str(root) or target.startswith(str(root) + '/'):
            consumers.append({'pid': int(process.name), 'reference': str(link), 'target': target})
messages = subprocess.check_output(['dmesg', '--level', 'err,warn'], text=True)
relevant = [line for line in messages.splitlines()
    if any(term in line for term in ('page allocation failure', 'device loop0', 'dev loop0', 'EXT4-fs error', 'Buffer I/O error on device loop0'))]
report = {'mount': str(root), 'mount_tree': mounts, 'consumers': consumers,
          'kernel_storage_warnings': relevant[-30:], 'inspection_only': True}
output = Path(__file__).resolve().parents[1] / 'out/finishing-storage-inspection.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print('Report: ' + str(output))
