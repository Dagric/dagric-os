#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "config/includes.chroot/usr/lib/dagric/foundations.py"
SPEC = importlib.util.spec_from_file_location("dagric_foundations", MODULE)
assert SPEC and SPEC.loader
foundations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(foundations)


class FoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base / "root"
        self.home = self.base / "home"
        self.state = self.base / "blackbox"
        self.write("etc/dagric-channel", "preview\n")
        self.write(
            "var/lib/dpkg/status",
            "Package: steam-installer\nStatus: install ok installed\nMaintainer: Alice <alice@example.com>\n\n"
            "Package: firefox-esr\nStatus: install ok installed\n\n"
            "Package: removed-package\nStatus: deinstall ok config-files\n",
        )
        self.write("proc/uptime", "321.5 200.0\n")
        for resource, value in (("cpu", 1.2), ("memory", 0.0), ("io", 2.5)):
            self.write(
                f"proc/pressure/{resource}",
                f"some avg10={value:.2f} avg60=0.50 avg300=0.10 total=1\n",
            )
        self.write("proc/mounts", "/dev/test / btrfs rw,compress=zstd 0 0\n")
        kde = self.home / ".config/kdeglobals"
        kde.parent.mkdir(parents=True, exist_ok=True)
        kde.write_text("[General]\nColorScheme=DagricDark\n[KDE]\nAnimationDurationFactor=0\n", encoding="utf-8")
        (self.home / ".local/share/flatpak/app/org.kde.krita").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_blueprint_is_private_declarative_and_non_destructive(self) -> None:
        blueprint = foundations.build_blueprint(self.root, self.home)
        self.assertEqual(foundations.validate_blueprint(blueprint), [])
        self.assertEqual(blueprint["system"]["channel"], "preview")
        self.assertEqual(blueprint["system"]["appearance"], "obsidian")
        self.assertTrue(blueprint["user_preferences"]["reduced_motion"])
        self.assertEqual(blueprint["applications"]["debian_packages"], ["firefox-esr", "steam-installer"])
        raw = json.dumps(blueprint)
        self.assertNotIn("alice@example.com", raw)
        self.assertNotIn(str(self.base), raw)
        plan = foundations.blueprint_plan(blueprint, blueprint)
        self.assertFalse(plan["apply_available"])
        self.assertEqual(plan["destructive_actions"], [])

    def test_blueprint_export_refuses_overwrite_and_uses_private_mode(self) -> None:
        target = self.base / "blueprint.json"
        blueprint = foundations.build_blueprint(self.root, self.home)
        foundations.write_json_exclusive(target, blueprint)
        if os.name == "posix":
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(ValueError, "will not overwrite"):
            foundations.write_json_exclusive(target, blueprint)

    def test_blueprint_rejects_hidden_payloads_and_relaxed_boundaries(self) -> None:
        blueprint = foundations.build_blueprint(self.root, self.home)
        attacks = []
        unknown_nested = copy.deepcopy(blueprint)
        unknown_nested["hardware_policies"]["post_install_command"] = "curl bad.example"
        attacks.append(unknown_nested)
        secret = copy.deepcopy(blueprint)
        secret["user_preferences"]["token"] = "secret-value"
        attacks.append(secret)
        changed_omissions = copy.deepcopy(blueprint)
        changed_omissions["omitted"] = []
        attacks.append(changed_omissions)
        invalid_package = copy.deepcopy(blueprint)
        invalid_package["applications"]["debian_packages"] = ["../../escape"]
        attacks.append(invalid_package)
        for attack in attacks:
            self.assertTrue(foundations.validate_blueprint(attack), attack)

    def test_blackbox_accepts_only_typed_bounded_events(self) -> None:
        timestamp = 1_800_000_000.0
        event = foundations.pressure_event(self.root, timestamp)
        self.assertEqual(foundations.validate_event(event), [])
        self.assertEqual(foundations.append_event(event, self.state, timestamp), 1)
        status = foundations.blackbox_status(self.state)
        self.assertFalse(status["network_upload"])
        self.assertFalse(status["content_collection"])
        malicious = dict(event, command="cat /home/alice/private")
        with self.assertRaises(ValueError):
            foundations.append_event(malicious, self.state, timestamp)
        with self.assertRaises(ValueError):
            foundations.mark_event("arbitrary_note")

    def test_blackbox_retention_and_ring_cap(self) -> None:
        now = 1_800_000_000.0
        rows = [foundations.pressure_event(self.root, now - 8 * 24 * 60 * 60)]
        rows.append(foundations.mark_event("update_started", now - 16 * 60))
        rows.extend(foundations.pressure_event(self.root, now - index) for index in range(2100))
        kept = foundations.prune_events(rows, now)
        self.assertEqual(len(kept), foundations.BLACKBOX_MAX_EVENTS)
        self.assertNotIn(rows[0], kept)
        self.assertNotIn(rows[1], kept)

    def test_life_support_is_read_only_and_explains_limits(self) -> None:
        self.write("proc/mounts", "/dev/test / btrfs ro 0 0\n")
        pressure = foundations.pressure_event(self.root, 1_800_000_000.0)
        pressure["pressure"]["io"]["avg10"] = 25.0
        report = foundations.assess_life_support(self.root, free_percent=1.0, events=[pressure])
        self.assertEqual(report["state"], "critical")
        self.assertFalse(report["automatic_changes_applied"])
        codes = {item["code"] for item in report["findings"]}
        self.assertTrue({"root-read-only", "storage-exhausted", "io-pressure-critical"} <= codes)
        self.assertIn("physical validation", report["limitations"])


if __name__ == "__main__":
    unittest.main()
