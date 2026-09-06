# SPDX-License-Identifier: GPL-3.0-or-later
"""Asynchronous Qt boundary; no shell evaluation and no GUI-thread DBus waits."""
import json
from PySide6.QtCore import QObject, QProcess, QTimer, Signal, Slot


class DesktopBridge(QObject):
    result = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None

    @Slot(str, str)
    def request(self, action, payload):
        if action not in ('query', 'apply', 'keep', 'revert', 'reset-layout', 'undo-layout') or len(payload) > 4096:
            self.result.emit(json.dumps({'ok': False, 'message': 'Unsupported desktop request.'}))
            return
        if self.process is not None:
            return
        process = QProcess(self)
        self.process = process
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.failed)
        process.start('/usr/bin/python3', ['/usr/lib/dagric/desktop_controls.py', action])
        process.write(payload.encode())
        process.closeWriteChannel()

    def failed(self, error):
        if self.process is not None and error == QProcess.FailedToStart:
            self.process.deleteLater(); self.process = None
            self.result.emit(json.dumps({'ok': False, 'message': 'Desktop controls could not start.'}))

    def finished(self, code, status):
        if self.process is None:
            return
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.process.deleteLater(); self.process = None
        try:
            value = json.loads(output)
        except ValueError:
            value = {'ok': False, 'message': 'Desktop controls stopped unexpectedly. Any active preview will revert automatically.'}
        self.result.emit(json.dumps(value))
