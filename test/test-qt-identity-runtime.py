#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual Qt protocol/property evidence, using isolated headless compositors.

The production runner is imported unchanged. Only SHARE points at a minimal
fixture window. Full application-page behavior is covered by the Quick suite.
This is not evidence of installed-image or physical accessibility acceptance.
"""
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'config/includes.chroot/usr/lib/dagric'
sys.path.insert(0, str(LIB))
import ui_runner


def fixture():
    from PySide6 import QtQml
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    original = QtQml.QQmlApplicationEngine
    class Engine(original):
        def load(self, url):
            super().load(url)
            QTimer.singleShot(2500, QGuiApplication.instance().quit)
    QtQml.QQmlApplicationEngine = Engine
    identity, share = sys.argv[2:]
    ui_runner.SHARE = Path(share)
    page = ui_runner.SHARE / ui_runner.APPS[identity][0] / 'main.qml'
    sys.argv = [identity, str(page)]
    return ui_runner.main()


def execute():
    rows = []
    with tempfile.TemporaryDirectory(prefix='dagric-identity-') as tmp:
        root = Path(tmp); runtime = root / 'runtime'; runtime.mkdir(mode=0o700)
        share = root / 'share'; share.mkdir()
        for identity, (directory, icon) in ui_runner.APPS.items():
            target = share / directory; target.mkdir()
            (target / 'main.qml').write_text('import QtQuick\nWindow { visible:true; width:400; height:240; title:Qt.application.name; Text { anchors.centerIn:parent; text:Qt.application.name } }\n')
        env = {**os.environ, 'XDG_RUNTIME_DIR': str(runtime), 'HOME': str(root),
               'QT_QUICK_BACKEND': 'software', 'QT_ACCESSIBILITY': '1'}
        # Xvfb chooses an unused display itself; no existing server is replaced.
        readfd, writefd = os.pipe()
        xlog = (root / 'xvfb.log').open('w+')
        xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(writefd), '-screen', '0', '1280x720x24', '-nolisten', 'tcp'],
                                pass_fds=(writefd,), stdout=subprocess.DEVNULL, stderr=xlog, text=True)
        os.close(writefd)
        try:
            ready, _, _ = select.select([readfd], [], [], 5)
            if not ready: raise RuntimeError('Xvfb startup timed out.')
            with os.fdopen(readfd) as result: display = result.readline().strip()
            if not display.isdigit():
                xlog.seek(0); raise RuntimeError('Xvfb did not start: ' + xlog.read()[-2000:])
            for identity in ui_runner.APPS:
                childenv = {**env, 'DISPLAY': ':' + display, 'QT_QPA_PLATFORM': 'xcb'}
                child = subprocess.Popen([sys.executable, __file__, '--fixture', identity, str(share)], env=childenv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                evidence = ''
                for _ in range(25):
                    time.sleep(0.06)
                    probe = subprocess.run(['xprop', '-name', identity, 'WM_CLASS', '_KDE_NET_WM_DESKTOP_FILE'], env=childenv, capture_output=True, text=True, timeout=3)
                    if probe.returncode == 0:
                        evidence = probe.stdout; break
                out, err = child.communicate(timeout=8)
                if child.returncode or f'= "{identity}"' not in evidence or '_KDE_NET_WM_DESKTOP_FILE' not in evidence:
                    raise RuntimeError(identity + ': X11 identity failed: ' + evidence + err)
                rows.append({'platform': 'X11', 'application': identity, 'evidence': evidence.strip()})
        finally:
            xvfb.terminate(); xvfb.wait(timeout=5)
            xlog.close()
        with (root / 'weston.log').open('w') as log:
            weston = subprocess.Popen(['weston', '--backend=headless', '--renderer=pixman', '--socket=dagric-identity', '--idle-time=0', '--no-config'], env=env, stdout=log, stderr=log)
            try:
                for _ in range(50):
                    if (runtime / 'dagric-identity').exists(): break
                    time.sleep(0.05)
                if not (runtime / 'dagric-identity').exists(): raise RuntimeError('Isolated Wayland compositor did not start.')
                for identity in ui_runner.APPS:
                    childenv = {**env, 'WAYLAND_DISPLAY': 'dagric-identity', 'QT_QPA_PLATFORM': 'wayland', 'WAYLAND_DEBUG': '1'}
                    result = subprocess.run([sys.executable, __file__, '--fixture', identity, str(share)], env=childenv, capture_output=True, text=True, timeout=8)
                    evidence = [line for line in result.stderr.splitlines() if 'set_app_id(' in line]
                    if result.returncode or not any(f'set_app_id("{identity}")' in line for line in evidence):
                        raise RuntimeError(identity + ': Wayland identity failed: ' + result.stderr[-2000:])
                    rows.append({'platform': 'Wayland', 'application': identity, 'evidence': evidence})
            finally:
                weston.terminate(); weston.wait(timeout=5)
    output = ROOT / 'out/qt-identity-runtime.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({'scope': 'production runner with fixture windows; isolated Xvfb/Weston, not an installed ISO', 'checks': rows}, indent=2) + '\n')
    print(f'Qt window identity: {len(rows)} actual X11/Wayland checks passed. Evidence: {output}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fixture': sys.exit(fixture())
    if os.geteuid() == 0 and '--private-x11' not in sys.argv:
        sys.exit(subprocess.run(['unshare', '--mount', '--propagation', 'private', sys.executable, __file__, '--private-x11']).returncode)
    if '--private-x11' in sys.argv:
        # WSLg owns a read-only /tmp/.X11-unix. Hide it ONLY inside this mount
        # namespace; no existing host display or socket is altered.
        with tempfile.TemporaryDirectory(prefix='dagric-x11-sockets-') as sockets:
            os.chmod(sockets, 0o1777)
            subprocess.run(['mount', '--bind', sockets, '/tmp/.X11-unix'], check=True)
            try: execute()
            finally: subprocess.run(['umount', '/tmp/.X11-unix'], check=True)
    else:
        execute()
