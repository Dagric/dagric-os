#!/usr/bin/env python3
"""Regression tests for the exact binary-to-source release gate."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dagric_site_audit", ROOT / "tools/audit-site.py")
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)

COMMIT = "1" * 40
HASH = "a" * 64


def debian_entry(name: str, version: str) -> dict[str, object]:
    return {
        "binary_name": name,
        "binary_version": version,
        "source_name": name.split(":", 1)[0],
        "source_version": version,
        "origin": "debian",
        "locator": {
            "dsc_url": f"https://snapshot.debian.org/archive/debian/20260101T000000Z/pool/{name[0]}/{name}/{name}_{version}.dsc"
        },
        "integrity": {"dsc_sha256": HASH},
    }


def dagric_entry(name: str, version: str) -> dict[str, object]:
    return {
        "binary_name": name,
        "binary_version": version,
        "source_name": "dagric-os",
        "source_version": version,
        "origin": "dagric",
        "locator": {
            "dagric_source_archive_url": f"https://github.com/Dagric/dagric-os/archive/{COMMIT}.tar.gz",
            "dagric_commit": COMMIT,
        },
        "integrity": {"source_archive_sha256": HASH},
    }


def valid_fixture() -> tuple[dict[str, object], dict[str, dict[str, object]], dict[str, list[tuple[str, str]]]]:
    artifacts = {
        "free": {
            "binary_package_manifest": "https://dagric.com/manifest/free.packages",
            "binary_package_manifest_sha256": "b" * 64,
        },
        "pro": {
            "binary_package_manifest": "https://dagric.com/manifest/pro.packages",
            "binary_package_manifest_sha256": "c" * 64,
        },
    }
    manifests = {
        "free": [("alpha", "1.0-1"), ("dagric-tools", "1.0")],
        "pro": [("beta:amd64", "2:3.0-4")],
    }
    exact_map: dict[str, object] = {
        "format": "dagric-exact-binary-source-map-v1",
        "generated_utc": "2026-09-04T12:00:00Z",
        "editions": {
            "free": {
                **artifacts["free"],
                "entries": [
                    debian_entry("alpha", "1.0-1"),
                    dagric_entry("dagric-tools", "1.0"),
                ],
            },
            "pro": {
                **artifacts["pro"],
                "entries": [debian_entry("beta:amd64", "2:3.0-4")],
            },
        },
    }
    return exact_map, artifacts, manifests


def errors_for(exact_map: object) -> list[str]:
    _, artifacts, manifests = valid_fixture()
    failures: list[str] = []
    AUDIT.validate_exact_source_map(exact_map, artifacts, manifests, COMMIT, failures)
    return failures


class ExactSourceMapGateTests(unittest.TestCase):
    def test_complete_status_cannot_omit_the_map(self) -> None:
        self.assertTrue(any("requires an exact source map" in item for item in errors_for(None)))

    def test_complete_map_accepts_an_exact_one_to_one_inventory(self) -> None:
        exact_map, _, _ = valid_fixture()
        self.assertEqual([], errors_for(exact_map))

    def test_missing_binary_is_rejected(self) -> None:
        exact_map, _, _ = valid_fixture()
        exact_map["editions"]["free"]["entries"].pop()  # type: ignore[index]
        failures = errors_for(exact_map)
        self.assertTrue(any("not a 1:1 match" in item for item in failures))

    def test_duplicate_binary_is_rejected(self) -> None:
        exact_map, _, _ = valid_fixture()
        entries = exact_map["editions"]["free"]["entries"]  # type: ignore[index]
        entries.append(copy.deepcopy(entries[0]))
        failures = errors_for(exact_map)
        self.assertTrue(any("more than once" in item for item in failures))
        self.assertTrue(any("not a 1:1 match" in item for item in failures))

    def test_source_name_version_locator_and_integrity_are_mandatory(self) -> None:
        exact_map, _, _ = valid_fixture()
        entry = exact_map["editions"]["pro"]["entries"][0]  # type: ignore[index]
        entry["source_name"] = ""
        entry["source_version"] = ""
        entry["locator"] = {}
        entry["integrity"] = {}
        failures = errors_for(exact_map)
        for expected in (
            "source package name",
            "exact source version",
            "archive/snapshot locator or .dsc URL",
            "SHA-256 digest for the .dsc",
        ):
            self.assertTrue(any(expected in item for item in failures), failures)

    def test_unofficial_dsc_host_is_rejected(self) -> None:
        exact_map, _, _ = valid_fixture()
        entry = exact_map["editions"]["pro"]["entries"][0]  # type: ignore[index]
        entry["locator"]["dsc_url"] = "https://example.com/beta_3.0-4.dsc"
        failures = errors_for(exact_map)
        self.assertTrue(any("invalid official Debian .dsc URL" in item for item in failures))

    def test_dagric_source_must_match_release_commit(self) -> None:
        exact_map, _, _ = valid_fixture()
        entry = exact_map["editions"]["free"]["entries"][1]  # type: ignore[index]
        entry["locator"]["dagric_commit"] = "2" * 40
        failures = errors_for(exact_map)
        self.assertTrue(any("does not match the release commit" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
