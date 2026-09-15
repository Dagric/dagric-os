"""Regression tests for package section inventory generation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "package_sections", ROOT / "tools/package-sections-from-status.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageSectionTests(unittest.TestCase):
    def test_reconciles_native_and_qualified_package_names(self) -> None:
        manifest = [("bash", "5.2"), ("shim-signed:amd64", "1.51")]
        status = [
            {"Package": "bash", "Version": "5.2", "Architecture": "amd64", "Section": "shells"},
            {"Package": "shim-signed", "Version": "1.51", "Architecture": "amd64", "Section": "utils"},
        ]
        self.assertEqual(
            MODULE.reconcile(manifest, status),
            [("bash", "5.2", "shells"), ("shim-signed:amd64", "1.51", "utils")],
        )

    def test_missing_manifest_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.InventoryError, "absent from the packed"):
            MODULE.reconcile(
                [("bash", "5.2"), ("shim-signed", "1.51")],
                [{"Package": "bash", "Version": "5.2", "Architecture": "amd64", "Section": "shells"}],
            )

    def test_uninstalled_status_record_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "status"
            path.write_text(
                "Package: old\nStatus: deinstall ok config-files\nVersion: 1\n"
                "Architecture: all\nSection: misc\n\nPackage: bash\n"
                "Status: install ok installed\nVersion: 5.2\nArchitecture: amd64\n"
                "Section: shells\n",
                encoding="utf-8",
            )
            records = MODULE.parse_status(path)
            self.assertEqual([record["Package"] for record in records], ["bash"])


if __name__ == "__main__":
    unittest.main()
