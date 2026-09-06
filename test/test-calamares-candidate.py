#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless integration of the real Calamares binary and Dagric QML/Python job.

Use only on a completed private build root. Loads NO partition, mount, users,
unpack or bootloader module. It is not installation or VM-boot acceptance.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import yaml


def check(root):
    root = Path(root).resolve(strict=True)
    assert os.geteuid() == 0
    assert str(root).startswith('/var/tmp/dagric-onepass-') and root.parts[-2:] == ('build', 'chroot')
    assert str(root) not in Path('/proc/self/mountinfo').read_text(), 'Wait for build mounts to be released'
    assert (root / 'usr/bin/calamares').is_file()
    for path in (root / 'dev').rglob('*'):
        assert not stat.S_ISBLK(path.lstat().st_mode), 'A block device must not be exposed to this test'
    fixture = Path(tempfile.mkdtemp(prefix='dagric-calamares-check-', dir=root / 'tmp'))
    guest = '/' + str(fixture.relative_to(root))
    shutil.copytree(root / 'etc/calamares/branding', fixture / 'branding')
    assert (root / 'usr/share/calamares/qml').is_dir()
    (fixture / 'qml').symlink_to('/usr/share/calamares/qml')
    modules = fixture / 'modules'; modules.mkdir()
    for name in ('dagricprofile-check.conf',):
        shutil.copyfile(root / 'etc/calamares/modules' / name, modules / name)
    # Uses the exact installed helper even on a package-complete build which
    # has not yet reached the later installer-configuration hook.
    spec = importlib.util.spec_from_file_location('candidate_profile', root / 'usr/lib/dagric/install_profile.py')
    profile = importlib.util.module_from_spec(spec); spec.loader.exec_module(profile)
    choice = profile.chooser_config()
    choice['qmlFilename'] = 'integration-test'
    (modules / 'dagricdesktop.conf').write_text(yaml.safe_dump(choice))
    (modules / 'finished.conf').write_text('restartNowMode: never\nnotifyOnFinished: false\nrestartNowCommand: /bin/false\n')
    expected = 'Light · Familiar · Old school icons · 150% text · Arctic'
    wrapper = '''import QtQuick
import io.calamares.ui 1.0
Item {
    Loader {
        id: actualPage
        anchors.fill: parent
        source: "file:///etc/calamares/branding/dagric/dagricdesktop.qml"
        onLoaded: {
            item.mode="light"; item.layout="classic"; item.icons="old-school"
            item.textSize="biggest"; item.wallpaper="arctic"
            proceed.start()
        }
    }
    Timer {
        id: proceed; interval: 1200
        onTriggered: {
            if (config.packageChoice !== EXPECTED) throw new Error("Profile binding failed")
            console.log("DAGRIC_ACTUAL_QML_PROFILE_OK")
            ViewManager.next()
            closeTest.start()
        }
    }
    Timer { id: closeTest; interval: 3000; onTriggered: ViewManager.quit() }
}'''.replace('EXPECTED', json.dumps(expected))
    (fixture / 'branding/dagric/integration-test.qml').write_text(wrapper)
    assertion = modules / 'dagricassert'; assertion.mkdir()
    (assertion / 'module.desc').write_text('type: job\nname: dagricassert\ninterface: python\nscript: main.py\n')
    assertion_code = '''from pathlib import Path
import libcalamares
def run():
    actual = libcalamares.globalstorage.value("packagechooser_dagricdesktop")
    if actual != EXPECTED:
        return ("Profile handoff failed", "Unexpected desktop choices")
    Path(MARKER).write_text(actual)
    return None
'''.replace('EXPECTED', repr(expected)).replace('MARKER', repr(guest + '/passed.txt'))
    (assertion / 'main.py').write_text(assertion_code)
    settings = {'modules-search': [guest + '/modules', '/usr/lib/calamares/modules',
                                  '/usr/lib/x86_64-linux-gnu/calamares/modules'],
        'instances': [
            {'id':'dagricdesktop','module':'packagechooserq','config':'dagricdesktop.conf'},
            {'id':'dagricprofilecheck','module':'dagricpersonalize','config':'dagricprofile-check.conf'}],
        'sequence': [{'show':['packagechooserq@dagricdesktop']},
                     {'exec':['dagricpersonalize@dagricprofilecheck','dagricassert']}, {'show':['finished']}],
        'branding':'dagric', 'prompt-install':False, 'quit-at-end':True, 'dont-chroot':False,
        'hide-back-and-next-during-exec':True,
        'disable-cancel':False, 'disable-cancel-during-exec':False, 'oem-setup':False}
    # Test-only configuration; destructive module names must never be present.
    assert set(settings['sequence'][1]['exec']) == {'dagricpersonalize@dagricprofilecheck','dagricassert'}
    (fixture / 'settings.conf').write_text(yaml.safe_dump(settings))
    (fixture / 'runtime').mkdir(mode=0o700)
    command = ['chroot', str(root), '/usr/bin/env', 'QT_QPA_PLATFORM=offscreen',
               'QT_QUICK_BACKEND=software', 'HOME=' + guest, 'XDG_RUNTIME_DIR=' + guest + '/runtime',
               'LANG=C.UTF-8', '/usr/bin/calamares', '-d', '-c', guest]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=35)
    except subprocess.TimeoutExpired as error:
        (fixture / 'integration.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise AssertionError('Calamares integration timed out; inspect ' + str(fixture)) from error
    log = result.stdout + result.stderr
    (fixture / 'integration.log').write_text(log)
    assert result.returncode == 0, (result.returncode, str(fixture))
    assert 'DAGRIC_ACTUAL_QML_PROFILE_OK' in log, str(fixture)
    assert (fixture / 'passed.txt').read_text() == expected
    print('PASS: actual Calamares QML -> GlobalStorage -> Dagric validation job -> assertion job')
    print('Fixture and log preserved:', fixture)
    print('Not tested: partitioning, account creation, installation, reboot or VM desktop.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('completed_build_root')
    check(parser.parse_args().completed_build_root)
