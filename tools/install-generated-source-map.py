#!/usr/bin/env python3
"""Atomically install a validated exact-source map into the public records."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json_atomic(path: Path, document: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map",
        dest="map_path",
        type=Path,
        default=ROOT / "out/exact-source-map-1.0.json",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=ROOT / "site/manifest/source-index-1.0.json",
    )
    parser.add_argument(
        "--release",
        type=Path,
        default=ROOT / "site/manifest/release.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verification = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/check-generated-source-map.py"),
            "--map",
            str(args.map_path),
            "--index",
            str(args.index),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if verification.returncode:
        sys.stderr.write(verification.stdout)
        sys.stderr.write(verification.stderr)
        print("install-source-map: BLOCKED: generated map did not validate", file=sys.stderr)
        return 1

    exact_map = json.loads(args.map_path.read_text(encoding="utf-8"))
    index = json.loads(args.index.read_text(encoding="utf-8"))
    release = json.loads(args.release.read_text(encoding="utf-8"))
    if release.get("source_index", {}).get("url") != (
        "https://dagric.com/manifest/source-index-1.0.json"
    ):
        print("install-source-map: BLOCKED: unexpected release source-index URL", file=sys.stderr)
        return 1
    debian = index.get("debian_layer")
    gate = index.get("next_release_gate")
    if not isinstance(debian, dict) or not isinstance(gate, dict):
        print("install-source-map: BLOCKED: source index lacks required records", file=sys.stderr)
        return 1

    debian["exact_binary_to_source_map_status"] = "complete"
    debian["exact_binary_to_source_map"] = exact_map
    debian["important_limit"] = (
        "This exact map binds every recorded Free and Pro binary name/version to its "
        "Dagric release commit or Debian source package/version, archived .dsc SHA-256, "
        "and the source-file SHA-256 values carried by that .dsc."
    )
    debian["retrieval_procedure"] = [
        "Find the exact binary name and version under the matching Free or Pro edition in this map.",
        "Download the mapped .dsc from Debian Snapshot and verify its recorded SHA-256.",
        "Download every source file listed for that entry and verify the SHA-256 recorded by the .dsc.",
        "For a Dagric-authored package, use the commit-pinned Dagric source archive and verify its recorded SHA-256.",
    ]
    debian["request_note"] = (
        "The exact release mapping is published in this record. Contact Dagric support for "
        "help obtaining the corresponding source for a named image and package."
    )
    gate["status"] = "complete"
    gate["block_if_release_identity_changes"] = False
    gate.pop("locked_release_identity", None)
    release["source_index"]["status"] = "complete"
    distribution = release.get("distribution")
    if not isinstance(distribution, dict) or distribution.get("status") != "held":
        print(
            "install-source-map: BLOCKED: release must retain an explicit distribution hold",
            file=sys.stderr,
        )
        return 1
    reasons = distribution.get("reason_codes")
    if not isinstance(reasons, list):
        print("install-source-map: BLOCKED: distribution hold lacks reason codes", file=sys.stderr)
        return 1
    distribution["reason_codes"] = [
        reason for reason in reasons if reason != "source-map-incomplete"
    ]
    if not distribution["reason_codes"]:
        print(
            "install-source-map: BLOCKED: source completion cannot silently lift the distribution hold",
            file=sys.stderr,
        )
        return 1

    write_json_atomic(args.index, index)
    write_json_atomic(args.release, release)
    print(
        "install-source-map: installed the validated map and marked only the source-index "
        "gate complete; distribution remains separately held"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
