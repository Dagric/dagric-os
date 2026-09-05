#!/usr/bin/env python3
"""Audit a primary source map; overall source-complete installation is held.

The former installer promoted a one-to-one package map to overall corresponding-
source completeness without accounting for embedded Built-Using sources. Until
the publication schema binds and independently checks those records against the
immutable images, this command deliberately performs no public-record writes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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

    sys.stdout.write(verification.stdout)
    print(
        "install-source-map: BLOCKED: a primary binary-to-source map cannot establish "
        "overall corresponding-source completeness. Inventory exact Built-Using and "
        "Static-Built-Using sources with tools/check-embedded-sources.py. Public "
        "installation remains disabled until the release schema and promotion gate "
        "independently bind that evidence to both immutable images. No records were changed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
