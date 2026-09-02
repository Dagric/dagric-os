#!/usr/bin/env python3
"""Create a more fluid, captioned and branded master for every scheduled video.

The narrated replacements remain untouched.  This script reads their manifest,
adds a gentle camera drift, karaoke captions, explicit synthetic-voice labels,
an animated progress rail, subtle audio meters, Dagric branding, and a final
call-to-action.  The result is intended to be the upload master for short-form
social platforms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(r"C:\Users\1248n\Documents\ChatGPT\Dagric Os")
PROMO = REPO / "promo"
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
SOURCE_ROOT = DELIVERY / "Narrated Replacements"
SOURCE_MANIFEST = SOURCE_ROOT / "narration-manifest.json"
OUTPUT_ROOT = DELIVERY / "Enhanced Masters"
WORK_ROOT = OUTPUT_ROOT / "_caption-masters"
LOGO = REPO / "site" / "assets" / "dagric-logo.png"
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")

ACCENTS = ["4FB3E8", "7BE0C8", "F0A04B", "A78BFA"]
CTA_COPY = [
    "TRY THE LIVE USB  •  DAGRIC.COM",
    "READ THE TEST NOTES  •  DAGRIC.COM",
    "CHECK YOUR PC FIRST  •  DAGRIC.COM",
]


@dataclass
class CaptionEvent:
    start: float
    end: float
    voice: str
    words: list[str]


def run(args: list[str], *, capture: bool = False) -> str:
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


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture=True,
        )
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ass_color(rgb: str, alpha: str = "00") -> str:
    red, green, blue = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{alpha}{blue}{green}{red}"


def ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def groups(words: list[str], target: int = 7) -> list[list[str]]:
    output: list[list[str]] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        strong_end = bool(re.search(r"[.!?]$", word))
        soft_end = bool(re.search(r"[,;:]$", word))
        if len(current) >= target + 2 or (strong_end and len(current) >= 4) or (soft_end and len(current) >= target):
            output.append(current)
            current = []
    if current:
        if output and len(current) <= 3 and len(output[-1]) + len(current) <= 11:
            output[-1].extend(current)
        else:
            output.append(current)
    return output


def caption_events(record: dict) -> list[CaptionEvent]:
    parts = record.get("voices") or []
    if not parts:
        return []
    total_voice = float(record.get("voiceDurationSeconds") or 0.0)
    start = 0.48
    end_limit = min(float(record["durationSeconds"]) - 0.45, start + total_voice)
    available = max(0.8, end_limit - start)
    part_words = [re.findall(r"\S+", str(part.get("text", "")).strip()) for part in parts]
    weights = [max(1, len(words)) for words in part_words]
    total_weight = sum(weights)
    events: list[CaptionEvent] = []
    cursor = start
    gap = 0.16 if len(parts) > 1 else 0.0
    spoken_available = max(0.6, available - gap * (len(parts) - 1))
    for part_index, (part, words, weight) in enumerate(zip(parts, part_words, weights)):
        if not words:
            continue
        part_duration = spoken_available * weight / total_weight
        word_groups = groups(words, 7)
        group_weights = [max(1, len(group)) for group in word_groups]
        group_total = sum(group_weights)
        for group, group_weight in zip(word_groups, group_weights):
            event_duration = part_duration * group_weight / group_total
            event_end = min(end_limit, cursor + event_duration)
            events.append(
                CaptionEvent(
                    start=cursor,
                    end=max(cursor + 0.42, event_end),
                    voice=str(part.get("voiceName") or "Narrator"),
                    words=group,
                )
            )
            cursor = event_end
        if part_index + 1 < len(parts):
            cursor += gap
    return events


def karaoke_text(words: list[str], duration: float) -> str:
    weights = [max(1, len(re.sub(r"[^A-Za-z0-9]", "", word))) for word in words]
    total_cs = max(len(words), int(round(duration * 100)))
    remaining = total_cs
    tags: list[str] = []
    for index, (word, weight) in enumerate(zip(words, weights)):
        if index + 1 == len(words):
            cs = remaining
        else:
            cs = max(4, int(round(total_cs * weight / sum(weights))))
            remaining -= cs
        tags.append(r"{\kf" + str(max(1, cs)) + "}" + ass_escape(word))
    return " ".join(tags)


def write_ass(record: dict, path: Path, accent: str) -> list[CaptionEvent]:
    events = caption_events(record)
    caption_secondary = ass_color(accent)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Segoe UI Semibold,48,{ass_color('FFFFFF')},{caption_secondary},{ass_color('07101C')},{ass_color('08111C', 'A0')},-1,0,0,0,100,100,0,0,3,14,0,2,74,74,252,1
Style: Voice,Segoe UI Semibold,26,{caption_secondary},{caption_secondary},{ass_color('07101C')},{ass_color('07101C', '90')},-1,0,0,0,100,100,1.2,0,3,10,0,7,62,60,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header.rstrip()]
    for event in events:
        start, end = ass_time(event.start), ass_time(event.end)
        spoken = karaoke_text(event.words, event.end - event.start)
        lines.append(f"Dialogue: 1,{start},{end},Caption,,0,0,0,,{{\\fad(100,110)}}{spoken}")
        lines.append(
            f"Dialogue: 2,{start},{end},Voice,,0,0,0,,{{\\fad(120,120)}}AI VOICE  •  {ass_escape(event.voice.upper())}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return events


def filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def cta_for(record: dict, index: int) -> str:
    topic = str(record.get("topic") or "")
    title = str(record.get("title") or "")
    if "engagement" in topic or title.rstrip().endswith("?"):
        return "COMMENT YOUR ANSWER  ↓"
    if any(word in topic for word in ("signed", "accessibility", "check-this-pc")):
        return "READ THE PROOF  •  DAGRIC.COM"
    return CTA_COPY[index % len(CTA_COPY)]


def video_filter(record: dict, index: int, ass_path: Path, accent: str) -> str:
    duration = float(record["durationSeconds"])
    phase = (index % 9) * 0.57
    accent_ff = "0x" + accent
    cta = cta_for(record, index).replace("'", r"\'").replace(":", r"\:")
    sub = filter_path(ass_path)
    font = filter_path(FONT_BOLD)
    drift_x = 13 + (index % 5) * 2
    drift_y = 18 + (index % 4) * 3
    cta_start = max(0.0, duration - 2.65)
    cta_out = max(cta_start + 0.4, duration - 0.34)

    meters = []
    for meter in range(5):
        meters.append(
            "drawbox="
            f"x={820 + meter * 18}:y='92+{7 + meter % 3}*sin(7.4*t+{phase + meter * 0.8:.3f})':"
            f"w=7:h={18 + meter * 3}:color={accent_ff}@0.74:t=fill"
        )

    base_filters = [
        "scale=1128:2006:flags=lanczos",
        f"crop=1080:1920:x='(iw-ow)/2+{drift_x}*sin(0.22*t+{phase:.3f})':y='(ih-oh)/2+{drift_y}*sin(0.16*t+{phase / 2:.3f})'",
        "fps=30",
        "eq=contrast=1.018:saturation=1.035:brightness=0.004",
        f"drawbox=x=0:y=0:w='min(iw,max(0,iw*t/{duration:.6f}))':h=8:color={accent_ff}@0.92:t=fill",
        f"drawbox=x=24:y=210:w=4:h='min(1450,max(0,1450*t/{duration:.6f}))':color={accent_ff}@0.38:t=fill",
        f"drawbox=x=12:y=12:w=1056:h=1896:color={accent_ff}@0.15:t=3",
        *meters,
        f"subtitles=filename='{sub}'",
    ]

    return (
        f"[0:v]{','.join(base_filters)}[base];"
        "[1:v]scale=64:64:flags=lanczos,format=rgba,colorchannelmixer=aa=0.82[logo];"
        "[base][logo]overlay=x=W-w-42:y=38:format=auto[branded];"
        f"color=c=black@0.0:s=1080x1920:r=30:d={duration:.6f},format=rgba,"
        f"drawbox=x=142:y=1790:w=796:h=70:color=0x08111C@0.90:t=fill,"
        f"drawbox=x=142:y=1790:w=796:h=70:color={accent_ff}@0.86:t=3,"
        f"drawtext=fontfile='{font}':text='{cta}':fontcolor=white:fontsize=29:"
        "x=(w-text_w)/2:y=1807,"
        f"fade=t=in:st={cta_start:.3f}:d=0.32:alpha=1,"
        f"fade=t=out:st={cta_out:.3f}:d=0.30:alpha=1[cta];"
        "[branded][cta]overlay=0:0:format=auto,"
        "scale=in_range=auto:out_range=tv,format=yuv420p,setparams=range=tv[v]"
    )


def render_one(record: dict, index: int, *, force: bool) -> dict:
    source = Path(record["output"])
    if not source.exists():
        raise FileNotFoundError(source)
    relative = source.relative_to(SOURCE_ROOT)
    output = OUTPUT_ROOT / relative
    ass_path = WORK_ROOT / relative.with_suffix(".ass")
    output.parent.mkdir(parents=True, exist_ok=True)
    accent = ACCENTS[index % len(ACCENTS)]
    events = write_ass(record, ass_path, accent)
    if output.exists() and not force:
        info = probe(output)
    else:
        duration = float(record["durationSeconds"])
        audio_out = max(0.0, duration - 0.38)
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(LOGO),
            "-filter_complex",
            video_filter(record, index, ass_path, accent),
            "-map",
            "[v]",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            f"highpass=f=42,lowpass=f=16500,acompressor=threshold=0.22:ratio=1.65:attack=14:release=130,afade=t=in:st=0:d=0.18,afade=t=out:st={audio_out:.3f}:d=0.36,alimiter=limit=0.95",
            "-t",
            f"{duration:.6f}",
            "-shortest",
            "-movflags",
            "+faststart",
            "-metadata",
            "title=Dagric OS enhanced narrated social master",
            "-metadata",
            "comment=Original visuals and sound bed; synthetic narration disclosed on screen; timed captions added",
            str(output),
        ]
        run(args)
        info = probe(output)

    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    duration_out = float(info["format"]["duration"])
    return {
        "number": index + 1,
        "batch": record["batch"],
        "topic": record["topic"],
        "title": record["title"],
        "publishAt": record["publishAt"],
        "source": str(source),
        "output": str(output),
        "captionMaster": str(ass_path),
        "accent": "#" + accent,
        "captionEvents": len(events),
        "voices": sorted({event.voice for event in events}),
        "cta": cta_for(record, index),
        "durationSeconds": round(duration_out, 3),
        "video": {
            "codec": video["codec_name"],
            "width": video["width"],
            "height": video["height"],
            "frameRate": video.get("avg_frame_rate"),
        },
        "audio": {
            "codec": audio["codec_name"],
            "sampleRate": int(audio["sample_rate"]),
            "channels": audio["channels"],
        },
        "sha256": sha256(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="One-based source record to start from")
    parser.add_argument("--limit", type=int, default=0, help="Render only N videos from --start")
    parser.add_argument("--force", action="store_true", help="Overwrite existing enhanced masters")
    args = parser.parse_args()

    required = [SOURCE_MANIFEST, LOGO, FONT_BOLD, FONT_SEMIBOLD]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(map(str, missing)))

    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    records = manifest["videos"]
    if len(records) != 74:
        raise RuntimeError(f"Expected 74 source videos; found {len(records)}")
    start_index = max(0, args.start - 1)
    indexed_records = list(enumerate(records))[start_index:]
    if args.limit > 0:
        indexed_records = indexed_records[: args.limit]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    enhanced: list[dict] = []
    for completed_index, (index, record) in enumerate(indexed_records):
        result = render_one(record, index, force=args.force)
        enhanced.append(result)
        print(
            f"[{completed_index + 1:02d}/{len(indexed_records):02d}] source={index + 1:02d} "
            f"{Path(result['output']).name} | "
            f"captions={result['captionEvents']} voices={','.join(result['voices'])}",
            flush=True,
        )

    output_manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceManifest": str(SOURCE_MANIFEST),
        "count": len(enhanced),
        "enhancements": [
            "gentle camera drift",
            "karaoke-style burned captions",
            "explicit AI voice labels",
            "animated audio meter",
            "animated progress rails",
            "Dagric logo watermark",
            "contextual final call-to-action",
            "audio fades and light dynamics control",
        ],
        "videos": enhanced,
    }
    (OUTPUT_ROOT / "enhanced-manifest.json").write_text(
        json.dumps(output_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Completed {len(enhanced)} enhanced masters in {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
