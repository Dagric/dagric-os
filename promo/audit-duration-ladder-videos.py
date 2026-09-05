#!/usr/bin/env python3
"""Audit the caption-free Dagric duration ladder and its live-capture provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
ROOT = DELIVERY / "Duration Ladder" / "caption-free-v4"
VIDEO_MANIFEST = ROOT / "duration-ladder-video-manifest.json"
AUDIO_MANIFEST = DELIVERY / "Duration Ladder" / "duration-ladder-audio-manifest.json"
AUDITOR = Path(r"C:\Users\1248n\plugins\dagric-lab\skills\dagric-iso-lab\scripts\audit-video.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_one(record: dict, editions: dict[str, dict], source_hash: str) -> dict:
    video = Path(record["output"])
    edition = editions[record["slug"]]
    transcript = ROOT / "audit-transcripts" / f"{record['slug']}.txt"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(
        " ".join(segment["text"].strip() for segment in edition["segments"]) + "\n",
        encoding="utf-8",
    )
    profile = "continuous" if float(record["durationSeconds"]) >= 300 else "social-ui"
    completed = subprocess.run(
        [
            "python", str(AUDITOR), "--video", str(video), "--mode", "final",
            "--profile", profile, "--caption-policy", "none", "--transcript", str(transcript),
        ],
        check=False, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    report_path = video.with_suffix(".quality-audit.json")
    if not report_path.is_file():
        return {"video": str(video), "automatedPassed": False, "failures": ["audit.reportMissing"],
                "error": completed.stderr.strip() or completed.stdout.strip()}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    receipt = Path(record["captureReceipt"])
    source = Path(record["source"])
    receipt_data = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {}
    provenance = {
        "outputHash": video.is_file() and record.get("sha256") == sha256(video),
        "exactDuration": abs(float(report.get("durationSeconds", -1)) - float(record["durationSeconds"])) <= 0.08,
        "oneVideoStream": record.get("videoStreams") == 1,
        "oneAudioStream": record.get("audioStreams") == 1,
        "noSubtitleStream": record.get("subtitleStreams") == 0,
        "noSnapshots": record.get("snapshotInputs") == [],
        "oneProductLayer": record.get("visibleProductVideoLayers") == 1,
        "introAtMostThreeSeconds": float(record.get("introMaximumSeconds", 99)) <= 3.0,
        "introOutsideProduct": record.get("introOverlapsProductFootage") is False,
        "sourceHash": source.is_file() and sha256(source) == source_hash,
        "receiptHash": source.is_file() and receipt_data.get("sha256") == source_hash,
        "continuousCapture": receipt_data.get("captureMode") == "continuous-vnc-stream",
        "continuousFrameEncoding": receipt_data.get("continuousFrameEncoding") is True,
        "receiptNoSnapshots": receipt_data.get("snapshotInputs") == [],
    }
    failures = [*report.get("automatedFailures", []),
                *(f"provenance.{name}" for name, passed in provenance.items() if not passed)]
    return {
        "video": str(video), "slug": record["slug"], "platform": record["platform"],
        "durationSeconds": report.get("durationSeconds"), "report": str(report_path),
        "automatedPassed": report.get("automatedPassed") is True and not failures,
        "manualPassed": report.get("manualPassed") is True,
        "publishReady": report.get("publishReady") is True and not failures,
        "failures": failures, "provenanceChecks": provenance,
        "longestFreezeSeconds": report.get("video", {}).get("events", {}).get("longestFreezeSeconds"),
        "freezeRatio": report.get("video", {}).get("events", {}).get("freezeRatio"),
        "integratedLufs": report.get("audio", {}).get("metrics", {}).get("integratedLufs"),
        "wordsPerMinute": report.get("content", {}).get("transcript", {}).get("wordsPerMinute"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", action="append", help="Audit selected editions and preserve other records")
    args = parser.parse_args()
    video_manifest = json.loads(VIDEO_MANIFEST.read_text(encoding="utf-8"))
    audio_manifest = json.loads(AUDIO_MANIFEST.read_text(encoding="utf-8"))
    editions = {edition["slug"]: edition for edition in audio_manifest["editions"]}
    source = Path(video_manifest["source"])
    source_hash = sha256(source)
    records: list[dict] = []
    selected_outputs = [
        record for record in video_manifest["outputs"]
        if not args.slug or record["slug"] in args.slug
    ]
    if args.slug and len({record["slug"] for record in selected_outputs}) != len(set(args.slug)):
        raise RuntimeError("One or more requested duration-ladder slugs are unknown")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(audit_one, record, editions, source_hash): record
            for record in selected_outputs
        }
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            records.append(result)
            print(f"[{index:02d}/{len(futures):02d}] {'PASS' if result['automatedPassed'] else 'FAIL'} "
                  f"{Path(result['video']).name}", flush=True)
    output = ROOT / "duration-ladder-quality-audit.json"
    if args.slug and output.is_file():
        previous = json.loads(output.read_text(encoding="utf-8"))
        replaced = set(args.slug)
        records = [record for record in previous.get("records", []) if record.get("slug") not in replaced] + records
    records.sort(key=lambda item: (item.get("slug", ""), item.get("platform", "")))
    passed = sum(record["automatedPassed"] for record in records)
    report = {
        "schema": "dagric-duration-ladder-quality-audit-v1",
        "auditedAtUtc": datetime.now(timezone.utc).isoformat(),
        "videoCount": len(records), "automatedPassCount": passed,
        "automatedFailCount": len(records) - passed,
        "manualReviewRequired": True,
        "publishReadyCount": sum(record["publishReady"] for record in records),
        "records": records,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), **{k: report[k] for k in
          ("videoCount", "automatedPassCount", "automatedFailCount", "publishReadyCount")}}, indent=2))
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
