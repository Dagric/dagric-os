#!/usr/bin/env python3
"""Linux regressions for local state and migration-report file boundaries."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import io


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "config/includes.chroot/usr/lib/dagric"
BIN = ROOT / "config/includes.chroot/usr/bin"
sys.path.insert(0, str(LIB))


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


pipeline = load("pipeline", LIB / "pipeline.py")
twin = load("dagric_twin_private_test", LIB / "twin.py")
restore = load("dagric_restore_private_test", BIN / "dagric-restore-assistant")
store = load("dagric_store_private_test", BIN / "dagric-store")
private_files = load("dagric_private_files_test", LIB / "private_files.py")


class PrivateStateWrites(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    @unittest.skipUnless(os.name == "posix", "Linux file modes and links")
    def test_predictable_pipeline_and_twin_temporary_links_cannot_clobber_files(self):
        for name, writer, old_name in (
            ("pipeline", pipeline.write_json_atomic, "state.json.tmp"),
            ("twin", twin.write_atomic, "state.tmp"),
        ):
            for link_kind in ("symlink", "hardlink"):
                with self.subTest(writer=name, link=link_kind):
                    directory = self.base / f"{name}-{link_kind}"
                    directory.mkdir()
                    victim = directory / "unrelated-private-file"
                    victim.write_text("original private contents", encoding="utf-8")
                    target = directory / "state.json"
                    old_temporary = directory / old_name
                    if link_kind == "symlink":
                        old_temporary.symlink_to(victim)
                    else:
                        os.link(victim, old_temporary)
                    writer(target, {"schema": 1, "private": "new state"})
                    self.assertEqual(victim.read_text(), "original private contents")
                    self.assertEqual(json.loads(target.read_text())["schema"], 1)
                    self.assertFalse(target.is_symlink())
                    self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    @unittest.skipUnless(os.name == "posix", "Linux file modes and links")
    def test_migration_notes_replace_public_output_with_private_file(self):
        target = self.base / "notes.html"
        target.write_text("old notes", encoding="utf-8")
        target.chmod(0o644)
        restore.write_notes({}, str(target))
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertIn("Dagric Migration Notes", target.read_text())

    @unittest.skipUnless(os.name == "posix", "Linux file modes and links")
    def test_migration_notes_do_not_follow_destination_links(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(link=kind):
                victim = self.base / f"{kind}-private-document"
                victim.write_text("keep my document", encoding="utf-8")
                target = self.base / f"{kind}-notes.html"
                if kind == "symlink":
                    target.symlink_to(victim)
                else:
                    os.link(victim, target)
                restore.write_notes({}, str(target))
                self.assertEqual(victim.read_text(), "keep my document")
                self.assertFalse(target.is_symlink())
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    @unittest.skipUnless(os.name == "posix", "Linux file modes and links")
    def test_picks_report_is_private_and_cannot_overwrite_a_link_target(self):
        victim = self.base / "unrelated-report"
        victim.write_text("keep this report", encoding="utf-8")
        target = self.base / "dagric-store.html"
        target.symlink_to(victim)
        with mock.patch.object(store, "CACHE_DIR", self.base), \
             mock.patch.object(store, "OUTPUT_FILE", target), \
             mock.patch.object(store, "find_default_report", return_value=None), \
             mock.patch.object(sys, "stdout", new_callable=io.StringIO), \
             mock.patch.object(sys, "argv", ["dagric-store", "--no-open"]):
            store.main()
        self.assertEqual(victim.read_text(), "keep this report")
        self.assertFalse(target.is_symlink())
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    @unittest.skipUnless(os.name == "posix", "Linux file modes")
    def test_temporary_contents_are_private_before_replace_under_permissive_umask(self):
        target = self.base / "report.txt"
        real_replace = private_files.os.replace
        observed = []

        def inspect_replace(source, destination):
            staged = Path(source)
            observed.append(stat.S_IMODE(staged.stat().st_mode))
            self.assertEqual(staged.read_text(), "private migration details")
            real_replace(source, destination)

        previous_umask = os.umask(0)
        try:
            with mock.patch.object(private_files.os, "replace", side_effect=inspect_replace):
                private_files.write_private_text(target, "private migration details")
        finally:
            os.umask(previous_umask)
        self.assertEqual(observed, [0o600])
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_failed_sync_leaves_previous_output_and_cleans_staging(self):
        target = self.base / "report.txt"
        target.write_text("previous complete report", encoding="utf-8")
        with mock.patch.object(private_files.os, "fsync", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                private_files.write_private_text(target, "incomplete replacement")
        self.assertEqual(target.read_text(), "previous complete report")
        self.assertEqual(list(self.base.iterdir()), [target])

    def test_failed_replace_leaves_previous_output_and_cleans_staging(self):
        target = self.base / "report.txt"
        target.write_text("previous complete report", encoding="utf-8")
        with mock.patch.object(private_files.os, "replace", side_effect=OSError("read-only filesystem")):
            with self.assertRaisesRegex(OSError, "read-only filesystem"):
                private_files.write_private_text(target, "replacement")
        self.assertEqual(target.read_text(), "previous complete report")
        self.assertEqual(list(self.base.iterdir()), [target])

    def test_concurrent_writes_publish_one_complete_output_without_temp_collisions(self):
        target = self.base / "state.json"
        candidates = [json.dumps({"writer": index, "contents": str(index) * 1000}) for index in range(24)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda value: private_files.write_private_text(target, value), candidates))
        self.assertIn(target.read_text(), candidates)
        self.assertEqual(list(self.base.iterdir()), [target])

    @unittest.skipUnless(os.name == "posix", "Linux file modes and links")
    def test_generated_launcher_does_not_follow_existing_symlink(self):
        apps = self.base / ".local/share/applications"
        apps.mkdir(parents=True)
        victim = self.base / "unrelated-launcher"
        victim.write_text("keep existing launcher", encoding="utf-8")
        target = apps / "dagric-migration-notes.desktop"
        target.symlink_to(victim)
        with mock.patch.object(restore, "HOME_DIR", str(self.base)):
            restore.kde_launcher(str(self.base / "notes.html"))
        self.assertEqual(victim.read_text(), "keep existing launcher")
        self.assertFalse(target.is_symlink())
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
