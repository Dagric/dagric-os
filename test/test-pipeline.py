#!/usr/bin/env python3
"""Regression tests for Dagric Adaptive Pipeline's safety boundary."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "config/includes.chroot/usr/lib/dagric"))
SPEC = importlib.util.spec_from_file_location(
    "dagric_pipeline", REPO / "config/includes.chroot/usr/lib/dagric/pipeline.py"
)
assert SPEC and SPEC.loader
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.write("/proc/meminfo", "MemTotal:        8388608 kB\nMemAvailable:    4194304 kB\n")
        self.write("/proc/mounts", "/dev/vda2 / btrfs rw,relatime 0 0\n")
        for resource in ("cpu", "memory", "io"):
            self.write(f"/proc/pressure/{resource}", "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")
        self.write("/proc/cpuinfo", "processor : 0\nprocessor : 1\nprocessor : 2\nprocessor : 3\n")
        self.write("/sys/kernel/mm/lru_gen/enabled", "0x7\n")
        self.write("/sys/fs/cgroup/cgroup.controllers", "cpu io memory\n")
        self.write("/sys/block/zram0/disksize", "4294967296\n")
        self.write("/sys/block/sda/queue/rotational", "1\n")
        self.write("/sys/block/sda/queue/scheduler", "mq-deadline [bfq] none\n")
        self.write("/sys/class/drm/card0/device/vendor", "0x1002\n")
        self.write("/sys/class/net/enp1s0/speed", "2500\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, destination: str, contents: str) -> None:
        target = self.root / destination.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    def test_low_memory_hdd_policy_is_capability_based_and_private(self) -> None:
        profile = pipeline.build_profile(self.root)
        self.assertEqual("low-memory", profile["policy"]["machine_class"])
        self.assertEqual(8, profile["policy"]["launch_prefetch_max_mib"])
        self.assertFalse(profile["policy"]["background_warming"])
        self.assertIn("bfq-for-rotational-via-udev", profile["policy"]["actions"])
        self.assertIn("retain-zram", profile["policy"]["actions"])
        self.assertIn("retain-btrfs-zstd", profile["policy"]["actions"])
        self.assertEqual([], pipeline.audit_profile(profile))
        hardware = profile["hardware"]
        for forbidden in ("serial", "uuid", "mac_address", "edid", "dmi"):
            self.assertNotIn(forbidden, hardware)

    def test_large_nvme_machine_gets_a_different_but_still_safe_policy(self) -> None:
        self.write("/proc/meminfo", "MemTotal:       67108864 kB\nMemAvailable:   33554432 kB\n")
        self.write("/sys/block/sda/queue/rotational", "0\n")
        self.write("/sys/block/nvme0n1/queue/rotational", "0\n")
        self.write("/sys/block/nvme0n1/queue/scheduler", "[none] mq-deadline\n")
        profile = pipeline.build_profile(self.root)
        self.assertEqual("high-memory", profile["policy"]["machine_class"])
        self.assertEqual(64, profile["policy"]["launch_prefetch_max_mib"])
        self.assertNotIn("bfq-for-rotational-via-udev", profile["policy"]["actions"])
        self.assertIn("keep-ssd-kernel-default", profile["policy"]["actions"])

    def test_atom_n450_class_gets_conservative_profile(self) -> None:
        self.write("/proc/meminfo", "MemTotal:        1572864 kB\nMemAvailable:    700000 kB\n")
        self.write("/proc/cpuinfo", "processor : 0\nprocessor : 1\nmodel name : Intel(R) Atom(TM) CPU N455 @ 1.66GHz\n")
        profile = pipeline.build_profile(self.root)
        policy = profile["policy"]
        self.assertEqual("atom-low-resource", policy["machine_class"])
        self.assertEqual(2, policy["launch_prefetch_max_mib"])
        self.assertTrue(policy["low_resource"]["enabled"])
        self.assertIn("atom-low-resource-profile", policy["actions"])
        self.assertEqual([], pipeline.audit_profile(profile))

    def test_unsafe_or_identifying_profile_is_rejected(self) -> None:
        profile = pipeline.build_profile(self.root)
        profile["policy"]["experimental"]["sched_ext"] = True
        profile["hardware"]["serial"] = "do-not-store-this"
        errors = pipeline.audit_profile(profile)
        self.assertTrue(any("experimental" in item for item in errors))
        self.assertTrue(any("privacy" in item for item in errors))

    def test_pressure_fails_closed(self) -> None:
        policy = pipeline.compile_policy(pipeline.hardware_projection(self.root))
        self.assertTrue(pipeline.system_pressure_ok(self.root, policy["pressure_limits_avg10"]))
        self.write("/proc/pressure/io", "some avg10=17.50 avg60=3.00 avg300=1.00 total=0\n")
        self.assertFalse(pipeline.system_pressure_ok(self.root, policy["pressure_limits_avg10"]))

    def test_prefetch_is_bounded_and_never_reads_file_contents(self) -> None:
        target = self.root / "library.so"
        target.write_bytes(b"x" * 8192)
        with mock.patch.object(pipeline, "allowed_prefetch_path", return_value=True), \
             mock.patch.object(pipeline.os, "posix_fadvise", create=True) as fadvise:
            result = pipeline.prefetch([str(target)], 1)
        self.assertEqual(1, result["files"])
        self.assertEqual(8192, result["bytes"])
        fadvise.assert_called_once()

    def test_launch_profiles_reject_home_paths(self) -> None:
        profile = self.root / "launches.json"
        profile.write_text(json.dumps({"files": ["/usr/lib/libok.so", "/home/alice/private.db"]}), encoding="utf-8")
        self.assertEqual(["/usr/lib/libok.so"], pipeline.load_launch_profile(profile))


if __name__ == "__main__":
    unittest.main()
