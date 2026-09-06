#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the shipped shell event loop with a real child process/FIFO.

All desktop and installer actions are fixtures; no real settings are changed.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'config/includes.chroot/usr/bin/dagric-firstrun').read_text()
EVENTS = SOURCE[SOURCE.index('\nlast_wall=\n'):]


class Finish(unittest.TestCase):
    def run_case(self, lines, *, exit_code=0, live=True, layout_ok=True, scale_ok=True):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake = directory / 'qml'
            fake.write_text('#!/bin/sh\n' + '\n'.join("printf '%s\\n' '" + line + "'" for line in lines)
                            + '\nexec 1>&- 2>&-\nsleep 0.1\n'
                            + ': > "$WORK/ui-exited"\nexit ' + str(exit_code) + '\n')
            fake.chmod(0o700)
            prelude = '''
set -eu
SCALE_MODE=x11
SCALE_STATUS=$WORK/scale-status.json
QMLFILE=fixture
CATALOG=fixture
deferred() { test -e "$WORK/ui-exited" || exit 97; printf '%s\n' "$1" >> "$WORK/actions"; }
gettext() { printf '%s' "$1"; }
notify() { printf '%s\n' "$1" >> "$WORK/notices"; }
stamp() { :; }
current_scale() { printf 100; }
lookup_layout() { if [ "$1" = classic ]; then printf '%s/layout.look' "$WORK"; fi; }
set_layout() { deferred layout; test "$LAYOUT_OK_FIXTURE" = true; }
run_downloads() { deferred "downloads:$APPS_QUEUE"; }
launch_installer() { deferred installer; }
capture_scale() { :; }
restore_scale() { printf restore >> "$WORK/actions"; }
set_scale() { test "$SCALE_OK_FIXTURE" = true; }
fallback_wizard() { printf fallback >> "$WORK/actions"; }
'''
            (directory / 'layout.look').touch()
            env = dict(os.environ, WORK=tmp, QML=str(fake), CAN_INSTALL=str(live).lower(),
                       LAYOUT_OK_FIXTURE=str(layout_ok).lower(), SCALE_OK_FIXTURE=str(scale_ok).lower())
            result = subprocess.run(['sh', '-c', prelude + EVENTS], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            return {name: (directory / name).read_text() if (directory / name).exists() else ''
                    for name in ('actions', 'notices', 'scale-status.json')}

    def test_finish_waits_for_closed_process_and_runs_once(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@LAYOUT|classic', '@DAGRIC@APPS|gimp',
                                '@DAGRIC@DONE', '@DAGRIC@DONE', '@DAGRIC@APPS|unexpected'])
        self.assertEqual(result['actions'], 'layout\ndownloads:gimp\n')
        self.assertIn('Dagric is set up.', result['notices'])

    def test_close_never_installs_queued_apps(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@APPS|gimp', '@DAGRIC@QUIT'])
        self.assertEqual(result['actions'], '')
        self.assertIn('nothing you ticked was installed', result['notices'])

    def test_crash_after_finish_does_not_apply(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@LAYOUT|classic', '@DAGRIC@APPS|gimp', '@DAGRIC@DONE'], exit_code=9)
        self.assertEqual(result['actions'], '')
        self.assertNotIn('Dagric is set up.', result['notices'])

    def test_layout_failure_does_not_claim_success(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@LAYOUT|classic', '@DAGRIC@DONE'], layout_ok=False)
        self.assertIn('taskbar could not be changed', result['notices'])
        self.assertNotIn('Dagric is set up.', result['notices'])

    def test_installer_waits_for_ui_and_does_not_apply_trial_queue(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@LAYOUT|classic', '@DAGRIC@INSTALL', '@DAGRIC@DONE'])
        self.assertEqual(result['actions'], 'installer\n')

    def test_installed_session_cannot_start_installer(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@INSTALL', '@DAGRIC@QUIT'], live=False)
        self.assertEqual(result['actions'], '')

    def test_x11_saves_before_acknowledging(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@SCALE|125', '@DAGRIC@QUIT'])
        self.assertIn('"phase":"saved","scale":125', result['scale-status.json'])

    def test_x11_failure_restores_and_reports_error(self):
        result = self.run_case(['@DAGRIC@READY', '@DAGRIC@SCALE|150', '@DAGRIC@QUIT'], scale_ok=False)
        self.assertEqual(result['actions'], 'restore')
        self.assertIn('"phase":"error","scale":100', result['scale-status.json'])

    def test_invalid_protocol_cannot_select_unknown_layout(self):
        result = self.run_case(['ordinary log', '@DAGRIC@READY', '@DAGRIC@LAYOUT|../../bad', '@DAGRIC@DONE'])
        self.assertEqual(result['actions'], 'downloads:\n')


if __name__ == '__main__':
    unittest.main()
