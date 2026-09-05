#!/usr/bin/env python3
"""Validate the primary binary-to-source map, without publishing or approving it.

This checks one source identity for each installed binary, not embedded source
dependencies. Run check-embedded-sources.py on the immutable dpkg inventories
as a separate check; neither pass is qualified legal/release approval.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_auditor():
    spec = importlib.util.spec_from_file_location(
        "dagric_audit_site", ROOT / "tools/audit-site.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load tools/audit-site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        "--free-manifest",
        type=Path,
        default=ROOT / "site/manifest/dagric-os-1.0.packages",
    )
    parser.add_argument(
        "--pro-manifest",
        type=Path,
        default=ROOT / "site/manifest/dagric-os-pro-1.0.packages",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    auditor = load_auditor()
    exact_map = json.loads(args.map_path.read_text(encoding="utf-8"))
    if "debian_layer" in exact_map:
        exact_map = exact_map.get("debian_layer", {}).get("exact_binary_to_source_map")
    if not isinstance(exact_map, dict):
        print("generated-source-map: BLOCKED: exact map object is missing", file=sys.stderr)
        return 1
    index = json.loads(args.index.read_text(encoding="utf-8"))
    release = index.get("release", {})
    commit = release.get("source_commit")
    if not isinstance(commit, str):
        print("generated-source-map: BLOCKED: index lacks release.source_commit", file=sys.stderr)
        return 1
    failures: list[str] = []
    identities = {
        "free": auditor.parse_binary_package_manifest(
            args.free_manifest, "free", failures
        ),
        "pro": auditor.parse_binary_package_manifest(args.pro_manifest, "pro", failures),
    }
    auditor.validate_exact_source_map(
        exact_map,
        auditor.artifact_map(release),
        identities,
        commit,
        failures,
    )
    if failures:
        print("generated-source-map: BLOCKED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    unique_sources = {
        (entry["source_name"], entry["source_version"])
        for edition in exact_map["editions"].values()
        for entry in edition["entries"]
    }
    print(
        "generated-source-map: primary binary-to-source mapping passed "
        f"({len(identities['free'])} Free, {len(identities['pro'])} Pro, "
        f"{len(unique_sources)} unique source identities)"
    )
    print(
        "NOT CHECKED: Built-Using/Static-Built-Using embedded sources; run "
        "tools/check-embedded-sources.py. This is not full corresponding-source "
        "clearance or release approval."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
