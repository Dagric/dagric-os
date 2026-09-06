#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read back a private candidate and optionally clear only its preparer header.

Creates a new verification directory/image; never overwrites the input or grants
release approval. The input must be source/out/<edition>.iso from a clean clone.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import yaml


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): {result.stderr[-4000:]}')
    return result.stdout


def sha(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def verify(base, revision, output_root='/var/tmp'):
    base = Path(base).resolve(strict=True)
    assert re.fullmatch('[a-f0-9]{40}', revision)
    assert base.name in ('dagric-os-1.0-amd64.iso', 'dagric-os-pro-1.0-amd64.iso')
    edition = 'pro' if '-pro-' in base.name else 'free'
    source = base.parent.parent
    assert run('git', 'rev-parse', 'HEAD', cwd=source).strip() == revision
    assert not run('git', 'status', '--porcelain', '--untracked-files=no', cwd=source)
    original_hash = sha(base)
    output_root = Path(output_root).resolve(strict=True)
    assert output_root.is_dir() and output_root != Path('/')
    folder = Path(tempfile.mkdtemp(prefix='dagric-onepass-verified-' + edition + '.', dir=output_root))
    print('VERIFICATION_WORKSPACE=' + str(folder), flush=True)
    target = folder / base.name
    run('xorriso', '-indev', str(base), '-outdev', str(target), '-boot_image', 'any', 'replay',
        '-preparer_id', '', '-commit', '-end')
    run('xorriso', '-osirrox', 'on', '-indev', str(base), '-extract', '/sha256sum.txt', str(folder / 'original-checksums'))
    run('xorriso', '-osirrox', 'on', '-indev', str(target), '-extract', '/', str(folder / 'iso'))
    assert (folder / 'original-checksums').read_bytes() == (folder / 'iso/sha256sum.txt').read_bytes()
    run('sha256sum', '--quiet', '-c', 'sha256sum.txt', cwd=folder / 'iso')
    print('ISO payload checksums passed.', flush=True)
    owned = {
        'dagric-tools': ['usr/bin/dagric-firstrun', 'usr/bin/dagric-desktop-settings',
            'usr/lib/dagric/install_profile.py',
            'usr/lib/dagric/ui_runner.py', 'usr/lib/dagric/desktop_controls.py',
            'usr/lib/dagric/desktop_bridge.py',
            'usr/lib/calamares/modules/dagricpersonalize/main.py',
            'usr/lib/calamares/modules/dagricpersonalize/module.desc',
            'usr/share/dagric/desktop-settings/main.qml',
            'usr/share/dagric/desktop-settings/PanelControls.qml',
            'usr/share/applications/dagric-desktop-settings.desktop',
            'usr/share/dagric/looks/classic.look', 'usr/share/dagric/looks/eleven.look'] +
            [f'usr/share/icons/{theme}/index.theme' for theme in ('DagricModern', 'DagricClassic', 'DagricOldSchool')],
        'dagric-branding': ['usr/share/plasma/look-and-feel/org.dagric.desktop/contents/layouts/org.kde.plasma.desktop-layout.js'],
        'dagric-desktop-defaults': ['etc/xdg/kicker-extra-favoritesrc'],
    }
    configs = ['etc/calamares/branding/dagric/ProfileChoice.qml',
        'etc/calamares/branding/dagric/DesktopPreview.qml',
        'etc/calamares/branding/dagric/dagricdesktop.qml',
        'etc/calamares/branding/dagric/lang/calamares-dagric_en.qm',
        'etc/calamares/modules/partition.conf', 'etc/calamares/modules/dagricprofile-check.conf',
        'etc/calamares/modules/dagricprofile-apply.conf']
    paths = sum(owned.values(), []) + configs
    extras = (['etc/dagric-edition', 'etc/calamares/settings.conf', 'etc/calamares/modules/dagricdesktop.conf',
        'etc/calamares/modules/users.conf', 'etc/calamares/modules/welcome.conf',
        'etc/calamares/modules/unpackfs.conf', 'etc/calamares/branding/dagric/branding.desc',
        'etc/skel/.config/autostart/dagric-firstrun.desktop',
        'usr/share/applications/calamares-install-debian.desktop', 'var/lib/dpkg/status',
        'usr/lib/x86_64-linux-gnu/calamares/modules/packagechooserq/module.desc'] +
        [f'var/lib/dpkg/info/{package}.md5sums' for package in owned] +
        [f'usr/lib/dagric/wm/{app}' for app in ('dagric-firstrun', 'dagric-appearance', 'dagric-family', 'dagric-rewind', 'dagric-desktop-settings')])
    root = folder / 'root'
    squashfs = folder / 'iso/live/filesystem.squashfs'
    run('unsquashfs', '-d', str(root), str(squashfs), *paths, *extras)
    for path in paths:
        assert sha(root / path) == sha(source / 'config/includes.chroot' / path), path
    for package, members in owned.items():
        sums = (root / f'var/lib/dpkg/info/{package}.md5sums').read_text()
        for path in members:
            assert sha(root / path, 'md5') + '  ' + path in sums, (package, path)
    settings = yaml.safe_load((root / 'etc/calamares/settings.conf').read_text())
    show = settings['sequence'][0]['show']; execute = settings['sequence'][1]['exec']
    assert show[-3:] == ['packagechooserq@dagricdesktop', 'users', 'summary']
    assert execute[0] == 'dagricpersonalize@dagricprofilecheck'
    assert execute[execute.index('users') + 1] == 'dagricpersonalize@dagricprofileapply'
    assert execute.index('unpackfs') < execute.index('users') < execute.index('umount')
    assert settings['prompt-install'] is True and settings['dont-chroot'] is False
    assert yaml.safe_load((root / 'usr/lib/calamares/modules/dagricpersonalize/module.desc').read_text())['type'] == 'job'
    spec = importlib.util.spec_from_file_location('profile', source / 'config/includes.chroot/usr/lib/dagric/install_profile.py')
    profile = importlib.util.module_from_spec(spec); spec.loader.exec_module(profile)
    assert yaml.safe_load((root / 'etc/calamares/modules/dagricdesktop.conf').read_text()) == profile.chooser_config()
    partition = yaml.safe_load((root / 'etc/calamares/modules/partition.conf').read_text())
    assert partition['userSwapChoices'] == ['none']
    assert partition['initialPartitioningChoice'] == 'none'
    assert partition['enableLuksAutomatedPartitioning'] is True
    assert partition['defaultFileSystemType'] == 'btrfs'
    assert 'availableFileSystemTypes' not in partition
    assert (root / 'etc/dagric-edition').read_text().strip() == edition
    assert 'Exec=dagric-firstrun --autostart\n' in (root / 'etc/skel/.config/autostart/dagric-firstrun.desktop').read_text()
    assert 'firstrun-done' not in run('unsquashfs', '-ll', str(squashfs), 'etc/skel')
    users = yaml.safe_load((root / 'etc/calamares/modules/users.conf').read_text())
    assert users['passwordRequirements']['nonempty'] is True
    assert users['setRootPassword'] is False and 'sudo' in users['defaultGroups']
    welcome = yaml.safe_load((root / 'etc/calamares/modules/welcome.conf').read_text())
    assert welcome['requirements']['requiredStorage'] == (40 if edition == 'pro' else 25)
    status = (root / 'var/lib/dpkg/status').read_text()
    for package in ('python3-yaml', 'python3-pyside6.qtquick', 'calamares', *owned):
        rows = [s for s in status.split('\n\n') if s.startswith('Package: ' + package + '\n')]
        assert len(rows) == 1 and 'Status: install ok installed' in rows[0], package
    for app in ('dagric-firstrun', 'dagric-appearance', 'dagric-family', 'dagric-rewind', 'dagric-desktop-settings'):
        alias = root / 'usr/lib/dagric/wm' / app
        assert alias.is_symlink() and str(alias.readlink()) == '/usr/lib/dagric/ui_runner.py', app
    assert sha(base) == original_hash
    boot = subprocess.run(['xorriso', '-indev', str(target), '-pvd_info', '-report_el_torito', 'plain'],
                          check=True, capture_output=True, text=True)
    boot_report = boot.stdout + boot.stderr
    assert 'BIOS' in boot_report and 'UEFI' in boot_report
    assert any(line.startswith('Preparer Id') and not line.split(':', 1)[1].strip() for line in boot_report.splitlines())
    record = {'source_commit': revision, 'edition': edition, 'base_sha256': original_hash,
        'sha256': sha(target), 'bytes': target.stat().st_size, 'iso': str(target),
        'payload_checksums': 'passed', 'exact_source_files': paths,
        'package_payloads': 'verified for listed owned files',
        'installer_sequence': 'validated before partition; applies after account creation',
        'optional_metadata_cleanup': 'preparer header cleared in copy; input and payload preserved',
        'boot_structures': 'BIOS and UEFI present; this is not runtime boot evidence',
        'runtime_acceptance': 'not established by this tool', 'release_approved': False}
    (folder / 'verification.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso'); parser.add_argument('source_revision')
    parser.add_argument('--output-root', default='/var/tmp', help='Existing directory on a drive with space for verification copies')
    args = parser.parse_args()
    verify(args.iso, args.source_revision, args.output_root)
