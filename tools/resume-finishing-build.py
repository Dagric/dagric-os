#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resume one known finishing-build workspace without cleaning or recopying it.

Requires an exact source revision and verifies the staged includes against that
clean checkout. Uses the normal native finalization code from that same revision.
This does not authorize resuming arbitrary directories or publishing an image.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid


def checked_run(run, revision):
    requested = Path(run)
    run = requested.resolve(strict=True)
    if requested != run or not re.fullmatch(r'/var/tmp/dagric-finishing-build-mount\.[A-Za-z0-9]+/(free|pro)\.[A-Za-z0-9]+', str(run)):
        raise ValueError('Expected one dedicated finishing-build run, not an arbitrary directory.')
    if os.geteuid() != 0 or not run.parent.is_mount():
        raise ValueError('Expected the mounted private root-owned build filesystem.')
    for path in (run.parent, run, run / 'source', run / 'build'):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unsafe build directory ownership or permissions: ' + str(path))
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('An exact source revision is required.')
    source, build = run / 'source', run / 'build'
    edition = run.name.split('.')[0]
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision or (source / 'out/SOURCE_COMMIT').read_text().strip() != revision:
        raise ValueError('Source identity does not match the original build.')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('Source checkout is dirty.')
    inc = source / 'config/includes.chroot'
    omissions = set()
    if edition == 'free':
        for folder in ('looks', 'styles'):
            for item in (inc / 'usr/share/dagric' / folder).iterdir():
                if item.is_file() and 'EDITION=pro' in item.read_text().splitlines():
                    omissions.add(item.relative_to(inc))
                    omissions.add(Path('usr/share/dagric/appearance/thumbs') / (item.stem + '.png'))
    for item in inc.rglob('*'):
        relative = item.relative_to(inc)
        target = build / 'config/includes.chroot' / relative
        if relative in omissions:
            if target.exists(): raise ValueError('Unexpected Pro asset in Free staging.')
        elif relative == Path('etc/dagric-edition'):
            if target.read_text().strip() != edition: raise ValueError('Edition mismatch.')
        elif item.is_symlink():
            if not target.is_symlink() or item.readlink() != target.readlink(): raise ValueError('Staged link differs: ' + str(relative))
        elif item.is_file():
            if not target.is_file() or target.is_symlink(): raise ValueError('Staged file missing: ' + str(relative))
            with item.open('rb') as first, target.open('rb') as second:
                if hashlib.file_digest(first, 'sha256').digest() != hashlib.file_digest(second, 'sha256').digest():
                    raise ValueError('Staged source differs: ' + str(relative))
    native = (source / 'build.sh').read_text()
    if native.count('\nlb build\n') != 1:
        raise ValueError('Native finalization boundary changed; inspect before resuming.')
    return source, build, edition, native.split('\nlb build\n', 1)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run'); parser.add_argument('source_revision')
    args = parser.parse_args()
    source, build, edition, finalize = checked_run(args.run, args.source_revision)
    spec = importlib.util.spec_from_file_location('build_guard', source / 'tools/build-guard.py')
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    descriptor = guard.acquire()
    guard.preflight(build, edition)
    guard.validate_source(source)
    env = {**os.environ, 'SRC': str(source), 'BUILD': str(build), 'EDITION': edition,
           'SOURCE_COMMIT': args.source_revision, 'DAGRIC_BUILD_LOCK_FD': str(descriptor),
           'WGETRC': str(source / 'tools/build-wgetrc')}
    log = Path(args.run) / ('resume-' + uuid.uuid4().hex[:12] + '.log')
    print('Resuming validated source ' + args.source_revision + '\nResume log: ' + str(log), flush=True)
    command = 'python3 "$SRC/tools/build-guard.py" --verify "$DAGRIC_BUILD_LOCK_FD"\nlb build\n' + finalize
    with log.open('x') as output:
        process = subprocess.Popen(['bash', '-euo', 'pipefail', '-s'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=build, env=env, pass_fds=(descriptor,))
        process.stdin.write(command); process.stdin.close()
        for line in process.stdout:
            output.write(line); output.flush(); print(line, end='', flush=True)
        code = process.wait()
    os.close(descriptor)
    return code


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error: sys.exit('resume-build: ' + str(error))
