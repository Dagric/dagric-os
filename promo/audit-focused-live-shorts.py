#!/usr/bin/env python3
"""Strict audit for the focused live-VM Dagric short batch."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\focused-live-shorts")
MANIFEST = ROOT / "focused-live-shorts-manifest.json"


def run(args: list[str]) -> str:
    result = subprocess.run(
        args, check=True, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return (result.stdout or "") + (result.stderr or "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,channels,sample_rate",
        "-of", "json", str(path),
    ]))


def motion(path: Path, start: float = 0.0, duration: float | None = None) -> tuple[int, int]:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start:
        args.extend(["-ss", f"{start:.3f}"])
    args.extend(["-i", str(path)])
    if duration is not None:
        args.extend(["-t", f"{duration:.3f}"])
    args.extend([
        "-map", "0:v:0", "-an", "-vf", "fps=1,scale=160:90,format=gray",
        "-f", "framemd5", "-",
    ])
    output = run(args)
    hashes: list[str] = []
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
    mean = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", output)
    peak = re.search(r"max_volume:\s*(-?[0-9.]+) dB", output)
    if not mean or not peak:
        raise RuntimeError(f"Could not measure audio in {path}")
    return float(mean.group(1)), float(peak.group(1))


def sustained(frames: int, unique: int) -> bool:
    return frames >= 10 and unique >= max(4, math.ceil(frames * 0.40))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = Path(manifest["source"])
    receipt_path = Path(manifest["captureReceipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    latest_iso = max(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda path: path.stat().st_mtime,
    )
    policy = manifest.get("visualPolicy", {})
    global_checks = {
        "sourceHash": manifest.get("sourceSha256") == sha256(source) == receipt.get("sha256"),
        "captureMode": manifest.get("captureMode") == receipt.get("captureMode") == "continuous-vnc-stream",
        "continuousEncoding": receipt.get("continuousFrameEncoding") is True,
        "newestIsoPath": Path(receipt.get("iso", "")).resolve() == latest_iso.resolve(),
        "newestIsoHash": manifest.get("isoSha256") == receipt.get("isoSha256") == sha256(latest_iso),
        "vmCopyHash": sha256(REPO / "out" / "_testing.iso") == sha256(latest_iso),
        "continuousFootagePolicy": policy.get("continuousFootageRequired") is True,
        "noSnapshotsPolicy": policy.get("snapshotsAllowed") is False,
        "noGeneratedVideoPolicy": policy.get("generatedVideoAllowed") is False,
        "oneLayerPolicy": policy.get("maximumSimultaneousProductVideoLayers") == 1,
        "noMontagePolicy": policy.get("montageAllowed") is False,
        "oneNaturalVoice": manifest.get("voice", {}).get("voiceId") == "am_michael",
        "noTimeStretch": manifest.get("voice", {}).get("timeStretched") is False,
        "syntheticVoiceDisclosed": manifest.get("voice", {}).get("syntheticVoiceDisclosure") is True,
        "allNarrationFits": all(item.get("fitsWindow") is True for item in manifest.get("narration", [])),
    }
    records: list[dict] = []
    errors: list[dict] = []
    digests: set[str] = set()
    for index, item in enumerate(manifest.get("outputs", []), start=1):
        path = Path(item["output"])
        info = probe(path)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
        expected = (1080, 1920) if item["aspect"] == "vertical" else (1920, 1080)
        frames, unique = motion(path)
        source_frames, source_unique = motion(
            source, float(item["sourceStartSeconds"]), float(item["sourceDurationSeconds"])
        )
        mean, peak = audio_levels(path)
        digest = sha256(path)
        checks = {
            **global_checks,
            "singleContinuousSourceInterval": item.get("source") == str(source),
            "singleProductVideoLayer": item.get("visibleProductVideoLayers") == 1,
            "noSnapshotInputs": item.get("snapshotInputs") == [],
            "noGeneratedVisuals": item.get("generatedVisuals") is False,
            "sourceMotion": sustained(source_frames, source_unique),
            "dimensions": (video["width"], video["height"]) == expected,
            "h264": video["codec_name"] == "h264",
            "thirtyFps": video["avg_frame_rate"] == "30/1",
            "yuv420p": video.get("pix_fmt") == "yuv420p",
            "aacStereo48k": audio["codec_name"] == "aac" and audio["channels"] == 2 and int(audio["sample_rate"]) == 48000,
            "duration": abs(float(info["format"]["duration"]) - float(item["sourceDurationSeconds"])) <= 0.12,
            "movingPicture": sustained(frames, unique),
            "audible": mean > -40.0 and peak > -10.0,
            "notClipped": peak <= 0.0,
            "matchingHash": item.get("sha256") == digest,
            "captionSidecar": path.with_suffix(".srt").is_file(),
            "uniqueFile": digest not in digests,
        }
        digests.add(digest)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            errors.append({"file": str(path), "failed": failed})
        records.append({
            "file": str(path),
            "passed": not failed,
            "durationSeconds": round(float(info["format"]["duration"]), 3),
            "dimensions": f"{video['width']}x{video['height']}",
            "motionCoverage": round(unique / max(1, frames), 3),
            "sourceMotionCoverage": round(source_unique / max(1, source_frames), 3),
            "meanVolumeDb": mean,
            "maxVolumeDb": peak,
            "checks": checks,
        })
        print(f"[{index:02d}/{len(manifest['outputs']):02d}] {'PASS' if not failed else 'FAIL'} {path.name}", flush=True)
    if len(records) != 12:
        errors.append({"file": str(MANIFEST), "failed": ["expectedTwelveOutputs"]})
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
    lines = [
        "# Focused Dagric live-short audit", "",
        f"Result: **{'PASS' if not errors else 'FAIL'}**", "",
        f"Files checked: {len(records)} MP4 masters plus matching SRT captions.", "",
        "Each video uses one continuous interval from a receipt-backed newest-ISO VM recording. The audit rejects snapshots, generated UI, montage edits, multiple product-video layers, insufficient motion, missing captions, incorrect delivery formats, clipped/inaudible audio, narration time-stretching, or missing synthetic-voice disclosure.",
    ]
    if errors:
        lines.extend(["", "Failures:"])
        lines.extend(f"- {item['file']}: {', '.join(item['failed'])}" for item in errors)
    (ROOT / "AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError(f"Focused-short audit failed with {len(errors)} error records")
    print("PASS: all 12 focused live-footage masters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
