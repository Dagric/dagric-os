#!/usr/bin/env python3
"""Technical and motion audit for the real Dagric OS footage delivery."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\finished")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
CAPTURE_MODE = "continuous-vnc-stream"


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


def motion_sample(path: Path, start: float = 0.0, duration: float | None = None) -> tuple[int, int]:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start:
        args.extend(["-ss", f"{start:.3f}"])
    if duration is not None:
        args.extend(["-t", f"{duration:.3f}"])
    args.extend([
        "-i", str(path), "-map", "0:v:0", "-an",
        "-vf", "fps=1,scale=160:90,format=gray", "-f", "framemd5", "-",
    ])
    output = run(args)
    hashes = []
    for line in output.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = [part.strip() for part in line.split(",")]
        if len(fields) >= 6:
            hashes.append(fields[-1])
    return len(hashes), len(set(hashes))


def has_sustained_motion(frame_count: int, unique_frames: int) -> bool:
    return frame_count >= 3 and unique_frames >= max(3, math.ceil(frame_count * 0.40))


def capture_receipt_valid(source: Path, receipt_path: Path) -> bool:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        return all([
            receipt.get("captureMode") == CAPTURE_MODE,
            receipt.get("continuousFrameEncoding") is True,
            receipt.get("asynchronousFramebufferRefresh") is True,
            receipt.get("snapshotInputs") == [],
            int(receipt.get("targetFramesPerSecond", 0)) >= 20,
            Path(receipt.get("output", "")).resolve() == source.resolve(),
            receipt.get("sha256") == sha256(source),
        ])
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


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
    manifest_path = ROOT / "real-footage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    policy = manifest.get("visualPolicy", {})
    policy_valid = all([
        policy.get("continuousFootageRequired") is True,
        policy.get("snapshotsAllowed") is False,
        policy.get("stillImagesAllowedAsProductVisuals") is False,
        policy.get("generatedVideoAllowed") is False,
        policy.get("captureReceiptsRequired") is True,
        policy.get("maximumSimultaneousProductVideoLayers") == 1,
    ])
    output_manifest = {Path(item["output"]).resolve(): item for item in manifest.get("outputs", [])}
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
        provenance = output_manifest.get(path.resolve(), {})
        source = Path(provenance.get("source", ""))
        source_is_video = source.suffix.lower() in VIDEO_EXTENSIONS and source.is_file()
        receipt_paths = [Path(value) for value in provenance.get("captureReceipts", [])]
        source_type = provenance.get("visualSourceType")
        if source_type == "continuous-live-vm-montage":
            segment_sources = [Path(item["source"]) for item in manifest.get("montageSegments", [])]
            receipts_valid = (
                len(segment_sources) > 0
                and len(receipt_paths) == len(segment_sources)
                and all(capture_receipt_valid(segment, receipt) for segment, receipt in zip(segment_sources, receipt_paths))
            )
        else:
            receipts_valid = (
                len(receipt_paths) == 1
                and source_is_video
                and capture_receipt_valid(source, receipt_paths[0])
            )
        if source_is_video:
            source_frame_count, source_unique_frames = motion_sample(
                source,
                float(provenance.get("visualSourceStartSeconds", 0.0)),
                float(provenance.get("visualSourceDurationSeconds", 0.0)) or None,
            )
        else:
            source_frame_count, source_unique_frames = 0, 0
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
            "movingPicture": has_sustained_motion(frame_count, unique_frames),
            "manifestEntry": bool(provenance),
            "realtimePolicy": policy_valid,
            "realtimeVisualSource": source_type in {"continuous-live-vm-video", "continuous-live-vm-montage"},
            "captureReceipts": receipts_valid and provenance.get("captureReceiptsVerified") is True,
            "sourceIsVideo": source_is_video,
            "sourceHasMotion": has_sustained_motion(source_frame_count, source_unique_frames),
            "noSnapshotInputs": provenance.get("snapshotInputs") == [],
            "noGeneratedVisuals": provenance.get("generatedVisuals") is False,
            "singleProductVideoLayer": provenance.get("visibleProductVideoLayers") == 1,
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
            "motionCoverage": round(unique_frames / max(1, frame_count), 3),
            "visualSource": str(source) if source else None,
            "sourceSampledFrames": source_frame_count,
            "sourceUniqueSampledFrames": source_unique_frames,
            "sourceMotionCoverage": round(source_unique_frames / max(1, source_frame_count), 3),
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
        "Checks: dimensions, H.264/yuv420p, 30 fps, AAC stereo at 48 kHz, audible/non-clipped audio, sustained motion in the final and its underlying video segment, continuous-capture receipts bound to source hashes, video-only provenance, exactly one visible product-video layer, no snapshot inputs, no generated visuals, caption sidecars, and unique file hashes.",
        "",
        "Required policy: product visuals must originate in continuous Dagric OS Pro live-ISO VM sessions. Text and caption overlays are permitted, but still screenshots and generated replacement visuals are rejected. A passing capture is still not a claim about physical-hardware compatibility.",
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
