#!/usr/bin/env python3
"""Build social masters whose primary visual is genuine Dagric OS VM footage."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
ROOT = DELIVERY / "Real VM Footage"
RAW = ROOT / "raw-realtime"
FINISHED = ROOT / "finished"
WORK = ROOT / "work"
NARRATED = DELIVERY / "Narrated Replacements"
CAPTIONS = DELIVERY / "Editorial Masters"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
CAPTURE_MODE = "continuous-vnc-stream"

MONTAGE_SEGMENTS = [
    (RAW / "07-real-firefox-dagric-site.mp4", 22.0, 6.0),
    (RAW / "02-real-dagric-hub.mp4", 10.0, 5.0),
    (RAW / "06-real-settings-accessibility-connect.mp4", 4.0, 5.0),
    (RAW / "05-real-everyday-desktop.mp4", 4.0, 5.0),
    (RAW / "06-real-settings-accessibility-connect.mp4", 9.0, 5.0),
    (RAW / "06-real-settings-accessibility-connect.mp4", 14.0, 5.0),
    (RAW / "06-real-settings-accessibility-connect.mp4", 19.0, 4.0),
    (RAW / "03-real-hardware-check.mp4", 6.0, 4.0),
    (RAW / "04-real-appearance-and-layouts.mp4", 14.0, 4.0),
    (RAW / "03-real-hardware-check.mp4", 20.0, 6.0),
]


@dataclass(frozen=True)
class Edit:
    slug: str
    title: str
    subtitle: str
    source: Path
    start: float
    duration: float
    audio: Path
    captions: Path


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


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int) -> ImageFont.FreeTypeFont:
    candidate = font(size, bold=True)
    while size > 30 and draw.textbbox((0, 0), text, font=candidate)[2] > max_width:
        size -= 2
        candidate = font(size, bold=True)
    return candidate


def title_overlay(edit: Edit, width: int, height: int, vertical: bool) -> Path:
    path = WORK / f"{edit.slug}-{'vertical' if vertical else 'landscape'}-overlay.png"
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if vertical:
        draw.rounded_rectangle((32, 30, 558, 94), radius=30, fill=(9, 29, 48, 236), outline=(70, 199, 255, 255), width=2)
        draw.ellipse((55, 51, 77, 73), fill=(70, 199, 255, 255))
        draw.text((93, 47), "REAL DAGRIC OS  |  LIVE ISO", font=font(26, bold=True), fill="white")
        title_font = fit_text(draw, edit.title, 1016, 64)
        draw.text((32, 114), edit.title, font=title_font, fill="white")
        draw.text((34, 206), edit.subtitle, font=font(31), fill=(207, 230, 244, 255))
        draw.rounded_rectangle((32, 1726, 1048, 1872), radius=28, fill=(5, 18, 31, 222), outline=(255, 255, 255, 32), width=2)
        draw.text((62, 1752), "ACTUAL DAGRIC OS PRO FOOTAGE", font=font(28, bold=True), fill=(89, 208, 255, 255))
        draw.text((62, 1798), "Recorded from the live ISO in a VM  |  No stock desktop footage", font=font(25), fill=(228, 239, 247, 255))
    else:
        draw.rounded_rectangle((40, 34, 566, 98), radius=30, fill=(9, 29, 48, 236), outline=(70, 199, 255, 255), width=2)
        draw.ellipse((63, 55, 85, 77), fill=(70, 199, 255, 255))
        draw.text((101, 51), "REAL DAGRIC OS  |  LIVE ISO", font=font(26, bold=True), fill="white")
        title_font = fit_text(draw, edit.title, 1190, 52)
        draw.rounded_rectangle((36, 120, 1320, 220), radius=22, fill=(5, 18, 31, 205))
        draw.text((58, 132), edit.title, font=title_font, fill="white")
        draw.rounded_rectangle((37, 932, 1883, 1044), radius=22, fill=(5, 18, 31, 212))
        draw.text((62, 948), edit.subtitle, font=font(29, bold=True), fill=(231, 242, 249, 255))
        draw.text((62, 995), "Actual Dagric OS Pro live-ISO footage recorded in a VM", font=font(23), fill=(89, 208, 255, 255))
    image.save(path)
    return path


def escape_subtitle_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def capture_receipt_path(path: Path) -> Path:
    return path.with_suffix(".capture.json")


def verify_capture_receipt(path: Path) -> Path:
    receipt_path = capture_receipt_path(path)
    if not receipt_path.is_file():
        raise RuntimeError(f"Realtime source is missing its capture receipt: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checks = {
        "capture mode": receipt.get("captureMode") == CAPTURE_MODE,
        "continuous frame encoding": receipt.get("continuousFrameEncoding") is True,
        "asynchronous framebuffer refresh": receipt.get("asynchronousFramebufferRefresh") is True,
        "no snapshot inputs": receipt.get("snapshotInputs") == [],
        "minimum capture rate": int(receipt.get("targetFramesPerSecond", 0)) >= 20,
        "matching source path": Path(receipt.get("output", "")).resolve() == path.resolve(),
        "matching source hash": receipt.get("sha256") == sha256(path),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Invalid capture receipt for {path}: {', '.join(failed)}")
    return receipt_path


def assert_realtime_visual_source(edit: Edit) -> None:
    if edit.source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise RuntimeError(f"Snapshot/image visual sources are forbidden: {edit.source}")
    info = probe(edit.source)
    video_streams = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
    if not video_streams:
        raise RuntimeError(f"Visual source has no video stream: {edit.source}")
    source_duration = float(info["format"]["duration"])
    if edit.start < 0 or edit.duration <= 0 or edit.start + edit.duration > source_duration + 0.05:
        raise RuntimeError(
            f"Requested live-footage segment exceeds {source_duration:.3f}s source: {edit.source}"
        )
    if edit.source.resolve().is_relative_to(RAW.resolve()):
        verify_capture_receipt(edit.source)
    elif edit.source.resolve() != (WORK / "00-real-dagric-showcase-source.mp4").resolve():
        raise RuntimeError(f"Visual source is outside the approved realtime capture roots: {edit.source}")


def make_montage() -> Path:
    output = WORK / "00-real-dagric-showcase-source.mp4"
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path, start, duration in MONTAGE_SEGMENTS:
        if path.suffix.lower() not in VIDEO_EXTENSIONS or not path.exists():
            raise RuntimeError(f"Montage requires continuous video footage: {path}")
        verify_capture_receipt(path)
        args.extend(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(path)])
    chains = []
    refs = []
    for index in range(len(MONTAGE_SEGMENTS)):
        chains.append(
            f"[{index}:v]fps=30,scale=2134:1334:flags=lanczos,format=yuv420p,setpts=PTS-STARTPTS[v{index}]"
        )
        refs.append(f"[v{index}]")
    chains.append(f"{''.join(refs)}concat=n={len(MONTAGE_SEGMENTS)}:v=1:a=0[outv]")
    args.extend([
        "-filter_complex", ";".join(chains), "-map", "[outv]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(output),
    ])
    run(args)
    return output


def render_vertical(edit: Edit) -> Path:
    output = FINISHED / "vertical" / f"{edit.slug}-vertical.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay = title_overlay(edit, 1080, 1920, vertical=True)
    subtitle = escape_subtitle_path(edit.captions)
    filters = (
        # One and only one product-video layer. The remaining portrait canvas is
        # a flat Dagric color field, not a second, blurred, cropped, or delayed
        # copy of the source feed.
        "[0:v]fps=30,scale=1032:720:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=1080:1920:24:300:color=0x08131F,format=yuv420p[base];"
        "[base][2:v]overlay=0:0:shortest=1[t0];"
        f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
        "FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
        "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=296'[outv]"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{edit.start:.3f}", "-t", f"{edit.duration:.3f}", "-i", str(edit.source),
        "-i", str(edit.audio), "-loop", "1", "-i", str(overlay),
        "-filter_complex", filters, "-map", "[outv]", "-map", "1:a:0",
        "-t", f"{edit.duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        "-metadata", f"title={edit.title} - real Dagric OS footage",
        "-metadata", "artist=Dagric OS",
        "-metadata", "comment=Actual Dagric OS Pro live ISO footage captured from a VM; synthetic narration disclosed; human-directed edit; no stock desktop footage",
        str(output),
    ])
    shutil.copyfile(edit.captions, output.with_suffix(".srt"))
    return output


def render_landscape(edit: Edit) -> Path:
    output = FINISHED / "landscape" / f"{edit.slug}-landscape.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay = title_overlay(edit, 1920, 1080, vertical=False)
    subtitle = escape_subtitle_path(edit.captions)
    filters = (
        "[0:v]fps=30,scale=1728:1080:flags=lanczos,"
        "pad=1920:1080:96:0:color=0x08131F,format=yuv420p[base];"
        "[base][2:v]overlay=0:0:shortest=1,crop=1920:1080,setsar=1[t0];"
        f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
        "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
        "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=164',"
        "crop=1920:1080,setsar=1[outv]"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{edit.start:.3f}", "-t", f"{edit.duration:.3f}", "-i", str(edit.source),
        "-i", str(edit.audio), "-loop", "1", "-i", str(overlay),
        "-filter_complex", filters, "-map", "[outv]", "-map", "1:a:0",
        "-t", f"{edit.duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        "-metadata", f"title={edit.title} - real Dagric OS footage",
        "-metadata", "artist=Dagric OS",
        "-metadata", "comment=Actual Dagric OS Pro live ISO footage captured from a VM; synthetic narration disclosed; human-directed edit; no stock desktop footage",
        str(output),
    ])
    shutil.copyfile(edit.captions, output.with_suffix(".srt"))
    return output


def main() -> int:
    FINISHED.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    montage = make_montage()
    edits = [
        Edit(
            "00-real-dagric-showcase", "THIS IS THE REAL DAGRIC OS",
            "A working live desktop: browser, files, hardware check, themes and settings",
            montage, 0.0, 45.0,
            NARRATED / "daily" / "14-dagric-promo-vertical-53s-final.mp4",
            CAPTIONS / "daily" / "14-dagric-promo-vertical-53s-final.srt",
        ),
        Edit(
            "01-real-onboarding", "SET UP YOUR DESKTOP",
            "The genuine first-run wizard: appearance, text, taskbar and optional apps",
            RAW / "01-real-onboarding.mp4", 0.0, 45.0,
            NARRATED / "daily" / "17-real-vm-onboarding-vertical-45s-final.mp4",
            CAPTIONS / "daily" / "17-real-vm-onboarding-vertical-45s-final.srt",
        ),
        Edit(
            "02-real-hardware-check", "CHECK THIS PC BEFORE INSTALLING",
            "A real VM report, including the limits Dagric found",
            RAW / "03-real-hardware-check.mp4", 5.0, 18.0,
            NARRATED / "launch" / "02-check-this-pc-vertical-18s-final.mp4",
            CAPTIONS / "launch" / "02-check-this-pc-vertical-18s-final.srt",
        ),
        Edit(
            "03-real-dagric-hub", "DAGRIC HUB",
            "Setup, security, support and owner guides in one real window",
            RAW / "02-real-dagric-hub.mp4", 8.0, 16.0,
            NARRATED / "launch" / "05-dagric-hub-vertical-16s-final.mp4",
            CAPTIONS / "launch" / "05-dagric-hub-vertical-16s-final.srt",
        ),
        Edit(
            "04-real-themes-and-layouts", "YOUR DESKTOP, YOUR WAY",
            "Watch the genuine Midnight theme and Focus layout preview live",
            RAW / "04-real-appearance-and-layouts.mp4", 13.0, 15.0,
            NARRATED / "daily" / "06-seven-desktop-layouts-vertical-15s-final.mp4",
            CAPTIONS / "daily" / "06-seven-desktop-layouts-vertical-15s-final.srt",
        ),
        Edit(
            "05-real-familiar-desktop", "A FAMILIAR DESKTOP",
            "Launcher, favorites and power controls—shown in the actual live session",
            RAW / "05-real-everyday-desktop.mp4", 2.0, 11.0,
            NARRATED / "daily" / "03-familiar-start-menu-vertical-11s-final.mp4",
            CAPTIONS / "daily" / "03-familiar-start-menu-vertical-11s-final.srt",
        ),
        Edit(
            "06-real-accessibility-settings", "ACCESSIBILITY & SYSTEM SETTINGS",
            "Real panels for accessibility, display, sound, Bluetooth and KDE Connect",
            RAW / "06-real-settings-accessibility-connect.mp4", 3.0, 24.0,
            NARRATED / "launch" / "11-measured-accessibility-vertical-24s-final.mp4",
            CAPTIONS / "launch" / "11-measured-accessibility-vertical-24s-final.srt",
        ),
    ]
    for edit in edits:
        for required in (edit.source, edit.audio, edit.captions):
            if not required.exists():
                raise FileNotFoundError(required)
        assert_realtime_visual_source(edit)

    outputs: list[dict] = []
    for index, edit in enumerate(edits, start=1):
        is_montage = edit.source.resolve() == montage.resolve()
        source_type = "continuous-live-vm-montage" if is_montage else "continuous-live-vm-video"
        receipt_paths = (
            [capture_receipt_path(path) for path, _, _ in MONTAGE_SEGMENTS]
            if is_montage
            else [capture_receipt_path(edit.source)]
        )
        print(f"[{index}/{len(edits)}] {edit.slug}: vertical", flush=True)
        vertical = render_vertical(edit)
        print(f"[{index}/{len(edits)}] {edit.slug}: landscape", flush=True)
        landscape = render_landscape(edit)
        for aspect, output in (("vertical", vertical), ("landscape", landscape)):
            info = probe(output)
            video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
            audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
            outputs.append({
                "slug": edit.slug,
                "title": edit.title,
                "aspect": aspect,
                "source": str(edit.source),
                "visualSourceType": source_type,
                "visualSourceStartSeconds": edit.start,
                "visualSourceDurationSeconds": edit.duration,
                "captureReceipts": [str(receipt) for receipt in receipt_paths],
                "captureReceiptsVerified": True,
                "visibleProductVideoLayers": 1,
                "snapshotInputs": [],
                "generatedVisuals": False,
                "graphicsOverlay": "Text, captions, borders, and color treatment only",
                "audioSource": str(edit.audio),
                "output": str(output),
                "captions": str(output.with_suffix(".srt")),
                "durationSeconds": round(float(info["format"]["duration"]), 3),
                "width": video["width"],
                "height": video["height"],
                "frameRate": video["avg_frame_rate"],
                "videoCodec": video["codec_name"],
                "pixelFormat": video.get("pix_fmt"),
                "audioCodec": audio["codec_name"],
                "audioChannels": audio["channels"],
                "audioSampleRate": int(audio["sample_rate"]),
                "sha256": sha256(output),
            })

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(outputs),
        "visualPolicy": {
            "continuousFootageRequired": True,
            "snapshotsAllowed": False,
            "stillImagesAllowedAsProductVisuals": False,
            "generatedVideoAllowed": False,
            "textAndCaptionOverlaysAllowed": True,
            "captureReceiptsRequired": True,
            "maximumSimultaneousProductVideoLayers": 1,
        },
        "montageSegments": [
            {
                "source": str(path),
                "startSeconds": start,
                "durationSeconds": duration,
                "captureReceipt": str(capture_receipt_path(path)),
            }
            for path, start, duration in MONTAGE_SEGMENTS
        ],
        "captureDisclosure": "Actual Dagric OS Pro live ISO footage captured from a QEMU virtual machine.",
        "audioDisclosure": "Synthetic narration is retained and identified in file metadata; sidecar and burned captions are included.",
        "stockDesktopFootage": False,
        "outputs": outputs,
    }
    (FINISHED / "real-footage-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (FINISHED / "README.md").write_text(
        "# Dagric OS real-footage social masters\n\n"
        "These videos use actual moving Dagric OS Pro live-ISO footage recorded from a QEMU virtual machine. "
        "The desktop, onboarding, Dagric Hub, hardware report, appearance previews, Dolphin, Firefox, and KDE settings are genuine UI captures.\n\n"
        "Each concept is delivered in 1080x1920 vertical and 1920x1080 landscape form, with burned captions and matching sidecar SRT files. "
        "Synthetic narration is identified in MP4 metadata and should also be disclosed through each social platform's required labeling controls.\n\n"
        "A VM proves the software workflow, not physical Wi-Fi, GPU, printer, suspend, or installation compatibility. Test those from the live USB on real target hardware before making hardware-support claims.\n",
        encoding="utf-8",
    )
    print(f"Completed {len(outputs)} real-footage masters in {FINISHED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
