#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the five installed Quick apps in a completed private candidate chroot.

The real runner, QML, dependencies and assets are used unchanged. A test engine
subclass only schedules inspection and exit. Catalogues are synthetic; no shell
wrappers, installer jobs, account creation or desktop mutation are invoked.
This is package/render integration, not VM or assistive-technology acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile


def inside(identity, directory):
    from PySide6 import QtQml, QtQuick
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    sys.path.insert(0, '/usr/lib/dagric')
    import ui_runner
    folder = Path(directory)
    original = QtQml.QQmlApplicationEngine
    observed = {}

    class Engine(original):
        def load(self, url):
            super().load(url)
            QTimer.singleShot(1800, self.inspect)

        def inspect(self):
            try:
                roots = self.rootObjects()
                assert len(roots) == 1, 'Expected one application root'
                window = roots[0]
                assert isinstance(window, QtQuick.QQuickWindow)
                assert window.isVisible() and window.width() > 0 and window.height() > 0
                assert QGuiApplication.instance().desktopFileName() == identity
                assert not window.property('loadError'), window.property('loadError')
                rendered = window.grabWindow()
                assert not rendered.isNull() and rendered.save(str(folder / (identity + '.png')))
                observed.update(application=identity, title=window.title(),
                                width=window.width(), height=window.height(),
                                desktop_file=QGuiApplication.instance().desktopFileName(),
                                root_visible=True, image=identity + '.png')
            except Exception as error:
                observed['error'] = str(error)
            finally:
                QGuiApplication.instance().quit()

    QtQml.QQmlApplicationEngine = Engine
    page = Path('/usr/share/dagric') / ui_runner.APPS[identity][0] / 'main.qml'
    sys.argv = [identity, str(page), '--', '--catalog=' + str(folder / (identity + '.json'))]
    code = ui_runner.main()
    if code or observed.get('error') or not observed.get('root_visible'):
        raise RuntimeError(str(observed))
    observed['qml_sha256'] = hashlib.sha256(page.read_bytes()).hexdigest()
    (folder / (identity + '.result.json')).write_text(json.dumps(observed, indent=2) + '\n')


def check(root):
    root = Path(root).resolve(strict=True)
    assert os.geteuid() == 0
    assert str(root).startswith('/var/tmp/dagric-finishing-build-mount.')
    assert root.parts[-2:] == ('build', 'chroot')
    assert str(root) not in Path('/proc/self/mountinfo').read_text(), 'Wait for build mounts to be released'
    for path in (root / 'dev').rglob('*'):
        assert not stat.S_ISBLK(path.lstat().st_mode), 'Block devices must not be exposed'
    folder = Path(tempfile.mkdtemp(prefix='dagric-quick-check-', dir=root / 'tmp'))
    guest = '/' + str(folder.relative_to(root))
    shutil.copyfile(__file__, folder / 'probe.py')
    (folder / 'runtime').mkdir(mode=0o700)
    edition = (root / 'etc/dagric-edition').read_text().strip()
    catalogues = {
        'dagric-firstrun': {'edition': edition, 'editionName': 'Dagric OS' + (' Pro' if edition == 'pro' else ''),
            'live': True, 'canInstall': True, 'currentMode': 'dark', 'currentScale': 100,
            'currentAccentHex': '#b82036', 'reducedMotion': True},
        'dagric-appearance': {'edition': edition, 'reducedMotion': True,
            'styles': [], 'layouts': [], 'icons': []},
        'dagric-family': {'people': [], 'strings': {}},
        'dagric-rewind': {'ready': False, 'reason': 'live', 'presets': [],
            'active': None, 'sessions': [], 'snapshots': [], 'review': None},
        'dagric-desktop-settings': {},
    }
    results = []
    for identity, catalogue in catalogues.items():
        (folder / (identity + '.json')).write_text(json.dumps(catalogue))
        command = ['chroot', str(root), '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
            'QT_QPA_PLATFORM=offscreen', 'QT_QUICK_BACKEND=software', 'QML_XHR_ALLOW_FILE_READ=1',
            'HOME=' + guest, 'XDG_RUNTIME_DIR=' + guest + '/runtime', 'LANG=C.UTF-8',
            '/usr/bin/python3', guest + '/probe.py', '--inside', identity, guest]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        log = result.stdout + result.stderr
        (folder / (identity + '.log')).write_text(log)
        assert result.returncode == 0, (identity, log[-4000:])
        assert not any(error in log for error in ('ReferenceError:', 'TypeError:', 'SyntaxError:',
            'QQmlApplicationEngine failed', 'is not installed', 'Unable to assign', 'Binding loop detected')), (identity, log)
        results.append(json.loads((folder / (identity + '.result.json')).read_text()))
        print('PASS: installed runner and full QML page rendered: ' + identity, flush=True)
    report = {'scope': 'Completed build chroot; full installed pages with synthetic catalogues; no VM/session/account/recovery acceptance',
        'edition': edition, 'runner_sha256': hashlib.sha256((root / 'usr/lib/dagric/ui_runner.py').read_bytes()).hexdigest(),
        'checks': results}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Evidence preserved: ' + str(folder), flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--inside':
        inside(*sys.argv[2:])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('completed_build_root')
        check(parser.parse_args().completed_build_root)
