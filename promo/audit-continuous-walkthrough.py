#!/usr/bin/env python3
"""Audit the single-session, newest-ISO Dagric walkthrough delivery."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\continuous-walkthrough")
MANIFEST = ROOT / "09-full-live-walkthrough-manifest.json"


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


def motion(path: Path) -> tuple[int, int]:
    output = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-an", "-vf", "fps=1,scale=160:90,format=gray",
        "-f", "framemd5", "-",
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
    mean = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", output)
    peak = re.search(r"max_volume:\s*(-?[0-9.]+) dB", output)
    if not mean or not peak:
        raise RuntimeError(f"Could not measure audio in {path}")
    return float(mean.group(1)), float(peak.group(1))


def loudness(path: Path) -> tuple[float, float, float]:
    output = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", "loudnorm=I=-16:LRA=7:TP=-1.5:print_format=json", "-f", "null", "NUL",
    ])
    integrated = re.search(r'"input_i"\s*:\s*"(-?[0-9.]+)"', output)
    true_peak = re.search(r'"input_tp"\s*:\s*"(-?[0-9.]+)"', output)
    range_value = re.search(r'"input_lra"\s*:\s*"(-?[0-9.]+)"', output)
    if not integrated or not true_peak or not range_value:
        raise RuntimeError(f"Could not measure EBU R128 loudness in {path}")
    return float(integrated.group(1)), float(true_peak.group(1)), float(range_value.group(1))


def freeze_profile(path: Path, duration: float) -> tuple[float, float, int]:
    output = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:v:0", "-an",
        "-vf", "freezedetect=noise=-45dB:d=1.0", "-f", "null", "NUL",
    ])
    freezes = [float(value) for value in re.findall(r"freeze_duration:\s*([0-9.]+)", output)]
    starts = [float(value) for value in re.findall(r"freeze_start:\s*([0-9.]+)", output)]
    ends = [float(value) for value in re.findall(r"freeze_end:\s*([0-9.]+)", output)]
    if len(starts) > len(ends):
        freezes.append(max(0.0, duration - starts[-1]))
    return max(freezes, default=0.0), sum(freezes), len(freezes)


def srt_seconds(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def caption_metrics(path: Path) -> tuple[int, int, float, int]:
    blocks = re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8-sig").strip())
    max_line_chars = 0
    max_lines = 0
    max_cps = 0.0
    events = 0
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start_text, end_text = lines[1].split(" --> ", 1)
        text_lines = [re.sub(r"<[^>]+>", "", line).strip() for line in lines[2:] if line.strip()]
        if not text_lines:
            continue
        text = " ".join(text_lines)
        span = max(0.001, srt_seconds(end_text) - srt_seconds(start_text))
        max_line_chars = max(max_line_chars, max(len(line) for line in text_lines))
        max_lines = max(max_lines, len(text_lines))
        max_cps = max(max_cps, len(text) / span)
        events += 1
    return max_line_chars, max_lines, max_cps, events


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = Path(manifest["source"])
    receipt_path = Path(manifest["captureReceipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    latest_iso = max(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda path: path.stat().st_mtime,
    )
    source_frames, source_unique = motion(source)
    source_motion = source_unique / max(1, source_frames)
    source_duration = float(probe(source)["format"]["duration"])
    source_longest_freeze, source_frozen_seconds, source_freeze_events = freeze_profile(
        source, source_duration
    )
    global_checks = {
        "singleUninterruptedSource": manifest.get("singleUninterruptedSource") is True,
        "singleProductVideoLayer": manifest.get("visibleProductVideoLayers") == 1,
        "noSnapshotInputs": manifest.get("snapshotInputs") == [],
        "noGeneratedVisuals": manifest.get("generatedVisuals") is False,
        "sourceHash": manifest.get("sourceSha256") == sha256(source) == receipt.get("sha256"),
        "captureMode": receipt.get("captureMode") == "continuous-vnc-stream",
        "continuousEncoding": receipt.get("continuousFrameEncoding") is True,
        "sourceMotion": source_frames >= 150 and source_motion >= 0.40,
        "sourceFlowCadence": source_longest_freeze <= 12.0,
        "newestIsoPath": Path(receipt.get("iso", "")).resolve() == latest_iso.resolve(),
        "newestIsoHash": receipt.get("isoSha256") == sha256(latest_iso),
        "vmCopyHash": sha256(REPO / "out" / "_testing.iso") == sha256(latest_iso),
        "oneNaturalVoice": manifest.get("voice", {}).get("voiceId") == "am_michael",
        "noTimeStretch": manifest.get("voice", {}).get("timeStretched") is False,
        "syntheticVoiceDisclosed": manifest.get("voice", {}).get("syntheticVoiceDisclosure") is True,
        "allNarrationFits": all(item.get("fitsWindow") is True for item in manifest.get("narration", [])),
    }
    records = []
    errors = []
    for item in manifest.get("outputs", []):
        path = Path(item["output"])
        info = probe(path)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
        expected = (1080, 1920) if item["aspect"] == "vertical" else (1920, 1080)
        frames, unique = motion(path)
        mean, peak = audio_levels(path)
        integrated_loudness, true_peak, loudness_range = loudness(path)
        duration = float(info["format"]["duration"])
        longest_freeze, frozen_seconds, freeze_events = freeze_profile(path, duration)
        max_caption_chars, max_caption_lines, max_caption_cps, caption_events = caption_metrics(
            path.with_suffix(".srt")
        )
        checks = {
            **global_checks,
            "dimensions": (video["width"], video["height"]) == expected,
            "h264": video["codec_name"] == "h264",
            "thirtyFps": video["avg_frame_rate"] == "30/1",
            "yuv420p": video.get("pix_fmt") == "yuv420p",
            "aacStereo48k": audio["codec_name"] == "aac" and audio["channels"] == 2 and int(audio["sample_rate"]) == 48000,
            "duration": abs(float(info["format"]["duration"]) - 198.0) <= 0.1,
            "movingPicture": frames >= 150 and unique >= max(3, math.ceil(frames * 0.40)),
            "audible": mean > -40.0 and peak > -10.0,
            "notClipped": peak <= 0.0,
            "integratedLoudness": -17.5 <= integrated_loudness <= -14.5,
            "truePeakHeadroom": true_peak <= -1.0,
            "outputContinuity": longest_freeze <= 25.0,
            "captionLineLength": max_caption_chars <= 42,
            "captionLineCount": max_caption_lines <= 2,
            "captionReadingSpeed": max_caption_cps <= 20.0,
            "matchingHash": item.get("sha256") == sha256(path),
            "captionSidecar": path.with_suffix(".srt").is_file(),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            errors.append({"file": str(path), "failed": failed})
        records.append({
            "file": str(path), "passed": not failed,
            "durationSeconds": round(float(info["format"]["duration"]), 3),
            "dimensions": f"{video['width']}x{video['height']}",
            "motionCoverage": round(unique / max(1, frames), 3),
            "sourceMotionCoverage": round(source_motion, 3),
            "sourceLongestFreezeSeconds": round(source_longest_freeze, 3),
            "sourceFrozenSecondsAtMinus45Db": round(source_frozen_seconds, 3),
            "sourceFreezeEvents": source_freeze_events,
            "meanVolumeDb": mean, "maxVolumeDb": peak,
            "integratedLoudnessLufs": integrated_loudness,
            "truePeakDbtp": true_peak,
            "loudnessRangeLu": loudness_range,
            "longestFreezeSeconds": round(longest_freeze, 3),
            "frozenSecondsAtMinus45Db": round(frozen_seconds, 3),
            "freezeEvents": freeze_events,
            "maxCaptionCharactersPerLine": max_caption_chars,
            "maxCaptionLines": max_caption_lines,
            "maxCaptionCharactersPerSecond": round(max_caption_cps, 3),
            "captionEvents": caption_events,
            "checks": checks,
        })
        print(f"{'PASS' if not failed else 'FAIL'} {path.name}")
    if len(records) != 2:
        errors.append({"file": str(MANIFEST), "failed": ["expectedTwoOutputs"]})
    report = {
        "auditedAt": datetime.now(timezone.utc).isoformat(),
        "passed": not errors,
        "errorCount": len(errors),
        "errors": errors,
        "records": records,
    }
    (ROOT / "audit-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Continuous Dagric walkthrough audit", "",
        f"Result: **{'PASS' if not errors else 'FAIL'}**", "",
        "This audit verifies one uninterrupted newest-ISO VM source, source and ISO hashes, continuous encoding, sustained source/output motion, exactly one product-video layer, no snapshots or generated UI, natural-rate single-voice narration without time-stretching, explicit synthetic-voice disclosure, caption line length and reading speed, freeze cadence, formats, dimensions, and EBU R128 audio levels.",
    ]
    if errors:
        lines.extend(["", "Failures:"])
        lines.extend(f"- {item['file']}: {', '.join(item['failed'])}" for item in errors)
    (ROOT / "AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError(f"Walkthrough audit failed with {len(errors)} error records")
    print("PASS: both uninterrupted walkthrough masters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
