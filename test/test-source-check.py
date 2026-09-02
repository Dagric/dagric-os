#!/usr/bin/env python3
"""Mutation tests for tools/check-source.py's failure paths."""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_check", REPO / "tools/check-source.py")
assert SPEC and SPEC.loader
source_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_check)


class SourceCheckMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        (self.root / "config/includes.chroot/usr/share/polkit-1/actions").mkdir(parents=True)
        (self.root / ".github/workflows").mkdir(parents=True)
        for folder in ("site", "test", "promo", "infra", "tools"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def patched(self):
        return mock.patch.multiple(
            source_check,
            ROOT=self.root,
            INCLUDES=self.root / "config/includes.chroot",
            POLICIES=self.root / "config/includes.chroot/usr/share/polkit-1/actions",
            WORKFLOWS=self.root / ".github/workflows",
        )

    def test_invalid_json_is_rejected(self):
        (self.root / "site/broken.json").write_text("{nope", encoding="utf-8")
        errors: list[str] = []
        with self.patched():
            self.assertEqual(1, source_check.check_json(errors))
        self.assertTrue(any("invalid JSON" in item for item in errors))

    def test_invalid_python_is_rejected(self):
        (self.root / "tools/broken.py").write_text("if :\n", encoding="utf-8")
        errors: list[str] = []
        with self.patched():
            self.assertEqual(1, source_check.check_python(errors))
        self.assertTrue(any("invalid Python" in item for item in errors))

    def test_unsafe_polkit_defaults_and_missing_helper_are_rejected(self):
        policy = self.root / "config/includes.chroot/usr/share/polkit-1/actions/bad.policy"
        policy.write_text("""<?xml version="1.0"?>
<policyconfig><action id="bad"><defaults>
<allow_any>yes</allow_any><allow_inactive>no</allow_inactive><allow_active>yes</allow_active>
</defaults><annotate key="org.freedesktop.policykit.exec.path">/usr/lib/missing</annotate>
</action></policyconfig>""", encoding="utf-8")
        errors: list[str] = []
        with self.patched():
            self.assertEqual(1, source_check.check_polkit(errors))
        joined = "\n".join(errors)
        self.assertIn("allow_any=no", joined)
        self.assertIn("unsafe allow_active", joined)
        self.assertIn("targets missing", joined)

    def test_unpinned_action_is_rejected_but_local_action_is_allowed(self):
        workflow = self.root / ".github/workflows/test.yml"
        workflow.write_text("""steps:
  - uses: actions/checkout@v4
  - uses: ./local-action
""", encoding="utf-8")
        errors: list[str] = []
        with self.patched():
            self.assertEqual(2, source_check.check_workflows(errors))
        self.assertEqual(1, len(errors))
        self.assertIn("actions/checkout@v4", errors[0])

    @unittest.skipUnless(shutil.which("git") or shutil.which("git.exe"), "git is required")
    def test_sensitive_path_private_key_and_merge_debris_are_rejected(self):
        git = [source_check.GIT, "-c", f"safe.directory={self.root}"]
        subprocess.run([*git, "init", "-q"], cwd=self.root, check=True)
        # Exercise the filename and content detectors independently. Keeping
        # the key marker in the sensitive-looking path makes one diagnostic
        # depend on Git's treatment of that path on the host filesystem.
        (self.root / "credentials.pem").write_text("not-a-real-key\n", encoding="utf-8")
        private_key_marker = "-----BEGIN " + "PRIVATE KEY-----\n"
        (self.root / "notes.txt").write_text(
            private_key_marker + "not-a-real-key\n", encoding="utf-8"
        )
        (self.root / "merge.txt").write_text("<<<<<<< ours\ntext\n=======\nother\n>>>>>>> theirs\n", encoding="utf-8")
        subprocess.run(
            [*git, "add", "credentials.pem", "notes.txt", "merge.txt"],
            cwd=self.root,
            check=True,
        )
        # The release scanner must inspect the staged source snapshot, not a
        # later worktree edit. Otherwise a key staged for commit can disappear
        # from the check merely because the file was cleaned locally afterward.
        (self.root / "notes.txt").write_text("clean worktree copy\n", encoding="utf-8")
        (self.root / "merge.txt").write_text("clean worktree copy\n", encoding="utf-8")
        errors: list[str] = []
        with self.patched():
            self.assertEqual(3, source_check.check_repository(errors))
        joined = "\n".join(errors)
        self.assertIn("tracked sensitive-looking path", joined)
        self.assertIn("unresolved merge markers", joined)
        self.assertIn("private key material", joined)


if __name__ == "__main__":
    unittest.main()
