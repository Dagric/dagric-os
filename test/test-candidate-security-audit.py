#!/usr/bin/env python3
"""Offline regressions for private-candidate Debian security evidence."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import shutil
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("candidate_security", ROOT / "tools/audit-candidate-security.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class CandidateSecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 5, 20, tzinfo=timezone.utc)
        self.release = {"Origin": "Debian", "Codename": "trixie-security",
                        "Date": "Sat, 05 Sep 2026 12:00:00 UTC",
                        "Valid-Until": "Sat, 12 Sep 2026 12:00:00 UTC",
                        "SHA256": "\n" + "a" * 64 + " 4 main/binary-amd64/Packages.xz"}

    def test_valid_release(self):
        result = AUDIT.validate_release(self.release, "trixie-security", self.now)
        self.assertEqual(result["checksums"]["main/binary-amd64/Packages.xz"], ("a" * 64, 4))

    def test_wrong_distribution_rejected(self):
        self.release["Codename"] = "forky"
        with self.assertRaises(ValueError):
            AUDIT.validate_release(self.release, "trixie-security", self.now)

    def test_wrong_origin_rejected(self):
        self.release["Origin"] = "unrelated"
        with self.assertRaises(ValueError):
            AUDIT.validate_release(self.release, "trixie-security", self.now)

    def test_expired_release_rejected(self):
        self.release["Valid-Until"] = "Fri, 04 Sep 2026 12:00:00 UTC"
        with self.assertRaises(ValueError):
            AUDIT.validate_release(self.release, "trixie-security", self.now)

    def test_future_release_rejected(self):
        self.release["Date"] = "Sun, 06 Sep 2026 12:00:00 UTC"
        with self.assertRaises(ValueError):
            AUDIT.validate_release(self.release, "trixie-security", self.now)

    def test_volatile_release_needs_expiry(self):
        del self.release["Valid-Until"]
        with self.assertRaises(ValueError):
            AUDIT.validate_release(self.release, "trixie-security", self.now)

    def test_stable_release_missing_expiry_is_visible(self):
        del self.release["Valid-Until"]
        self.release["Codename"] = "trixie"
        self.assertIsNone(AUDIT.validate_release(self.release, "trixie", self.now)["valid_until"])

    def test_corrupt_index_rejected(self):
        with self.assertRaises(ValueError):
            AUDIT.verify_blob(b"bad", (AUDIT.sha(b"good"), 4))

    def test_valid_index(self):
        AUDIT.verify_blob(b"good", (AUDIT.sha(b"good"), 4))

    def test_duplicate_release_fields_rejected(self):
        with self.assertRaises(ValueError):
            AUDIT.deb822("Codename: trixie\nCodename: sid\n")

    def test_unassigned_and_nodsa_records_are_retained(self):
        tracker = {"cups": {"CVE-TEST": {"releases": {"trixie": {
            "status": "open", "urgency": "not yet assigned", "nodsa": "minor issue",
            "nodsa_reason": "ignored"}}}}}
        result = AUDIT.issue_rows({("cups", "1")}, tracker)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["urgency"], "not yet assigned")
        self.assertEqual(result[0]["nodsa_reason"], "ignored")

    def test_undetermined_records_are_retained(self):
        tracker = {"x": {"CVE-TEST": {"releases": {"trixie": {"status": "undetermined"}}}}}
        self.assertEqual(len(AUDIT.issue_rows({("x", "1")}, tracker)), 1)

    def test_sid_fix_is_not_a_stable_fix(self):
        tracker = {"x": {"CVE-TEST": {"releases": {
            "trixie": {"status": "open"}, "sid": {"status": "resolved", "fixed_version": "2"}}}}}
        result = AUDIT.issue_rows({("x", "1")}, tracker)
        self.assertFalse(result[0]["candidate_older_than_trixie_fixed_version"])
        self.assertIsNone(result[0]["fixed_version"])

    def test_fixed_record_does_not_clear_older_candidate(self):
        tracker = {"x": {"CVE-TEST": {"releases": {
            "trixie": {"status": "resolved", "fixed_version": "2"}}}}}
        with mock.patch.object(AUDIT, "older", return_value=True):
            result = AUDIT.issue_rows({("x", "1")}, tracker)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["candidate_older_than_trixie_fixed_version"])

    def test_malformed_tracker_fix_remains_explicitly_unresolved(self):
        tracker = {"x": {"CVE-TEST": {"releases": {
            "trixie": {"status": "resolved", "fixed_version": "1:0.23.0+dfsg-"}}}}}
        with mock.patch.object(AUDIT, "older", side_effect=ValueError("invalid Debian version")):
            result = AUDIT.issue_rows({("x", "1:0.27.0-2")}, tracker)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["candidate_older_than_trixie_fixed_version"])
        self.assertEqual(result[0]["version_comparison_error"], "invalid Debian version")

    def test_non_string_tracker_fix_is_retained_as_unknown_comparison(self):
        for version in (12, True, ["1.0"], {"version": "1.0"}):
            tracker = {"x": {"CVE-TEST": {"releases": {
                "trixie": {"status": "resolved", "fixed_version": version}}}}}
            with self.subTest(version=version):
                result = AUDIT.issue_rows({("x", "2")}, tracker)
                self.assertEqual(len(result), 1)
                self.assertIsNone(result[0]["candidate_older_than_trixie_fixed_version"])
                self.assertIn("invalid Debian tracker fixed_version", result[0]["version_comparison_error"])

    @unittest.skipUnless(shutil.which("dpkg"), "Debian version tool required")
    def test_actual_dpkg_warning_syntax_does_not_silently_clear_tracker_finding(self):
        # dpkg --compare-versions returns 1, not a fatal error, for 2 lt 1_2
        # even though --validate-version rejects that underscore syntax.
        for version in ("1_2", "1.0/2", "latest", "1:0.23.0+dfsg-"):
            tracker = {"x": {"CVE-TEST": {"releases": {
                "trixie": {"status": "resolved", "fixed_version": version}}}}}
            with self.subTest(version=version):
                result = AUDIT.issue_rows({("x", "2")}, tracker)
                self.assertEqual(len(result), 1)
                self.assertIsNone(result[0]["candidate_older_than_trixie_fixed_version"])
                self.assertIn("invalid Debian version", result[0]["version_comparison_error"])
        with self.assertRaisesRegex(ValueError, "invalid Debian version"):
            AUDIT.older("1_2", "2")

    def test_priority_summary_never_mixes_different_versions_or_architectures(self):
        rows = [{"binary": "kernel:amd64", "version": "1+b1", "architecture": "amd64", "source": "linux", "source_version": "1"},
                {"binary": "kernel:i386", "version": "2+b1", "architecture": "i386", "source": "linux", "source_version": "2"},
                {"binary": "headers", "version": "1", "architecture": "all", "source": "linux", "source_version": "1"},
                {"binary": "other", "version": "1", "architecture": "all", "source": "other", "source_version": "1"}]
        issues = [{"source": "linux", "installed_source_version": "1", "cve": "CVE-OLD"},
                  {"source": "linux", "installed_source_version": "2", "cve": "CVE-NEW"},
                  {"source": "other", "installed_source_version": "1", "cve": "CVE-OTHER"}]
        available = {"kernel:amd64": {"version": "3"}, "kernel:i386": {"version": "4"}}
        result = AUDIT.priority_findings(rows, issues, available)
        self.assertEqual(len(result), 2)
        old, new = result
        self.assertEqual(old["installed_source_version"], "1")
        self.assertEqual([row["binary"] for row in old["binaries"]], ["kernel:amd64", "headers"])
        self.assertEqual(old["findings"], [issues[0]])
        self.assertEqual(old["binaries"][0]["available"], {"version": "3"})
        self.assertEqual(new["installed_source_version"], "2")
        self.assertEqual([row["binary"] for row in new["binaries"]], ["kernel:i386"])
        self.assertEqual(new["findings"], [issues[1]])
        self.assertEqual(new["binaries"][0]["available"], {"version": "4"})

    def test_foreign_architecture_is_not_replaced_by_native_version(self):
        versions = {}
        AUDIT.record_available(versions, {"Package": "wine", "Architecture": "i386", "Version": "1"}, "trixie", "main")
        AUDIT.record_available(versions, {"Package": "wine", "Architecture": "amd64", "Version": "2"}, "trixie", "main")
        self.assertEqual(versions["wine:i386"]["version"], "1")
        self.assertEqual(versions["wine:amd64"]["version"], "2")

    def test_architecture_all_is_independent(self):
        self.assertEqual(AUDIT.package_key("x", "all"), "x:all")
        self.assertEqual(AUDIT.package_key("x:i386", "i386"), "x:i386")

    def status(self, declarations, architecture="amd64", selection="install"):
        return (f"Package: kernel\nVersion: 1.0+b1\nArchitecture: {architecture}\n"
                f"Multi-Arch: same\nStatus: {selection} ok installed\n{declarations}\n").encode()

    def test_embedded_epoch_and_folded_fields_preserve_exact_versions(self):
        refs = AUDIT.declared_source_references(self.status(
            "Built-Using: linux (= 1:6.12.107-1),\n rustc (= 1.85.0+dfsg3-1)\n"
            "Static-Built-Using: golang-1.24 (= 1.24.4-1)"), "free")
        self.assertEqual(len(refs), 3)
        self.assertEqual(refs[0]["source_version"], "1:6.12.107-1")
        self.assertEqual(refs[0]["binary"], "kernel:amd64")
        self.assertEqual(refs[2]["field"], "Static-Built-Using")

    def test_held_installed_package_is_included(self):
        refs = AUDIT.declared_source_references(self.status("Built-Using: linux (= 1)", selection="hold"), "free")
        self.assertEqual(len(refs), 1)

    def test_non_exact_embedded_dependencies_are_rejected(self):
        for value in ("linux (>= 1)", "linux", "linux (= 1) | other (= 1)", "linux (= 1),", "linux (= latest)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AUDIT.declared_source_references(self.status("Built-Using: " + value), "free")

    def test_embedded_reference_duplicates_do_not_inflate_findings(self):
        refs = AUDIT.declared_source_references(self.status("Built-Using: linux (= 1), linux (= 1)"), "free")
        self.assertEqual(len(refs), 1)

    def test_duplicate_installed_identity_is_rejected(self):
        raw = self.status("Built-Using: linux (= 1)")
        with self.assertRaises(ValueError):
            AUDIT.declared_source_references(raw + b"\n" + raw, "free")

    def test_underlying_kernel_finding_keeps_binary_attribution(self):
        refs = AUDIT.declared_source_references(self.status("Built-Using: linux (= 1)"), "free")
        tracker = {"linux": {"CVE-TEST": {"releases": {"trixie": {"status": "open"}}}}}
        result = AUDIT.embedded_findings(refs, tracker)
        self.assertEqual(result["embedded_source_identity_count"], 1)
        self.assertEqual(result["embedded_issue_count"], 1)
        self.assertEqual(result["embedded_issues"][0]["referenced_by"], refs)
        self.assertEqual(result["embedded_issues"][0]["installed_source_version"], "1")

    def test_multiarch_references_are_not_collapsed(self):
        raw = self.status("Built-Using: linux (= 1)") + b"\n" + self.status("Built-Using: linux (= 1)", "i386")
        refs = AUDIT.declared_source_references(raw, "pro")
        result = AUDIT.embedded_findings(refs, {})
        self.assertEqual(len(refs), 2)
        self.assertEqual(result["embedded_source_identity_count"], 1)
        self.assertEqual(len(result["declared_embedded_sources"][0]["referenced_by"]), 2)
        self.assertEqual(result["embedded_sources_without_tracker_records"], ["linux"])

    @unittest.skipUnless(shutil.which("dpkg"), "Debian version tool required")
    def test_debian_epochs_and_bin_nmu_versions(self):
        self.assertTrue(AUDIT.older("1.1.15+ds1-2", "1.1.15+ds1-2+b4"))
        self.assertFalse(AUDIT.older("1:1.0-1", "99.0-1"))
        self.assertTrue(AUDIT.older("2.0~rc1-1", "2.0-1"))


if __name__ == "__main__":
    unittest.main()
