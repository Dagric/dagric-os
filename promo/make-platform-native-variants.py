#!/usr/bin/env python3
"""Build platform-native Dagric OS cuts from the audited enhanced masters.

Every source produces a TikTok, Instagram Reel, YouTube Short, and Snapchat
variant.  The narration remains complete, but pacing, camera treatment,
opening label, synthesized end sting, outro duration, outro copy, and metadata
are platform-specific.  No downloaded music or third-party footage is used.
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
WORK_ROOT = OUTPUT_ROOT / "_text"
LOGO = REPO / "site" / "assets" / "dagric-logo.png"
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    speed: float
    zoom: float
    outro: float
    accent: str
    background: str
    tone_hz: int
    hook_labels: tuple[str, ...]
    outros: tuple[str, ...]
    subline: str


PLATFORMS = (
    Platform(
        key="tiktok",
        label="TikTok",
        speed=1.07,
        zoom=1.060,
        outro=1.70,
        accent="4FB3E8",
        background="07111F",
        tone_hz=740,
        hook_labels=("QUICK TEST", "REAL DESKTOP", "BEFORE YOU SWITCH", "DAGRIC EXPLAINED"),
        outros=("COMMENT YOUR PC MODEL", "WHAT SHOULD WE TEST NEXT?", "WOULD YOU TRY THE LIVE USB?", "FOLLOW THE BUILD"),
        subline="@DAGRICOSOFFICIAL  •  DAGRIC.COM",
    ),
    Platform(
        key="instagram",
        label="Instagram Reels",
        speed=1.00,
        zoom=1.035,
        outro=2.55,
        accent="7BE0C8",
        background="081A20",
        tone_hz=620,
        hook_labels=("SAVE THIS", "REAL DAGRIC FOOTAGE", "PC SWITCH GUIDE", "DESKTOP PROOF"),
        outros=("SAVE THIS GUIDE", "SHARE WITH A WINDOWS 10 USER", "FOLLOW FOR RELEASE TESTS", "COMMENT YOUR HARDWARE"),
        subline="@DAGRICOSOFFICIAL  •  DAGRIC.COM",
    ),
    Platform(
        key="youtube",
        label="YouTube Shorts",
        speed=0.97,
        zoom=1.020,
        outro=3.25,
        accent="F05B68",
        background="110C19",
        tone_hz=520,
        hook_labels=("DAGRIC OS SHORT", "REAL PC TEST", "PROOF BEFORE PROMISES", "WINDOWS 10 PC?"),
        outros=("SUBSCRIBE FOR REAL PC TESTS", "WATCH THE NEXT DAGRIC DEMO", "SUBSCRIBE FOR BUILD UPDATES", "TRY THE LIVE USB • REPORT BACK"),
        subline="@DAGRICOS  •  DAGRIC.COM",
    ),
    Platform(
        key="snapchat",
        label="Snapchat Spotlight",
        speed=1.10,
        zoom=1.075,
        outro=1.25,
        accent="FFD84D",
        background="090A0C",
        tone_hz=830,
        hook_labels=("FAST FACT", "TRY THIS FIRST", "OLD PC CHECK", "DAGRIC IN 15 SECONDS"),
        outros=("SCREENSHOT THIS", "SEND TO A WINDOWS 10 USER", "TRY IT FROM USB", "FOLLOW @DAGRICOS"),
        subline="@DAGRICOS  •  DAGRIC.COM",
    ),
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
    return json.loads(
        run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture=True)
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ffpath(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def safe_title(value: str) -> str:
    value = value.split("|", 1)[0].strip()
    return value[:68].rstrip(" .")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def render_variant(record: dict, index: int, platform: Platform, *, force: bool) -> dict:
    source = Path(record["output"])
    if not source.exists():
        raise FileNotFoundError(source)

    # A tiny deterministic variation prevents every cut on one network from
    # sharing the exact same duration or camera rhythm.
    speed = platform.speed + ((index % 3) - 1) * 0.004
    outro_duration = platform.outro + (index % 4) * 0.12
    hook_label = platform.hook_labels[index % len(platform.hook_labels)]
    outro_copy = platform.outros[index % len(platform.outros)]
    title = safe_title(str(record["title"]))

    relative = source.relative_to(SOURCE_ROOT)
    stem = relative.stem.removesuffix("-final")
    output_dir = OUTPUT_ROOT / platform.key / relative.parent
    output = output_dir / f"{stem}-{platform.key}-native.mp4"
    text_dir = WORK_ROOT / platform.key / relative.parent
    hook_file = text_dir / f"{stem}-hook.txt"
    title_file = text_dir / f"{stem}-title.txt"
    outro_file = text_dir / f"{stem}-outro.txt"
    subline_file = text_dir / f"{stem}-subline.txt"
    write_text(hook_file, hook_label)
    write_text(title_file, title)
    write_text(outro_file, outro_copy)
    write_text(subline_file, platform.subline)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output.exists() and not force:
        info = probe(output)
    else:
        accent = "0x" + platform.accent
        zoom_w = int(round(1080 * platform.zoom / 2) * 2)
        zoom_h = int(round(1920 * platform.zoom / 2) * 2)
        x_motion = 8 + (index % 5) * 2
        y_motion = 10 + (index % 4) * 2
        phase = (index % 11) * 0.37
        hook = ffpath(hook_file)
        title_path = ffpath(title_file)
        outro_path = ffpath(outro_file)
        subline_path = ffpath(subline_file)
        font_bold = ffpath(FONT_BOLD)
        font_regular = ffpath(FONT_REGULAR)
        logo_path = str(LOGO)

        if platform.key == "tiktok":
            grade = "eq=contrast=1.045:saturation=1.075:brightness=0.006"
            side = f"drawbox=x=20:y=310:w=5:h=1190:color={accent}@0.72:t=fill"
        elif platform.key == "instagram":
            grade = "eq=contrast=1.020:saturation=1.045:brightness=0.008"
            side = f"drawbox=x=28:y=330:w=4:h=1120:color={accent}@0.48:t=fill"
        elif platform.key == "youtube":
            grade = "eq=contrast=1.035:saturation=1.025:brightness=0.002,vignette=PI/7"
            side = f"drawbox=x=18:y=260:w=1044:h=4:color={accent}@0.70:t=fill"
        else:
            grade = "eq=contrast=1.060:saturation=1.100:brightness=0.006"
            side = f"drawbox=x=0:y=0:w=1080:h=12:color={accent}@0.90:t=fill"

        filters = (
            f"[0:v]setpts=PTS/{speed:.6f},scale={zoom_w}:{zoom_h}:flags=lanczos,"
            f"crop=1080:1920:x='(iw-ow)/2+{x_motion}*sin(0.31*t+{phase:.3f})':"
            f"y='(ih-oh)/2+{y_motion}*sin(0.23*t+{phase / 2:.3f})',setsar=1,fps=30,{grade},{side},"
            f"drawbox=x=54:y=76:w=972:h=120:color=0x07101C@0.88:t=fill:enable='between(t,0,1.55)',"
            f"drawbox=x=54:y=76:w=972:h=120:color={accent}@0.92:t=3:enable='between(t,0,1.55)',"
            f"drawtext=fontfile='{font_bold}':textfile='{hook}':fontcolor=white:fontsize=31:"
            "x=78:y=98:enable='between(t,0,1.55)',"
            f"drawtext=fontfile='{font_regular}':textfile='{title_path}':fontcolor=white@0.94:fontsize=24:"
            "x=78:y=142:enable='between(t,0,1.55)'[mainv];"
            f"color=c=0x{platform.background}:s=1080x1920:r=30:d={outro_duration:.3f},setsar=1,format=rgba,"
            f"drawbox=x=70:y=680:w=940:h=430:color=0x07101C@0.84:t=fill,"
            f"drawbox=x=70:y=680:w=940:h=430:color={accent}@0.88:t=4,"
            f"drawbox=x=70:y=680:w='min(940,940*t/{outro_duration:.3f})':h=12:color={accent}@0.95:t=fill,"
            f"drawtext=fontfile='{font_bold}':textfile='{outro_path}':fontcolor=white:fontsize=46:"
            "x=(w-text_w)/2:y=815,"
            f"drawtext=fontfile='{font_regular}':textfile='{subline_path}':fontcolor=0x{platform.accent}:"
            "fontsize=28:x=(w-text_w)/2:y=930,"
            f"fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0.2, outro_duration - 0.24):.3f}:d=0.22:alpha=1[outbase];"
            "[1:v]scale=108:108:flags=lanczos,format=rgba,colorchannelmixer=aa=0.90[logo];"
            "[outbase][logo]overlay=x=(W-w)/2:y=700:format=auto[outv];"
            "[mainv][outv]concat=n=2:v=1:a=0,format=yuv420p[v];"
            f"[0:a]atempo={speed:.6f},aresample=48000,"
            "highpass=f=42,lowpass=f=16500,alimiter=limit=0.95[maina];"
            f"[2:a]volume=0.055,afade=t=in:st=0:d=0.08,"
            f"afade=t=out:st={max(0.15, outro_duration - 0.32):.3f}:d=0.30,"
            "aformat=sample_rates=48000:channel_layouts=stereo[outa];"
            "[maina][outa]concat=n=2:v=0:a=1[a]"
        )

        run(
            [
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
                logo_path,
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={platform.tone_hz}:sample_rate=48000:duration={outro_duration:.3f}",
                "-filter_complex",
                filters,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
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
                "-movflags",
                "+faststart",
                "-metadata",
                f"title=Dagric OS {platform.label} native cut",
                "-metadata",
                f"comment=Platform-native pacing and original synthesized outro; source={record['topic']}",
                str(output),
            ]
        )
        info = probe(output)

    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    duration = float(info["format"]["duration"])
    return {
        "sourceNumber": record["number"],
        "batch": record["batch"],
        "topic": record["topic"],
        "title": record["title"],
        "publishAt": record["publishAt"],
        "platform": platform.key,
        "platformLabel": platform.label,
        "source": str(source),
        "output": str(output),
        "speed": round(speed, 4),
        "outroDurationSeconds": round(outro_duration, 3),
        "hookLabel": hook_label,
        "outroCopy": outro_copy,
        "subline": platform.subline,
        "durationSeconds": round(duration, 3),
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
    parser.add_argument("--start", type=int, default=1, help="One-based source record")
    parser.add_argument("--limit", type=int, default=0, help="Number of source records")
    parser.add_argument("--platform", choices=[p.key for p in PLATFORMS], action="append")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    required = [SOURCE_MANIFEST, LOGO, FONT_BOLD, FONT_REGULAR]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(map(str, missing)))

    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    records = manifest["videos"]
    selected = list(enumerate(records))[max(0, args.start - 1) :]
    if args.limit:
        selected = selected[: args.limit]
    platforms = tuple(p for p in PLATFORMS if not args.platform or p.key in args.platform)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    total = len(selected) * len(platforms)
    completed = 0
    for index, record in selected:
        for platform in platforms:
            completed += 1
            result = render_variant(record, index, platform, force=args.force)
            results.append(result)
            print(
                f"[{completed:03d}/{total:03d}] {platform.key:9s} "
                f"{Path(result['output']).name} | {result['durationSeconds']:.2f}s | {result['outroCopy']}",
                flush=True,
            )

    manifest_path = OUTPUT_ROOT / "platform-native-manifest.json"
    existing: list[dict] = []
    if manifest_path.exists() and (args.start != 1 or args.limit or args.platform):
        existing = json.loads(manifest_path.read_text(encoding="utf-8")).get("videos", [])
    merged = {(item["sourceNumber"], item["platform"]): item for item in existing}
    merged.update({(item["sourceNumber"], item["platform"]): item for item in results})
    ordered = [merged[key] for key in sorted(merged)]
    output_manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceManifest": str(SOURCE_MANIFEST),
        "count": len(ordered),
        "platforms": [p.key for p in PLATFORMS],
        "rights": "Original Dagric visuals and narration; original synthesized outro tone; no downloaded music or creator footage.",
        "videos": ordered,
    }
    manifest_path.write_text(json.dumps(output_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifest contains {len(ordered)} variants: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
