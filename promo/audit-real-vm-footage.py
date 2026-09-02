#!/usr/bin/env python3
"""Technical and motion audit for the real Dagric OS footage delivery."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\finished")


def run(args: list[str]) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (result.stdout or "") + (result.stderr or "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(
        run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,color_range,channels,sample_rate",
            "-of", "json", str(path),
        ])
    )


def motion_sample(path: Path) -> tuple[int, int]:
    output = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", "fps=1,scale=160:90,format=gray", "-f", "framemd5", "-",
    ])
    hashes = []
    for line in output.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = [part.strip() for part in line.split(",")]
        if len(fields) >= 6:
            hashes.append(fields[-1])
    return len(hashes), len(set(hashes))


def audio_levels(path: Path) -> tuple[float, float]:
    output = run([
        "ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a:0",
        "-af", "volumedetect", "-f", "null", "-",
    ])
    mean_match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", output)
    max_match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", output)
    if not mean_match or not max_match:
        raise RuntimeError(f"Could not read audio levels for {path}")
    return float(mean_match.group(1)), float(max_match.group(1))


def main() -> int:
    videos = sorted(ROOT.glob("*/*.mp4"))
    if len(videos) != 14:
        raise RuntimeError(f"Expected 14 delivered MP4 files; found {len(videos)}")

    records = []
    errors = []
    hashes = set()
    for index, path in enumerate(videos, start=1):
        info = probe(path)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
        aspect = path.parent.name
        expected = (1080, 1920) if aspect == "vertical" else (1920, 1080)
        frame_count, unique_frames = motion_sample(path)
        mean_volume, max_volume = audio_levels(path)
        digest = sha256(path)
        checks = {
            "dimensions": (video["width"], video["height"]) == expected,
            "h264": video["codec_name"] == "h264",
            "thirtyFps": video["avg_frame_rate"] == "30/1",
            "yuv420p": video.get("pix_fmt") == "yuv420p",
            "aac": audio["codec_name"] == "aac",
            "stereo": audio["channels"] == 2,
            "fortyEightKhz": int(audio["sample_rate"]) == 48000,
            "audible": mean_volume > -45.0 and max_volume > -10.0,
            "notClipped": max_volume <= 0.0,
            "movingPicture": unique_frames >= 3,
            "sidecarCaptions": path.with_suffix(".srt").exists(),
            "uniqueFile": digest not in hashes,
        }
        hashes.add(digest)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            errors.append({"file": str(path), "failed": failed})
        records.append({
            "file": str(path),
            "aspect": aspect,
            "durationSeconds": round(float(info["format"]["duration"]), 3),
            "sizeBytes": int(info["format"]["size"]),
            "dimensions": f"{video['width']}x{video['height']}",
            "frameRate": video["avg_frame_rate"],
            "videoCodec": video["codec_name"],
            "pixelFormat": video.get("pix_fmt"),
            "audioCodec": audio["codec_name"],
            "audioChannels": audio["channels"],
            "audioSampleRate": int(audio["sample_rate"]),
            "meanVolumeDb": mean_volume,
            "maxVolumeDb": max_volume,
            "sampledFrames": frame_count,
            "uniqueSampledFrames": unique_frames,
            "sha256": digest,
            "checks": checks,
            "passed": not failed,
        })
        print(f"[{index:02d}/14] {'PASS' if not failed else 'FAIL'} {path.name}", flush=True)

    report = {
        "auditedAt": datetime.now(timezone.utc).isoformat(),
        "passed": not errors,
        "videoCount": len(records),
        "errorCount": len(errors),
        "errors": errors,
        "records": records,
    }
    (ROOT / "audit-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = [
        "# Real-footage delivery audit",
        "",
        f"Result: **{'PASS' if not errors else 'FAIL'}**",
        "",
        f"Files checked: {len(records)} MP4 masters plus matching SRT captions.",
        "",
        "Checks: dimensions, H.264/yuv420p, 30 fps, AAC stereo at 48 kHz, audible/non-clipped audio, sampled visual motion, caption sidecars, and unique file hashes.",
        "",
        "All visuals originate in the captured Dagric OS Pro live-ISO VM sessions. The moving-picture check verifies multiple distinct decoded frames; it is not a claim about physical-hardware compatibility.",
        "",
    ]
    if errors:
        rows.append("Failures:\n")
        rows.extend(f"- {item['file']}: {', '.join(item['failed'])}" for item in errors)
    (ROOT / "AUDIT.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError(f"Audit failed for {len(errors)} files")
    print("PASS: all 14 real-footage masters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
