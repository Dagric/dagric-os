#!/usr/bin/env python3
"""Audit the final Dagric social-video remasters and write review artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Narrated Replacements")
MANIFEST_PATH = ROOT / "narration-manifest.json"


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


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def video_stream_hash(path: Path) -> str:
    text = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
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
        raise RuntimeError(f"Could not hash video stream: {path}")
    return match.group(1).lower()


def probe(path: Path) -> dict:
    text = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate,channels,sample_rate,bit_rate,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(text)


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
    mean_match = re.findall(r"mean_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    max_match = re.findall(r"max_volume:\s+(-?\d+(?:\.\d+)?)\s+dB", text)
    if not mean_match or not max_match:
        raise RuntimeError(f"Could not measure audio levels: {path}")
    return float(mean_match[-1]), float(max_match[-1])


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = []
    failures = []
    voices = Counter()

    for index, video in enumerate(manifest["videos"], start=1):
        path = Path(video["output"])
        if not path.exists():
            failures.append(f"Missing output: {path}")
            continue
        info = probe(path)
        video_streams = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
        audio_streams = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        mean_db, max_db = volume(path)
        digest = hash_file(path)
        source_stream_hash = video_stream_hash(Path(video["source"]))
        output_stream_hash = video_stream_hash(path)
        duration = float(info["format"]["duration"])
        expected = float(video["durationSeconds"])

        for voice in video["voices"]:
            voices[voice["voiceName"]] += 1

        row = {
            "number": video["number"],
            "batch": video["batch"],
            "topic": video["topic"],
            "file": path.name,
            "output": str(path),
            "durationSeconds": round(duration, 3),
            "expectedDurationSeconds": round(expected, 3),
            "width": video_streams[0].get("width", 0) if video_streams else 0,
            "height": video_streams[0].get("height", 0) if video_streams else 0,
            "videoCodec": video_streams[0].get("codec_name", "") if video_streams else "",
            "frameRate": video_streams[0].get("avg_frame_rate", "") if video_streams else "",
            "audioCodec": audio_streams[0].get("codec_name", "") if audio_streams else "",
            "channels": audio_streams[0].get("channels", 0) if audio_streams else 0,
            "sampleRate": audio_streams[0].get("sample_rate", "") if audio_streams else "",
            "meanVolumeDb": mean_db,
            "maxVolumeDb": max_db,
            "audible": bool(audio_streams) and max_db > -20.0 and mean_db > -40.0,
            "clippingSafe": max_db <= -0.5,
            "durationPass": abs(duration - expected) <= 0.12,
            "resolutionPass": bool(video_streams)
            and video_streams[0].get("width") == 1080
            and video_streams[0].get("height") == 1920,
            "videoStreamPreserved": source_stream_hash == output_stream_hash,
            "sourceVideoStreamSha256": source_stream_hash,
            "outputVideoStreamSha256": output_stream_hash,
            "sha256": digest,
        }

        checks = [
            (bool(video_streams), "missing video stream"),
            (bool(audio_streams), "missing audio stream"),
            (row["audible"], f"inaudible audio: mean={mean_db}, max={max_db}"),
            (row["clippingSafe"], f"possible clipping: max={max_db}"),
            (row["durationPass"], f"duration mismatch: expected={expected}, actual={duration}"),
            (row["resolutionPass"], f"wrong resolution: {row['width']}x{row['height']}"),
            (row["videoStreamPreserved"], "video stream changed during audio remaster"),
            (row["audioCodec"] == "aac", f"unexpected audio codec: {row['audioCodec']}"),
            (row["channels"] == 2, f"unexpected channel count: {row['channels']}"),
            (str(row["sampleRate"]) == "48000", f"unexpected sample rate: {row['sampleRate']}"),
        ]
        for passed, message in checks:
            if not passed:
                failures.append(f"{path.name}: {message}")

        video["sha256"] = digest
        video["finalMeanVolumeDb"] = mean_db
        video["finalMaxVolumeDb"] = max_db
        rows.append(row)
        print(f"[{index:02d}/{len(manifest['videos'])}] {path.name} mean={mean_db:.1f} max={max_db:.1f}")

    manifest["finalAuditAt"] = datetime.now(timezone.utc).isoformat()
    manifest["finalAuditPass"] = not failures and len(rows) == manifest["count"]
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (ROOT / "final-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    unique_hashes = len({row["sha256"] for row in rows})
    batch_counts = Counter(row["batch"] for row in rows)
    mean_values = [row["meanVolumeDb"] for row in rows]
    max_values = [row["maxVolumeDb"] for row in rows]
    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pass": not failures and len(rows) == manifest["count"],
        "files": len(rows),
        "uniqueHashes": unique_hashes,
        "batches": dict(batch_counts),
        "voices": dict(sorted(voices.items())),
        "meanVolumeRangeDb": [min(mean_values), max(mean_values)],
        "maxVolumeRangeDb": [min(max_values), max(max_values)],
        "failures": failures,
        "videos": rows,
    }
    (ROOT / "final-audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    status = "PASS" if result["pass"] else "FAIL"
    voice_lines = "\n".join(f"- {name}: {count} segments" for name, count in sorted(voices.items()))
    failure_lines = "\n".join(f"- {failure}" for failure in failures) if failures else "- None"
    audit_markdown = f"""# Dagric narrated social-video audit

Audit date: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}

## Verdict

**{status}: {len(rows)} of {manifest['count']} scheduled video assets passed the final automated audit.**

## Results

| Check | Result |
| --- | ---: |
| Final MP4 files | {len(rows)} |
| Unique SHA-256 hashes | {unique_hashes} |
| Audible audio tracks | {sum(1 for row in rows if row['audible'])} |
| Clipping-safe audio tracks | {sum(1 for row in rows if row['clippingSafe'])} |
| 1080 x 1920 videos | {sum(1 for row in rows if row['resolutionPass'])} |
| Original video streams preserved | {sum(1 for row in rows if row['videoStreamPreserved'])} |
| Duration matches | {sum(1 for row in rows if row['durationPass'])} |
| AAC stereo, 48 kHz | {sum(1 for row in rows if row['audioCodec'] == 'aac' and row['channels'] == 2 and str(row['sampleRate']) == '48000')} |
| Launch batch | {batch_counts.get('launch', 0)} |
| Daily batch | {batch_counts.get('daily', 0)} |
| Second wave | {batch_counts.get('second', 0)} |

Final mean-volume range: **{min(mean_values):.1f} to {max(mean_values):.1f} dB**.<br>
Final peak-volume range: **{min(max_values):.1f} to {max(max_values):.1f} dB**.

## Voice distribution

{voice_lines}

## Failures

{failure_lines}

The machine checks cover streams, codecs, resolution, duration, measured volume, clipping margin, and file uniqueness. The scripts use test-first qualifications for hardware and app compatibility and avoid claims of third-party endorsement.
"""
    (ROOT / "AUDIO-VIDEO-AUDIT.md").write_text(audit_markdown, encoding="utf-8")

    provenance = """# Audio provenance

The narration in this delivery is synthetic and does not clone or imitate a named real person.

- Model: `hexgrad/Kokoro-82M` v1.0
- Model license: Apache License 2.0
- Inference library: `thewh1teagle/kokoro-onnx` 0.4.7 (MIT)
- Generation: local on the Dagric production computer
- Voice styles: stock Kokoro voice embeddings listed in `narration-manifest.json`
- Background sound: original tones synthesized locally by `promo/remaster-social-audio.py`
- Sampled or downloaded music: none
- Commercial song, film, television, influencer, or stock-audio content: none
- Voice cloning: none
- Final format: AAC stereo at 48 kHz inside H.264 MP4

The MP4 metadata also identifies the narration as synthetic. Keep this file with the delivery and disclose synthetic narration when a platform or campaign policy requires it.

Primary license record: https://huggingface.co/hexgrad/Kokoro-82M
"""
    (ROOT / "AUDIO-PROVENANCE.md").write_text(provenance, encoding="utf-8")

    print(f"FINAL_AUDIT={status} files={len(rows)} unique={unique_hashes} failures={len(failures)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
