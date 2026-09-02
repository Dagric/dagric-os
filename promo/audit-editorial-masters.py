#!/usr/bin/env python3
"""Audit the final Dagric editorial video delivery."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Editorial Masters")
MANIFEST = ROOT / "editorial-manifest.json"
DISCLOSURE = "Synthetic narration; original locally synthesized sound bed; human-directed editorial design; sidecar captions included"


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


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration,size:format_tags=title,artist,comment:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,color_range,channels,sample_rate",
                "-of", "json", str(path),
            ]
        )
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stream_hash(path: Path, selector: str) -> str:
    text = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", selector, "-c", "copy", "-f", "hash", "-hash", "sha256", "-",
    ])
    match = re.search(r"SHA256=([0-9a-fA-F]{64})", text)
    if not match:
        raise RuntimeError(f"Could not hash {selector} for {path}")
    return match.group(1).lower()


def volume(path: Path) -> tuple[float, float]:
    text = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", "volumedetect", "-f", "null", "NUL",
    ])
    means = re.findall(r"mean_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    peaks = re.findall(r"max_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    if not means or not peaks:
        raise RuntimeError(f"Could not measure audio for {path}")
    return float(means[-1]), float(peaks[-1])


def fps(rate: str) -> float:
    numerator, denominator = rate.split("/", 1)
    return float(numerator) / float(denominator)


def srt_events(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if " --> " in line)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    rows: list[dict] = []
    expected = 74
    if manifest.get("count") != expected:
        failures.append(f"Manifest count is {manifest.get('count')}; expected {expected}")

    for position, item in enumerate(manifest.get("videos", []), start=1):
        output = Path(item["output"])
        captions = Path(item["captions"])
        visual_source = Path(item["visualSource"])
        audio_source = Path(item["audioSource"])
        missing = [str(path) for path in (output, captions, visual_source, audio_source) if not path.exists()]
        if missing:
            failures.extend(f"Missing: {path}" for path in missing)
            continue

        data = probe(output)
        video = next((stream for stream in data["streams"] if stream["codec_type"] == "video"), {})
        audio = next((stream for stream in data["streams"] if stream["codec_type"] == "audio"), {})
        duration = float(data["format"]["duration"])
        frame_rate = fps(video.get("avg_frame_rate", "0/1")) if video else 0.0
        mean_db, peak_db = volume(output)
        event_count = srt_events(captions)
        caption_text = captions.read_text(encoding="utf-8-sig")
        tags = data.get("format", {}).get("tags", {})
        metadata_comment = tags.get("comment", tags.get("COMMENT", ""))
        video_preserved = stream_hash(output, "0:v:0") == stream_hash(visual_source, "0:v:0")
        audio_preserved = stream_hash(output, "0:a:0") == stream_hash(audio_source, "0:a:0")
        row = {
            "number": item["number"],
            "batch": item["batch"],
            "topic": item["topic"],
            "file": output.name,
            "visualDirection": item["visualDirection"],
            "durationSeconds": round(duration, 3),
            "durationPass": abs(duration - float(item["durationSeconds"])) <= 0.15,
            "width": video.get("width", 0),
            "height": video.get("height", 0),
            "frameRate": round(frame_rate, 3),
            "videoCodec": video.get("codec_name", ""),
            "pixelFormat": video.get("pix_fmt", ""),
            "colorRange": video.get("color_range", ""),
            "audioCodec": audio.get("codec_name", ""),
            "channels": audio.get("channels", 0),
            "sampleRate": str(audio.get("sample_rate", "")),
            "meanVolumeDb": mean_db,
            "peakVolumeDb": peak_db,
            "audible": mean_db > -40.0 and peak_db > -20.0,
            "clippingSafe": peak_db <= -0.2,
            "captionEvents": event_count,
            "captionPass": event_count == int(item["captionEvents"]) and event_count > 0,
            "captionClean": "AI VOICE" not in caption_text.upper(),
            "videoPreserved": video_preserved,
            "audioPreserved": audio_preserved,
            "disclosureMetadata": metadata_comment == DISCLOSURE,
            "sha256": sha256(output),
            "sizeBytes": int(data["format"]["size"]),
        }
        rows.append(row)
        checks = [
            (row["durationPass"], "duration mismatch"),
            (row["width"] == 1080 and row["height"] == 1920, "not 1080x1920"),
            (abs(frame_rate - 30.0) < 0.02, f"unexpected frame rate {frame_rate}"),
            (row["videoCodec"] == "h264", f"unexpected video codec {row['videoCodec']}"),
            (row["pixelFormat"] == "yuv420p" and row["colorRange"] in {"tv", ""}, f"unsafe color delivery {row['pixelFormat']}/{row['colorRange']}"),
            (row["audioCodec"] == "aac" and row["channels"] == 2 and row["sampleRate"] == "48000", "unexpected audio format"),
            (row["audible"], f"audio too quiet mean={mean_db:.1f} peak={peak_db:.1f}"),
            (row["clippingSafe"], f"audio clipping risk peak={peak_db:.1f}"),
            (row["captionPass"], f"caption mismatch manifest={item['captionEvents']} actual={event_count}"),
            (row["captionClean"], "caption includes a distracting AI VOICE label"),
            (video_preserved, "final video stream differs from selected visual master"),
            (audio_preserved, "final audio stream differs from audited narration master"),
            (row["disclosureMetadata"], "synthetic-narration metadata disclosure missing"),
            (row["sizeBytes"] > 200_000, "suspiciously small output"),
        ]
        failures.extend(f"{output.name}: {message}" for passed, message in checks if not passed)
        print(f"[{position:02d}/74] {output.name} | {row['pixelFormat']}/{row['colorRange']} | mean={mean_db:.1f} peak={peak_db:.1f}", flush=True)

    unique = len({row["sha256"] for row in rows})
    directions = Counter(row["visualDirection"] for row in rows)
    batches = Counter(row["batch"] for row in rows)
    if len(rows) != expected:
        failures.append(f"Audited {len(rows)} files; expected {expected}")
    if unique != len(rows):
        failures.append(f"Only {unique} unique hashes for {len(rows)} files")
    if directions != Counter({"editorial-system": 68, "custom-original": 6}):
        failures.append(f"Unexpected visual direction counts: {dict(directions)}")

    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pass": not failures,
        "files": len(rows),
        "uniqueHashes": unique,
        "visualDirections": dict(directions),
        "batches": dict(batches),
        "meanVolumeRangeDb": [min(row["meanVolumeDb"] for row in rows), max(row["meanVolumeDb"] for row in rows)],
        "peakVolumeRangeDb": [min(row["peakVolumeDb"] for row in rows), max(row["peakVolumeDb"] for row in rows)],
        "failures": failures,
        "videos": rows,
    }
    (ROOT / "editorial-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (ROOT / "editorial-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    pass_count = lambda fn: sum(1 for row in rows if fn(row))
    failure_lines = "- None" if not failures else "\n".join(f"- {failure}" for failure in failures)
    status = "PASS" if not failures else "FAIL"
    report = f"""# Dagric editorial-master audit

Audit date: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}

## Verdict

**{status}: {len(rows)} of {expected} editorial masters audited.**

| Check | Result |
| --- | ---: |
| Unique finished videos | {unique}/{len(rows)} |
| 1080×1920 H.264 at 30 fps | {pass_count(lambda r: r['width'] == 1080 and r['height'] == 1920 and r['videoCodec'] == 'h264' and abs(r['frameRate'] - 30) < .02)}/{len(rows)} |
| Broadcast-safe yuv420p color | {pass_count(lambda r: r['pixelFormat'] == 'yuv420p' and r['colorRange'] in {'tv', ''})}/{len(rows)} |
| Audible AAC stereo at 48 kHz | {pass_count(lambda r: r['audible'] and r['audioCodec'] == 'aac' and r['channels'] == 2 and r['sampleRate'] == '48000')}/{len(rows)} |
| Clipping-safe audio | {pass_count(lambda r: r['clippingSafe'])}/{len(rows)} |
| Sidecar captions present and matched | {pass_count(lambda r: r['captionPass'])}/{len(rows)} |
| Selected video stream preserved | {pass_count(lambda r: r['videoPreserved'])}/{len(rows)} |
| Audited narration stream preserved | {pass_count(lambda r: r['audioPreserved'])}/{len(rows)} |
| Synthetic narration disclosed in metadata | {pass_count(lambda r: r['disclosureMetadata'])}/{len(rows)} |
| Editorial-system videos | {directions.get('editorial-system', 0)} |
| Purpose-built custom videos retained | {directions.get('custom-original', 0)} |

Audio mean-volume range: **{result['meanVolumeRangeDb'][0]:.1f} to {result['meanVolumeRangeDb'][1]:.1f} dB**.<br>
Audio peak range: **{result['peakVolumeRangeDb'][0]:.1f} to {result['peakVolumeRangeDb'][1]:.1f} dB**.

## Failures

{failure_lines}
"""
    (ROOT / "EDITORIAL-VIDEO-AUDIT.md").write_text(report, encoding="utf-8")
    print(f"{status}: {len(rows)}/{expected} files; {unique} unique hashes; {len(failures)} failures")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
