#!/usr/bin/env python3
"""Regression tests for Dagric Twin's proof and rollback boundary."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest
import stat


REPO = pathlib.Path(__file__).resolve().parents[1]
LIB = REPO / "config/includes.chroot/usr/lib/dagric"
sys.path.insert(0, str(LIB))
SPEC = importlib.util.spec_from_file_location("dagric_twin", LIB / "twin.py")
assert SPEC and SPEC.loader
twin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(twin)


def sample(mode: str, wall_ms: float, pressure: float = 0.0) -> dict[str, object]:
    values = {"cpu": pressure, "memory": pressure, "io": pressure}
    return {"mode": mode, "wall_ms": wall_ms, "exit_code": 0, "pressure_before": values, "pressure_after": values, "at": 1}


class TwinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.write("/proc/meminfo", "MemTotal: 16777216 kB\n")
        self.write("/proc/cpuinfo", "processor : 0\n")
        self.write("/proc/mounts", "/dev/vda / ext4 rw 0 0\n")
        for resource in ("cpu", "memory", "io"):
            self.write(f"/proc/pressure/{resource}", "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, destination: str, contents: str) -> None:
        target = self.root / destination.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    def entry(self) -> dict[str, object]:
        state = twin.empty_state()
        return twin.application_entry(state, "a" * 32, self.root)

    def test_local_evidence_retains_only_material_improvement(self) -> None:
        entry = self.entry()
        entry["trials"] = [sample("baseline", 100.0) for _ in range(5)] + [sample("canary", 80.0) for _ in range(5)]
        decision = twin.evaluate_entry(entry, timestamp=100)
        self.assertEqual("retained", decision["state"])
        self.assertGreater(decision["confidence"], 0.0)
        self.assertEqual(100 + twin.RETAIN_SECONDS, decision["expires_at"])

    def test_regression_quarantines_and_expiry_returns_to_shadow(self) -> None:
        entry = self.entry()
        entry["trials"] = [sample("baseline", 100.0) for _ in range(5)] + [sample("canary", 103.0) for _ in range(5)]
        decision = twin.evaluate_entry(entry, timestamp=200)
        self.assertEqual("quarantined", decision["state"])
        twin.expire(entry, timestamp=200 + twin.QUARANTINE_SECONDS)
        self.assertEqual("shadow", entry["decision"]["state"])

    def test_pressure_regression_is_not_retained_even_when_faster(self) -> None:
        entry = self.entry()
        entry["trials"] = [sample("baseline", 100.0, 0.0) for _ in range(5)] + [sample("canary", 80.0, 1.0) for _ in range(5)]
        self.assertEqual("quarantined", twin.evaluate_entry(entry, timestamp=300)["state"])

    def test_contract_and_state_reject_privacy_data_and_background_work(self) -> None:
        state = twin.empty_state()
        state["serial"] = "not-allowed"
        self.assertTrue(any("privacy" in item for item in twin.audit_state(state)))
        entry = self.entry()
        self.assertFalse(entry["contract"]["safety_limits"]["background_warming"])
        self.assertEqual(twin.POLICY_ID, entry["contract"]["policy_id"])

    def test_insufficient_evidence_stays_shadow_only(self) -> None:
        entry = self.entry()
        entry["trials"] = [sample("baseline", 100.0), sample("canary", 50.0)]
        self.assertEqual("shadow", twin.evaluate_entry(entry, timestamp=400)["state"])

    def test_state_is_owner_only(self) -> None:
        target = self.root / "private" / "trials.json"
        twin.save_state(twin.empty_state(), target)
        self.assertEqual(0o700, stat.S_IMODE(target.parent.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))


if __name__ == "__main__":
    unittest.main()
