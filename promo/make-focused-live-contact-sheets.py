#!/usr/bin/env python3
"""Render start/middle/end review sheets for the focused live-short masters."""

from __future__ import annotations

import json
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\focused-live-shorts")
MANIFEST = ROOT / "focused-live-shorts-manifest.json"
OUT = ROOT / "review"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def frame(path: Path, at: float) -> Image.Image:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{at:.3f}",
            "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return Image.open(BytesIO(result.stdout)).convert("RGB")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for aspect in ("vertical", "landscape"):
        items = sorted(
            (item for item in manifest["outputs"] if item["aspect"] == aspect),
            key=lambda item: item["number"],
        )
        cell_w, cell_h, label_h = 460, 256, 44
        sheet = Image.new("RGB", (cell_w * 3, 60 + len(items) * (cell_h + label_h)), (4, 13, 23))
        draw = ImageDraw.Draw(sheet)
        draw.text((18, 14), f"DAGRiC FOCUSED LIVE SHORTS — {aspect.upper()} — START / MIDDLE / END", font=font(24, True), fill="white")
        for row, item in enumerate(items):
            path = Path(item["output"])
            duration = float(item["durationSeconds"])
            for column, fraction in enumerate((0.15, 0.50, 0.85)):
                image = frame(path, duration * fraction)
                image.thumbnail((cell_w - 14, cell_h - 12), Image.Resampling.LANCZOS)
                x = column * cell_w + (cell_w - image.width) // 2
                y0 = 60 + row * (cell_h + label_h)
                y = y0 + (cell_h - image.height) // 2
                sheet.paste(image, (x, y))
                draw.rectangle((column * cell_w, y0, (column + 1) * cell_w - 1, y0 + cell_h + label_h - 1), outline=(47, 86, 112), width=1)
                label = f"{item['number']:02d} {item['slug']} · {('start', 'middle', 'end')[column]}"
                draw.text((column * cell_w + 9, y0 + cell_h + 9), label, font=font(14, column == 0), fill=(210, 232, 243))
        output = OUT / f"focused-live-{aspect}-contact-sheet.jpg"
        sheet.save(output, quality=91)
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
