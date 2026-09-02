#!/usr/bin/env python3
"""Unit tests for Dagric Update's no-removal, configuration-preserving contract."""

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "config/includes.chroot/usr/lib/dagric/update_core.py"
SPEC = importlib.util.spec_from_file_location("update_core", MODULE)
update = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = update
SPEC.loader.exec_module(update)


class PlanTests(unittest.TestCase):
    def test_parses_all_relevant_apt_sections(self):
        text = """The following packages will be upgraded:
 dagric-tools linux-image-amd64
The following NEW packages will be installed:
 firmware-example
The following packages have been kept back:
 mesa-vulkan-drivers

2 upgraded, 1 newly installed, 0 to remove and 1 not upgraded.
"""
        plan = update.parse_plan(text)
        self.assertEqual(("dagric-tools", "linux-image-amd64"), plan.upgraded)
        self.assertEqual(("firmware-example",), plan.installed)
        self.assertEqual(("mesa-vulkan-drivers",), plan.held_back)
        self.assertFalse(plan.removed)
        self.assertEqual(3, plan.changes)

    def test_detects_a_removal_even_when_apt_only_gives_a_summary(self):
        plan = update.parse_plan("0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.\n")
        self.assertEqual(2, plan.summary_removed)

    def test_does_not_treat_versions_as_package_names(self):
        plan = update.parse_plan("""The following packages will be upgraded:
 dagric-tools (1.1.14 => 1.1.15)

1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
""")
        self.assertEqual(("dagric-tools",), plan.upgraded)


class CommandContractTests(unittest.TestCase):
    def test_install_command_cannot_become_a_removal_capable_upgrade(self):
        for command in (update.safe_upgrade_command(), update.safe_upgrade_command(download_only=True)):
            self.assertIn("upgrade", command)
            self.assertIn("--with-new-pkgs", command)
            self.assertIn("--yes", command)
            self.assertNotIn("full-upgrade", command)
            self.assertNotIn("dist-upgrade", command)
            self.assertNotIn("autoremove", command)
            self.assertIn("Dpkg::Options::=--force-confold", command)

    def test_simulation_has_no_configuration_or_mutating_flags(self):
        command = update.safe_upgrade_command(simulate=True)
        self.assertIn("--simulate", command)
        self.assertNotIn("--yes", command)
        self.assertNotIn("--download-only", command)
        self.assertNotIn("Dpkg::Options::=--force-confold", command)


if __name__ == "__main__":
    unittest.main()
