#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tarfile
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "config/includes.chroot/usr/lib/dagric/trust.py"
SPEC = importlib.util.spec_from_file_location("dagric_trust", MODULE)
assert SPEC and SPEC.loader
trust = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trust)


class TrustLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base / "root"
        self.state_home = self.base / "state-home"
        self.write("etc/os-release", 'PRETTY_NAME="Dagric OS"\nVERSION_ID="1.0"\n')
        self.write("proc/cpuinfo", "processor : 0\nmodel name : Test CPU\nprocessor : 1\nmodel name : Test CPU\n")
        self.write("proc/meminfo", "MemTotal:       8388608 kB\n")
        self.write("proc/mounts", "/dev/test / btrfs rw,compress=zstd 0 0\n")
        self.write("proc/sys/kernel/osrelease", "6.12-test\n")
        self.write("etc/snapper/configs/root", "SUBVOLUME=/\n")
        self.write("usr/bin/snapper", "")
        self.write("usr/bin/btrfs", "")
        self.write("sys/class/drm/card0/device/uevent", "DRIVER=amdgpu\nPCI_ID=1002:1234\n")
        secure = self.root / "sys/firmware/efi/efivars/SecureBoot-test"
        secure.parent.mkdir(parents=True, exist_ok=True)
        secure.write_bytes(b"\x07\x00\x00\x00\x01")
        self.write("var/lib/dagric/pipeline/profile.json", json.dumps({
            "schema": 1,
            "generated_at": "2026-09-02T12:00:00Z",
            "actions": ["retain-btrfs-zstd", "enable-bounded-launch-prefetch"],
        }))
        self.write("var/lib/dagric/rewind/history.jsonl", json.dumps({
            "finishedAt": "2026-09-02T12:30:00Z", "preset": "software"
        }) + "\n")
        twin = self.state_home / ".local/state/dagric/twin/state.json"
        twin.parent.mkdir(parents=True, exist_ok=True)
        twin.write_text(json.dumps({
            "schema": 1,
            "applications": {"0" * 32: {"decision": {"state": "retained", "at": 1788350400}}},
        }), encoding="utf-8")
        kup = self.state_home / ".config/kup/kupsettings.xml"
        kup.parent.mkdir(parents=True, exist_ok=True)
        kup.write_text("<kup/>\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_report_is_honest_and_privacy_safe(self) -> None:
        report = trust.build_report(self.root, self.state_home)
        self.assertEqual(report["protection"]["restore_points"], "ready")
        self.assertIn("restore not yet verified", report["protection"]["personal_backup"])
        self.assertEqual(report["hardware_passport"]["cpu"]["lab_rating"], "not evaluated")
        self.assertEqual(len(report["history"]), 3)
        self.assertEqual(trust.privacy_errors(report), [])
        raw = json.dumps(report)
        self.assertNotIn(str(self.base), raw)
        self.assertNotIn("0" * 32, raw)

    def test_support_archive_contains_only_preview_and_report(self) -> None:
        report = trust.build_report(self.root, self.state_home)
        target = self.base / "support.tar.gz"
        trust.export_report(report, target)
        # Windows/NTFS synthesizes POSIX mode bits. Dagric runs this code on
        # Linux, where the O_EXCL create mode is a meaningful security gate.
        if os.name == "posix":
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        with tarfile.open(target, "r:gz") as archive:
            self.assertEqual(
                sorted(archive.getnames()),
                ["dagric-support/README.txt", "dagric-support/report.json"],
            )
            payload = json.load(archive.extractfile("dagric-support/report.json"))
        self.assertEqual(trust.privacy_errors(payload), [])
        with self.assertRaisesRegex(ValueError, "will not overwrite"):
            trust.export_report(report, target)

    def test_sensitive_cpu_label_is_withheld(self) -> None:
        self.write("proc/cpuinfo", "processor : 0\nmodel name : /home/alice/private\n")
        report = trust.build_report(self.root, self.state_home)
        self.assertEqual(report["hardware_passport"]["cpu"]["model"], "Detected (details withheld)")
        self.assertEqual(trust.privacy_errors(report), [])

    def test_privacy_audit_rejects_identifiers(self) -> None:
        self.assertTrue(trust.privacy_errors({"hostname": "gaming-pc"}))
        self.assertTrue(trust.privacy_errors({"note": "alice@example.com"}))
        self.assertTrue(trust.privacy_errors({"note": "aa:bb:cc:dd:ee:ff"}))


if __name__ == "__main__":
    unittest.main()
