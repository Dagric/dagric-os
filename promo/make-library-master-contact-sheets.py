#!/usr/bin/env python3
"""Create midpoint contact sheets for every current and legacy Dagric master."""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


VIDEO_ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
AUDIT_JSON = VIDEO_ROOT / "All Video Audit" / "all-video-audit.json"
OUT = VIDEO_ROOT / "All Video Audit" / "contact-sheets"
THUMBS = OUT / "thumbs"
CELL_W = 300
CELL_H = 238
IMAGE_H = 184
COLS = 6
ROWS = 7


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def extract(item: tuple[int, dict]) -> tuple[int, Path]:
    index, record = item
    source = Path(record["path"])
    duration = float(record.get("durationSeconds", 0.0) or 0.0)
    at = max(0.0, duration * 0.5)
    completed = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{at:.3f}",
            "-i", str(source), "-frames:v", "1", "-vf",
            f"scale={CELL_W - 16}:{IMAGE_H - 12}:force_original_aspect_ratio=decrease",
            "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0 or not completed.stdout:
        image = Image.new("RGB", (CELL_W - 16, IMAGE_H - 12), (80, 16, 24))
        ImageDraw.Draw(image).text((10, 10), "FRAME ERROR", font=font(18, True), fill="white")
    else:
        image = Image.open(BytesIO(completed.stdout)).convert("RGB")
    thumb = Image.new("RGB", (CELL_W, CELL_H), (8, 18, 29))
    x = (CELL_W - image.width) // 2
    y = 6 + (IMAGE_H - image.height) // 2
    thumb.paste(image, (x, y))
    draw = ImageDraw.Draw(thumb)
    draw.rectangle((0, 0, CELL_W - 1, CELL_H - 1), outline=(47, 86, 112), width=1)
    short = record["relativePath"]
    if len(short) > 49:
        short = "…" + short[-48:]
    draw.text((8, IMAGE_H + 3), f"{index + 1:03d}  {record['tier']}", font=font(14, True), fill=(80, 210, 239))
    draw.text((8, IMAGE_H + 23), short, font=font(12), fill=(232, 239, 244))
    path = THUMBS / f"{index + 1:04d}.jpg"
    thumb.save(path, quality=88)
    return index, path


def main() -> int:
    report = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    records = [
        record for record in report["videos"]
        if record["tier"] in {"current-master", "legacy-master"}
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(extract, item): item[0] for item in enumerate(records)}
        for position, future in enumerate(as_completed(futures), start=1):
            index, path = future.result()
            paths[index] = path
            if position % 50 == 0 or position == len(records):
                print(f"[{position}/{len(records)}] midpoint frames", flush=True)
    per_sheet = COLS * ROWS
    sheet_paths: list[str] = []
    for sheet_index in range((len(records) + per_sheet - 1) // per_sheet):
        sheet = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H + 54), (4, 13, 23))
        draw = ImageDraw.Draw(sheet)
        start = sheet_index * per_sheet
        end = min(len(records), start + per_sheet)
        draw.text(
            (16, 13),
            f"DAGRiC MASTER REVIEW — {start + 1:03d}–{end:03d} OF {len(records)}",
            font=font(23, True), fill="white",
        )
        for offset, index in enumerate(range(start, end)):
            thumb = Image.open(paths[index]).convert("RGB")
            x = (offset % COLS) * CELL_W
            y = 54 + (offset // COLS) * CELL_H
            sheet.paste(thumb, (x, y))
        output = OUT / f"master-contact-{sheet_index + 1:02d}.jpg"
        sheet.save(output, quality=91)
        sheet_paths.append(str(output))
    (OUT / "contact-sheet-index.json").write_text(
        json.dumps({"masters": len(records), "sheets": sheet_paths}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {len(sheet_paths)} contact sheets for {len(records)} masters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
