#!/usr/bin/env python3
"""Focused tests for the Snapshot-backed exact-source-map generator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dagric_generate_exact_source_map",
    ROOT / "tools/generate-exact-source-map.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExactSourceMapGeneratorTests(unittest.TestCase):
    def test_manifest_preserves_architecture_qualified_identity(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "filesystem.packages"
            path.write_text("libc6:amd64\t2.41-12\nadduser\t3.152\n", encoding="utf-8")
            self.assertEqual(
                MODULE.parse_manifest(path),
                [("libc6:amd64", "2.41-12"), ("adduser", "3.152")],
            )

    def test_manifest_rejects_duplicate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "filesystem.packages"
            path.write_text("adduser\t3.152\nadduser\t3.152\n", encoding="utf-8")
            with self.assertRaises(MODULE.SourceMapError):
                MODULE.parse_manifest(path)

    def test_dsc_parser_requires_sha256_and_safe_names(self) -> None:
        payload = b"""Format: 3.0 (quilt)\nChecksums-Sha256:\n aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 10 pkg_1.orig.tar.xz\n bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 20 pkg_1.debian.tar.xz\nFiles:\n"""
        self.assertEqual(
            MODULE.parse_dsc_source_files(payload, "https://snapshot.debian.org/archive/debian/20260904T000000Z/pool/main/p/pkg"),
            [
                {
                    "filename": "pkg_1.orig.tar.xz",
                    "url": "https://snapshot.debian.org/archive/debian/20260904T000000Z/pool/main/p/pkg/pkg_1.orig.tar.xz",
                    "sha256": "a" * 64,
                },
                {
                    "filename": "pkg_1.debian.tar.xz",
                    "url": "https://snapshot.debian.org/archive/debian/20260904T000000Z/pool/main/p/pkg/pkg_1.debian.tar.xz",
                    "sha256": "b" * 64,
                },
            ],
        )
        unsafe = payload.replace(b"pkg_1.orig.tar.xz", b"../pkg_1.orig.tar.xz")
        with self.assertRaises(MODULE.SourceMapError):
            MODULE.parse_dsc_source_files(unsafe, "https://snapshot.debian.org")

    def test_archive_selection_rejects_debug_and_prefers_debian(self) -> None:
        rows = [
            {
                "archive_name": "debian-debug",
                "first_seen": "20260901T000000Z",
                "path": "/pool/main/p/pkg",
                "name": "pkg_1.dsc",
            },
            {
                "archive_name": "debian-security",
                "first_seen": "20260902T000000Z",
                "path": "/pool/updates/main/p/pkg",
                "name": "pkg_1.dsc",
            },
            {
                "archive_name": "debian",
                "first_seen": "20260903T000000Z",
                "path": "/pool/main/p/pkg",
                "name": "pkg_1.dsc",
            },
        ]
        self.assertEqual(MODULE.choose_archive_record(rows)["archive_name"], "debian")


if __name__ == "__main__":
    unittest.main()
