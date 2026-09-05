#!/usr/bin/env python3
"""Exercise audit selection and failure propagation without running its gates."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which("sh")


@unittest.skipUnless(SHELL and os.name == "posix", "requires a POSIX shell")
class AuditModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tools").mkdir()
        self.script = self.root / "tools/audit-all.sh"
        self.script.write_text((ROOT / "tools/audit-all.sh").read_text(), encoding="utf-8")
        self.log = self.root / "calls"
        stub = self.root / "bin"
        stub.mkdir()
        for name in ("python3", "node", "sh"):
            path = stub / name
            path.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$*" >> "$AUDIT_MODE_TEST_LOG"\n'
                'if [ -n "${AUDIT_MODE_TEST_FAIL:-}" ] && '
                '[ "$1" = "$AUDIT_MODE_TEST_FAIL" ]; then exit 19; fi\n',
                encoding="utf-8",
            )
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": str(stub) + os.pathsep + os.environ.get("PATH", ""),
            "AUDIT_MODE_TEST_LOG": str(self.log),
        }

    def invoke(self, *args, fail=None):
        env = {**self.env}
        if fail:
            env["AUDIT_MODE_TEST_FAIL"] = fail
        result = subprocess.run(
            [SHELL, str(self.script), *args], env=env,
            text=True, capture_output=True, check=False,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_default_still_requires_generated_map(self):
        result, calls = self.invoke(fail="tools/check-generated-source-map.py")
        self.assertEqual(result.returncode, 19)
        self.assertIn("tools/check-generated-source-map.py", calls)
        self.assertNotIn("every selected gate passed", result.stdout)

    def test_source_only_omits_only_generated_map(self):
        full, full_calls = self.invoke()
        self.log.unlink()
        source, source_calls = self.invoke("--source-only")
        self.assertEqual(full.returncode, 0)
        self.assertEqual(source.returncode, 0)
        self.assertEqual(
            source_calls,
            [call for call in full_calls if call != "tools/check-generated-source-map.py"],
        )
        self.assertIn("tools/check-site.sh", source_calls)
        self.assertIn("test/test-source-map-gate.py", source_calls)
        self.assertIn("NOT CHECKED: generated candidate", source.stdout)
        self.assertIn("NOT a release approval", source.stdout)

    def test_source_failure_still_stops_source_only(self):
        result, calls = self.invoke("--source-only", fail="tools/check-site.sh")
        self.assertEqual(result.returncode, 19)
        self.assertNotIn("tools/check-rewind.sh", calls)
        self.assertNotIn("developer checks passed", result.stdout)

    def test_artifact_conflict_fails_before_any_check(self):
        for args in (("--source-only", "--artifacts"), ("--artifacts", "--source-only")):
            with self.subTest(args=args):
                result, calls = self.invoke(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])

    def test_optional_package_resolution_and_full_artifact_gate_remain(self):
        result, calls = self.invoke("--source-only", "--package-names")
        self.assertEqual(result.returncode, 0)
        self.assertIn("tools/check-package-names.sh", calls)
        self.log.unlink()
        result, calls = self.invoke("--artifacts")
        self.assertEqual(result.returncode, 0)
        self.assertIn("tools/check-generated-source-map.py", calls)
        self.assertIn("tools/check-artifacts.sh out/week-audit", calls)

    def test_unknown_option_is_not_ignored(self):
        result, calls = self.invoke("--source-onyl")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
