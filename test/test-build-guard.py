#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guard', ROOT / 'tools/build-guard.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)


class Guard(unittest.TestCase):
    def test_lock_competition_and_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'locks/native.lock'
            fd = guard.acquire(path)
            try:
                self.assertTrue(os.get_inheritable(fd))
                guard.verify(fd, path)
                with self.assertRaises(ValueError): guard.acquire(path)
            finally: os.close(fd)
            second = guard.acquire(path); os.close(second)

    def test_symlink_lock_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'; target.write_text('do not change')
            link = Path(tmp) / 'link'; link.symlink_to(target)
            with self.assertRaises(OSError): guard.acquire(link)
            self.assertEqual(target.read_text(), 'do not change')

    def test_linux_low_space_does_not_create_build_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / 'new-build'
            with self.assertRaises(ValueError):
                guard.preflight(build, 'free', disk_usage=lambda p: SimpleNamespace(free=10*guard.GIB), drive_lookup=lambda p: None)
            self.assertFalse(build.exists())

    def test_windows_low_space_catches_large_wsl_logical_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'backing drive D:'):
                guard.preflight(Path(tmp), 'pro', disk_usage=lambda p: SimpleNamespace(free=350*guard.GIB), drive_lookup=lambda p: 'D', ps=lambda script: 10*guard.GIB)

    def test_sufficient_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard.preflight(Path(tmp), 'pro', disk_usage=lambda p: SimpleNamespace(free=100*guard.GIB), drive_lookup=lambda p: 'C', ps=lambda script: 200*guard.GIB)

    def test_preflight_before_build_directory_or_output_creation(self):
        script = (ROOT / 'build.sh').read_text()
        self.assertLess(script.index('tools/build-guard.py'), script.index('mkdir -p "$SRC/out"'))
        self.assertLess(script.index('tools/build-guard.py'), script.index('tools/prepare-build-dir.py'))


if __name__ == '__main__': unittest.main()
