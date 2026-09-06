#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Give each Dagric Quick application its real desktop identity on X11/Wayland."""
import os
from pathlib import Path
import sys

APPS = {
    'dagric-firstrun': ('firstrun', 'dagric-firstrun'),
    'dagric-appearance': ('appearance', 'dagric-appearance'),
    'dagric-family': ('family', 'dagric-family'),
    'dagric-rewind': ('rewind', 'dagric-rewind'),
    'dagric-desktop-settings': ('desktop-settings', 'dagric-desktop-settings'),
}
SHARE = Path('/usr/share/dagric')


def main():
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    identity = Path(sys.argv[0]).name
    if identity not in APPS:
        raise SystemExit('Start this application through its Dagric launcher.')
    directory, icon = APPS[identity]
    page = SHARE / directory / 'main.qml'
    if len(sys.argv) < 2 or Path(sys.argv[1]) != page:
        raise SystemExit('Unexpected application page; refusing to load it.')
    app = QGuiApplication(sys.argv)
    app.setApplicationName(identity)
    app.setOrganizationDomain('dagric.com')
    app.setDesktopFileName(identity)
    app.setWindowIcon(QIcon.fromTheme(icon))
    engine = QQmlApplicationEngine()
    engine.quit.connect(app.quit)
    if identity == 'dagric-desktop-settings':
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from desktop_bridge import DesktopBridge
        bridge = DesktopBridge(engine)
        engine.rootContext().setContextProperty('desktopBridge', bridge)
    engine.load(QUrl.fromLocalFile(str(page)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
