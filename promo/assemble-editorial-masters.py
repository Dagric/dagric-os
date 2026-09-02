#!/usr/bin/env python3
"""Assemble human-directed visuals, narrated audio, and sidecar captions."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
NARRATED_ROOT = DELIVERY / "Narrated Replacements"
NARRATION_MANIFEST = NARRATED_ROOT / "narration-manifest.json"
VISUAL_ROOT = DELIVERY / "Editorial Visuals"
OUTPUT_ROOT = DELIVERY / "Editorial Masters"
CUSTOM_TOPICS = {
    "dagric-promo",
    "installation-walkthrough",
    "dagric-short",
    "desktop-looks",
    "real-vm-onboarding",
    "real-vm-settings",
}


def run(args: list[str], capture: bool = False) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return ((result.stdout or "") + (result.stderr or "")) if capture else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def groups(words: list[str], target: int = 8) -> list[list[str]]:
    result: list[list[str]] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        sentence_end = bool(re.search(r"[.!?]$", word))
        if len(current) >= target + 2 or (sentence_end and len(current) >= 4):
            result.append(current)
            current = []
    if current:
        if result and len(current) <= 3 and len(result[-1]) + len(current) <= 12:
            result[-1].extend(current)
        else:
            result.append(current)
    return result


def caption_events(record: dict) -> list[tuple[float, float, str]]:
    parts = record.get("voices") or []
    if not parts:
        return []
    duration = float(record["durationSeconds"])
    voice_duration = float(record.get("voiceDurationSeconds") or max(1.0, duration - 1.0))
    start = 0.48
    end = min(duration - 0.35, start + voice_duration)
    gap = 0.16 if len(parts) > 1 else 0.0
    part_words = [re.findall(r"\S+", str(part.get("text", ""))) for part in parts]
    part_weights = [max(1, len(words)) for words in part_words]
    spoken = max(0.6, end - start - gap * (len(parts) - 1))
    total_weight = sum(part_weights)
    cursor = start
    events: list[tuple[float, float, str]] = []
    for part_index, (words, part_weight) in enumerate(zip(part_words, part_weights)):
        if not words:
            continue
        part_duration = spoken * part_weight / total_weight
        word_groups = groups(words)
        weights = [max(1, len(group)) for group in word_groups]
        weight_total = sum(weights)
        for group, weight in zip(word_groups, weights):
            event_duration = max(0.5, part_duration * weight / weight_total)
            event_end = min(end, cursor + event_duration)
            events.append((cursor, max(cursor + 0.45, event_end), " ".join(group)))
            cursor = event_end
        if part_index + 1 < len(parts):
            cursor += gap
    return events


def write_srt(record: dict, path: Path) -> int:
    events = caption_events(record)
    lines: list[str] = []
    for index, (start, end, text) in enumerate(events, start=1):
        lines.extend([str(index), f"{srt_time(start)} --> {srt_time(end)}", text, ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return len(events)


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,color_range,channels,sample_rate",
                "-of", "json", str(path),
            ],
            capture=True,
        )
    )


def main() -> int:
    source_manifest = json.loads(NARRATION_MANIFEST.read_text(encoding="utf-8"))
    records = source_manifest["videos"]
    if len(records) != 74:
        raise RuntimeError(f"Expected 74 narration records; found {len(records)}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    completed: list[dict] = []
    for index, record in enumerate(records, start=1):
        audio_master = Path(record["output"])
        source_visual = Path(record["source"])
        editorial_visual = VISUAL_ROOT / record["batch"] / source_visual.name
        corrected_custom_visual = VISUAL_ROOT / "custom" / source_visual.name
        if record["topic"] in CUSTOM_TOPICS:
            visual = corrected_custom_visual if corrected_custom_visual.exists() else source_visual
            visual_direction = "custom-original"
        else:
            visual = editorial_visual if editorial_visual.exists() else source_visual
            visual_direction = "editorial-system" if editorial_visual.exists() else "missing-editorial-system"
        if not visual.exists():
            raise FileNotFoundError(visual)
        if not audio_master.exists():
            raise FileNotFoundError(audio_master)

        relative = Path(record["batch"]) / source_visual.name
        output = OUTPUT_ROOT / relative
        srt = output.with_suffix(".srt")
        output.parent.mkdir(parents=True, exist_ok=True)
        caption_count = write_srt(record, srt)
        duration = float(record["durationSeconds"])

        run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(visual),
                "-i", str(audio_master),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "copy",
                "-t", f"{duration:.6f}", "-movflags", "+faststart",
                "-metadata", "title=Dagric OS human-directed editorial master",
                "-metadata", "artist=Dagric OS",
                "-metadata", "comment=Synthetic narration; original locally synthesized sound bed; human-directed editorial design; sidecar captions included",
                str(output),
            ]
        )
        info = probe(output)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
        completed.append(
            {
                "number": index,
                "batch": record["batch"],
                "topic": record["topic"],
                "title": record["title"],
                "publishAt": record["publishAt"],
                "visualDirection": visual_direction,
                "visualSource": str(visual),
                "audioSource": str(audio_master),
                "output": str(output),
                "captions": str(srt),
                "captionEvents": caption_count,
                "voices": sorted({voice["voiceName"] for voice in record.get("voices", [])}),
                "durationSeconds": round(float(info["format"]["duration"]), 3),
                "video": {
                    "codec": video["codec_name"],
                    "width": video["width"],
                    "height": video["height"],
                    "frameRate": video["avg_frame_rate"],
                    "pixelFormat": video.get("pix_fmt"),
                    "colorRange": video.get("color_range"),
                },
                "audio": {
                    "codec": audio["codec_name"],
                    "channels": audio["channels"],
                    "sampleRate": int(audio["sample_rate"]),
                },
                "sha256": sha256(output),
            }
        )
        print(f"[{index:02d}/74] {relative} | visual={visual_direction} captions={caption_count}", flush=True)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(completed),
        "editorialPrinciples": [
            "topic-specific composition instead of one repeated template",
            "real Dagric screenshots kept central",
            "shorter on-screen copy with visible limits and evidence",
            "no distracting on-screen synthetic-voice badge",
            "synthetic narration retained in metadata and platform disclosure workflow",
            "accessible sidecar SRT captions rather than a permanent caption box",
        ],
        "videos": completed,
    }
    (OUTPUT_ROOT / "editorial-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "README.md").write_text(
        "# Dagric editorial masters\n\n"
        "Seventy-four human-directed vertical masters with six topic-driven visual formats, narrated audio, and sidecar captions.\n\n"
        "The 68 campaign-template videos were rebuilt in the editorial system. The six long custom videos retain their purpose-built scene direction. Synthetic narration remains identified in metadata and should be disclosed through each platform's required controls.\n",
        encoding="utf-8",
    )
    print(f"Completed {len(completed)} editorial masters in {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
