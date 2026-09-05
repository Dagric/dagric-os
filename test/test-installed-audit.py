#!/usr/bin/env python3
"""Run the actual installed-audit shell helpers with offline command fixtures.

These are acceptance-checker regressions, not installed-system or VM evidence.
The full audit is exercised only on preflight-refusal paths; no daemon is
started, guest touched, mount changed, or real package database queried.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "test/installed-audit.sh").read_text(encoding="utf-8")
HELPERS = SCRIPT.split("# BEGIN INSTALLED AUDIT HELPERS", 1)[1].split(
    "# END INSTALLED AUDIT HELPERS.", 1)[0]
# The marker carries a comment on the same line, not executable shell text.
HELPERS = HELPERS.split("\n", 1)[1]
DPKG = shutil.which("dpkg")
COUNTERS = """PASS=0; FAIL=0; SKIP=0
pass() { PASS=$((PASS + 1)); printf '[PASS] %s\\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf '[FAIL] %s\\n' "$1"; }
"""
MOCK = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
data = json.loads(Path(os.environ['DAGRIC_AUDIT_FIXTURE']).read_text())
with Path(os.environ['DAGRIC_AUDIT_CALLS']).open('a') as stream:
    stream.write(json.dumps([name] + sys.argv[1:]) + '\\n')
key = name
if name == 'dpkg-query':
    key = 'inventory' if len(sys.argv) == 3 else 'package:' + sys.argv[-1]
elif name == 'systemctl' and sys.argv[1] == 'show':
    key = 'unit:' + sys.argv[-1]
elif name == 'cat':
    key = 'cat:' + sys.argv[-1]
response = data.get(key, data.get(name))
if response is None:
    sys.stderr.write('Unexpected mock command: ' + repr(sys.argv) + '\\n')
    sys.exit(99)
sys.stdout.write(response.get('stdout', ''))
sys.stderr.write(response.get('stderr', ''))
sys.exit(response.get('status', 0))
"""


def output(text="", status=0, stderr=""):
    return {"stdout": text, "status": status, "stderr": stderr}


def unit(enable="disabled", active="inactive", sub="dead", load="loaded", triggers=""):
    return output(f"LoadState={load}\nUnitFileState={enable}\nActiveState={active}\n"
                  f"SubState={sub}\nTriggeredBy={triggers}\n")


@unittest.skipUnless(shutil.which("sh"), "POSIX shell is required")
class InstalledAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dagric-installed-audit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        mock_bin = self.directory / "bin"
        mock_bin.mkdir()
        for name in ("dpkg-query", "dpkg", "systemctl", "id", "findmnt", "mountpoint", "cat"):
            path = mock_bin / name
            path.write_text(MOCK, encoding="utf-8")
            path.chmod(0o700)
        self.fixture = self.directory / "fixture.json"
        self.calls = self.directory / "calls.jsonl"
        self.environment = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ["PATH"],
                                DAGRIC_AUDIT_FIXTURE=str(self.fixture), DAGRIC_AUDIT_CALLS=str(self.calls))
        self.data = {"dpkg-query": output("installed\n"), "dpkg": output(), "id": output("0\n"),
                     "cat:/proc/cmdline": output("BOOT_IMAGE=/vmlinuz root=UUID=test ro quiet\n"),
                     "findmnt": output("btrfs\n"), "mountpoint": output(status=1)}

    def run_helper(self, invocation, edition="free", setup=""):
        self.fixture.write_text(json.dumps(self.data), encoding="utf-8")
        return subprocess.run(["sh", "-c", "set -eu\n" + COUNTERS + HELPERS +
                               "\nEXPECTED_EDITION=" + edition + "\n" + setup + "\n" + invocation],
                              env=self.environment, capture_output=True, text=True, check=False)

    def assert_pass(self, invocation, **kwargs):
        result = self.run_helper(invocation, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def assert_fail(self, invocation, **kwargs):
        result = self.run_helper(invocation, **kwargs)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_core_package_query_accepts_multiarch_but_not_query_failure(self):
        self.data["dpkg-query"] = output("installed\ninstalled\n")
        self.assert_pass("has_pkg mangohud")
        self.data["dpkg-query"] = output("installed\n", status=2)
        self.assert_fail("has_pkg mangohud")
        self.data["dpkg-query"] = output("config-files\n")
        self.assert_fail("has_pkg dagric-tools")

    def test_free_exclusion_requires_successful_valid_inventory(self):
        for response in (output(status=2), output(), output("database unavailable\n"),
                         output("opensnitch\tunknown\n"), output("opensnitch\tinstalled\n", status=2)):
            with self.subTest(response=response):
                self.data["inventory"] = response
                self.assert_fail("lacks_pkg opensnitch")
        self.data["inventory"] = output("dagric-tools\tinstalled\nopensnitch\tconfig-files\n")
        self.assert_pass("lacks_pkg opensnitch")
        for package in ("opensnitch", "opensnitch:amd64", "opensnitch:i386"):
            self.data["inventory"] = output(package + "\tinstalled\n")
            self.assert_fail("lacks_pkg opensnitch")

    def test_clean_dpkg_verification_requires_every_core_package(self):
        self.assertIn("Dagric packages verify with dpkg", self.assert_pass("audit_package_integrity").stdout)
        for package in ("dagric-branding", "dagric-desktop-defaults", "dagric-security-policy", "dagric-tools"):
            with self.subTest(package=package):
                self.data["package:" + package] = output(status=1)
                result = self.assert_fail("audit_package_integrity")
                self.assertIn("missing or its state could not be read", result.stdout)
                self.assertNotIn("packages verify with dpkg", result.stdout)
                del self.data["package:" + package]

    def test_verifier_error_never_becomes_empty_success(self):
        for response in (output(status=1), output(status=2),
                         output(stderr="dpkg: database unavailable\n", status=2),
                         output(stderr="dpkg: warning: verification incomplete\n")):
            with self.subTest(response=response):
                self.data["dpkg"] = response
                result = self.assert_fail("audit_package_integrity")
                self.assertIn("[FAIL]", result.stdout)
                self.assertNotIn("packages verify with dpkg", result.stdout)

    def test_free_allows_only_two_exact_launcher_removals(self):
        allowed = ("missing     /usr/share/applications/dagric-usb-protect.desktop\n"
                   "missing     /usr/share/applications/dagric-vm.desktop\n")
        self.data["dpkg"] = output(allowed)
        self.assertIn("two intentional Free", self.assert_pass("audit_package_integrity").stdout)
        for text in (allowed + "??5??????   /usr/bin/dagric-update\n", allowed.replace(".desktop", ".desktop.backup"),
                     allowed.splitlines()[0] + "\n", allowed.replace("missing", "??5??????")):
            self.data["dpkg"] = output(text)
            self.assert_fail("audit_package_integrity")
        self.data["dpkg"] = output(allowed, status=2)
        self.assert_fail("audit_package_integrity")

    def test_pro_requires_exact_md5_diagnostic_and_roundtrip_check(self):
        diagnostic = "??5??????   /usr/share/sddm/themes/dagric/theme.conf\n"
        self.data["dpkg"] = output(diagnostic)
        self.assert_pass("audit_package_integrity", edition="pro",
                         setup="pro_badge_is_only_change() { return 0; }")
        self.assert_fail("audit_package_integrity", edition="pro",
                         setup="pro_badge_is_only_change() { return 1; }")
        for text in (diagnostic.replace("??5??????", "missing"), diagnostic + diagnostic,
                     diagnostic.replace("theme.conf", "theme.conf.backup")):
            self.data["dpkg"] = output(text)
            self.assert_fail("audit_package_integrity", edition="pro",
                             setup="pro_badge_is_only_change() { return 0; }")

    def test_pro_badge_roundtrip_rejects_other_theme_edits(self):
        theme = self.directory / "theme.conf"
        checksums = self.directory / "md5sums"
        original = b"[General]\nbackground=/usr/share/dagric/background.png\neditionBadge=\n"
        digest = hashlib.md5(original, usedforsecurity=False).hexdigest()
        checksums.write_text(digest + "  usr/share/sddm/themes/dagric/theme.conf\n", encoding="utf-8")
        pro = original.replace(b"editionBadge=\n", b"editionBadge=PRO EDITION\n")
        invocation = "pro_badge_is_only_change " + shlex.quote(str(theme)) + " " + shlex.quote(str(checksums))
        theme.write_bytes(pro)
        self.assert_pass(invocation)
        for changed in (pro + b"other=change\n", pro + b"editionBadge=PRO EDITION\n",
                        pro.replace(b"background.png", b"other.png"), original, pro + b"\n"):
            theme.write_bytes(changed)
            self.assert_fail(invocation)
        theme.write_bytes(pro)
        checksums.write_text("", encoding="utf-8")
        self.assert_fail(invocation)
        checksums.unlink()
        self.assert_fail(invocation)

    def test_enablement_and_runtime_are_independent_checks(self):
        self.data["unit:docker.service"] = unit(active="active", sub="running")
        self.assert_pass("is_disabled docker.service")
        self.assert_fail("is_inactive docker.service")
        self.data["unit:docker.service"] = unit(enable="enabled")
        self.assert_fail("is_disabled docker.service")
        self.assert_pass("is_inactive docker.service")
        for enable in ("enabled-runtime", "linked", "alias", "generated", ""):
            self.data["unit:docker.service"] = unit(enable=enable)
            self.assert_fail("is_disabled docker.service")
        for active, sub in (("failed", "failed"), ("activating", "start"), ("inactive", "running")):
            self.data["unit:docker.service"] = unit(active=active, sub=sub)
            self.assert_fail("is_inactive docker.service")

    def test_unreadable_or_incomplete_unit_state_cannot_pass(self):
        for response in (output(status=1), output(), output("LoadState=not-found\n"),
                         output("LoadState=error\nUnitFileState=disabled\nActiveState=inactive\nSubState=dead\n")):
            self.data["unit:docker.service"] = response
            for helper in ("is_disabled", "is_inactive", "triggers_inactive"):
                self.assert_fail(helper + " docker.service")
        self.data["unit:docker.service"] = unit(enable="", load="not-found")
        for helper in ("is_disabled", "is_inactive", "triggers_inactive"):
            self.assert_pass(helper + " docker.service")

    def test_socket_activation_must_be_disabled_and_inactive(self):
        self.data["unit:docker.service"] = unit(triggers="docker.socket other.timer")
        self.data["unit:docker.socket"] = unit()
        self.data["unit:other.timer"] = unit()
        self.assert_pass("triggers_inactive docker.service")
        for response in (unit(enable="enabled"), unit(active="active", sub="listening"), output(status=1)):
            self.data["unit:docker.socket"] = response
            self.assert_fail("triggers_inactive docker.service")
        self.data["unit:docker.socket"] = unit()
        self.data["unit:other.timer"] = unit(active="active", sub="waiting")
        self.assert_fail("triggers_inactive docker.service")

    def test_failed_service_query_failure_is_not_no_failed_services(self):
        self.data["systemctl"] = output()
        self.assert_pass("no_failed_services")
        for response in (output(status=1), output(stderr="Failed to connect to bus\n", status=1),
                         output("bad.service loaded failed failed Bad service\n")):
            self.data["systemctl"] = response
            self.assert_fail("no_failed_services")

    def test_preflight_accepts_installed_root_and_refuses_live_or_unknown(self):
        self.assert_pass("installed_environment")
        for key, response in (("id", output("1000\n")), ("id", output(status=1)),
                              ("cat:/proc/cmdline", output("quiet boot=live components\n")),
                              ("cat:/proc/cmdline", output("boot=casper\n")),
                              ("cat:/proc/cmdline", output(status=1)),
                              ("findmnt", output("overlay\n")), ("findmnt", output("squashfs\n")),
                              ("findmnt", output("tmpfs\n")), ("findmnt", output(status=1)),
                              ("mountpoint", output())):
            with self.subTest(key=key, response=response):
                saved = self.data[key]
                self.data[key] = response
                self.assert_fail("installed_environment")
                self.data[key] = saved

    def test_full_audit_refuses_live_before_any_mutating_command(self):
        self.data["cat:/proc/cmdline"] = output("quiet boot=live\n")
        self.fixture.write_text(json.dumps(self.data), encoding="utf-8")
        result = subprocess.run(["sh", "-c", SCRIPT, "installed-audit.sh", "pro"], env=self.environment,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no installed acceptance checks were run", result.stdout)
        self.assertIn("0 pass, 1 fail, 0 skip", result.stdout)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any(call[0] in ("dpkg", "dpkg-query", "systemctl") for call in calls), calls)

    def test_all_risky_services_receive_each_distinct_check(self):
        block = SCRIPT.split("for unit in docker.service", 1)[1].split("\n    done", 1)[0]
        for name in ("docker.socket", "containerd.service", "libvirtd-ro.socket", "libvirtd-admin.socket",
                     "ssh.service", "sshd.service", "ssh.socket"):
            self.assertIn(name, block)
        for helper in ("is_disabled", "is_inactive", "triggers_inactive"):
            self.assertIn(helper + ' "$unit"', block)
        self.assertIn("audit_package_integrity || :", SCRIPT)
        self.assertIn("not physical Secure Boot", SCRIPT)
        self.assertNotIn("dpkg_verify=$(dpkg", SCRIPT)

    @unittest.skipUnless(DPKG, "dpkg is required for isolated verifier-format evidence")
    def test_real_dpkg_changed_and_missing_formats_in_isolated_database(self):
        # Only these temporary fixture paths are passed to real dpkg. This
        # confirms that successful verification can report changed/missing
        # files on stdout, independently of fatal verifier command errors.
        fixture_root = self.directory / "isolated-root"
        database = fixture_root / "var/lib/dpkg"
        info = database / "info"
        info.mkdir(parents=True)
        (database / "status").write_text(
            "Package: dagric-fixture\nStatus: install ok installed\n"
            "Priority: optional\nSection: misc\nInstalled-Size: 1\n"
            "Maintainer: Test <test@example.invalid>\nArchitecture: all\n"
            "Version: 1\nDescription: Offline verification fixture\n\n", encoding="utf-8")
        fixture_file = fixture_root / "usr/share/dagric-fixture.txt"
        fixture_file.parent.mkdir(parents=True)
        fixture_file.write_bytes(b"original\n")
        digest = hashlib.md5(fixture_file.read_bytes(), usedforsecurity=False).hexdigest()
        (info / "dagric-fixture.md5sums").write_text(digest + "  usr/share/dagric-fixture.txt\n", encoding="utf-8")
        (info / "dagric-fixture.list").write_text("/usr/share/dagric-fixture.txt\n", encoding="utf-8")
        fixture_file.write_bytes(b"changed\n")
        command = [DPKG, "--root=" + str(fixture_root), "--verify", "dagric-fixture"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "??5??????   /usr/share/dagric-fixture.txt\n")
        fixture_file.unlink()
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "missing     /usr/share/dagric-fixture.txt\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
