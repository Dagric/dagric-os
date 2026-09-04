#!/usr/bin/env python3
"""Fail a release when its repository rights baseline is incomplete."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "LICENSE",
    "COPYING",
    "LICENSES.md",
    "TRADEMARKS.md",
    "THIRD-PARTY-NOTICES.md",
    "promo/SOCIAL-PUBLISHING-CHECKLIST.md",
)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            failures.append(f"Missing required rights file: {relative}")

    licensing_map = ROOT / "LICENSES.md"
    if licensing_map.is_file() and re.search(
        r"repository\s+is\s+private",
        licensing_map.read_text(encoding="utf-8"),
        re.IGNORECASE,
    ):
        failures.append("LICENSES.md still claims the public repository is private.")

    wallpaper_root = ROOT / "config/includes.chroot/usr/share/wallpapers"
    wallpaper_metadata = sorted(wallpaper_root.rglob("metadata.json"))
    if not wallpaper_metadata:
        failures.append("No wallpaper metadata files were found.")
    for metadata_file in wallpaper_metadata:
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            plugin = metadata["KPlugin"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            failures.append(f"Invalid wallpaper metadata: {metadata_file}: {error}")
            continue
        if plugin.get("License") != "CC-BY-SA-4.0":
            failures.append(f"Unexpected or missing wallpaper license: {metadata_file}")
        authors = plugin.get("Authors")
        if isinstance(authors, dict):
            author_names = [authors.get("Name")]
        elif isinstance(authors, list):
            author_names = [
                author.get("Name")
                for author in authors
                if isinstance(author, dict)
            ]
        else:
            author_names = []
        if not any(author_names):
            failures.append(f"Missing wallpaper author: {metadata_file}")

    tracked_secrets = git("ls-files", "--", ".secrets", ".secrets/**")
    if tracked_secrets.returncode != 0:
        warnings.append("Could not determine whether .secrets contains tracked files.")
    elif tracked_secrets.stdout.strip():
        failures.append("Files inside .secrets are tracked by Git.")

    credential_scan = git(
        "grep", "-l", "-I", "-E", r"sk_[A-Za-z0-9_-]{20,}", "--", "."
    )
    if credential_scan.returncode not in (0, 1):
        warnings.append("The tracked-file credential scan could not complete.")
    elif credential_scan.stdout.strip():
        for path in credential_scan.stdout.splitlines():
            failures.append(f"Potential API credential in tracked file: {path}")

    firefox_policy = (
        ROOT
        / "config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json"
    )
    if firefox_policy.is_file():
        policy_text = firefox_policy.read_text(encoding="utf-8")
        if re.search(r"ExtensionSettings|OverrideFirstRunPage|FirefoxHome", policy_text):
            warnings.append(
                "Firefox defaults are modified; complete "
                "docs/MOZILLA-DISTRIBUTION-REVIEW.md before release."
            )

    print(f"Rights preflight: {len(wallpaper_metadata)} wallpaper records checked.")
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if failures:
        print("Rights preflight FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Rights preflight passed with no blocking repository findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
