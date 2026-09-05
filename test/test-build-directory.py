#!/usr/bin/env python3
"""Native build path regressions; all fixtures stay in a disposable directory."""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_build", ROOT / "tools/prepare-build-dir.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BuildDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.temp.name).resolve()
        self.source = self.base / "source"
        self.source.mkdir()
        self.sentinel = self.source / "keep.txt"
        self.sentinel.write_text("keep", encoding="utf-8")

    def tearDown(self):
        self.assertEqual(self.sentinel.read_text(encoding="utf-8"), "keep")
        self.temp.cleanup()

    def test_creates_new_sibling_with_spaces(self):
        target = self.base / "private build"
        self.assertEqual(module.prepare(self.source, target), target)
        self.assertTrue(target.is_dir())

    def test_existing_directory_and_contents_are_preserved(self):
        target = self.base / "existing"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_text("not build data", encoding="utf-8")
        with self.assertRaises(ValueError):
            module.prepare(self.source, target)
        self.assertEqual(marker.read_text(encoding="utf-8"), "not build data")

    def test_empty_directory_is_not_silently_claimed(self):
        target = self.base / "empty"
        target.mkdir()
        with self.assertRaises(ValueError):
            module.prepare(self.source, target)

    def test_source_descendant_and_ancestors_are_rejected(self):
        for target in (self.source, self.source / "build", self.base, pathlib.Path(self.base.anchor)):
            with self.subTest(target=target), self.assertRaises(ValueError):
                module.prepare(self.source, target)

    def test_relative_path_is_rejected(self):
        with self.assertRaises(ValueError):
            module.prepare(self.source, pathlib.Path("build"))

    def test_existing_file_is_preserved(self):
        target = self.base / "file"
        target.write_text("owner data", encoding="utf-8")
        with self.assertRaises(ValueError):
            module.prepare(self.source, target)
        self.assertEqual(target.read_text(encoding="utf-8"), "owner data")

    def test_missing_parent_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            module.prepare(self.source, self.base / "missing" / "build")
        self.assertFalse((self.base / "missing").exists())

    def link(self, destination, target):
        try:
            destination.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable on this host: {exc}")

    def test_symlink_to_source_is_rejected(self):
        link = self.base / "source-link"
        self.link(link, self.source)
        with self.assertRaises(ValueError):
            module.prepare(self.source, link)

    def test_symlinked_parent_cannot_enter_source(self):
        link = self.base / "source-link"
        self.link(link, self.source)
        with self.assertRaises(ValueError):
            module.prepare(self.source, link / "build")
        self.assertFalse((self.source / "build").exists())

    def test_dangling_link_is_not_followed_or_replaced(self):
        link = self.base / "dangling"
        target = self.base / "not-created"
        self.link(link, target)
        with self.assertRaises(ValueError):
            module.prepare(self.source, link)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_native_entrypoint_has_no_recursive_clean(self):
        script = (ROOT / "build.sh").read_text(encoding="utf-8")
        self.assertIn('tools/prepare-build-dir.py', script)
        self.assertNotIn('rm -rf "$BUILD"', script)
        self.assertIn('free|pro)', script)

    @unittest.skipUnless(shutil.which('sh'), 'requires a POSIX shell')
    def test_private_launcher_rejects_bad_editions_before_side_effects(self):
        launcher = ROOT / 'tools/resume-private-pro-build.sh'
        for args in (['unknown'], ['../outside'], ['pro', 'unexpected']):
            result = subprocess.run(['sh', str(launcher), *args], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('Private build directory:', result.stdout)


if __name__ == "__main__":
    unittest.main()
