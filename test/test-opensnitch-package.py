#!/usr/bin/env python3
"""Exercise actual dpkg diversions inside a disposable, unmounted chroot.

Run with sudo on Debian/Ubuntu. Fixtures contain synthetic package payloads and
the repository's actual preinst/postrm, not the full operating system. No host
package database, service, diversion or configuration file is modified.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "packages/dagric-tools/DEBIAN"
INCLUDES = REPO / "config/includes.chroot"
MANAGED_DROPIN = "usr/lib/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf"
WRAPPER = "usr/bin/opensnitch-ui"
UPSTREAM = "usr/lib/dagric/opensnitch-ui-upstream"
MANAGED_ADDRESS = "unix:///run/dagric-opensnitch/osui.sock"
VENDOR_ADDRESS = "unix:///tmp/osui.sock"
ROOT_TESTS = os.name == "posix" and os.geteuid() == 0 and all(shutil.which(name) for name in ("dpkg", "dpkg-deb", "dpkg-divert", "ldd"))


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


class SourceLayoutTests(unittest.TestCase):
    def test_new_service_wiring_is_removed_with_package_not_preserved_as_conffile(self):
        self.assertTrue((INCLUDES / MANAGED_DROPIN).is_file())
        self.assertFalse((INCLUDES / "etc/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf").exists())
        self.assertNotIn("20-dagric-control-socket.conf", (PACKAGE / "conffiles").read_text())


@unittest.skipUnless(ROOT_TESTS, "Run with sudo on Debian/Ubuntu for actual isolated dpkg lifecycle tests")
class DiversionLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_temp = tempfile.TemporaryDirectory(prefix="dagric-diversion-template-")
        cls.template = Path(cls.template_temp.name)
        # Copy only trusted system tools needed by maintainer scripts and their
        # dynamic-loader dependencies. The fixture has no mounts or network.
        for name in ("sh", "install", "dpkg", "dpkg-divert", "rm", "mkdir", "grep", "cp", "mv", "stat", "id", "readlink", "dirname"):
            source = Path(shutil.which(name))
            cls.copy_binary(source, cls.template)
        # A stable /bin/sh independent of Debian's merged-/usr symlinks.
        cls.copy_binary(Path("/bin/sh"), cls.template)
        for relative in ("usr/lib", "usr/bin", "var/lib/dpkg/updates", "var/lib/dpkg/info", "etc", "tmp"):
            (cls.template / relative).mkdir(parents=True, exist_ok=True)
        (cls.template / "tmp").chmod(0o1777)
        write(cls.template / "var/lib/dpkg/status", "")

    @classmethod
    def tearDownClass(cls):
        cls.template_temp.cleanup()

    @staticmethod
    def copy_binary(source, destination):
        target = destination / str(source).lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source.resolve(), target)
        result = subprocess.run(["ldd", str(source)], capture_output=True, text=True, check=False)
        for path in re.findall(r"(?:=>\s*)?(/[^\s]+)", result.stdout):
            library = Path(path)
            if library.is_file():
                output = destination / path.lstrip("/")
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(library.resolve(), output)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dagric-diversion-test-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "root"
        shutil.copytree(self.template, self.root)
        # /tmp may be nodev. A private disposable regular sink is sufficient
        # for these scripts' diagnostic redirects; no device mount is needed.
        write(self.root / "dev/null", "", 0o666)
        self.package_index = 0

    def python_in_fixture(self):
        self.copy_binary(Path("/usr/bin/python3"), self.root)
        # Copy the interpreter's actual standard library, not the test host's
        # optional site-packages or user configuration.
        version = subprocess.run(["/usr/bin/python3", "-c", "import sys;print('%s.%s' % sys.version_info[:2])"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        source = Path("/usr/lib") / ("python" + version)
        target = self.root / source.relative_to("/")
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "test", "tests"), dirs_exist_ok=True)

    def run_dpkg(self, *arguments, success=True):
        command = ["dpkg", "--root=" + str(self.root), *map(str, arguments)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, "Failure injection unexpectedly succeeded")
        return result

    def build_package(self, *, vendor=False, version="1.1.19", wrapper=True, fail_preinst=False):
        self.package_index += 1
        root = self.work / ("package-%d" % self.package_index)
        name = "python3-opensnitch-ui" if vendor else "dagric-tools"
        write(root / "DEBIAN/control", "Package: %s\nVersion: %s\nArchitecture: all\nMaintainer: Dagric Test <test@example.invalid>\nDescription: isolated lifecycle fixture\n" % (name, version))
        if vendor:
            write(root / WRAPPER, "#!/bin/sh\nprintf 'vendor-ui-%s\\n'\n" % version, 0o755)
        elif wrapper:
            write(root / WRAPPER, (INCLUDES / WRAPPER).read_text(), 0o755)
            write(root / MANAGED_DROPIN, (INCLUDES / MANAGED_DROPIN).read_text())
            write(root / "usr/lib/tmpfiles.d/dagric-opensnitch.conf", (INCLUDES / "usr/lib/tmpfiles.d/dagric-opensnitch.conf").read_text())
            preinst = (PACKAGE / "preinst").read_text()
            if fail_preinst:
                # Fail after the real preinst has done its work, so dpkg itself
                # invokes the new postrm abort-install/abort-upgrade path.
                location = preinst.rfind("exit 0")
                self.assertGreater(location, 0)
                preinst = preinst[:location] + "exit 99" + preinst[location + len("exit 0"):]
            write(root / "DEBIAN/preinst", preinst, 0o755)
            write(root / "DEBIAN/postrm", (PACKAGE / "postrm").read_text(), 0o755)
        else:
            write(root / "usr/share/dagric/pre-wrapper-fixture", "old tools package\n")
        output = self.work / ("fixture-%d.deb" % self.package_index)
        result = subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(output)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return output

    def diversion_owner(self):
        result = subprocess.run(["dpkg-divert", "--root=" + str(self.root), "--listpackage", "/" + WRAPPER],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def record_service_calls(self):
        (self.root / "run/systemd/system").mkdir(parents=True)
        write(self.root / "usr/bin/systemctl",
              '#!/bin/sh\nprintf "%s\\n" "$*" >> /systemctl.calls\n', 0o755)
        return self.root / "systemctl.calls"

    def assert_wrapper_installed(self):
        self.assertEqual(self.diversion_owner(), "dagric-tools")
        self.assertEqual((self.root / WRAPPER).read_text(), (INCLUDES / WRAPPER).read_text())
        self.assertTrue((self.root / MANAGED_DROPIN).is_file())

    def test_fresh_install_vendor_upgrade_remove_and_reinstall(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        tools = self.build_package()
        self.run_dpkg("--install", tools)
        self.assert_wrapper_installed()
        self.assertIn("vendor-ui-1.0", (self.root / UPSTREAM).read_text())
        self.run_dpkg("--install", self.build_package(vendor=True, version="2.0"))
        self.assert_wrapper_installed()
        self.assertIn("vendor-ui-2.0", (self.root / UPSTREAM).read_text())
        self.run_dpkg("--remove", "dagric-tools")
        self.assertEqual(self.diversion_owner(), "")
        self.assertFalse((self.root / MANAGED_DROPIN).exists())
        self.assertFalse((self.root / "usr/lib/tmpfiles.d/dagric-opensnitch.conf").exists())
        self.assertIn("vendor-ui-2.0", (self.root / WRAPPER).read_text())
        self.run_dpkg("--install", tools)
        self.assert_wrapper_installed()
        self.run_dpkg("--purge", "dagric-tools")
        self.assertEqual(self.diversion_owner(), "")
        self.assertIn("vendor-ui-2.0", (self.root / WRAPPER).read_text())

    def test_tools_can_precede_vendor_on_free_to_pro_transition(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package())
        self.assert_wrapper_installed()
        self.assertFalse((self.root / UPSTREAM).exists())
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.assert_wrapper_installed()
        self.assertIn("vendor-ui-1.0", (self.root / UPSTREAM).read_text())

    def test_first_diversion_upgrade_abort_restores_pre_wrapper_state(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package(version="1.1.18", wrapper=False))
        result = self.run_dpkg("--install", self.build_package(fail_preinst=True), success=False)
        self.assertIn("99", result.stderr)
        self.assertEqual(self.diversion_owner(), "")
        self.assertIn("vendor-ui-1.0", (self.root / WRAPPER).read_text())
        self.assertFalse((self.root / MANAGED_DROPIN).exists())

    def test_abort_never_changes_existing_service_or_managed_configuration(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        calls = self.record_service_calls()
        config = self.root / "etc/opensnitchd/default-config.json"
        original = json.dumps({"Server": {"Address": MANAGED_ADDRESS}, "DefaultAction": "deny"})
        write(config, original)
        # Neither failed initial installation nor a first-diversion upgrade
        # rollback may stop a firewall that was already running beforehand.
        self.run_dpkg("--install", self.build_package(fail_preinst=True), success=False)
        self.assertFalse(calls.exists(), calls.read_text() if calls.exists() else "")
        self.assertEqual(config.read_text(), original)
        self.run_dpkg("--install", self.build_package(version="1.1.18", wrapper=False))
        self.run_dpkg("--install", self.build_package(fail_preinst=True), success=False)
        self.assertFalse(calls.exists(), calls.read_text() if calls.exists() else "")
        self.assertEqual(config.read_text(), original)
        self.assertEqual(self.diversion_owner(), "")

    def test_successful_removal_stops_and_reloads_but_never_restarts_firewall(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package())
        calls = self.record_service_calls()
        self.run_dpkg("--remove", "dagric-tools")
        self.assertEqual(calls.read_text().splitlines(), ["stop opensnitch.service", "daemon-reload"])
        self.assertEqual(self.diversion_owner(), "")
        self.assertFalse((self.root / MANAGED_DROPIN).exists())

    def test_repeated_wrapper_upgrade_and_later_abort_retain_diversion(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package())
        self.run_dpkg("--install", self.build_package(version="1.1.20"))
        self.assert_wrapper_installed()
        self.run_dpkg("--install", self.build_package(version="1.1.21", fail_preinst=True), success=False)
        self.assert_wrapper_installed()
        self.assertIn("vendor-ui-1.0", (self.root / UPSTREAM).read_text())

    def test_failed_initial_install_restores_vendor(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package(fail_preinst=True), success=False)
        self.assertEqual(self.diversion_owner(), "")
        self.assertIn("vendor-ui-1.0", (self.root / WRAPPER).read_text())

    def test_no_python_is_required_before_unpack_or_after_removal(self):
        # python3 is Depends, not Essential. Maintainer scripts must not require
        # it before unpack or after dependency removal.
        self.assertFalse((self.root / "usr/bin/python3").exists())
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package())
        self.assert_wrapper_installed()
        self.run_dpkg("--remove", "dagric-tools")
        self.assertEqual(self.diversion_owner(), "")

    def test_removal_restores_only_managed_daemon_address(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        self.run_dpkg("--install", self.build_package())
        config = self.root / "etc/opensnitchd/default-config.json"
        document = {"Server": {"Address": MANAGED_ADDRESS, "Other": "keep"}, "DefaultAction": "deny"}
        write(config, json.dumps(document))
        result = self.run_dpkg("--remove", "dagric-tools")
        document["Server"]["Address"] = VENDOR_ADDRESS
        self.assertEqual(json.loads(config.read_text()), document, result.stdout + result.stderr)

    def test_conflicting_administrator_diversion_is_preserved(self):
        self.python_in_fixture()
        self.run_dpkg("--install", self.build_package(vendor=True, version="1.0"))
        subprocess.run(["dpkg-divert", "--root=" + str(self.root), "--local", "--add", "--rename",
                        "--divert", "/usr/bin/opensnitch-ui.admin", "/" + WRAPPER],
                       check=True, capture_output=True)
        self.run_dpkg("--install", self.build_package(), success=False)
        self.assertEqual(self.diversion_owner(), "LOCAL")
        self.assertIn("vendor-ui-1.0", (self.root / "usr/bin/opensnitch-ui.admin").read_text())


if __name__ == "__main__":
    unittest.main()
