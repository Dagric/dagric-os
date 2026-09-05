#!/usr/bin/env python3
"""Inventory and audit every Dagric MP4 without treating legacy renders as publish-ready.

The technical scan is intentionally broader than the strict delivery audits. It
finds every MP4 below the Dagric video root, probes its streams, samples motion,
hashes the file, and assigns a workflow tier. Only masters backed by one of the
strict real-VM audit reports can pass the current no-snapshot publishing policy.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
REPORT_ROOT = VIDEO_ROOT / "All Video Audit"
REAL_VM_ROOT = VIDEO_ROOT / "Real VM Footage"
CURRENT_AUDIT_REPORTS = (
    REAL_VM_ROOT / "finished" / "audit-report.json",
    REAL_VM_ROOT / "continuous-walkthrough" / "audit-report.json",
    REAL_VM_ROOT / "focused-live-shorts" / "audit-report.json",
)
CAPTURE_MODE = "continuous-vnc-stream"
MOTION_SAMPLES = 9


def run(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fps_value(rate: str | None) -> float:
    if not rate or "/" not in rate:
        return 0.0
    numerator, denominator = rate.split("/", 1)
    try:
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return 0.0


def load_current_audit_records() -> dict[Path, dict[str, Any]]:
    records: dict[Path, dict[str, Any]] = {}
    for report_path in CURRENT_AUDIT_REPORTS:
        if not report_path.is_file():
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in report.get("records", []):
            file_value = item.get("file")
            if file_value:
                video_path = Path(file_value).resolve()
                quality_path = video_path.with_suffix(".quality-audit.json")
                quality: dict[str, Any] = {}
                if quality_path.is_file():
                    try:
                        quality = json.loads(quality_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        quality = {}
                records[video_path] = {
                    "auditReport": str(report_path),
                    "strictAuditPassed": bool(item.get("passed")),
                    "strictChecks": item.get("checks", {}),
                    "qualityAuditReport": str(quality_path) if quality_path.is_file() else None,
                    "qualityAutomatedPassed": quality.get("automatedPassed") is True,
                    "qualityManualPassed": quality.get("manualPassed") is True,
                    "qualityPublishReady": quality.get("publishReady") is True,
                }
    return records


def classify(path: Path, current_records: dict[Path, dict[str, Any]]) -> tuple[str, str]:
    resolved = path.resolve()
    relative = path.relative_to(VIDEO_ROOT)
    parts = tuple(part.lower() for part in relative.parts)
    if resolved in current_records:
        return "current-master", "Strict continuous-capture audit record found"
    if parts[0] == "real vm footage":
        if any(part in {"raw", "raw-highres", "raw-realtime", "work"} for part in parts):
            return "source-intermediate", "Raw or working real-VM footage"
        if any("test" in part for part in parts):
            return "test", "Recorder or display test"
        if "finished" in parts or "continuous-walkthrough" in parts or "focused-live-shorts" in parts:
            return "unverified-master", "Delivery location without a passing strict audit record"
        return "test", "Unclassified file in the real-VM working area"
    if parts[0] == "source footage":
        return "source-intermediate", "Source footage, not a final master"
    if any(part in {"raw", "work", "_segments", "source", "sources"} for part in parts):
        return "legacy-intermediate", "Legacy raw, working, or platform segment file"
    if any("test" in part or "rejected" in part for part in parts):
        return "test", "Legacy test or rejected capture"
    if parts[0] in {
        "editorial masters",
        "enhanced masters",
        "narrated replacements",
        "platform-native campaign",
        "human campaign",
        "september 2-3 posts",
    }:
        return "legacy-master", "Predates the continuous-footage proof requirement"
    if parts[0] in {"editorial visuals", "editorial samples"}:
        return "legacy-intermediate", "Legacy visual or editorial sample"
    return "unclassified", "No workflow classification rule matched"


def probe(path: Path) -> dict[str, Any]:
    completed = run([
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration,size,format_name:stream=index,codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,channels,sample_rate",
        "-of", "json", str(path),
    ])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace").strip())
    return json.loads(completed.stdout.decode("utf-8", errors="replace"))


def motion_sample(path: Path, duration: float) -> tuple[int, int, float]:
    # Nine uniformly spaced grayscale frames provide a fast library-wide signal.
    # This detects motion, not provenance; animated text over a still can move.
    sample_fps = MOTION_SAMPLES / max(1.0, duration)
    completed = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-an",
        "-vf", f"fps={sample_fps:.8f},scale=160:90:flags=fast_bilinear,format=gray",
        "-frames:v", str(MOTION_SAMPLES), "-f", "framemd5", "-",
    ])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace").strip())
    hashes: list[str] = []
    for line in completed.stdout.decode("utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) >= 6:
            hashes.append(fields[-1])
    unique = len(set(hashes))
    return len(hashes), unique, unique / max(1, len(hashes))


def audit_one(path: Path, current_records: dict[Path, dict[str, Any]]) -> dict[str, Any]:
    relative = path.relative_to(VIDEO_ROOT)
    tier, tier_reason = classify(path, current_records)
    record: dict[str, Any] = {
        "path": str(path),
        "relativePath": str(relative),
        "topFolder": relative.parts[0],
        "tier": tier,
        "tierReason": tier_reason,
        "sizeBytes": path.stat().st_size,
        "sha256": "",
        "probePassed": False,
        "motionSamplePassed": False,
        "technicalPassed": False,
        "policyPassed": False,
        "qualityAutomatedPassed": False,
        "qualityManualPassed": False,
        "qualityPublishReady": False,
        "publishReady": False,
        "failures": [],
        "warnings": [],
    }
    try:
        record["sha256"] = sha256(path)
        info = probe(path)
        streams = info.get("streams", [])
        videos = [stream for stream in streams if stream.get("codec_type") == "video"]
        audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not videos:
            raise RuntimeError("No video stream")
        video = videos[0]
        audio = audios[0] if audios else {}
        duration = float(info.get("format", {}).get("duration", 0.0) or 0.0)
        sampled, unique, coverage = motion_sample(path, duration)
        width = int(video.get("width", 0) or 0)
        height = int(video.get("height", 0) or 0)
        fps = fps_value(video.get("avg_frame_rate"))
        record.update({
            "probePassed": True,
            "durationSeconds": round(duration, 3),
            "width": width,
            "height": height,
            "orientation": "vertical" if height > width else "landscape" if width > height else "square",
            "frameRate": round(fps, 3),
            "videoCodec": video.get("codec_name", ""),
            "pixelFormat": video.get("pix_fmt", ""),
            "videoStreamCount": len(videos),
            "audioStreamCount": len(audios),
            "audioCodec": audio.get("codec_name", ""),
            "audioChannels": int(audio.get("channels", 0) or 0),
            "audioSampleRate": int(audio.get("sample_rate", 0) or 0),
            "sampledFrames": sampled,
            "uniqueSampledFrames": unique,
            "motionCoverage": round(coverage, 3),
            "motionSamplePassed": sampled >= 3 and unique >= 3 and coverage >= 0.34,
        })
        checks = {
            "duration": duration >= 0.5,
            "dimensions": width >= 320 and height >= 240,
            "frameRate": fps >= 20.0,
            "videoCodec": bool(video.get("codec_name")),
            "motionObserved": bool(record["motionSamplePassed"]),
            "size": path.stat().st_size >= 50_000,
        }
        if tier in {"current-master", "legacy-master"}:
            checks.update({
                "deliveryDimensions": (width, height) in {(1080, 1920), (1920, 1080)},
                "h264": video.get("codec_name") == "h264",
                "yuv420p": video.get("pix_fmt") == "yuv420p",
                "thirtyFps": abs(fps - 30.0) <= 0.05,
                "audioPresent": len(audios) >= 1,
                "aac": audio.get("codec_name") == "aac",
            })
        record["technicalChecks"] = checks
        record["failures"] = [name for name, passed in checks.items() if not passed]
        record["technicalPassed"] = not record["failures"]

        strict = current_records.get(path.resolve())
        if strict:
            record.update(strict)
            strict_checks = strict.get("strictChecks", {})
            required = {
                "strictAuditPassed": strict.get("strictAuditPassed") is True,
                "singleProductVideoLayer": strict_checks.get("singleProductVideoLayer") is True,
                "noSnapshotInputs": strict_checks.get("noSnapshotInputs") is True,
                "noGeneratedVisuals": strict_checks.get("noGeneratedVisuals") is True,
                "sourceHasMotion": (
                    strict_checks.get("sourceHasMotion") is True
                    or strict_checks.get("sourceMotion") is True
                ),
                "captureProof": (
                    strict_checks.get("captureReceipts") is True
                    or strict_checks.get("captureMode") is True
                ),
            }
            record["policyChecks"] = required
            record["policyPassed"] = all(required.values())
            if record.get("qualityPublishReady") is not True:
                record["warnings"].append(
                    "Strict capture policy passed, but the final video quality/manual gate has not approved publishing."
                )
        else:
            record["strictAuditPassed"] = False
            record["policyChecks"] = {
                "strictAuditPassed": False,
                "singleProductVideoLayer": False,
                "noSnapshotInputs": False,
                "noGeneratedVisuals": False,
                "sourceHasMotion": False,
                "captureProof": False,
            }
            if tier in {"legacy-master", "legacy-intermediate"}:
                record["warnings"].append(
                    "Motion sampling cannot prove the product visual is live; hold until rebuilt from receipt-backed VM footage."
                )
        record["publishReady"] = (
            tier == "current-master"
            and record["technicalPassed"]
            and record["policyPassed"]
            and record.get("qualityPublishReady") is True
        )
    except Exception as error:  # noqa: BLE001 - one bad file must not abort the library audit
        record["failures"].append(f"auditError: {error}")
    return record


def markdown_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    tiers = report["tiers"]
    folders = report["folders"]
    failures = report["technicalFailureExamples"]
    duplicates = report["duplicateGroups"]
    lines = [
        "# Dagric complete video-library audit",
        "",
        f"Audit time: {report['auditedAt']}",
        "",
        "## Verdict",
        "",
        f"**{counts['publishReady']} current masters are publish-ready.** "
        f"The scan covered all **{counts['total']} MP4 files** in the Dagric video root.",
        "",
        "Technical motion is not accepted as proof of live product footage. A video must also have a passing strict audit tied to continuous VM capture receipts, one visible product-video layer, no snapshots, no generated UI, and a completed automated plus manual quality review.",
        "",
        "## Library totals",
        "",
        "| Result | Count |",
        "| --- | ---: |",
        f"| Total MP4 files | {counts['total']} |",
        f"| Technically passed | {counts['technicalPassed']} |",
        f"| Technically failed | {counts['technicalFailed']} |",
        f"| Motion observed | {counts['motionObserved']} |",
        f"| Low/static motion signal | {counts['lowMotion']} |",
        f"| Continuous-footage policy passed | {counts['policyPassed']} |",
        f"| Publish-ready current masters | {counts['publishReady']} |",
        f"| Exact duplicate-hash groups | {len(duplicates)} |",
        "",
        "## Workflow tiers",
        "",
        "| Tier | Count | Publishing decision |",
        "| --- | ---: | --- |",
    ]
    for tier, count in sorted(tiers.items()):
        decision = "Eligible only when all checks pass" if tier == "current-master" else "Hold / not a publishing master"
        lines.append(f"| {tier} | {count} | {decision} |")
    lines.extend(["", "## Top-level folders", "", "| Folder | Videos | Publish-ready |", "| --- | ---: | ---: |"])
    for name, item in sorted(folders.items()):
        lines.append(f"| {name} | {item['videos']} | {item['publishReady']} |")
    lines.extend(["", "## Technical failures", ""])
    if failures:
        lines.extend(f"- `{item['relativePath']}` — {', '.join(item['failures'])}" for item in failures)
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Publishing rule",
        "",
        "Legacy videos remain preserved, but they are not approved for new posting under the current real-time-footage rule. Rebuild them from receipt-backed continuous VM sources before publishing.",
        "",
        "The detailed CSV and JSON contain one record for every MP4, including hashes, streams, dimensions, frame rate, motion samples, tier, failures, and policy checks.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    if not VIDEO_ROOT.is_dir():
        raise FileNotFoundError(VIDEO_ROOT)
    videos = sorted(VIDEO_ROOT.rglob("*.mp4"), key=lambda path: str(path).lower())
    if not videos:
        raise RuntimeError("No MP4 files found")
    current_records = load_current_audit_records()
    workers = min(8, max(2, (os.cpu_count() or 4) // 2))
    rows: list[dict[str, Any]] = []
    print(f"Auditing {len(videos)} MP4 files with {workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(audit_one, path, current_records): path for path in videos}
        for position, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            if position % 50 == 0 or position == len(videos):
                print(f"[{position}/{len(videos)}] audited", flush=True)
    rows.sort(key=lambda item: item["relativePath"].lower())

    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("sha256"):
            by_hash[row["sha256"]].append(row["relativePath"])
    duplicate_groups = [
        {"sha256": digest, "count": len(paths), "files": paths}
        for digest, paths in sorted(by_hash.items()) if len(paths) > 1
    ]
    tier_counts = Counter(row["tier"] for row in rows)
    folder_counts: dict[str, dict[str, int]] = {}
    for folder in sorted({row["topFolder"] for row in rows}):
        matches = [row for row in rows if row["topFolder"] == folder]
        folder_counts[folder] = {
            "videos": len(matches),
            "publishReady": sum(bool(row["publishReady"]) for row in matches),
        }
    counts = {
        "total": len(rows),
        "technicalPassed": sum(bool(row["technicalPassed"]) for row in rows),
        "technicalFailed": sum(not bool(row["technicalPassed"]) for row in rows),
        "motionObserved": sum(bool(row["motionSamplePassed"]) for row in rows),
        "lowMotion": sum(not bool(row["motionSamplePassed"]) for row in rows),
        "policyPassed": sum(bool(row["policyPassed"]) for row in rows),
        "publishReady": sum(bool(row["publishReady"]) for row in rows),
    }
    report = {
        "auditedAt": datetime.now(timezone.utc).isoformat(),
        "videoRoot": str(VIDEO_ROOT),
        "policy": {
            "continuousCaptureReceiptRequired": True,
            "snapshotsAllowed": False,
            "generatedProductVisualsAllowed": False,
            "maximumVisibleProductVideoLayers": 1,
            "motionSamplingIsNotProvenance": True,
            "manualQualityApprovalRequired": True,
        },
        "counts": counts,
        "tiers": dict(sorted(tier_counts.items())),
        "folders": folder_counts,
        "duplicateGroups": duplicate_groups,
        "technicalFailureExamples": [
            {"relativePath": row["relativePath"], "failures": row["failures"]}
            for row in rows if not row["technicalPassed"]
        ][:100],
        "videos": rows,
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "all-video-audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    columns = [
        "relativePath", "topFolder", "tier", "publishReady", "technicalPassed",
        "policyPassed", "durationSeconds", "width", "height", "orientation",
        "frameRate", "videoCodec", "pixelFormat", "audioStreamCount", "audioCodec",
        "audioChannels", "audioSampleRate", "motionSamplePassed", "motionCoverage",
        "qualityAutomatedPassed", "qualityManualPassed", "qualityPublishReady",
        "sampledFrames", "uniqueSampledFrames", "sizeBytes", "sha256", "failures",
        "warnings", "tierReason",
    ]
    with (REPORT_ROOT / "all-video-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flattened = dict(row)
            flattened["failures"] = "; ".join(str(item) for item in row.get("failures", []))
            flattened["warnings"] = "; ".join(str(item) for item in row.get("warnings", []))
            writer.writerow(flattened)
    (REPORT_ROOT / "ALL-VIDEO-AUDIT.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(counts, indent=2), flush=True)
    print(f"Reports written to {REPORT_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
