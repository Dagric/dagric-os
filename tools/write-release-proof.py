#!/usr/bin/env python3
"""Write the public, machine-readable Dagric release record.

The signed SHA256SUMS file remains the security authority. This record makes
the same release easy to inspect without scraping HTML and ties it to the exact
source commit and package manifests published beside it.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
SITE = ROOT / "site"
MANIFEST = SITE / "manifest"
EXPECTED = (
    "dagric-os-1.0-amd64.iso",
    "dagric-os-pro-1.0-amd64.iso",
)


def source_commit() -> str:
    """Return the commit captured when the ISO build began.

    An explicit environment value supports detached build workers. The file in
    out/ is the normal path and deliberately survives later release-only
    commits. Git (including Windows git.exe under WSL) is only a development
    fallback for older build outputs.
    """
    candidates: list[str] = []
    if value := os.environ.get("DAGRIC_SOURCE_COMMIT"):
        candidates.append(value)
    marker = OUT / "SOURCE_COMMIT"
    if marker.is_file():
        candidates.append(marker.read_text(encoding="ascii", errors="ignore").strip())
    git_command = shutil.which("git") or shutil.which("git.exe")
    if git_command:
        try:
            candidates.append(
                subprocess.check_output(
                    [git_command, "rev-parse", "HEAD"],
                    cwd=ROOT,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
            )
        except (OSError, subprocess.CalledProcessError):
            pass
    for candidate in candidates:
        if re.fullmatch(r"[0-9a-fA-F]{40}", candidate):
            return candidate.lower()
    raise RuntimeError(
        "source commit unavailable; preserve out/SOURCE_COMMIT from the build "
        "or set DAGRIC_SOURCE_COMMIT"
    )


def read_signed_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (OUT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            result[parts[1].lstrip("*")] = parts[0]
    return result


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_manifest(name: str) -> dict[str, object]:
    path = MANIFEST / name
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "url": f"https://dagric.com/manifest/{name}",
        "packages": len(lines),
        "sha256": file_sha256(path),
    }


def main() -> int:
    sums = read_signed_hashes()
    missing = [name for name in EXPECTED if name not in sums or not (OUT / name).is_file()]
    if missing:
        print("release-proof: missing " + ", ".join(missing), file=sys.stderr)
        return 1

    MANIFEST.mkdir(parents=True, exist_ok=True)
    release = {
        "schema": "https://dagric.com/manifest/release.schema.json",
        "product": "Dagric OS",
        "version": "1.0",
        "codename": "Foundation",
        "architecture": "amd64",
        "base": "Debian 13 (Trixie)",
        "source": {
            "repository": "https://github.com/Dagric/dagric-os",
            "commit": source_commit(),
        },
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "signature": {
            "manifest": "https://dagric.com/SHA256SUMS",
            "detached_signature": "https://dagric.com/SHA256SUMS.sig",
            "public_key": "https://dagric.com/dagric-signing-key.asc",
            "fingerprint": "3A079F85DE74375DD65557096CE37402BA0A0EF8",
        },
        "artifacts": [
            {
                "edition": "pro" if "-pro-" in name else "free",
                "filename": name,
                "bytes": (OUT / name).stat().st_size,
                "sha256": sums[name],
            }
            for name in EXPECTED
        ],
        "package_manifests": {
            "free": package_manifest("dagric-os-1.0.packages"),
            "pro": package_manifest("dagric-os-pro-1.0.packages"),
        },
        "test_record": "https://dagric.com/testing",
        "known_limitations": "https://dagric.com/testing#limitations",
    }
    target = MANIFEST / "release.json"
    target.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    print(f"release-proof: wrote {target.relative_to(ROOT)} for {release['source']['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
