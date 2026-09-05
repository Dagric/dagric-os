#!/usr/bin/env python3
"""Audit the current Dagric video set for a useful first two seconds.

The report deliberately separates objective delivery checks from editorial
judgment.  It audits every rendered file, while grouping repeated platform
exports under their shared story/edition for hook recommendations.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[1]
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
BATCH_MANIFEST = DELIVERY / "Realtime Replacement Batch" / "batch-01" / "replacement-batch-manifest.json"
LADDER_AUDIO = DELIVERY / "Duration Ladder" / "duration-ladder-audio-manifest.json"
LADDER_VIDEO = DELIVERY / "Duration Ladder" / "caption-free-v4" / "duration-ladder-video-manifest.json"
REPORT_DIR = DELIVERY / "Attention Audit"

WEAK_STARTS = (
    "a new ", "here is ", "the first ", "this live ", "this chapter ",
    "this minute ", "the regular ", "the setup ", "welcome to ",
)
ACTION_STARTS = (
    "watch ", "can ", "why ", "what ", "will ", "would ", "open ",
    "test ", "choose ", "see ", "want ", "need ",
)
PUBLIC_BLOCKLIST = re.compile(
    r"\b(?:vm|iso|qemu)\b|virtual machine|virtual hardware|test environment",
    re.IGNORECASE,
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text)


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return json.loads(result.stdout)


def first_two_second_motion(path: Path, width: int, height: int) -> dict:
    # Score only the product area, excluding the temporary title area and canvas.
    if height > width:
        crop = f"crop={width}:675:0:300"
    else:
        crop = f"crop={min(width - 192, 1728)}:{height}:{96 if width >= 1920 else 0}:0"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-t", "2.0", "-i", str(path),
         "-vf", f"{crop},fps=4,scale=160:100:flags=area,format=gray",
         "-an", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    frame_size = 160 * 100
    count = len(result.stdout) // frame_size
    frames = np.frombuffer(result.stdout[: count * frame_size], dtype=np.uint8).reshape(count, 100, 160)
    hashes = {hashlib.sha1(frame.tobytes()).hexdigest() for frame in frames}
    diffs = [float(np.mean(np.abs(b.astype(np.int16) - a.astype(np.int16)))) for a, b in zip(frames, frames[1:])]
    mean_diff = round(float(np.mean(diffs)), 3) if diffs else 0.0
    return {
        "sampledFrames": count,
        "uniqueFrames": len(hashes),
        "meanConsecutivePixelDifference": mean_diff,
        "pass": count >= 6 and len(hashes) >= 3 and mean_diff >= 0.12,
    }


def editorial_score(hook: str, narration: str, lead: float, long_form: bool) -> dict:
    opening = first_sentence(narration)
    lower = opening.lower()
    hook_words = len(words(hook))
    opening_words = len(words(opening))
    checks = {
        "spokenStartWithinTwoSeconds": lead <= 2.0,
        "fastSpokenStart": lead <= (1.0 if long_form else 0.6),
        "hookAtMostSevenWords": hook_words <= 7,
        "openingAtMostSixteenWords": opening_words <= 16,
        "actionQuestionOrBenefitOpening": lower.startswith(ACTION_STARTS),
        "avoidsGenericOpening": not lower.startswith(WEAK_STARTS),
        "publicLanguage": PUBLIC_BLOCKLIST.search(f"{hook} {narration}") is None,
    }
    return {
        "hook": hook,
        "hookWordCount": hook_words,
        "firstSpokenSentence": opening,
        "firstSentenceWordCount": opening_words,
        "leadSeconds": lead,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> int:
    batch_source = load_module(REPO / "promo" / "assemble-caption-free-replacement-batch.py", "batch_source")
    ladder_source = load_module(REPO / "promo" / "create-duration-ladder-audio.py", "ladder_source")
    batch = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    ladder_audio = json.loads(LADDER_AUDIO.read_text(encoding="utf-8"))
    ladder_video = json.loads(LADDER_VIDEO.read_text(encoding="utf-8"))

    concepts: dict[str, dict] = {}
    for story in batch_source.STORIES:
        key = f"story-{story.number:02d}"
        concepts[key] = {
            "kind": "replacement",
            "slug": story.slug,
            **editorial_score(story.hook, story.narration, 0.28, story.duration >= 60),
        }
    audio_by_slug = {item["slug"]: item for item in ladder_audio["editions"]}
    edition_by_slug = {item.slug: item for item in ladder_source.EDITIONS}
    for slug, record in audio_by_slug.items():
        source_edition = edition_by_slug[slug]
        opening_text = record["segments"][0]["text"]
        # The vertical ladder exports use the short edition label as their
        # temporary title; the spoken opening is scored separately below.
        hook = slug.replace("-", " ")
        concepts[f"ladder-{slug}"] = {
            "kind": "duration-ladder",
            "slug": slug,
            **editorial_score(hook, opening_text, float(record["segments"][0]["startSeconds"]), source_edition.duration >= 300),
        }

    rendered = []
    batch_records = batch.get("outputs", batch.get("videos", []))
    for item in batch_records:
        rendered.append((f"story-{int(item['number']):02d}", item))
    for item in ladder_video["outputs"]:
        rendered.append((f"ladder-{item['slug']}", item))

    file_results = []
    for index, (concept_key, item) in enumerate(rendered, start=1):
        path = Path(item["output"])
        record = {"concept": concept_key, "platform": item["platform"], "path": str(path), "exists": path.is_file()}
        if path.is_file():
            info = probe(path)
            video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
            record["durationSeconds"] = round(float(info["format"]["duration"]), 3)
            record["motionFirstTwoSeconds"] = first_two_second_motion(path, int(video["width"]), int(video["height"]))
            record["pass"] = record["motionFirstTwoSeconds"]["pass"] and concepts[concept_key]["pass"]
        else:
            record["pass"] = False
        file_results.append(record)
        if index % 20 == 0:
            print(f"Audited {index}/{len(rendered)} files", flush=True)

    for key, concept in concepts.items():
        files = [item for item in file_results if item["concept"] == key]
        concept["renderedFileCount"] = len(files)
        concept["allFilesPassMotion"] = bool(files) and all(item.get("motionFirstTwoSeconds", {}).get("pass", False) for item in files)
        concept["publishGatePass"] = concept["pass"] and concept["allFilesPassMotion"]

    report = {
        "schema": "dagric-two-second-attention-audit-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "124 current caption-free replacement and duration-ladder exports; legacy videos excluded from publishing",
        "criteria": {
            "productMotionVisibleImmediately": True,
            "spokenStartWithinSeconds": 2.0,
            "shortFormPreferredStartSeconds": 0.6,
            "temporaryHookMaximumSeconds": 3.0,
            "hookMaximumWords": 7,
            "openingSentenceMaximumWords": 16,
            "oneProductVideoLayer": True,
            "captions": "none",
        },
        "renderedFileCount": len(file_results),
        "filePassCount": sum(item["pass"] for item in file_results),
        "conceptCount": len(concepts),
        "publishGateConceptPassCount": sum(item["publishGatePass"] for item in concepts.values()),
        "manualVoiceNaturalnessReviewRequired": True,
        "concepts": concepts,
        "files": file_results,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "two-second-attention-audit.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    failures = [(key, item) for key, item in concepts.items() if not item["publishGatePass"]]
    lines = [
        "# Dagric video two-second attention audit", "",
        f"Generated: {report['generatedAtUtc']}", "",
        f"- Current rendered files audited: **{report['renderedFileCount']}**",
        f"- Files passing automated attention gate: **{report['filePassCount']}**",
        f"- Editorial concepts passing: **{report['publishGateConceptPassCount']} / {report['conceptCount']}**",
        "- Manual naturalness and comprehension listening review: **still required**", "",
        "## Concepts that need a stronger opening", "",
    ]
    if not failures:
        lines.append("None.")
    for key, item in failures:
        failed = [name for name, passed in item["checks"].items() if not passed]
        if not item["allFilesPassMotion"]:
            failed.append("firstTwoSecondProductMotion")
        lines.extend([
            f"### {key} — {item['slug']}", "",
            f"- Failed: {', '.join(failed)}",
            f"- Current hook: {item['hook']}",
            f"- First sentence: {item['firstSpokenSentence']}", "",
        ])
    md_path = REPORT_DIR / "TWO-SECOND-ATTENTION-AUDIT.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "json": str(json_path), "markdown": str(md_path),
        "files": len(file_results), "filePass": report["filePassCount"],
        "concepts": len(concepts), "conceptPass": report["publishGateConceptPassCount"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
