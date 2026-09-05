#!/usr/bin/env python3
"""Regression checks for the security floor and current design contract."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('flow', ROOT / 'tools/check-flow.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


class FixTests(unittest.TestCase):
    def test_current_flow(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(flow.main(), 0)

    def test_wrong_defaults_and_accents_fail(self):
        cases = [
            ('org.dagric.desktop/contents/defaults', 'Image=DagricObsidianPulse', 'Image=Wrong'),
            ('org.dagric.desktop/contents/defaults', 'ColorScheme=DagricDark', 'ColorScheme=Wrong'),
            ('usr/bin/dagric-firstrun', "BRAND='#b82036'", "BRAND='#ffffff'"),
            ('dagric/firstrun/main.qml', 'startAccent: "#b82036"', 'startAccent: "#ffffff"'),
            ('dagric/firstrun/main.qml', 'cAccent: "#b82036"', 'cAccent: "#ffffff"'),
            ('contents/splash/Splash.qml', 'color: "#b82036"', 'color: "#ffffff"'),
        ]
        original = Path.read_text
        for suffix, before, after in cases:
            def changed(path, *args, **kwargs):
                text = original(path, *args, **kwargs)
                return text.replace(before, after) if path.as_posix().endswith(suffix) else text
            with self.subTest(suffix=suffix, before=before), patch.object(Path, 'read_text', changed):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(flow.main(), 1)

    def test_browser_floor(self):
        hook = (ROOT / 'config/hooks/normal/0995-chromium-security-floor.hook.chroot').read_text()
        # Substitute only the fixture edition input; exercise the original hook
        # and real Debian version comparison without touching an installed system.
        hook = hook.replace('edition=$(cat /etc/dagric-edition)', 'edition=$FIXTURE_EDITION')
        with tempfile.TemporaryDirectory() as directory:
            query = Path(directory) / 'dpkg-query'
            query.write_text('#!/bin/sh\n[ "$FIXTURE_VERSION" != missing ] || exit 1\nprintf "%s" "$FIXTURE_VERSION"\n')
            query.chmod(0o755)
            for edition, version, success in [
                ('pro', '152.0.7977.75-1~deb13u1', False),
                ('pro', '152.0.7977.82-1~deb13u1', True),
                ('pro', '153.0.0.1-1', True),
                ('pro', 'missing', False),
                ('free', 'missing', True),
            ]:
                env = dict(os.environ, PATH=directory + ':' + os.environ['PATH'],
                           FIXTURE_EDITION=edition, FIXTURE_VERSION=version)
                with self.subTest(edition=edition, version=version):
                    result = subprocess.run(['sh', '-s'], input=hook, text=True,
                                            capture_output=True, env=env)
                    self.assertEqual(result.returncode == 0, success, result.stderr)


if __name__ == '__main__':
    unittest.main()
