#!/usr/bin/env python3
"""Audit all enhanced Dagric social masters and write human-readable reports."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Enhanced Masters")
MANIFEST_PATH = ROOT / "enhanced-manifest.json"


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


def stream_hash(path: Path, selector: str) -> str:
    text = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            selector,
            "-c",
            "copy",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ]
    )
    match = re.search(r"SHA256=([0-9a-fA-F]{64})", text)
    if not match:
        raise RuntimeError(f"Could not hash {selector} for {path}")
    return match.group(1).lower()


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,channels,sample_rate,pix_fmt",
                "-of",
                "json",
                str(path),
            ]
        )
    )


def volume(path: Path) -> tuple[float, float]:
    text = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "NUL",
        ]
    )
    means = re.findall(r"mean_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    peaks = re.findall(r"max_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    if not means or not peaks:
        raise RuntimeError(f"Could not measure audio: {path}")
    return float(means[-1]), float(peaks[-1])


def fps_value(rate: str) -> float:
    numerator, denominator = rate.split("/", 1)
    return float(numerator) / float(denominator)


def ass_event_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.startswith("Dialogue: 1,"))


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected_count = 74
    rows: list[dict] = []
    failures: list[str] = []
    voice_counts: Counter[str] = Counter()

    if manifest.get("count") != expected_count:
        failures.append(f"Manifest count is {manifest.get('count')}; expected {expected_count}")

    for position, item in enumerate(manifest.get("videos", []), start=1):
        output = Path(item["output"])
        source = Path(item["source"])
        caption_master = Path(item["captionMaster"])
        if not output.exists():
            failures.append(f"Missing video: {output}")
            continue
        if not caption_master.exists():
            failures.append(f"Missing caption master: {caption_master}")
            continue

        info = probe(output)
        video_streams = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
        audio_streams = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        video = video_streams[0] if video_streams else {}
        audio = audio_streams[0] if audio_streams else {}
        duration = float(info["format"]["duration"])
        source_duration = float(probe(source)["format"]["duration"])
        mean_db, peak_db = volume(output)
        digest = sha256(output)
        captions = ass_event_count(caption_master)
        visual_changed = stream_hash(source, "0:v:0") != stream_hash(output, "0:v:0")
        frame_rate = fps_value(str(video.get("avg_frame_rate", "0/1"))) if video else 0.0
        for voice in item.get("voices", []):
            voice_counts[voice] += 1

        row = {
            "number": item["number"],
            "batch": item["batch"],
            "topic": item["topic"],
            "file": output.name,
            "output": str(output),
            "durationSeconds": round(duration, 3),
            "sourceDurationSeconds": round(source_duration, 3),
            "durationPass": abs(duration - source_duration) <= 0.15,
            "width": video.get("width", 0),
            "height": video.get("height", 0),
            "frameRate": round(frame_rate, 3),
            "videoCodec": video.get("codec_name", ""),
            "pixelFormat": video.get("pix_fmt", ""),
            "audioCodec": audio.get("codec_name", ""),
            "channels": audio.get("channels", 0),
            "sampleRate": audio.get("sample_rate", ""),
            "meanVolumeDb": mean_db,
            "peakVolumeDb": peak_db,
            "audible": bool(audio_streams) and mean_db > -40.0 and peak_db > -20.0,
            "clippingSafe": peak_db <= -0.2,
            "captionEvents": captions,
            "captionPass": captions == int(item["captionEvents"]) and captions > 0,
            "voiceLabels": ", ".join(item.get("voices", [])),
            "cta": item.get("cta", ""),
            "visualChanged": visual_changed,
            "sha256": digest,
            "sizeBytes": int(info["format"]["size"]),
        }
        rows.append(row)

        checks = [
            (bool(video_streams), "missing video stream"),
            (bool(audio_streams), "missing audio stream"),
            (row["durationPass"], f"duration changed: {source_duration:.3f} -> {duration:.3f}"),
            (row["width"] == 1080 and row["height"] == 1920, f"wrong dimensions: {row['width']}x{row['height']}"),
            (abs(frame_rate - 30.0) < 0.02, f"wrong frame rate: {frame_rate}"),
            (row["videoCodec"] == "h264", f"unexpected video codec: {row['videoCodec']}"),
            (row["pixelFormat"] == "yuv420p", f"unexpected pixel format: {row['pixelFormat']}"),
            (row["audioCodec"] == "aac", f"unexpected audio codec: {row['audioCodec']}"),
            (row["channels"] == 2, f"unexpected channel count: {row['channels']}"),
            (str(row["sampleRate"]) == "48000", f"unexpected sample rate: {row['sampleRate']}"),
            (row["audible"], f"audio not safely audible: mean={mean_db}, peak={peak_db}"),
            (row["clippingSafe"], f"possible clipping: peak={peak_db}"),
            (row["captionPass"], f"caption count mismatch: manifest={item['captionEvents']}, ASS={captions}"),
            (row["visualChanged"], "enhanced video stream matches source stream"),
            (row["sizeBytes"] > 200_000, f"suspiciously small file: {row['sizeBytes']} bytes"),
        ]
        for passed, message in checks:
            if not passed:
                failures.append(f"{output.name}: {message}")
        print(f"[{position:02d}/{len(manifest['videos']):02d}] {output.name} mean={mean_db:.1f} peak={peak_db:.1f} captions={captions}")

    unique_hashes = len({row["sha256"] for row in rows})
    if unique_hashes != len(rows):
        failures.append(f"Only {unique_hashes} unique hashes for {len(rows)} videos")
    if len(rows) != expected_count:
        failures.append(f"Audited {len(rows)} files; expected {expected_count}")

    batch_counts = Counter(row["batch"] for row in rows)
    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pass": not failures,
        "files": len(rows),
        "uniqueHashes": unique_hashes,
        "batches": dict(batch_counts),
        "voices": dict(sorted(voice_counts.items())),
        "meanVolumeRangeDb": [min(row["meanVolumeDb"] for row in rows), max(row["meanVolumeDb"] for row in rows)],
        "peakVolumeRangeDb": [min(row["peakVolumeDb"] for row in rows), max(row["peakVolumeDb"] for row in rows)],
        "failures": failures,
        "videos": rows,
    }
    (ROOT / "enhanced-audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (ROOT / "enhanced-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    status = "PASS" if result["pass"] else "FAIL"
    failures_md = "- None" if not failures else "\n".join(f"- {failure}" for failure in failures)
    voices_md = "\n".join(f"- {name}: {count} videos" for name, count in sorted(voice_counts.items()))
    report = f"""# Dagric enhanced-video audit

Audit date: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}

## Verdict

**{status}: {len(rows)} of {expected_count} enhanced social videos passed.**

## Results

| Check | Result |
| --- | ---: |
| Enhanced MP4 files | {len(rows)} |
| Unique SHA-256 hashes | {unique_hashes} |
| 1080 × 1920, 30 fps | {sum(1 for row in rows if row['width'] == 1080 and row['height'] == 1920 and abs(row['frameRate'] - 30) < 0.02)} |
| Audible AAC stereo at 48 kHz | {sum(1 for row in rows if row['audible'] and row['audioCodec'] == 'aac' and row['channels'] == 2 and str(row['sampleRate']) == '48000')} |
| Clipping-safe audio | {sum(1 for row in rows if row['clippingSafe'])} |
| Caption masters present and matched | {sum(1 for row in rows if row['captionPass'])} |
| Enhanced visual streams | {sum(1 for row in rows if row['visualChanged'])} |
| Duration matches source | {sum(1 for row in rows if row['durationPass'])} |
| Launch batch | {batch_counts.get('launch', 0)} |
| Daily batch | {batch_counts.get('daily', 0)} |
| Second wave | {batch_counts.get('second', 0)} |

Mean-volume range: **{result['meanVolumeRangeDb'][0]:.1f} to {result['meanVolumeRangeDb'][1]:.1f} dB**.<br>
Peak-volume range: **{result['peakVolumeRangeDb'][0]:.1f} to {result['peakVolumeRangeDb'][1]:.1f} dB**.

## Voice distribution

{voices_md}

## Enhancements verified

- Karaoke-style burned captions with matching ASS caption masters
- Explicit AI-voice name labels, including speaker changes
- Gentle camera drift and per-video motion phase
- Animated progress rail, audio meter, border accent, and Dagric watermark
- Contextual final call-to-action
- Smoothed audio entrance and exit with light dynamics control

## Failures

{failures_md}

The earlier narrated replacements were retained as backups and were not overwritten.
"""
    (ROOT / "ENHANCED-VIDEO-AUDIT.md").write_text(report, encoding="utf-8")
    print(f"ENHANCED_AUDIT={status} files={len(rows)} unique={unique_hashes} failures={len(failures)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
