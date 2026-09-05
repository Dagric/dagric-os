#!/usr/bin/env python3
"""Assemble caption-free duration variants from one continuous Dagric recording."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
SOURCE = DELIVERY / "Real VM Footage" / "long-form-v4" / "00-dagric-15-minute-live-showcase-v4.mp4"
RECEIPT = SOURCE.with_suffix(".capture.json")
AUDIO_MANIFEST = DELIVERY / "Duration Ladder" / "duration-ladder-audio-manifest.json"
OUT = DELIVERY / "Duration Ladder" / "caption-free-v4"
WORK = OUT / "work"


@dataclass(frozen=True)
class Platform:
    slug: str
    label: str
    vertical: bool
    canvas: str
    accent: tuple[int, int, int, int]


PLATFORMS = (
    Platform("tiktok", "TikTok", True, "102A2A", (232, 93, 84, 255)),
    Platform("instagram", "Instagram", True, "241B21", (226, 104, 76, 255)),
    Platform("youtube", "YouTube", False, "160E25", (220, 70, 180, 255)),
    Platform("snapchat", "Snapchat", True, "182317", (105, 145, 74, 255)),
)


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


def probe(path: Path) -> dict:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,channels,sample_rate",
        "-of", "json", str(path),
    ], capture=True))


def latest_iso() -> tuple[Path, str]:
    candidates = sorted(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No named Dagric ISO in out/")
    return candidates[0], sha256(candidates[0])


def validate_source() -> tuple[dict, dict]:
    if not SOURCE.is_file() or not RECEIPT.is_file():
        raise FileNotFoundError("The new 15-minute continuous source and receipt are required")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    info = probe(SOURCE)
    iso, iso_hash = latest_iso()
    checks = {
        "continuousCapture": receipt.get("captureMode") == "continuous-vnc-stream",
        "continuousFrameEncoding": receipt.get("continuousFrameEncoding") is True,
        "noSnapshots": receipt.get("snapshotInputs") == [],
        "sourceHash": receipt.get("sha256") == sha256(SOURCE),
        "newestIsoPath": Path(receipt.get("iso", "")).resolve() == iso.resolve(),
        "newestIsoHash": receipt.get("isoSha256") == iso_hash,
        "duration": float(info["format"]["duration"]) >= 899.9,
        "oneVideoStream": len([s for s in info["streams"] if s["codec_type"] == "video"]) == 1,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Long-form source failed validation: " + ", ".join(failed))
    return receipt, checks


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def intro_card(slug: str, platform: Platform) -> Path:
    path = WORK / f"{slug}-{platform.slug}-intro.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    label = slug.replace("-", " ").upper()
    draw.rounded_rectangle((48, 1118, 1032, 1296), radius=30, fill=(18, 24, 31, 238))
    draw.rectangle((48, 1118, 60, 1296), fill=platform.accent)
    draw.text((84, 1145), label[:34], font=font(38, True), fill="white")
    draw.text((84, 1215), "DAGRiC OS • LIVE FOOTAGE", font=font(24), fill=platform.accent)
    image.save(path)
    return path


def render(edition: dict, platform: Platform, audio_only: bool = False) -> dict:
    slug = edition["slug"]
    duration = float(edition["durationSeconds"])
    source_start = float(edition["sourceStartSeconds"])
    audio = Path(edition["audio"])
    if not audio.is_file():
        raise FileNotFoundError(audio)
    output_dir = OUT / platform.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{slug}-{platform.slug}.mp4"
    if audio_only:
        if not output.is_file():
            raise FileNotFoundError(output)
        refreshed = output.with_name(output.stem + "-audio-refresh.mp4")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(output), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
            "-t", f"{duration:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-ac", "2",
            "-af", "highpass=f=72,lowpass=f=15800,acompressor=threshold=0.12:ratio=1.8:attack=15:release=140:makeup=1.25,loudnorm=I=-16:LRA=7:TP=-1.5",
            "-movflags", "+faststart", "-metadata", "artist=Dagric OS",
            "-metadata", "comment=Continuous live product footage; one video layer; no captions or subtitles; synthetic narration",
            str(refreshed),
        ])
        refreshed.replace(output)
        info = probe(output)
        streams = info["streams"]
        return {
            "slug": slug, "platform": platform.slug, "output": str(output), "sha256": sha256(output),
            "durationSeconds": round(float(info["format"]["duration"]), 3),
            "sourceStartSeconds": source_start, "source": str(SOURCE), "captureReceipt": str(RECEIPT),
            "videoStreams": len([s for s in streams if s["codec_type"] == "video"]),
            "audioStreams": len([s for s in streams if s["codec_type"] == "audio"]),
            "subtitleStreams": len([s for s in streams if s["codec_type"] == "subtitle"]),
            "captionPolicy": "none", "snapshotInputs": [], "visibleProductVideoLayers": 1,
            "introMaximumSeconds": 3.0 if platform.vertical else 0.0,
            "introOverlapsProductFootage": False,
        }
    common = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{source_start:.3f}", "-i", str(SOURCE), "-i", str(audio),
    ]
    if platform.vertical:
        intro = intro_card(slug, platform)
        filters = (
            f"color=c=0x{platform.canvas}:s=1080x1920:r=30:d={duration:.3f}[bg];"
            "[0:v]fps=30,scale=1140:713:flags=lanczos,"
            "crop=1080:675:x='30+30*sin(t*0.50)':y='19+19*cos(t*0.41)',format=yuv420p[screen];"
            "[bg][screen]overlay=0:300:shortest=1[base];"
            "[2:v]format=rgba,fade=t=in:st=0:d=0.2:alpha=1,"
            "fade=t=out:st=2.6:d=0.4:alpha=1[intro];"
            "[base][intro]overlay=0:0:shortest=1[outv]"
        )
        args = [*common, "-loop", "1", "-i", str(intro), "-filter_complex", filters, "-map", "[outv]"]
    else:
        filters = (
            f"color=c=0x{platform.canvas}:s=1920x1080:r=30:d={duration:.3f}[bg];"
            "[0:v]fps=30,scale=1810:1131:flags=lanczos,"
            "crop=1728:1080:x='41+41*sin(t*0.42)':y='25+25*cos(t*0.37)',format=yuv420p[screen];"
            "[bg][screen]overlay=96:0:shortest=1[outv]"
        )
        args = [*common, "-filter_complex", filters, "-map", "[outv]"]
    run([
        *args, "-map", "1:a:0", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-af", "highpass=f=72,lowpass=f=15800,acompressor=threshold=0.12:ratio=1.8:attack=15:release=140:makeup=1.25,loudnorm=I=-16:LRA=7:TP=-1.5",
        "-movflags", "+faststart", "-metadata", "artist=Dagric OS",
        "-metadata", "comment=Continuous live product footage; one video layer; no captions or subtitles; synthetic narration",
        str(output),
    ])
    info = probe(output)
    streams = info["streams"]
    return {
        "slug": slug,
        "platform": platform.slug,
        "output": str(output),
        "sha256": sha256(output),
        "durationSeconds": round(float(info["format"]["duration"]), 3),
        "sourceStartSeconds": source_start,
        "source": str(SOURCE),
        "captureReceipt": str(RECEIPT),
        "videoStreams": len([s for s in streams if s["codec_type"] == "video"]),
        "audioStreams": len([s for s in streams if s["codec_type"] == "audio"]),
        "subtitleStreams": len([s for s in streams if s["codec_type"] == "subtitle"]),
        "captionPolicy": "none",
        "snapshotInputs": [],
        "visibleProductVideoLayers": 1,
        "introMaximumSeconds": 3.0 if platform.vertical else 0.0,
        "introOverlapsProductFootage": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", action="append", help="Render selected editions and preserve other records")
    parser.add_argument("--audio-only", action="store_true", help="Refresh audio while stream-copying existing video")
    args = parser.parse_args()
    receipt, source_checks = validate_source()
    manifest = json.loads(AUDIO_MANIFEST.read_text(encoding="utf-8"))
    editions = [edition for edition in manifest["editions"] if not args.slug or edition["slug"] in args.slug]
    if args.slug and len(editions) != len(set(args.slug)):
        raise RuntimeError("One or more requested duration-ladder slugs are unknown")
    outputs = []
    for edition in editions:
        for platform in PLATFORMS:
            print(f"Rendering {edition['slug']} for {platform.label}", flush=True)
            outputs.append(render(edition, platform, audio_only=args.audio_only))
    path = OUT / "duration-ladder-video-manifest.json"
    if args.slug and path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        replaced = {edition["slug"] for edition in editions}
        outputs = [item for item in existing.get("outputs", []) if item.get("slug") not in replaced] + outputs
        edition_order = {edition["slug"]: index for index, edition in enumerate(manifest["editions"])}
        platform_order = {platform.slug: index for index, platform in enumerate(PLATFORMS)}
        outputs.sort(key=lambda item: (edition_order[item["slug"]], platform_order[item["platform"]]))
    result = {
        "schema": "dagric-caption-free-duration-ladder-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE),
        "sourceReceipt": str(RECEIPT),
        "sourceReceiptSha256": sha256(RECEIPT),
        "sourceChecks": source_checks,
        "captionPolicy": "none",
        "maximumSimultaneousProductVideoLayers": 1,
        "outputCount": len(outputs),
        "outputs": outputs,
    }
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Completed {len(outputs)} duration-ladder videos in {OUT}")
    print(f"Manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
