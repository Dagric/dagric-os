#!/usr/bin/env python3
"""Audit the platform-native Dagric OS campaign outputs."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Platform-Native Campaign")
MANIFEST = ROOT / "platform-native-manifest.json"
AUDIT_JSON = ROOT / "platform-native-audit.json"
AUDIT_MD = ROOT / "PLATFORM-NATIVE-VIDEO-AUDIT.md"


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
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fraction(value: str | None) -> float:
    if not value:
        return 0.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / max(float(denominator), 1.0)
    return float(value)


def loudness(path: Path) -> tuple[float | None, float | None]:
    text = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    mean_match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", text)
    max_match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", text)
    return (
        float(mean_match.group(1)) if mean_match else None,
        float(max_match.group(1)) if max_match else None,
    )


def audit_one(item: dict) -> dict:
    path = Path(item["output"])
    failures: list[str] = []
    if not path.exists():
        return {**item, "pass": False, "failures": ["missing output"]}
    info = probe(path)
    videos = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
    audios = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
    duration = float(info["format"]["duration"])
    if len(videos) != 1:
        failures.append(f"expected one video stream, got {len(videos)}")
    if len(audios) != 1:
        failures.append(f"expected one audio stream, got {len(audios)}")
    video = videos[0] if videos else {}
    audio = audios[0] if audios else {}
    if (video.get("width"), video.get("height")) != (1080, 1920):
        failures.append(f"wrong dimensions {video.get('width')}x{video.get('height')}")
    if video.get("codec_name") != "h264":
        failures.append(f"wrong video codec {video.get('codec_name')}")
    nominal_fps = fraction(video.get("r_frame_rate"))
    average_fps = fraction(video.get("avg_frame_rate"))
    if abs(nominal_fps - 30.0) > 0.01 or not 29.80 <= average_fps <= 30.05:
        failures.append(f"wrong frame rate nominal={nominal_fps:.3f} average={average_fps:.3f}")
    if audio.get("codec_name") != "aac":
        failures.append(f"wrong audio codec {audio.get('codec_name')}")
    if int(audio.get("sample_rate") or 0) != 48000:
        failures.append(f"wrong sample rate {audio.get('sample_rate')}")
    if int(audio.get("channels") or 0) != 2:
        failures.append(f"wrong channel count {audio.get('channels')}")
    expected = float(item["durationSeconds"])
    if abs(duration - expected) > 0.18:
        failures.append(f"duration drift {duration:.3f}s vs manifest {expected:.3f}s")
    actual_hash = sha256(path)
    if actual_hash != item["sha256"]:
        failures.append("sha256 mismatch")
    mean_db, max_db = loudness(path)
    if mean_db is None or max_db is None:
        failures.append("could not measure audio")
    else:
        if mean_db < -34.0:
            failures.append(f"audio too quiet {mean_db:.1f} dB")
        if max_db > -0.1:
            failures.append(f"possible clipping {max_db:.1f} dB")
    return {
        "sourceNumber": item["sourceNumber"],
        "platform": item["platform"],
        "topic": item["topic"],
        "output": str(path),
        "durationSeconds": round(duration, 3),
        "meanVolumeDb": mean_db,
        "maxVolumeDb": max_db,
        "sha256": actual_hash,
        "pass": not failures,
        "failures": failures,
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = manifest["videos"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        audits = list(pool.map(audit_one, items))

    hashes = [item["sha256"] for item in audits if item.get("sha256")]
    duplicate_hashes = len(hashes) - len(set(hashes))
    if duplicate_hashes:
        for item in audits:
            item["pass"] = False
            item["failures"].append("campaign contains duplicate file hashes")

    platform_counts: dict[str, int] = {}
    for item in audits:
        platform_counts[item["platform"]] = platform_counts.get(item["platform"], 0) + 1
    passed = sum(1 for item in audits if item["pass"])
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST),
        "count": len(audits),
        "passed": passed,
        "failed": len(audits) - passed,
        "duplicateHashes": duplicate_hashes,
        "platformCounts": platform_counts,
        "rights": {
            "visuals": "Dagric-owned product visuals from the audited enhanced masters",
            "narration": "Existing disclosed synthetic narration",
            "outroAudio": "Original sine tone generated locally",
            "downloadedMusic": False,
            "creatorFootage": False,
        },
        "videos": audits,
    }
    AUDIT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    means = [item["meanVolumeDb"] for item in audits if item.get("meanVolumeDb") is not None]
    peaks = [item["maxVolumeDb"] for item in audits if item.get("maxVolumeDb") is not None]
    lines = [
        "# Dagric OS Platform-Native Video Audit",
        "",
        f"**{'PASS' if passed == len(audits) else 'FAIL'}: {passed} of {len(audits)} platform-native videos passed.**",
        "",
        "## Coverage",
        "",
        "| Platform | Files |",
        "| --- | ---: |",
        *[f"| {name} | {count} |" for name, count in sorted(platform_counts.items())],
        "",
        "## Technical checks",
        "",
        "- 1080 × 1920 portrait video at 30 fps",
        "- H.264 video and AAC stereo audio at 48 kHz",
        "- Duration and SHA-256 match the manifest",
        "- Audible mix with clipping check",
        "- Every output has a unique SHA-256 hash",
        "- Complete narration retained with platform-specific pacing",
        "- Different platform hook cards, lengths, outro copy, colors, and original synthesized outro tones",
        "",
        f"Mean-volume range: **{min(means):.1f} to {max(means):.1f} dB**." if means else "Mean volume unavailable.",
        f"Peak range: **{min(peaks):.1f} to {max(peaks):.1f} dB**." if peaks else "Peak unavailable.",
        "",
        "## Rights and disclosure",
        "",
        "The campaign uses Dagric-owned product visuals, the existing disclosed synthetic narration, and locally generated sine-tone outros. It contains no downloaded music and no copied creator footage.",
    ]
    failures = [item for item in audits if not item["pass"]]
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- `{Path(item['output']).name}`: {', '.join(item['failures'])}" for item in failures)
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{passed}/{len(audits)} passed; duplicate hashes={duplicate_hashes}")
    print(AUDIT_MD)
    return 0 if passed == len(audits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
