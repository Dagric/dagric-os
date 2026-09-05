#!/usr/bin/env python3
"""Validate every generated Dagric icon family without requiring Pillow."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "branding/icons/apps"
ICONS = ROOT / "config/includes.chroot/usr/share/icons"
DAGRIC = ROOT / "config/includes.chroot/usr/share/dagric"
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)
THEMES = {
    "DagricModern": ("modern.iconstyle", "icons-modern.png"),
    "DagricClassic": ("classic.iconstyle", "icons-classic.png"),
    "DagricOldSchool": ("old-school.iconstyle", "icons-old-school.png"),
}
CONTACT_SHEET = ROOT / "branding/icons/dagric-app-icons-contact-sheet.png"
CONTACT_MANIFEST = CONTACT_SHEET.with_suffix(".json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def main() -> int:
    names = sorted(path.name.removesuffix("-source.png") for path in SOURCES.glob("*-source.png"))
    errors: list[str] = []
    if not names:
        errors.append("no Dagric source icons found")

    try:
        contact = json.loads(CONTACT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"missing or invalid contact-sheet manifest: {exc}")
        contact = {}
    expected_source_files = {f"{name}-source.png" for name in names}
    recorded_sources = contact.get("sources", {}) if isinstance(contact, dict) else {}
    if not isinstance(recorded_sources, dict) or set(recorded_sources) != expected_source_files:
        errors.append("contact-sheet manifest does not cover every current source icon")
    else:
        for filename, expected_hash in recorded_sources.items():
            source = SOURCES / filename
            if not source.is_file() or expected_hash != sha256(source):
                errors.append(f"contact sheet is stale for {filename}; rebuild app icons")
    recorded_sheet = contact.get("sheet", {}) if isinstance(contact, dict) else {}
    dimensions = png_size(CONTACT_SHEET)
    expected_dimensions = (1080, math.ceil(len(names) / 6) * 150)
    if dimensions != expected_dimensions:
        errors.append(f"contact sheet dimensions are {dimensions}, expected {expected_dimensions}")
    if not isinstance(recorded_sheet, dict) or not CONTACT_SHEET.is_file():
        errors.append("contact-sheet manifest lacks sheet metadata")
    elif recorded_sheet.get("sha256") != sha256(CONTACT_SHEET):
        errors.append("contact-sheet PNG does not match its freshness manifest")

    for theme, (style_name, preview_name) in THEMES.items():
        theme_dir = ICONS / theme
        index = theme_dir / "index.theme"
        if not index.is_file():
            errors.append(f"{theme}: missing index.theme")
        else:
            text = index.read_text(encoding="utf-8")
            inherits = next((line for line in text.splitlines() if line.startswith("Inherits=")), "")
            inherited = {part.strip() for part in inherits.removeprefix("Inherits=").split(",")}
            if not {"breeze", "hicolor"}.issubset(inherited):
                errors.append(f"{theme}: must inherit Breeze and hicolor for third-party marks")
            for size in SIZES:
                if f"{size}x{size}/apps" not in text:
                    errors.append(f"{theme}: index.theme omits {size}x{size}/apps")

        for size in SIZES:
            for name in names:
                icon = theme_dir / f"{size}x{size}/apps/{name}.png"
                dimensions = png_size(icon)
                if dimensions is None:
                    errors.append(f"{theme}: missing or invalid PNG {icon.relative_to(ROOT)}")
                elif dimensions != (size, size):
                    errors.append(
                        f"{theme}: {icon.relative_to(ROOT)} is {dimensions[0]}x{dimensions[1]}, "
                        f"expected {size}x{size}"
                    )

        style = DAGRIC / "icon-styles" / style_name
        preview = DAGRIC / "appearance/thumbs" / preview_name
        if not style.is_file():
            errors.append(f"{theme}: missing selector metadata {style.relative_to(ROOT)}")
        else:
            style_text = style.read_text(encoding="utf-8")
            if f"THEME={theme}" not in style_text:
                errors.append(f"{style_name}: THEME does not name {theme}")
            if f"THUMB={preview_name}" not in style_text:
                errors.append(f"{style_name}: THUMB does not name {preview_name}")
        if png_size(preview) is None:
            errors.append(f"{theme}: missing or invalid selector preview {preview.relative_to(ROOT)}")

    if errors:
        print("icon-themes: FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    total = len(names) * len(SIZES) * len(THEMES)
    print(
        f"icon-themes: OK — {len(THEMES)} selectable families, {len(names)} Dagric icons, "
        f"{total} sized theme PNGs; Breeze inheritance preserves third-party marks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
