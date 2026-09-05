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
    "LICENSE-POLICY.md",
    "COPYING",
    "LICENSES.md",
    "TRADEMARKS.md",
    "THIRD-PARTY-NOTICES.md",
    "promo/SOCIAL-PUBLISHING-CHECKLIST.md",
)

PROPRIETARY_GAME_CLIENT_PACKAGES = {
    "steam",
    "steam-installer",
    "steam-launcher",
    "steamcmd",
    "gog-galaxy",
    "epic-games-launcher",
    "amazon-games",
}

FIRMWARE_DOWNLOADER_PACKAGES = {
    "firmware-b43-installer",
    "firmware-b43legacy-installer",
}


def proprietary_game_client_package(name: str) -> bool:
    """Treat Steam runtime library bundles as client payload, not controller rules."""
    return name in PROPRIETARY_GAME_CLIENT_PACKAGES or name.startswith("steam-libs")

REQUIRED_GAME_NOTICE_TERMS = (
    "Steam",
    "Heroic Games Launcher",
    "GOG",
    "Epic Games",
    "Amazon Games",
    "steam-devices",
    "firmware-nvidia-graphics",
    "firmware-nvidia-tesla-535-gsp",
    "not affiliated",
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

    package_inputs = sorted((ROOT / "config/package-lists").glob("*.list.chroot"))
    package_inputs += sorted((ROOT / "site/manifest").glob("*.packages"))
    for package_list in package_inputs:
        for raw_line in package_list.read_text(encoding="utf-8").splitlines():
            package = raw_line.split("#", 1)[0].strip().split(maxsplit=1)
            normalized = package[0].lower().rstrip("+-").split(":", 1)[0] if package else ""
            if proprietary_game_client_package(normalized):
                failures.append(
                    "Proprietary game client listed for ISO inclusion: "
                    f"{normalized} in {package_list.relative_to(ROOT)}"
                )
            if (
                package_list.parent.name == "package-lists"
                and normalized in FIRMWARE_DOWNLOADER_PACKAGES
                and not package[0].endswith("-")
            ):
                failures.append(
                    "Firmware downloader listed for future image inclusion: "
                    f"{normalized} in {package_list.relative_to(ROOT)}"
                )

    live_build_config = ROOT / "auto/config"
    if live_build_config.is_file():
        config_text = live_build_config.read_text(encoding="utf-8")
        if not re.search(r"--firmware-chroot\s+false(?:\s|\\)", config_text):
            failures.append(
                "auto/config must disable live-build's automatic chroot firmware "
                "scan; use the explicit reviewed firmware package list."
            )
        if not re.search(r"--firmware-binary\s+false(?:\s|\\)", config_text):
            failures.append(
                "auto/config must not create an unreviewed installer-firmware bundle."
            )

    release_record = ROOT / "site/manifest/release.json"
    if release_record.is_file():
        try:
            release = json.loads(release_record.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"Invalid release record: {release_record}: {error}")
        else:
            source_status = (release.get("source_index") or {}).get("status")
            if source_status != "complete":
                public_site_text = "\n".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in (ROOT / "site").rglob("*")
                    if path.is_file() and path.suffix.lower() in {".html", ".js"}
                )
                if re.search(r"https://buy\.stripe\.com/", public_site_text):
                    failures.append(
                        "Checkout links must remain disabled while the release source "
                        "index is not complete."
                    )
                if "https://schema.org/InStock" in public_site_text:
                    failures.append(
                        "Structured offers must not advertise availability while the "
                        "release source index is not complete."
                    )
                if re.search(r"https://[^\s\"']+\.r2\.dev/[^\s\"']+\.iso", public_site_text):
                    failures.append(
                        "Direct ISO links must remain disabled while the release source "
                        "index is not complete."
                    )
                wrangler_config = ROOT / "infra/wrangler.toml"
                wrangler_text = (
                    wrangler_config.read_text(encoding="utf-8")
                    if wrangler_config.is_file()
                    else ""
                )
                if not re.search(
                    r'(?m)^DISTRIBUTION_ENABLED\s*=\s*"false"\s*$',
                    wrangler_text,
                ):
                    failures.append(
                        "The download Worker must remain fail-closed while the release "
                        "source index is not complete."
                    )

    notices = ROOT / "THIRD-PARTY-NOTICES.md"
    if notices.is_file():
        notice_text = notices.read_text(encoding="utf-8")
        for term in REQUIRED_GAME_NOTICE_TERMS:
            if term.casefold() not in notice_text.casefold():
                failures.append(
                    f"THIRD-PARTY-NOTICES.md is missing game-platform notice: {term}"
                )

    firefox_policy = (
        ROOT
        / "config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json"
    )
    if firefox_policy.exists():
        failures.append(
            "Dagric injects a Firefox distribution policy. Remove it to preserve the "
            "unmodified Debian Firefox ESR distribution posture, or obtain and archive "
            "written Mozilla permission for the exact candidate."
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
