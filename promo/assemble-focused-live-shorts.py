#!/usr/bin/env python3
"""Create focused Dagric shorts from continuous newest-ISO VM footage."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
ROOT = DELIVERY / "Real VM Footage"
SOURCE = ROOT / "raw-realtime" / "08-real-continuous-walkthrough.mp4"
RECEIPT = SOURCE.with_suffix(".capture.json")
OUT = ROOT / "focused-live-shorts"
WORK = OUT / "work"
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
VOICE_ID = "am_michael"
VOICE_NAME = "Michael"
VOICE_SPEED = 0.95
CAPTURE_MODE = "continuous-vnc-stream"


@dataclass(frozen=True)
class Short:
    number: int
    slug: str
    title: str
    subtitle: str
    source_start: float
    duration: float
    narration: str


SHORTS = [
    Short(
        9, "first-run-customization", "FIRST RUN, YOUR WAY",
        "Theme, text size, panel layout, then finish",
        1.0, 30.0,
        "This is the real first-run setup in Dagric OS Pro. Choose the appearance, adjust text sizing, select a panel layout, and review optional apps before finishing. The choices happen in one continuous recording of the running operating system, with no replacement screenshots.",
    ),
    Short(
        10, "dagric-hub-live", "DAGRIC HUB, LIVE",
        "Practical tools in one searchable place",
        41.0, 22.0,
        "Dagric Hub opens inside the running live system and puts the project's practical tools in one searchable place. Browse hardware checks, appearance, migration, security, owner guidance, support, and recovery without hunting through unrelated menus.",
    ),
    Short(
        11, "check-this-pc-honest", "CHECK THIS PC FIRST",
        "A useful report should show limits too",
        64.0, 29.5,
        "Check This PC examines the machine before you make an installation decision. Here, the report clearly identifies missing Wi-Fi and storage devices. Test Dagric from a USB drive on your own computer to check the hardware you depend on.",
    ),
    Short(
        12, "files-on-the-live-desktop", "FILES, BEFORE INSTALLING",
        "Explore the live desktop without committing",
        95.0, 24.5,
        "The live desktop includes the regular Dolphin file manager. Open Home, Downloads, and Pictures, then move through the familiar file system before installing anything. This is the real application responding inside the same recorded Dagric session.",
    ),
    Short(
        13, "system-settings-live", "SYSTEM SETTINGS, LIVE",
        "Accessibility, display, sound, Bluetooth, and more",
        120.5, 36.0,
        "System Settings is shown running, not represented by a still image. The continuous recording moves through accessibility, display configuration, sound, Bluetooth, and KDE Connect. Use Dagric from a USB drive to test the exact screen, audio, wireless, and accessibility features you depend on.",
    ),
    Short(
        14, "website-from-dagric", "FROM DAGRIC TO DAGRIC.COM",
        "One uninterrupted session through the live website",
        157.5, 40.5,
        "Firefox opens from the Dagric desktop inside the same uninterrupted recording. The browser loads dagric.com, scrolls through the real page, and returns to the product information. Review the details, download the Free edition, and test your own hardware before deciding about Pro. The screen remains genuine Dagric OS footage from beginning to end.",
    ),
]


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


def synthesize(kokoro: Kokoro, item: Short) -> tuple[Path, dict]:
    sample_rate = 24000
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", item.narration) if part.strip()]
    speech_parts: list[np.ndarray] = []
    for index, part in enumerate(parts):
        samples, actual_rate = kokoro.create(part, voice=VOICE_ID, speed=VOICE_SPEED, lang="en-us")
        if actual_rate != sample_rate:
            raise RuntimeError(f"Unexpected sample rate: {actual_rate}")
        samples = np.asarray(samples, dtype=np.float32)
        fade = min(int(sample_rate * 0.045), len(samples) // 3)
        if fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            samples[:fade] *= ramp
            samples[-fade:] *= ramp[::-1]
        speech_parts.append(samples)
        if index + 1 < len(parts):
            speech_parts.append(np.zeros(int(sample_rate * 0.29), dtype=np.float32))
    speech = np.concatenate(speech_parts)
    speech_duration = len(speech) / sample_rate
    speech_start = 0.65
    if speech_duration > item.duration - 1.5:
        raise RuntimeError(
            f"{item.slug}: narration is {speech_duration:.2f}s for a {item.duration:.2f}s clip"
        )
    rms = float(np.sqrt(np.mean(np.square(speech))) + 1e-12)
    speech *= min(4.0, (10 ** (-21.0 / 20.0)) / rms)
    master = np.zeros((int(item.duration * sample_rate), 2), dtype=np.float32)
    start = int(speech_start * sample_rate)
    master[start:start + len(speech), 0] += speech
    master[start:start + len(speech), 1] += speech
    t = np.arange(len(master), dtype=np.float32) / sample_rate
    envelope = np.minimum(1.0, np.minimum(t / 0.8, (item.duration - t) / 0.8))
    envelope = np.clip(envelope, 0.0, 1.0)
    bed = (
        np.sin(2 * math.pi * 82.41 * t) * 0.0020
        + np.sin(2 * math.pi * 123.47 * t) * 0.0011
    ) * envelope
    master[:, 0] += bed
    master[:, 1] += bed * 0.92
    peak = float(np.max(np.abs(master)))
    if peak > 0.92:
        master *= 0.92 / peak
    path = WORK / f"{item.number:02d}-{item.slug}-natural-voice.wav"
    sf.write(path, master, sample_rate, subtype="PCM_24")
    return path, {
        "text": item.narration,
        "words": len(item.narration.split()),
        "speechStartSeconds": speech_start,
        "speechDurationSeconds": round(speech_duration, 3),
        "windowSeconds": round(item.duration - 1.5, 3),
        "fitsWindow": True,
    }


def caption_chunks(text: str, limit: int = 10) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for word in text.split():
        current.append(word)
        if len(current) >= limit or (word.endswith((".", "?", "!", ":")) and len(current) >= 6):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def make_captions(item: Short, narration: dict) -> Path:
    chunks = caption_chunks(item.narration)
    weights = [len(chunk.split()) for chunk in chunks]
    cursor = float(narration["speechStartSeconds"])
    speech_duration = float(narration["speechDurationSeconds"])
    rows: list[str] = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        duration = speech_duration * weight / sum(weights)
        rows.extend([str(index), f"{srt_time(cursor)} --> {srt_time(cursor + duration)}", chunk, ""])
        cursor += duration
    path = WORK / f"{item.number:02d}-{item.slug}.srt"
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def make_overlay(item: Short, aspect: str) -> Path:
    vertical = aspect == "vertical"
    width, height = ((1080, 1920) if vertical else (1920, 1080))
    path = WORK / f"{item.number:02d}-{item.slug}-{aspect}-overlay.png"
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if vertical:
        draw.rounded_rectangle((28, 26, 470, 88), radius=28, fill=(7, 24, 40, 236), outline=(72, 206, 241, 255), width=2)
        draw.text((52, 43), "DAGRIC OS • LIVE FOOTAGE", font=font(24, True), fill="white")
        draw.text((30, 116), item.title, font=font(57, True), fill="white")
        draw.text((32, 196), item.subtitle, font=font(26), fill=(190, 225, 242, 255))
        draw.rounded_rectangle((28, 1744, 1052, 1878), radius=24, fill=(5, 18, 31, 228))
        draw.text((54, 1766), "ONE CONTINUOUS PRODUCT VIDEO", font=font(27, True), fill=(83, 211, 239, 255))
        draw.text((54, 1810), "No snapshots • Synthetic narration disclosed", font=font(24), fill=(224, 237, 245, 255))
    else:
        draw.rounded_rectangle((32, 28, 472, 88), radius=28, fill=(7, 24, 40, 236), outline=(72, 206, 241, 255), width=2)
        draw.text((56, 44), "DAGRIC OS • LIVE FOOTAGE", font=font(24, True), fill="white")
        draw.rounded_rectangle((30, 105, 1190, 190), radius=22, fill=(5, 18, 31, 214))
        draw.text((54, 116), item.title, font=font(44, True), fill="white")
        draw.rounded_rectangle((30, 984, 1890, 1054), radius=18, fill=(5, 18, 31, 214))
        draw.text((54, 999), "One continuous product video • no snapshots • synthetic narration disclosed", font=font(24), fill=(206, 231, 244, 255))
    image.save(path)
    return path


def escape_subtitle(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def render(item: Short, aspect: str, audio: Path, captions: Path) -> dict:
    vertical = aspect == "vertical"
    output = OUT / aspect / f"{item.number:02d}-{item.slug}-{aspect}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay = make_overlay(item, aspect)
    subtitle = escape_subtitle(captions)
    trim = f"trim=start={item.source_start:.3f}:duration={item.duration:.3f},setpts=PTS-STARTPTS"
    if vertical:
        filters = (
            f"[0:v]{trim},fps=30,scale=1032:645:flags=lanczos,"
            "pad=1080:1920:24:300:color=0x08131F,format=yuv420p[base];"
            "[base][2:v]overlay=0:0:shortest=1[t0];"
            f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
            "FontSize=9,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
            "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=120'[outv]"
        )
    else:
        filters = (
            f"[0:v]{trim},fps=30,scale=1728:1080:flags=lanczos,"
            "pad=1920:1080:96:0:color=0x08131F,format=yuv420p[base];"
            "[base][2:v]overlay=0:0:shortest=1,crop=1920:1080,setsar=1[t0];"
            f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
            "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
            "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=92',"
            "crop=1920:1080,setsar=1[outv]"
        )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(SOURCE), "-i", str(audio), "-loop", "1", "-i", str(overlay),
        "-filter_complex", filters, "-map", "[outv]", "-map", "1:a:0",
        "-t", f"{item.duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-af", "highpass=f=70,lowpass=f=15500,acompressor=threshold=0.125:ratio=2:attack=20:release=180:makeup=1.4,loudnorm=I=-16:LRA=7:TP=-1.5",
        "-movflags", "+faststart", "-metadata", "title=" + item.title.title(),
        "-metadata", "artist=Dagric OS",
        "-metadata", "comment=One continuous newest-ISO Dagric Pro VM segment; one product-video layer; synthetic Kokoro narration disclosed; no snapshots or generated UI",
        str(output),
    ])
    sidecar = output.with_suffix(".srt")
    sidecar.write_text(captions.read_text(encoding="utf-8"), encoding="utf-8")
    info = probe(output)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    return {
        "number": item.number,
        "slug": item.slug,
        "title": item.title,
        "aspect": aspect,
        "output": str(output),
        "sha256": sha256(output),
        "durationSeconds": round(float(info["format"]["duration"]), 3),
        "width": video["width"],
        "height": video["height"],
        "frameRate": video["avg_frame_rate"],
        "videoCodec": video["codec_name"],
        "pixelFormat": video.get("pix_fmt"),
        "audioCodec": audio_stream["codec_name"],
        "audioChannels": audio_stream["channels"],
        "audioSampleRate": int(audio_stream["sample_rate"]),
        "source": str(SOURCE),
        "sourceStartSeconds": item.source_start,
        "sourceDurationSeconds": item.duration,
        "captureReceipt": str(RECEIPT),
        "visibleProductVideoLayers": 1,
        "snapshotInputs": [],
        "generatedVisuals": False,
        "captions": str(sidecar),
    }


def main() -> int:
    for required in (SOURCE, RECEIPT, MODEL, VOICES):
        if not required.is_file():
            raise FileNotFoundError(required)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    newest_iso, newest_hash = latest_iso()
    source_duration = float(probe(SOURCE)["format"]["duration"])
    checks = {
        "captureMode": receipt.get("captureMode") == CAPTURE_MODE,
        "continuousEncoding": receipt.get("continuousFrameEncoding") is True,
        "noSnapshots": receipt.get("snapshotInputs") == [],
        "sourceHash": receipt.get("sha256") == sha256(SOURCE),
        "newestIsoPath": Path(receipt.get("iso", "")).resolve() == newest_iso.resolve(),
        "newestIsoHash": receipt.get("isoSha256") == newest_hash,
        "sourceDuration": source_duration >= max(item.source_start + item.duration for item in SHORTS) - 0.1,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Source validation failed: " + ", ".join(failed))
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(MODEL), str(VOICES))
    outputs: list[dict] = []
    narration_records: list[dict] = []
    for item in SHORTS:
        print(f"Preparing {item.number:02d} {item.slug}", flush=True)
        audio, narration = synthesize(kokoro, item)
        captions = make_captions(item, narration)
        narration_records.append({"number": item.number, "slug": item.slug, **narration})
        for aspect in ("vertical", "landscape"):
            print(f"Rendering {item.number:02d} {aspect}", flush=True)
            outputs.append(render(item, aspect, audio, captions))
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(outputs),
        "source": str(SOURCE),
        "sourceSha256": sha256(SOURCE),
        "captureReceipt": str(RECEIPT),
        "captureMode": CAPTURE_MODE,
        "iso": str(newest_iso),
        "isoSha256": newest_hash,
        "visualPolicy": {
            "continuousFootageRequired": True,
            "snapshotsAllowed": False,
            "generatedVideoAllowed": False,
            "maximumSimultaneousProductVideoLayers": 1,
            "montageAllowed": False,
        },
        "voice": {
            "provider": "local Kokoro-82M",
            "model": "hexgrad/Kokoro-82M v1.0",
            "voiceId": VOICE_ID,
            "voiceName": VOICE_NAME,
            "speed": VOICE_SPEED,
            "timeStretched": False,
            "syntheticVoiceDisclosure": True,
        },
        "narration": narration_records,
        "outputs": outputs,
    }
    (OUT / "focused-live-shorts-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Completed {len(outputs)} focused live-footage masters in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
