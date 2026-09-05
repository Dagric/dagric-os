#!/usr/bin/env python3
"""Primary-map validation must never silently write source-complete records."""
import argparse
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_installer', ROOT / 'tools/install-generated-source-map.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SourceCompletenessGuardTests(unittest.TestCase):
    def invoke(self, primary_ok):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            paths = [folder / name for name in ('candidate.json', 'source-index.json', 'release.json')]
            for path in paths:
                path.write_text('{"status":"complete","reason_codes":["source-map-incomplete"]}')
            before = {path: path.read_bytes() for path in paths}
            args = argparse.Namespace(map_path=paths[0], index=paths[1], release=paths[2])
            result = subprocess.CompletedProcess([], 0 if primary_ok else 1, 'primary check executed\n', '')
            errors = io.StringIO()
            with patch.object(installer, 'parse_args', return_value=args), \
                 patch.object(installer.subprocess, 'run', return_value=result) as checker, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                self.assertEqual(installer.main(), 1)
            self.assertIn('check-generated-source-map.py', ' '.join(checker.call_args.args[0]))
            self.assertEqual({path: path.read_bytes() for path in paths}, before)
            self.assertEqual(set(folder.iterdir()), set(paths))
            return errors.getvalue()

    def test_primary_success_cannot_write_complete_or_clear_hold(self):
        self.assertIn('immutable images', self.invoke(True))

    def test_primary_failure_remains_a_validation_failure_without_writes(self):
        self.assertIn('generated map did not validate', self.invoke(False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
