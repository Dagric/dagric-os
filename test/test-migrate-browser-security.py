#!/usr/bin/env python3
"""Privacy regression tests for browser migration files and scratch data."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config/includes.chroot/usr/share/dagric/migrate-browser.py"
SPEC = importlib.util.spec_from_file_location("dagric_migrate_browser", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MigrationPrivacyTests(unittest.TestCase):
    def test_all_browser_outputs_are_private_even_when_replacing_a_public_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outputs = {
                "tabs.html": lambda path: MODULE.write_tabs(
                    [("Firefox", "Private title", "https://example.invalid/private")], path
                ),
                "context.json": lambda path: MODULE.write_metadata(
                    {"windows_user": "private-user", "tabs": 1}, path
                ),
                "passwords.csv": lambda path: MODULE.write_passwords(
                    [("https://example.invalid", "owner", "secret")], path
                ),
            }
            for name, writer in outputs.items():
                path = os.path.join(directory, name)
                Path(path).write_text("old", encoding="utf-8")
                os.chmod(path, 0o644)
                writer(path)
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600, name)
                self.assertNotEqual(Path(path).read_text(encoding="utf-8"), "old", name)

    def test_registered_credential_workdirs_are_removed(self) -> None:
        path = MODULE.private_temp_dir()
        Path(path, "key4.db").write_text("sensitive", encoding="utf-8")
        MODULE.cleanup_private_temp_dirs()
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
