#!/usr/bin/env python3
"""Build the single-session Dagric Pro walkthrough with natural local narration."""

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
SOURCE = ROOT / "raw-realtime" / "09-real-full-walkthrough-latest.mp4"
RECEIPT = SOURCE.with_suffix(".capture.json")
OUT = ROOT / "continuous-walkthrough"
WORK = OUT / "work"
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
VOICE_ID = "am_michael"
VOICE_NAME = "Michael"
VOICE_SPEED = 0.95
VIDEO_DURATION = 198.0
CAPTURE_MODE = "continuous-vnc-stream"


@dataclass(frozen=True)
class Narration:
    start: float
    end: float
    text: str


NARRATION = [
    Narration(0.6, 10.7,
        "Here is Dagric OS Pro running live. No mockup, no generated desktop, and no hidden cuts in this session."),
    Narration(11.5, 30.0,
        "We start with the real first-run setup: appearance, text sizing, taskbar layout, and optional apps. I'm choosing a dark look and the Unity panel, then finishing the wizard exactly as a new user would."),
    Narration(31.5, 41.2,
        "The live trial reaches the desktop. Nothing is installed to the computer, and the session stays temporary until shutdown."),
    Narration(42.3, 61.3,
        "Dagric Hub brings the project's setup and maintenance tools into one searchable place. The list includes hardware checks, appearance choices, migration, security, support, owner guides, and recovery tools. Each item explains itself before it opens."),
    Narration(63.3, 93.0,
        "Before installing, Check This PC examines the current machine. The report openly identifies limits such as missing Wi-Fi and no installation drive. Your own computer still needs a USB test for the hardware you depend on. It is a decision tool, not a green badge."),
    Narration(94.5, 119.0,
        "Next, the regular desktop tools. Dolphin opens the home folder, Downloads, Pictures, and the rest of the familiar file system. You can explore Dagric from the live environment before committing to an installation. The folders stay predictable as the task moves."),
    Narration(120.3, 156.0,
        "System Settings is the standard KDE control center, presented here in the actual running session. Accessibility, display configuration, sound, Bluetooth, and KDE Connect are all visible. Test the features and hardware you personally depend on from a USB drive. These are ordinary settings, not prerecorded slides."),
    Narration(157.3, 173.1,
        "Finally, Firefox opens inside the same uninterrupted session. We are not switching to promotional footage; this is still Dagric OS Pro running live."),
    Narration(174.0, 197.2,
        "At dagric.com, you can review the evidence and download Free before deciding about Pro. Follow Dagric OS on TikTok, Instagram, YouTube, and Snapchat for the next live PC test. Then try it yourself at dagric dot com. Follow us and name the next machine to test."),
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


def synthesize(kokoro: Kokoro, text: str) -> tuple[np.ndarray, int]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    audio: list[np.ndarray] = []
    sample_rate = 24000
    for index, part in enumerate(parts):
        samples, sample_rate = kokoro.create(
            part, voice=VOICE_ID, speed=VOICE_SPEED, lang="en-us"
        )
        samples = np.asarray(samples, dtype=np.float32)
        fade = min(int(sample_rate * 0.045), len(samples) // 3)
        if fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            samples[:fade] *= ramp
            samples[-fade:] *= ramp[::-1]
        audio.append(samples)
        if index + 1 < len(parts):
            audio.append(np.zeros(int(sample_rate * 0.30), dtype=np.float32))
    return np.concatenate(audio), sample_rate


def make_audio() -> tuple[Path, list[dict]]:
    kokoro = Kokoro(str(MODEL), str(VOICES))
    sample_rate = 24000
    master = np.zeros((int(VIDEO_DURATION * sample_rate), 2), dtype=np.float32)
    records: list[dict] = []
    timing_failures: list[str] = []
    for index, item in enumerate(NARRATION, start=1):
        samples, actual_rate = synthesize(kokoro, item.text)
        if actual_rate != sample_rate:
            raise RuntimeError(f"Unexpected Kokoro sample rate: {actual_rate}")
        speech_duration = len(samples) / sample_rate
        window = item.end - item.start
        if speech_duration > window - 0.25:
            timing_failures.append(
                f"Narration {index}: {speech_duration:.2f}s for a {window:.2f}s window"
            )
        rms = float(np.sqrt(np.mean(np.square(samples))) + 1e-12)
        target_rms = 10 ** (-21.0 / 20.0)
        samples = samples * min(4.0, target_rms / rms)
        start = int(item.start * sample_rate)
        end = start + len(samples)
        master[start:end, 0] += samples
        master[start:end, 1] += samples
        records.append({
            "index": index,
            "startSeconds": item.start,
            "windowEndSeconds": item.end,
            "speechDurationSeconds": round(speech_duration, 3),
            "windowSeconds": round(window, 3),
            "words": len(item.text.split()),
            "fitsWindow": speech_duration <= window - 0.25,
            "text": item.text,
        })

    if timing_failures:
        raise RuntimeError("Narration timing failed; rewrite without time-stretching:\n" + "\n".join(timing_failures))

    # A very low original tonal bed avoids dead digital silence without masking
    # consonants or pretending that VM audio was captured.
    t = np.arange(len(master), dtype=np.float32) / sample_rate
    envelope = np.minimum(1.0, np.minimum(t / 1.2, (VIDEO_DURATION - t) / 1.2))
    envelope = np.clip(envelope, 0.0, 1.0)
    bed = (
        np.sin(2 * math.pi * 82.41 * t) * 0.0022
        + np.sin(2 * math.pi * 123.47 * t) * 0.0013
    ) * envelope
    master[:, 0] += bed
    master[:, 1] += bed * 0.92
    peak = float(np.max(np.abs(master)))
    if peak > 0.92:
        master *= 0.92 / peak
    output = WORK / "09-full-walkthrough-natural-voice.wav"
    sf.write(output, master, sample_rate, subtype="PCM_24")
    return output, records


def caption_chunks(text: str, max_chars: int = 42, max_words: int = 7) -> list[str]:
    words = text.split()
    result: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and (len(candidate) > max_chars or len(current) >= max_words):
            result.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
        if word.endswith((".", "?", "!", ":")) and len(current) >= 4:
            result.append(" ".join(current))
            current = []
    if current:
        result.append(" ".join(current))
    balanced: list[str] = []
    for chunk in result:
        current_words = chunk.split()
        if balanced and (len(current_words) < 3 or len(chunk) < 12):
            previous_words = balanced[-1].split()
            while (
                (len(current_words) < 3 or len(" ".join(current_words)) < 12)
                and len(previous_words) > 3
                and len(" ".join([previous_words[-1], *current_words])) <= max_chars
            ):
                current_words.insert(0, previous_words.pop())
            balanced[-1] = " ".join(previous_words)
            chunk = " ".join(current_words)
            if len(balanced[-1]) + 1 + len(chunk) <= max_chars:
                balanced[-1] = f"{balanced[-1]} {chunk}"
                continue
        balanced.append(chunk)
    return balanced


def srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def make_captions(records: list[dict]) -> Path:
    path = OUT / "09-dagric-pro-full-live-walkthrough.srt"
    rows: list[str] = []
    event = 1
    for item, record in zip(NARRATION, records):
        chunks = caption_chunks(item.text)
        # Allocate display time by visible characters so short words do not
        # create a caption event that flashes faster than the reading-speed gate.
        weights = [len(chunk) for chunk in chunks]
        speech_duration = float(record["speechDurationSeconds"])
        cursor = item.start
        for chunk, weight in zip(chunks, weights):
            duration = speech_duration * weight / sum(weights)
            rows.extend([
                str(event),
                f"{srt_time(cursor)} --> {srt_time(cursor + duration)}",
                chunk,
                "",
            ])
            cursor += duration
            event += 1
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def overlay(width: int, height: int, vertical: bool) -> Path:
    path = WORK / f"walkthrough-{'vertical' if vertical else 'landscape'}-overlay.png"
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if vertical:
        draw.rounded_rectangle((28, 26, 654, 88), radius=28, fill=(7, 24, 40, 236), outline=(72, 206, 241, 255), width=2)
        draw.text((54, 43), "ONE UNINTERRUPTED LIVE SESSION", font=font(24, True), fill="white")
        draw.text((30, 112), "DAGRIC OS PRO", font=font(66, True), fill="white")
        draw.text((32, 194), "Setup → Hub → Hardware → Files → Settings → Web", font=font(27), fill=(190, 225, 242, 255))
        draw.rounded_rectangle((28, 1726, 1052, 1886), radius=24, fill=(5, 18, 31, 228))
        draw.text((54, 1748), "FOLLOW THE NEXT LIVE PC TEST", font=font(27, True), fill=(83, 211, 239, 255))
        draw.text((54, 1790), "TikTok + Instagram @dagricosofficial • YouTube @DagricOS", font=font(21), fill=(224, 237, 245, 255))
        draw.text((54, 1828), "Snapchat @dagricos • Try Free at dagric.com", font=font(23, True), fill="white")
    else:
        draw.rounded_rectangle((32, 28, 650, 88), radius=28, fill=(7, 24, 40, 236), outline=(72, 206, 241, 255), width=2)
        draw.text((58, 44), "ONE UNINTERRUPTED LIVE SESSION", font=font(24, True), fill="white")
        draw.rounded_rectangle((30, 105, 1050, 190), radius=22, fill=(5, 18, 31, 214))
        draw.text((54, 116), "DAGRIC OS PRO — REAL WALKTHROUGH", font=font(44, True), fill="white")
        draw.rounded_rectangle((30, 966, 1890, 1058), radius=18, fill=(5, 18, 31, 214))
        draw.text((54, 980), "FOLLOW: TikTok + Instagram @dagricosofficial • YouTube @DagricOS • Snapchat @dagricos", font=font(21, True), fill=(206, 231, 244, 255))
        draw.text((54, 1018), "TRY FREE AT DAGRIC.COM • LIVE OPERATING SYSTEM FOOTAGE", font=font(21), fill="white")
    image.save(path)
    return path


def escape_subtitle(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def render(aspect: str, audio: Path, captions: Path) -> tuple[Path, dict]:
    vertical = aspect == "vertical"
    width, height = ((1080, 1920) if vertical else (1920, 1080))
    output = OUT / aspect / f"09-dagric-pro-full-live-walkthrough-{aspect}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    art = overlay(width, height, vertical)
    subtitle = escape_subtitle(captions)
    if vertical:
        filters = (
            "[0:v]fps=30,scale=1032:720:force_original_aspect_ratio=decrease:flags=lanczos,"
            "pad=1080:1920:24:280:color=0x08131F,format=yuv420p[base];"
            "[base][2:v]overlay=0:0:shortest=1[t0];"
            f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
            "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
            "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=330'[outv]"
        )
    else:
        filters = (
            "[0:v]fps=30,scale=1728:1080:flags=lanczos,"
            "pad=1920:1080:96:0:color=0x08131F,format=yuv420p[base];"
            "[base][2:v]overlay=0:0:shortest=1,crop=1920:1080,setsar=1[t0];"
            f"[t0]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,"
            "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,"
            "BackColour=&H9A101A24,Outline=1,Shadow=0,Alignment=2,MarginV=92',"
            "crop=1920:1080,setsar=1[outv]"
        )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(SOURCE), "-i", str(audio), "-loop", "1", "-i", str(art),
        "-filter_complex", filters, "-map", "[outv]", "-map", "1:a:0",
        "-t", f"{VIDEO_DURATION:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-af", "highpass=f=70,lowpass=f=15500,acompressor=threshold=0.125:ratio=2:attack=20:release=180:makeup=1.4,loudnorm=I=-16:LRA=7:TP=-1.5",
        "-movflags", "+faststart", "-metadata", "title=Dagric OS Pro — one uninterrupted live walkthrough",
        "-metadata", "artist=Dagric OS",
        "-metadata", "comment=One continuous newest-ISO Dagric Pro VM recording; one product-video layer; synthetic Kokoro narration disclosed; no snapshots or generated UI",
        str(output),
    ])
    sidecar = output.with_suffix(".srt")
    sidecar.write_text(captions.read_text(encoding="utf-8"), encoding="utf-8")
    info = probe(output)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    return output, {
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
    checks = {
        "capture mode": receipt.get("captureMode") == CAPTURE_MODE,
        "continuous encoding": receipt.get("continuousFrameEncoding") is True,
        "no snapshots": receipt.get("snapshotInputs") == [],
        "source hash": receipt.get("sha256") == sha256(SOURCE),
        "newest ISO hash": receipt.get("isoSha256") == sha256(Path(receipt["iso"])),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Source receipt failed: {', '.join(failed)}")
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    audio, narration_records = make_audio()
    captions = make_captions(narration_records)
    outputs = []
    for aspect in ("vertical", "landscape"):
        print(f"Rendering continuous walkthrough: {aspect}", flush=True)
        _, record = render(aspect, audio, captions)
        outputs.append(record)
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE),
        "sourceSha256": sha256(SOURCE),
        "captureReceipt": str(RECEIPT),
        "captureMode": CAPTURE_MODE,
        "iso": receipt["iso"],
        "isoSha256": receipt["isoSha256"],
        "singleUninterruptedSource": True,
        "visibleProductVideoLayers": 1,
        "snapshotInputs": [],
        "generatedVisuals": False,
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
    (OUT / "09-full-live-walkthrough-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Completed {len(outputs)} uninterrupted walkthrough masters in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
