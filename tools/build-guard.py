#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Serialize native builds, check real backing storage, and validate before copy."""
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

GIB = 1024**3
MIN_GIB = {'free': 25, 'pro': 40}
LOCK_DIR = Path('/run/lock/dagric-build')
LOCK = LOCK_DIR / 'native.lock'


def powershell_json(script):
    encoded = base64.b64encode(script.encode('utf-16le')).decode()
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            check=True, capture_output=True, text=True, timeout=20)
    return json.loads(result.stdout.strip())


def existing_parent(path):
    path = Path(path).absolute()
    while not path.exists():
        if path == path.parent:
            raise ValueError('Cannot determine build filesystem.')
        path = path.parent
    return path.resolve()


def backing_drive(path):
    """Follow a loop filesystem to its file; otherwise inspect WSL registration."""
    path = existing_parent(path)
    info = subprocess.run(['findmnt', '-J', '-T', str(path), '-o', 'SOURCE,TARGET'],
                          check=True, capture_output=True, text=True)
    mount = json.loads(info.stdout)['filesystems'][0]
    if str(mount['source']).startswith('/dev/loop'):
        backing = subprocess.run(['losetup', '--noheadings', '--output', 'BACK-FILE', mount['source']],
                                 check=True, capture_output=True, text=True).stdout.strip()
        return backing_drive(backing)
    match = re.match(r'^/mnt/([a-z])(?:/|$)', str(path), re.I)
    if match:
        return match.group(1).upper()
    distro = os.environ.get('WSL_DISTRO_NAME')
    if not distro:
        return None
    if not re.fullmatch(r'[A-Za-z0-9_. -]+', distro):
        raise ValueError('Cannot safely determine the WSL backing drive.')
    script = (r"$entry = Get-ChildItem -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' | "
              "Get-ItemProperty | Where-Object { $_.DistributionName -eq '" + distro + "' }; "
              "if (-not $entry) { throw 'WSL registration missing' }; "
              "$entry.BasePath | ConvertTo-Json -Compress")
    base = powershell_json(script)
    match = re.search(r'([A-Za-z]):[\\/]', base)
    if not match:
        raise ValueError('Cannot identify the physical drive backing WSL.')
    return match.group(1).upper()


def preflight(path, edition, disk_usage=shutil.disk_usage, drive_lookup=backing_drive, ps=powershell_json):
    required = MIN_GIB[edition] * GIB
    free = disk_usage(existing_parent(path)).free
    if free < required:
        raise ValueError(f'{edition} build needs at least {MIN_GIB[edition]} GiB free; Linux filesystem has {free / GIB:.1f} GiB. Nothing was cleaned.')
    drive = drive_lookup(path)
    if drive:
        host_free = ps(f"[double](Get-PSDrive -Name '{drive}').Free | ConvertTo-Json -Compress")
        if not isinstance(host_free, (int, float)) or host_free < required:
            raise ValueError(f'{edition} build needs at least {MIN_GIB[edition]} GiB on backing drive {drive}:; it has {host_free / GIB:.1f} GiB. Nothing was cleaned.')
        print(f'Backing drive {drive}: {host_free / GIB:.1f} GiB free', flush=True)
    print(f'Build filesystem: {free / GIB:.1f} GiB free; minimum {MIN_GIB[edition]} GiB', flush=True)


def acquire(lock=LOCK):
    lock = Path(lock)
    lock.parent.mkdir(mode=0o700, exist_ok=True)
    info = lock.parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError('Unsafe build-lock directory.')
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise ValueError('Unsafe build-lock file.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another Dagric build is running. Wait for it; full builds are serialized.')
        os.set_inheritable(fd, True)
        return fd
    except Exception:
        os.close(fd)
        raise


def verify(fd, lock=LOCK):
    descriptor = os.fstat(fd)
    expected = Path(lock).lstat()
    if not stat.S_ISREG(expected.st_mode) or expected.st_uid != os.geteuid() or (descriptor.st_dev, descriptor.st_ino) != (expected.st_dev, expected.st_ino):
        raise ValueError('Invalid inherited build lock.')
    probe = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        raise ValueError('Build lock is not held.')
    finally:
        os.close(probe)


def validate_source(source):
    for relative in ('tools/check-source.py', 'test/test-build-directory.py',
                     'test/test-build-guard.py', 'test/test-install-profile.py',
                     'test/test-setup-integration.py', 'test/test-desktop-controls.py',
                     'test/test-private-user-state.py', 'test/test-pro-download.py'):
        subprocess.run([sys.executable, str(source / relative)], cwd=source, check=True)
    subprocess.run([sys.executable, str(source / 'tools/check-quick-ui.py')], cwd=source, check=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--verify':
        verify(int(sys.argv[2])); return
    if len(sys.argv) == 4 and sys.argv[1] == '--check-space':
        preflight(Path(sys.argv[2]), sys.argv[3]); return
    if len(sys.argv) < 5:
        raise ValueError('Expected source, build path, edition and build script.')
    source, destination = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    edition = sys.argv[3]
    if edition not in MIN_GIB:
        raise ValueError('Edition must be free or pro.')
    fd = acquire()
    preflight(destination, edition)
    validate_source(source)
    os.environ['DAGRIC_BUILD_LOCK_FD'] = str(fd)
    os.execv('/bin/sh', ['sh', *sys.argv[4:]])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit('build-preflight: ' + str(error))
