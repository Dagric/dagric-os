#!/usr/bin/env python3
"""Release gate for Dagric Flow palette, artwork, and desktop/login continuity."""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
INC = ROOT / "config/includes.chroot"


def linear(channel: int) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb: str) -> float:
    channels = [int(value) for value in rgb.split(",")]
    if len(channels) != 3 or any(value < 0 or value > 255 for value in channels):
        raise ValueError(f"invalid RGB value {rgb!r}")
    return 0.2126 * linear(channels[0]) + 0.7152 * linear(channels[1]) + 0.0722 * linear(channels[2])


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def parse_scheme(path: pathlib.Path) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    section = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
            groups.setdefault(section, {})
        elif "=" in line and section:
            key, value = line.split("=", 1)
            groups[section][key] = value
    return groups


def audit_scheme(path: pathlib.Path, text_minimum: float, decoration_minimum: float) -> list[str]:
    errors: list[str] = []
    groups = parse_scheme(path)
    pairs = 0
    for section, values in groups.items():
        if not section.startswith("[Colors:"):
            continue
        for key, foreground in values.items():
            if not key.startswith(("Foreground", "Decoration")):
                continue
            threshold = decoration_minimum if key.startswith("Decoration") else text_minimum
            for background_key in ("BackgroundNormal", "BackgroundAlternate"):
                background = values.get(background_key)
                if not background:
                    continue
                pairs += 1
                ratio = contrast(foreground, background)
                if ratio + 1e-9 < threshold:
                    errors.append(
                        f"{path.name} {section} {key} on {background_key}: "
                        f"{ratio:.2f}:1, needs {threshold:.1f}:1"
                    )
    if pairs == 0:
        errors.append(f"{path.name}: no color pairs measured")
    return errors


def png_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a readable PNG")
    return struct.unpack(">II", data[16:24])


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_text(path: pathlib.Path, *tokens: str) -> list[str]:
    if not path.is_file():
        return [f"missing {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    return [f"{path.relative_to(ROOT)} lacks {token!r}" for token in tokens if token not in text]


def main() -> int:
    errors: list[str] = []
    schemes = INC / "usr/share/color-schemes"
    errors.extend(audit_scheme(schemes / "DagricDark.colors", 4.5, 3.0))
    errors.extend(audit_scheme(schemes / "DagricLight.colors", 4.5, 3.0))
    errors.extend(audit_scheme(schemes / "DagricHighContrast.colors", 7.0, 7.0))

    wallpaper = INC / "usr/share/wallpapers/DagricObsidianPulse"
    image_1080 = wallpaper / "contents/images/1920x1080.png"
    image_4k = wallpaper / "contents/images/3840x2160.png"
    sddm = INC / "usr/share/dagric/sddm/background.png"
    for path, expected in ((image_1080, (1920, 1080)), (image_4k, (3840, 2160)), (sddm, (1920, 1080))):
        try:
            actual = png_size(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if actual != expected:
            errors.append(f"{path.relative_to(ROOT)} is {actual}, expected {expected}")
    if image_1080.is_file() and sddm.is_file() and sha256(image_1080) != sha256(sddm):
        errors.append("SDDM backdrop does not match the 1080p Obsidian Pulse wallpaper")

    token_path = INC / "usr/share/dagric/appearance/flow-tokens.json"
    try:
        tokens = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"Flow tokens unreadable: {exc}")
        tokens = {}
    expected_palette = {
        "obsidian": "#0B0D12",
        "frost": "#F5F7FA",
        "pulseRed": "#FF3B5C",
        "signalViolet": "#8B5CF6",
        "success": "#38D982",
        "warning": "#F6B84A",
        "danger": "#E53935",
    }
    for key, expected in expected_palette.items():
        actual = tokens.get("palette", {}).get(key) if isinstance(tokens, dict) else None
        if actual != expected:
            errors.append(f"Flow token {key} is {actual!r}, expected {expected!r}")

    errors.extend(require_text(
        ROOT / "config/hooks/normal/0500-desktop-defaults.hook.chroot",
        "Image=DagricObsidianPulse", "ColorScheme=DagricDark",
    ))
    errors.extend(require_text(
        INC / "usr/share/dagric/styles/obsidian-flow.style",
        "SCHEME=DagricDark", "ACCENT=255,59,92", "WALLPAPER=DagricObsidianPulse",
    ))
    errors.extend(require_text(
        INC / "usr/share/sddm/themes/dagric/Main.qml",
        'cAccent: "#ff3b5c"', 'cInk:    "#f5f7fa"',
    ))

    if errors:
        print("flow-check: FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("flow-check: palettes meet contrast floors; wallpaper sizes, SDDM continuity and tokens passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
