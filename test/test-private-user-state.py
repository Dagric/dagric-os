#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real skeleton-permissions hook against disposable fixtures."""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = (ROOT / 'config/hooks/normal/0996-private-user-state.hook.chroot').read_text()


class PrivateStateSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dagric-skel-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'skel'
        self.root.mkdir()

    def run_hook(self):
        # Only fixture paths and the expected fixture owner differ from the
        # production hook; no environment override is added to the OS hook.
        code = HOOK.replace('/etc/skel', str(self.root)).replace('-eq 0 ]', f'-eq {os.getuid()} ]')
        return subprocess.run(['sh', '-eu'], input=code, text=True, capture_output=True)

    def test_seeds_private_directories_and_is_idempotent(self):
        for _ in range(2):
            result = self.run_hook()
            self.assertEqual(result.returncode, 0, result.stderr)
            for path in ('.config', '.local', '.local/state', '.local/state/dagric'):
                self.assertEqual(stat.S_IMODE((self.root / path).stat().st_mode), 0o700)

    def test_normalizes_only_named_directories_and_preserves_data(self):
        state = self.root / '.local/state/dagric'
        state.mkdir(parents=True)
        for path in (self.root / '.local', state): path.chmod(0o775)
        data = state / 'keep.json'; data.write_text('{"keep": true}'); data.chmod(0o640)
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data.read_text(), '{"keep": true}')
        self.assertEqual(stat.S_IMODE(data.stat().st_mode), 0o640)

    def test_rejects_linked_parent_without_following_it(self):
        external = Path(self.tmp.name) / 'external'; external.mkdir(); external.chmod(0o755)
        (self.root / '.local').symlink_to(external, target_is_directory=True)
        result = self.run_hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(stat.S_IMODE(external.stat().st_mode), 0o755)
        self.assertFalse((external / 'state').exists())

    def test_rejects_non_directory_without_changing_it(self):
        target = self.root / '.config'; target.write_text('keep me')
        self.assertNotEqual(self.run_hook().returncode, 0)
        self.assertEqual(target.read_text(), 'keep me')


if __name__ == '__main__':
    unittest.main()
