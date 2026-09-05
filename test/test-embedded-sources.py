#!/usr/bin/env python3
"""Offline exact embedded-source inventory regressions; no network required."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("embedded_sources", ROOT / "tools/check-embedded-sources.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
COMMIT = "a" * 40
ISO_HASHES = {"free": "f" * 64, "pro": "e" * 64}


def source(name="primary", version="1.0-1"):
    prefix = "https://snapshot.debian.org/archive/debian/20250901T010203Z/"
    base = prefix + f"pool/main/{name[0]}/{name}/"
    filename = f"{name}_{version.split(':', 1)[-1]}.orig.tar.xz"
    return {"source_name": name, "source_version": version, "origin": "debian",
            "locator": {"dsc_url": base + quote(f"{name}_{version.split(':', 1)[-1]}.dsc", safe=""),
                        "debian_archive_url": prefix},
            "integrity": {"dsc_sha256": "d" * 64, "source_files": [
                {"filename": filename, "url": base + quote(filename, safe=""), "sha256": "c" * 64}]}}


def status(declarations="", *, arch="amd64", multiarch=False):
    return ("Package: demo\nStatus: install ok installed\nArchitecture: " + arch
            + "\nVersion: 1.0-1\n" + ("Multi-Arch: same\n" if multiarch else "") + declarations + "\n").encode()


def primary_map(*, source_record=None, binary="demo"):
    entry = {"binary_name": binary, "binary_version": "1.0-1", **(source_record or source())}
    return {"format": "dagric-exact-binary-source-map-v1", "editions": {
        edition: {"entries": [copy.deepcopy(entry)]} for edition in ("free", "pro")}}


def supplement(records):
    return {"format": "dagric-embedded-source-supplement-v1", "source_commit": COMMIT, "entries": records}


class EmbeddedSourceTests(unittest.TestCase):
    def report(self, body=None, primary=None, additional=None, commit=COMMIT, iso_hashes=None):
        body = body if body is not None else status("Built-Using: embedded (= 2.0-1)\n")
        return checker.build_report({"free": body, "pro": body}, primary or primary_map(), additional,
                                    commit, iso_hashes or ISO_HASHES, "b" * 64, "9" * 64 if additional else None)

    def test_folded_fields_exact_versions_and_provenance(self):
        body = status("Built-Using: primary (= 1.0-1),\n embedded (= 2:3.0+dfsg-1)\nStatic-Built-Using: embedded (= 2:3.0+dfsg-1)\n")
        report = self.report(body, additional=supplement([source("embedded", "2:3.0+dfsg-1")]))
        self.assertEqual(report["missing_exact_source_identities"], 0)
        self.assertEqual(report["unique_declared_embedded_source_identities"], 2)
        self.assertEqual(len(report["entries"][0]["referenced_by"]), 4)
        self.assertEqual(report["declarations_by_edition"]["free"]["Built-Using"], 2)
        self.assertEqual(report["inputs"]["dpkg_status_sha256"]["free"], checker.sha256(body))
        self.assertEqual(report["inputs"]["iso_sha256_from_supplied_receipts"], ISO_HASHES)
        self.assertFalse(report["release_approved"])
        self.assertFalse(report["corresponding_source_complete"])

    def test_missing_supplement_is_not_covered_by_other_version(self):
        report = self.report(additional=supplement([source("embedded", "2.0-2")]))
        self.assertEqual(report["missing_exact_source_identities"], 1)
        self.assertEqual(report["entries"][0]["coverage"], "missing")

    def test_primary_requires_exact_version_not_just_name(self):
        report = self.report(primary=primary_map(source_record=source("embedded", "2.0-2")))
        self.assertEqual(report["missing_exact_source_identities"], 1)

    def test_primary_exact_identity_is_covered(self):
        report = self.report(primary=primary_map(source_record=source("embedded", "2.0-1")))
        self.assertEqual(report["already_in_primary_map"], 1)
        self.assertEqual(report["missing_exact_source_identities"], 0)

    def test_architecture_is_preserved_and_multiarch_matches_primary(self):
        report = self.report(status("Built-Using: primary (= 1.0-1)\n", arch="arm64", multiarch=True), primary_map(binary="demo:arm64"))
        reference = report["entries"][0]["referenced_by"][0]
        self.assertEqual(reference["binary_name"], "demo:arm64")
        self.assertEqual(reference["binary_architecture"], "arm64")
        with self.assertRaisesRegex(checker.InventoryError, "exactly match"):
            self.report(status(arch="arm64", multiarch=True), primary_map(binary="demo:amd64"))

    def test_unsupported_dependency_syntax_fails_closed(self):
        for declaration in ("embedded", "embedded (>= 2.0)", "embedded (= 2.0) | other (= 1)",
                            "embedded:any (= 2.0)", "embedded (= 2.0) [amd64]", "embedded (= 2.0),", ""):
            with self.subTest(declaration=declaration), self.assertRaises(checker.InventoryError):
                self.report(status(f"Built-Using: {declaration}\n"))

    def test_foreign_allowed_architecture_qualification_is_exact(self):
        body = status("Multi-Arch: allowed\nBuilt-Using: primary (= 1.0-1)\n", arch="i386")
        report = self.report(body, primary_map(binary="demo:i386"))
        reference = report["entries"][0]["referenced_by"][0]
        self.assertEqual(reference["binary_name"], "demo:i386")
        self.assertEqual(reference["binary_architecture"], "i386")
        with self.assertRaisesRegex(checker.InventoryError, "exactly match"):
            self.report(body, primary_map(binary="demo:amd64"))
        ambiguous = primary_map()
        for edition in ambiguous["editions"].values():
            duplicate = copy.deepcopy(edition["entries"][0])
            duplicate["binary_name"] += ":i386"
            edition["entries"].append(duplicate)
        with self.assertRaisesRegex(checker.InventoryError, "exactly match"):
            self.report(body, ambiguous)

    def test_duplicate_contradictory_installed_identity(self):
        body = status() + status().replace(b"Version: 1.0-1", b"Version: 2.0-1")
        with self.assertRaisesRegex(checker.InventoryError, "duplicate contradictory installed identity"):
            self.report(body)
        with self.assertRaisesRegex(checker.InventoryError, "duplicate repeated"):
            self.report(status() + status())

    def test_noninstalled_ignored_and_held_installed_counted(self):
        body = status().replace(b"install ok installed", b"hold ok installed")
        body += b"Package: removed\nStatus: deinstall ok config-files\n\n"
        self.assertEqual(self.report(body)["declarations_by_edition"]["free"]["installed_binaries"], 1)

    def test_malformed_control_paragraphs_fail(self):
        for body in (b" orphan\n", status().replace(b"Architecture: amd64\n", b""),
                     status() + b"broken field\n", status().replace(b"Version: 1.0-1", b"Version: 1.0-1\nversion: 2"),
                     status().replace(b"install ok installed", b"install reinstreq installed"),
                     status() + b"Package: invalid\nStatus: nonsense ok ignored\n\n"):
            with self.subTest(body=body), self.assertRaises(checker.InventoryError):
                self.report(body)

    def test_metadata_must_be_complete(self):
        mutations = (
            lambda row: row.pop("source_version"),
            lambda row: row["integrity"].pop("dsc_sha256"),
            lambda row: row["integrity"].pop("source_files"),
            lambda row: row["integrity"].update(source_files=[]),
            lambda row: row["integrity"].update(dsc_sha256="bad"),
            lambda row: row["integrity"]["source_files"][0].pop("sha256"),
            lambda row: row["locator"].pop("debian_archive_url"),
            lambda row: row.update(origin="unknown"),
        )
        for change in mutations:
            row = source("embedded", "2.0-1")
            change(row)
            with self.subTest(row=row), self.assertRaises(checker.InventoryError):
                self.report(additional=supplement([row]))

    def test_unofficial_unpinned_or_mismatched_locators_fail(self):
        mutations = (
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"].replace("https:", "http:")),
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"].replace("snapshot.debian.org", "snapshot.debian.org.example")),
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"].replace("snapshot.debian.org", "user@snapshot.debian.org")),
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"].replace("20250901T010203Z", "latest")),
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"] + "?other"),
            lambda row: row["locator"].update(dsc_url=row["locator"]["dsc_url"].replace("embedded_2.0-1", "embedded_2.0-2")),
            lambda row: row["integrity"]["source_files"][0].update(filename="unrelated.tar.xz"),
            lambda row: row["integrity"]["source_files"][0].update(filename="../outside"),
            lambda row: row["integrity"]["source_files"][0].update(url=row["integrity"]["source_files"][0]["url"].replace("20250901T010203Z", "20250902T010203Z")),
        )
        for change in mutations:
            row = source("embedded", "2.0-1")
            change(row)
            with self.subTest(row=row), self.assertRaises(checker.InventoryError):
                self.report(additional=supplement([row]))

    def test_duplicate_and_wrong_commit_supplements_fail(self):
        row = source("embedded", "2.0-1")
        with self.assertRaisesRegex(checker.InventoryError, "duplicate supplementary"):
            self.report(additional=supplement([row, row]))
        wrong = supplement([row])
        wrong["source_commit"] = "0" * 40
        with self.assertRaisesRegex(checker.InventoryError, "source commit"):
            self.report(additional=wrong)
        for commit in ("abc", "A" * 40):
            with self.assertRaises(checker.InventoryError):
                self.report(commit=commit)
        with self.assertRaisesRegex(checker.InventoryError, "iso-sha256"):
            self.report(iso_hashes={"free": "short", "pro": "e" * 64})

    def test_primary_map_must_match_installed_and_be_complete(self):
        wrong = primary_map()
        wrong["editions"]["free"]["entries"][0]["binary_version"] = "1.0-2"
        with self.assertRaisesRegex(checker.InventoryError, "exactly match"):
            self.report(primary=wrong)
        incomplete = primary_map()
        incomplete["editions"]["free"]["entries"][0]["integrity"].pop("source_files")
        with self.assertRaisesRegex(checker.InventoryError, "source_files"):
            self.report(primary=incomplete)

    def test_duplicate_json_members_rejected(self):
        with self.assertRaisesRegex(checker.InventoryError, "duplicate JSON"):
            json.loads('{"entries": [], "entries": [{}]}', object_pairs_hook=checker.unique_json)

    def test_cli_writes_missing_inventory_but_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "status").write_bytes(status("Built-Using: embedded (= 2.0-1)\n"))
            (folder / "map.json").write_text(json.dumps(primary_map()), encoding="utf-8")
            destination = folder / "inventory.private.json"
            args = ["--free-status", str(folder / "status"), "--pro-status", str(folder / "status"),
                    "--free-iso-sha256", ISO_HASHES["free"], "--pro-iso-sha256", ISO_HASHES["pro"],
                    "--map", str(folder / "map.json"), "--dagric-commit", COMMIT, "--output", str(destination)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(checker.main(args), 1)
                original = destination.read_bytes()
                self.assertEqual(checker.main(args), 2)
                self.assertEqual(destination.read_bytes(), original)
            report = json.loads(original)
            self.assertEqual(report["status"], "missing-exact-source-records")
            self.assertEqual(report["missing_exact_source_identities"], 1)
            self.assertTrue(report["private"])

    def test_primary_checker_retains_scope_warning(self):
        body = (ROOT / "tools/check-generated-source-map.py").read_text(encoding="utf-8")
        for phrase in ("Built-Using", "Static-Built-Using", "NOT CHECKED", "corresponding-source", "release approval"):
            self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
