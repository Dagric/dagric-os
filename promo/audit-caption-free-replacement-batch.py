#!/usr/bin/env python3
"""Audit every caption-free replacement with the Dagric Lab quality gate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
ROOT = DELIVERY / "Realtime Replacement Batch" / "batch-01"
MANIFEST = ROOT / "replacement-batch-manifest.json"
AUDITOR = Path(
    r"C:\Users\1248n\plugins\dagric-lab\skills\dagric-iso-lab\scripts\audit-video.py"
)
EXPECTED_PROFILES = {"open-horizon", "night-orbit", "wild-meadow", "open-coast"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_one(record: dict) -> dict:
    video = Path(record["output"])
    transcript = Path(record["transcriptForAuditOnly"])
    source = Path(record["source"])
    receipt_path = Path(record["captureReceipt"])
    transcript_text = transcript.read_text(encoding="utf-8") if transcript.is_file() else ""
    completed = subprocess.run(
        [
            "python",
            str(AUDITOR),
            "--video",
            str(video),
            "--mode",
            "final",
            "--profile",
            "social-ui",
            "--caption-policy",
            "none",
            "--transcript",
            str(transcript),
        ],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    report_path = video.with_suffix(".quality-audit.json")
    if not report_path.is_file():
        return {
            "video": str(video),
            "platform": record["platform"],
            "automatedPassed": False,
            "publishReady": False,
            "failures": ["audit.reportMissing"],
            "error": completed.stderr.strip() or completed.stdout.strip(),
        }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    provenance_checks = {
        "sourceExists": source.is_file(),
        "receiptExists": receipt_path.is_file(),
        "sourceHash": source.is_file() and record.get("sourceSha256") == sha256(source),
        "visualProfileKnown": record.get("visualProfile") in EXPECTED_PROFILES,
        "profileAppliedInGuest": record.get("visualProfileAppliedInGuest") is True,
        "noSnapshotInputs": record.get("snapshotInputs") == [],
        "oneProductVideoLayer": record.get("visibleProductVideoLayers") == 1,
        "introLabelAtMostThreeSeconds": (
            record.get("introLabel", {}).get("maximumVisibleSeconds", float("inf")) <= 3.0
        ),
        "introLabelDoesNotCoverProduct": (
            record.get("introLabel", {}).get("overlapsProductFootage") is False
        ),
        "publicLanguageAvoidsCaptureInfrastructure": not re.search(
            r"\b(?:VM|virtual machine|ISO)\b", transcript_text, flags=re.IGNORECASE
        ),
    }
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        provenance_checks.update(
            {
                "receiptSourceHash": source.is_file() and receipt.get("sha256") == sha256(source),
                "receiptVisualProfile": receipt.get("visualProfile") == record.get("visualProfile"),
                "receiptProfileAppliedInGuest": receipt.get("visualProfileAppliedInGuest") is True,
                "receiptProfileAppliedDuringContinuousCapture": receipt.get(
                    "visualProfileApplicationTiming"
                )
                in {"before-frame-zero", "during-continuous-capture-after-first-run"},
                "receiptContinuousVnc": receipt.get("captureMode") == "continuous-vnc-stream",
                "receiptNoSnapshotInputs": receipt.get("snapshotInputs") == [],
            }
        )
    provenance_failures = [name for name, passed in provenance_checks.items() if not passed]
    auditor_passed = report.get("automatedPassed") is True
    return {
        "video": str(video),
        "platform": record["platform"],
        "story": record["slug"],
        "report": str(report_path),
        "contactSheet": report.get("artifacts", {}).get("contactSheet"),
        "visualProfile": record.get("visualProfile"),
        "source": str(source),
        "captureReceipt": str(receipt_path),
        "provenanceChecks": provenance_checks,
        "automatedPassed": auditor_passed and not provenance_failures,
        "manualPassed": report.get("manualPassed") is True,
        "publishReady": report.get("publishReady") is True,
        "failures": [
            *report.get("automatedFailures", []),
            *(f"provenance.{name}" for name in provenance_failures),
        ],
        "durationSeconds": report.get("durationSeconds"),
        "longestFreezeSeconds": report.get("video", {}).get("events", {}).get(
            "longestFreezeSeconds"
        ),
        "freezeRatio": report.get("video", {}).get("events", {}).get("freezeRatio"),
        "integratedLufs": report.get("audio", {}).get("metrics", {}).get(
            "integratedLufs"
        ),
        "truePeakDbfs": report.get("audio", {}).get("metrics", {}).get("truePeakDbfs"),
        "wordsPerMinute": (
            report.get("content", {}).get("transcript") or {}
        ).get("wordsPerMinute"),
        "subtitleStreamCount": report.get("content", {}).get("subtitleStreamCount"),
        "noCaptionSidecars": report.get("content", {}).get("checks", {}).get(
            "noCaptionSidecars"
        ),
    }


def board_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts\segoeui.ttf")), size=size)


def build_platform_board(platform: str, records: list[dict]) -> Path | None:
    sheets = []
    for record in records:
        path_value = record.get("contactSheet")
        path = Path(path_value) if path_value else None
        if path is not None and path.is_file():
            sheets.append((record, path))
    if not sheets:
        return None
    cell_width, cell_height = 340, 470
    columns = 3
    rows = (len(sheets) + columns - 1) // columns
    board = Image.new("RGB", (columns * cell_width, 70 + rows * cell_height), "#08131f")
    draw = ImageDraw.Draw(board)
    draw.text((24, 18), f"{platform.upper()} • CAPTION-FREE LIVE-FOOTAGE QA", font=board_font(28), fill="white")
    for index, (record, path) in enumerate(sheets):
        row, column = divmod(index, columns)
        x, y = column * cell_width + 10, 70 + row * cell_height
        with Image.open(path) as opened:
            image = opened.convert("RGB")
            image.thumbnail((320, 410), Image.Resampling.LANCZOS)
            board.paste(image, (x + (320 - image.width) // 2, y))
        label = (
            f"{record['story']} • {record.get('visualProfile', 'unknown')} • "
            f"auto={'PASS' if record['automatedPassed'] else 'FAIL'}"
        )
        draw.text((x, y + 418), label, font=board_font(14), fill="#bfe9f6")
    output = ROOT / f"qa-board-{platform}.jpg"
    board.save(output, quality=90)
    return output


def main() -> int:
    if not MANIFEST.is_file():
        raise FileNotFoundError(MANIFEST)
    if not AUDITOR.is_file():
        raise FileNotFoundError(AUDITOR)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    visual_policy = manifest.get("visualPolicy", {})
    composition_checks = {
        "oneProductVideoMaximum": (
            visual_policy.get("maximumSimultaneousProductVideoLayers") == 1
        ),
        "snapshotsForbidden": visual_policy.get("snapshotsAllowed") is False,
        "platformBannersForbidden": (
            visual_policy.get("platformSpecificBanners") is False
        ),
        "productFootageOverlaysForbidden": (
            visual_policy.get("overlaysOnProductFootageAllowed") is False
        ),
        "introLabelAtMostThreeSeconds": (
            visual_policy.get("maximumIntroLabelSeconds", float("inf")) <= 3.0
        ),
        "progressRailForbidden": visual_policy.get("animatedProgressRail") is False,
        "publicInfrastructureLabelsForbidden": (
            visual_policy.get("publicInfrastructureLabelsAllowed") is False
            and visual_policy.get("publicCaptureDescription") == "live footage"
        ),
    }
    composition_failures = [
        name for name, passed in composition_checks.items() if not passed
    ]
    outputs = manifest.get("outputs", [])
    if not outputs:
        raise RuntimeError("Replacement manifest contains no outputs")
    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(audit_one, record): record for record in outputs}
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            records.append(result)
            print(
                f"[{index:02d}/{len(outputs):02d}] "
                f"{'PASS' if result['automatedPassed'] else 'FAIL'} "
                f"{Path(result['video']).name}",
                flush=True,
            )
    records.sort(key=lambda record: (record["platform"], record["story"]))
    boards = {}
    for platform in sorted({record["platform"] for record in records}):
        board = build_platform_board(
            platform,
            [record for record in records if record["platform"] == platform],
        )
        boards[platform] = str(board) if board else None
    failed = [record for record in records if not record["automatedPassed"]]
    profile_counts = Counter(record.get("visualProfile") for record in records)
    ordered_manifest_profiles = [record.get("visualProfile") for record in outputs]
    variety_checks = {
        "allFourProfilesRepresented": set(profile_counts) == EXPECTED_PROFILES,
        "balancedProfileShare": bool(records)
        and max(profile_counts.values()) / len(records) <= 0.25,
        "noAdjacentProfileRepeats": all(
            left != right
            for left, right in zip(ordered_manifest_profiles, ordered_manifest_profiles[1:])
        ),
        "eachOutputBoundToProfile": all(record.get("visualProfile") for record in records),
    }
    variety_failures = [name for name, passed in variety_checks.items() if not passed]
    report = {
        "schema": "dagric-caption-free-replacement-batch-audit-v1",
        "auditedAtUtc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST),
        "qualityProfile": "social-ui",
        "captionPolicy": "none",
        "videoCount": len(records),
        "automatedPassCount": len(records) - len(failed),
        "automatedFailCount": len(failed),
        "visualProfileCounts": dict(sorted(profile_counts.items())),
        "visualVarietyChecks": variety_checks,
        "visualVarietyFailures": variety_failures,
        "compositionChecks": composition_checks,
        "compositionFailures": composition_failures,
        "manualPassCount": sum(record["manualPassed"] for record in records),
        "publishReadyCount": sum(record["publishReady"] for record in records),
        "qaBoards": boards,
        "records": records,
    }
    report_path = ROOT / "batch-quality-audit.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown = [
        "# Caption-free replacement batch audit",
        "",
        f"- Videos audited: {len(records)}",
        f"- Automated passes: {len(records) - len(failed)}",
        f"- Automated failures: {len(failed)}",
        f"- Visual profiles: {dict(sorted(profile_counts.items()))}",
        f"- Visual variety gate: {'PASS' if not variety_failures else 'FAIL'}",
        f"- Clean composition gate: {'PASS' if not composition_failures else 'FAIL'}",
        "- Subtitle streams: must be zero",
        "- Caption sidecars: `.srt` and `.vtt` forbidden",
        f"- Manual/publish-ready: {sum(record['publishReady'] for record in records)} (voice listening review remains required)",
        "",
        "## Failures",
        "",
    ]
    if failed:
        markdown.extend(
            f"- `{Path(record['video']).name}`: {', '.join(record['failures'])}"
            for record in failed
        )
    else:
        markdown.append("- None.")
    markdown.extend(["", "## Visual QA boards", ""])
    markdown.extend(f"- {platform}: `{path}`" for platform, path in boards.items())
    (ROOT / "BATCH-AUDIT.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(report_path),
        "videoCount": len(records),
        "automatedPassCount": len(records) - len(failed),
        "automatedFailCount": len(failed),
        "visualProfileCounts": dict(sorted(profile_counts.items())),
        "visualVarietyChecks": variety_checks,
        "compositionChecks": composition_checks,
        "publishReadyCount": sum(record["publishReady"] for record in records),
        "qaBoards": boards,
    }, indent=2))
    return 0 if not failed and not variety_failures and not composition_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
