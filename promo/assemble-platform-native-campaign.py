#!/usr/bin/env python3
"""Assemble unique platform cuts without re-encoding the audited core video.

Each output is a newly rendered hook card + the untouched enhanced master + a
new platform-native outro.  This preserves the audited narration/captions while
giving TikTok, Instagram, YouTube, and Snapchat visibly different pacing,
lengths, calls to action, colors, and original synthesized audio stings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(r"C:\Users\1248n\Documents\ChatGPT\Dagric Os")
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
SOURCE_ROOT = DELIVERY / "Enhanced Masters"
SOURCE_MANIFEST = SOURCE_ROOT / "enhanced-manifest.json"
OUTPUT_ROOT = DELIVERY / "Platform-Native Campaign"
SEGMENT_ROOT = OUTPUT_ROOT / "_segments"
WORK_ROOT = OUTPUT_ROOT / "_work"
LOGO = REPO / "site" / "assets" / "dagric-logo.png"
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    intro: float
    outro: float
    accent: str
    background: str
    tone_hz: int
    hook_labels: tuple[str, ...]
    outros: tuple[str, ...]
    subline: str


PLATFORMS = (
    Platform("tiktok", "TikTok", 0.62, 1.70, "4FB3E8", "07111F", 740,
             ("QUICK TEST", "REAL DESKTOP", "BEFORE YOU SWITCH", "DAGRIC EXPLAINED"),
             ("COMMENT YOUR PC MODEL", "WHAT SHOULD WE TEST NEXT?", "WOULD YOU TRY THE LIVE USB?", "FOLLOW THE BUILD"),
             "@DAGRICOSOFFICIAL  •  DAGRIC.COM"),
    Platform("instagram", "Instagram Reels", 1.02, 2.55, "7BE0C8", "081A20", 620,
             ("SAVE THIS", "REAL DAGRIC FOOTAGE", "PC SWITCH GUIDE", "DESKTOP PROOF"),
             ("SAVE THIS GUIDE", "SHARE WITH A WINDOWS 10 USER", "FOLLOW FOR RELEASE TESTS", "COMMENT YOUR HARDWARE"),
             "@DAGRICOSOFFICIAL  •  DAGRIC.COM"),
    Platform("youtube", "YouTube Shorts", 0.82, 3.25, "F05B68", "110C19", 520,
             ("DAGRIC OS SHORT", "REAL PC TEST", "PROOF BEFORE PROMISES", "WINDOWS 10 PC?"),
             ("SUBSCRIBE FOR REAL PC TESTS", "WATCH THE NEXT DAGRIC DEMO", "SUBSCRIBE FOR BUILD UPDATES", "TRY THE LIVE USB • REPORT BACK"),
             "DAGRIC OS  •  DAGRIC.COM"),
    Platform("snapchat", "Snapchat Spotlight", 0.45, 1.25, "FFD84D", "090A0C", 830,
             ("FAST FACT", "TRY THIS FIRST", "OLD PC CHECK", "DAGRIC IN 15 SECONDS"),
             ("SCREENSHOT THIS", "SEND TO A WINDOWS 10 USER", "TRY IT FROM USB", "FOLLOW @DAGRICOS"),
             "@DAGRICOS  •  DAGRIC.COM"),
)


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
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture=True))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ffpath(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def safe_title(value: str) -> str:
    return value.split("|", 1)[0].strip()[:68].rstrip(" .")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def render_card(
    output: Path,
    *,
    duration: float,
    background: str,
    accent: str,
    headline_file: Path,
    detail_file: Path,
    tone_hz: int,
    kind: str,
    force: bool,
) -> None:
    if output.exists() and output.stat().st_size > 0 and not force:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    headline = ffpath(headline_file)
    detail = ffpath(detail_file)
    font_bold = ffpath(FONT_BOLD)
    font_regular = ffpath(FONT_REGULAR)
    accent_ff = "0x" + accent
    if kind == "intro":
        box_y, headline_y, detail_y, logo_y = 650, 790, 900, 675
        progress = f"drawbox=x=70:y=650:w='min(940,940*t/{duration:.3f})':h=12:color={accent_ff}@0.96:t=fill,"
    else:
        box_y, headline_y, detail_y, logo_y = 680, 815, 930, 700
        progress = f"drawbox=x=70:y=1098:w='min(940,940*t/{duration:.3f})':h=12:color={accent_ff}@0.96:t=fill,"
    video_filter = (
        "setsar=1,format=rgba,"
        f"drawbox=x=70:y={box_y}:w=940:h=430:color=0x07101C@0.86:t=fill,"
        f"drawbox=x=70:y={box_y}:w=940:h=430:color={accent_ff}@0.90:t=4,"
        f"{progress}"
        f"drawtext=fontfile='{font_bold}':textfile='{headline}':fontcolor=white:fontsize=46:"
        f"x=(w-text_w)/2:y={headline_y},"
        f"drawtext=fontfile='{font_regular}':textfile='{detail}':fontcolor={accent_ff}:fontsize=28:"
        f"x=(w-text_w)/2:y={detail_y},"
        f"fade=t=in:st=0:d=0.16:alpha=1,fade=t=out:st={max(0.12, duration - 0.18):.3f}:d=0.16:alpha=1[base];"
        "[1:v]scale=108:108:flags=lanczos,format=rgba,colorchannelmixer=aa=0.90[logo];"
        f"[base][logo]overlay=x=(W-w)/2:y={logo_y}:format=auto,format=yuv420p[v]"
    )
    audio_filter = (
        f"volume=0.050,afade=t=in:st=0:d=0.06,afade=t=out:st={max(0.10, duration - 0.20):.3f}:d=0.18,"
        "aformat=sample_rates=48000:channel_layouts=stereo[a]"
    )
    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{background}:s=1080x1920:r=30:d={duration:.3f}",
        "-loop", "1", "-framerate", "30", "-i", str(LOGO),
        "-f", "lavfi", "-i", f"sine=frequency={tone_hz}:sample_rate=48000:duration={duration:.3f}",
        "-filter_complex", f"[0:v]{video_filter};[2:a]{audio_filter}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "20", "-qp_p", "20",
        "-profile:v", "high", "-level", "42", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", f"{duration:.3f}",
        "-movflags", "+faststart", str(output),
    ]
    try:
        run(args)
    except subprocess.CalledProcessError:
        # Keep the workflow portable if hardware encoding is temporarily busy.
        codec_at = args.index("h264_amf")
        profile_at = args.index("-profile:v", codec_at)
        fallback = args[:codec_at] + ["libx264", "-preset", "ultrafast", "-crf", "20"] + args[profile_at:]
        run(fallback)


def concat_copy(intro: Path, source: Path, outro: Path, output: Path, list_path: Path) -> None:
    def entry(path: Path) -> str:
        return "file '" + str(path.resolve()).replace("'", "'\\''") + "'"
    list_path.parent.mkdir(parents=True, exist_ok=True)
    list_path.write_text("\n".join([entry(intro), entry(source), entry(outro)]) + "\n", encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", "-avoid_negative_ts", "make_zero", str(output),
    ])


def build_one(record: dict, index: int, platform: Platform, *, force: bool) -> dict:
    source = Path(record["output"])
    relative = source.relative_to(SOURCE_ROOT)
    stem = relative.stem.removesuffix("-final")
    intro_duration = platform.intro + (index % 3) * 0.07
    outro_duration = platform.outro + (index % 4) * 0.12
    hook_label = platform.hook_labels[index % len(platform.hook_labels)]
    outro_copy = platform.outros[index % len(platform.outros)]
    title = safe_title(str(record["title"]))

    text_dir = WORK_ROOT / platform.key / relative.parent
    hook_text = text_dir / f"{stem}-hook.txt"
    title_text = text_dir / f"{stem}-title.txt"
    outro_text = text_dir / f"{stem}-outro.txt"
    subline_text = text_dir / f"{stem}-subline.txt"
    write_text(hook_text, hook_label)
    write_text(title_text, title)
    write_text(outro_text, outro_copy)
    write_text(subline_text, platform.subline)

    segment_dir = SEGMENT_ROOT / platform.key / relative.parent
    intro = segment_dir / f"{stem}-intro.mp4"
    outro = segment_dir / f"{stem}-outro.mp4"
    render_card(intro, duration=intro_duration, background=platform.background, accent=platform.accent,
                headline_file=hook_text, detail_file=title_text, tone_hz=platform.tone_hz + 90,
                kind="intro", force=force)
    render_card(outro, duration=outro_duration, background=platform.background, accent=platform.accent,
                headline_file=outro_text, detail_file=subline_text, tone_hz=platform.tone_hz,
                kind="outro", force=force)

    output = OUTPUT_ROOT / platform.key / relative.parent / f"{stem}-{platform.key}-native.mp4"
    list_path = WORK_ROOT / platform.key / relative.parent / f"{stem}-concat.txt"
    if force or not output.exists() or output.stat().st_size == 0:
        concat_copy(intro, source, outro, output, list_path)
    info = probe(output)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    return {
        "sourceNumber": record["number"], "batch": record["batch"], "topic": record["topic"],
        "title": record["title"], "publishAt": record["publishAt"], "platform": platform.key,
        "platformLabel": platform.label, "source": str(source), "output": str(output), "speed": 1.0,
        "introDurationSeconds": round(intro_duration, 3), "outroDurationSeconds": round(outro_duration, 3),
        "hookLabel": hook_label, "outroCopy": outro_copy, "subline": platform.subline,
        "durationSeconds": round(float(info["format"]["duration"]), 3),
        "video": {"codec": video["codec_name"], "width": video["width"], "height": video["height"],
                  "frameRate": video.get("avg_frame_rate")},
        "audio": {"codec": audio["codec_name"], "sampleRate": int(audio["sample_rate"]),
                  "channels": audio["channels"]},
        "sha256": sha256(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--platform", choices=[p.key for p in PLATFORMS], action="append")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    records = manifest["videos"]
    selected = list(enumerate(records))[max(0, args.start - 1):]
    if args.limit:
        selected = selected[:args.limit]
    platforms = tuple(p for p in PLATFORMS if not args.platform or p.key in args.platform)
    results: list[dict] = []
    total = len(selected) * len(platforms)
    for completed, (index, record) in enumerate((pair for pair in selected for _ in [0]), start=1):
        for platform_index, platform in enumerate(platforms):
            position = (completed - 1) * len(platforms) + platform_index + 1
            result = build_one(record, index, platform, force=args.force)
            results.append(result)
            print(f"[{position:03d}/{total:03d}] {platform.key:9s} {Path(result['output']).name} | "
                  f"{result['durationSeconds']:.2f}s | {result['outroCopy']}", flush=True)

    manifest_path = OUTPUT_ROOT / "platform-native-manifest.json"
    existing: list[dict] = []
    if manifest_path.exists() and (args.start != 1 or args.limit or args.platform):
        existing = json.loads(manifest_path.read_text(encoding="utf-8")).get("videos", [])
    merged = {(item["sourceNumber"], item["platform"]): item for item in existing}
    merged.update({(item["sourceNumber"], item["platform"]): item for item in results})
    ordered = [merged[key] for key in sorted(merged)]
    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(), "sourceManifest": str(SOURCE_MANIFEST),
        "count": len(ordered), "platforms": [p.key for p in PLATFORMS],
        "rights": "Dagric-owned core video plus locally rendered cards and original synthesized tones; no downloaded music.",
        "videos": ordered,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifest contains {len(ordered)} variants: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
