#!/usr/bin/env python3
"""Render nine honest, caption-free portrait demos from live Dagric footage.

The source clips are receipt-backed continuous VNC recordings of the newest
named Dagric build.  Portrait framing uses fixed 450x800 crops and deliberate
hard cuts at real interface actions.  It never adds camera drift, a second
video layer, a screenshot, a persistent banner, or burned captions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


REPO = Path(__file__).resolve().parents[1]
VIDEO_ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
SOURCE_ROOT = VIDEO_ROOT / "Real VM Footage" / "raw-realtime-clean-v3"
OUTPUT_ROOT = VIDEO_ROOT / "Daily 9" / "starter-01"
WORK = OUTPUT_ROOT / "work"
TRANSCRIPTS = OUTPUT_ROOT / "transcripts"
MODEL_ROOT = VIDEO_ROOT / "_tts-model"
MODEL = MODEL_ROOT / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_ROOT / "voices-v1.0.bin"
VOICE = "af_heart"
VOICE_NAME = "Heart"
BASE_SPEED = 1.08
SAMPLE_RATE = 24_000
SOURCE_WIDTH = 1_280
SOURCE_HEIGHT = 800
PORTRAIT_CROP_WIDTH = 450


@dataclass(frozen=True)
class Segment:
    start: float
    duration: float
    crop_x: int


@dataclass(frozen=True)
class Video:
    number: int
    slug: str
    platform: str
    scheduled_at: str
    profile: str
    narration: str
    caption: str
    segments: tuple[Segment, ...]

    @property
    def duration(self) -> float:
        return sum(segment.duration for segment in self.segments)

    @property
    def source(self) -> Path:
        return SOURCE_ROOT / f"09-real-full-walkthrough-{self.profile}.mp4"


VIDEOS = (
    Video(
        1,
        "choose-a-desktop-that-fits",
        "youtube-shorts",
        "2026-09-06T08:15:00-05:00",
        "open-horizon",
        "Your computer should not force one look on you. Pick the theme, text size, taskbar style, and optional apps before the desktop opens. Every choice here happens in the running Dagric setup, and you can change it again later.",
        "Make the desktop feel like yours before day one. See Dagric OS in motion at https://dagric.com #DagricOS #Linux #YouTubeShorts",
        (
            Segment(1.2, 3.0, 0),
            Segment(10.2, 3.0, 520),
            Segment(14.2, 3.0, 520),
            Segment(18.2, 3.0, 720),
            Segment(21.2, 2.0, 720),
            Segment(25.2, 1.0, 720),
        ),
    ),
    Video(
        2,
        "a-clean-desktop-that-opens-up",
        "instagram-reels",
        "2026-09-06T08:15:00-05:00",
        "open-coast",
        "What if your desktop felt calm before you opened anything? Dagric gives the wallpaper room to breathe, keeps everyday tools close, and opens its owner hub from search. The result feels personal without hiding where your apps and files live.",
        "A desktop can feel open and still keep the useful things close. Explore Dagric OS at https://dagric.com #DagricOS #LinuxDesktop #Reels",
        (
            Segment(40.7, 2.8, 0),
            Segment(43.2, 2.6, 0),
            Segment(45.5, 2.6, 0),
            Segment(48.2, 2.8, 415),
            Segment(53.2, 2.6, 415),
            Segment(56.2, 2.6, 415),
        ),
    ),
    Video(
        3,
        "find-owner-tools-fast",
        "tiktok",
        "2026-09-06T08:15:00-05:00",
        "night-orbit",
        "Why should basic computer help be scattered across the web? Dagric Hub keeps hardware checks, appearance tools, migration help, security, recovery, and guides in one searchable window. Watch the real list respond as we move through it.",
        "The useful owner tools belong in one place. Follow Dagric OS and see more live demos at https://dagric.com #DagricOS #LinuxTok #TechTok",
        (
            Segment(48.2, 3.0, 415),
            Segment(53.2, 3.0, 415),
            Segment(56.2, 3.0, 415),
            Segment(60.2, 3.0, 415),
            Segment(63.2, 3.0, 415),
        ),
    ),
    Video(
        4,
        "check-the-computer-first",
        "youtube-shorts",
        "2026-09-06T13:30:00-05:00",
        "wild-meadow",
        "Never change your computer and simply hope the hardware works. Check This PC reviews graphics, networking, sound, storage, firmware, and other basics first. This report even shows missing devices instead of hiding them, so you know what still needs a real hardware test.",
        "Check first. Decide second. Dagric shows the useful results and the limits at https://dagric.com #DagricOS #Linux #YouTubeShorts",
        (
            Segment(64.2, 3.0, 0),
            Segment(69.2, 3.0, 415),
            Segment(76.2, 3.0, 415),
            Segment(81.2, 3.0, 415),
            Segment(86.2, 3.0, 415),
            Segment(90.2, 3.0, 415),
        ),
    ),
    Video(
        5,
        "files-stay-familiar",
        "tiktok",
        "2026-09-06T13:30:00-05:00",
        "open-horizon",
        "New system, familiar file habits. Search for Files, open Downloads, move to Pictures, and return Home without learning a strange workflow. This is the everyday part that matters after the exciting setup screen is gone.",
        "A new operating system should not make simple file work feel foreign. Follow for more Dagric tutorials. https://dagric.com #DagricOS #LinuxTok #ComputerTips",
        (
            Segment(98.2, 3.0, 0),
            Segment(100.2, 3.0, 560),
            Segment(106.2, 3.0, 650),
            Segment(110.2, 3.0, 580),
            Segment(114.2, 3.0, 670),
        ),
    ),
    Video(
        6,
        "accessibility-before-decoration",
        "instagram-reels",
        "2026-09-06T18:00:00-05:00",
        "night-orbit",
        "Can you make the screen comfortable before making it pretty? Open System Settings, choose accessibility controls, then adjust the display. Dagric keeps those practical choices easy to reach because a desktop should work for you, not the other way around.",
        "Comfort comes before decoration. Follow Dagric OS for clear feature demos and owner guides. https://dagric.com #DagricOS #Accessibility #LinuxDesktop",
        (
            Segment(119.2, 2.6, 0),
            Segment(122.2, 2.6, 0),
            Segment(124.2, 2.6, 500),
            Segment(130.2, 2.6, 500),
            Segment(135.2, 2.6, 650),
            Segment(140.2, 3.0, 650),
        ),
    ),
    Video(
        7,
        "sound-bluetooth-and-phone",
        "tiktok",
        "2026-09-06T18:00:00-05:00",
        "open-coast",
        "Here are three settings people need on a real computer: sound, Bluetooth, and phone connection. Dagric keeps each one in the same clear settings window. Open a section, read the result, and move on without digging through hidden panels.",
        "Sound, Bluetooth, and phone tools should be easy to find. Follow for more Dagric OS walkthroughs. https://dagric.com #DagricOS #LinuxTok #TechTips",
        (
            Segment(124.2, 3.2, 500),
            Segment(140.2, 3.2, 650),
            Segment(145.2, 3.2, 650),
            Segment(150.2, 3.2, 650),
            Segment(155.2, 3.2, 650),
        ),
    ),
    Video(
        8,
        "open-the-web-from-the-desktop",
        "youtube-shorts",
        "2026-09-07T08:15:00-05:00",
        "wild-meadow",
        "A useful desktop gets you moving fast. Search for the browser, open it, enter the Dagric website, and load the real page in one clean flow. The interface stays clear through every step, so you can see exactly how the system responds.",
        "From desktop search to the open web in one clean flow. Follow Dagric OS for more tutorials. https://dagric.com #DagricOS #Linux #YouTubeShorts",
        (
            Segment(157.2, 3.0, 0),
            Segment(160.2, 3.0, 200),
            Segment(162.2, 3.0, 500),
            Segment(170.2, 3.0, 350),
            Segment(175.2, 3.0, 50),
        ),
    ),
    Video(
        9,
        "optional-apps-stay-optional",
        "instagram-reels",
        "2026-09-07T08:15:00-05:00",
        "open-horizon",
        "Why install extra apps you may never use? Dagric lets you review optional tools during setup, keep the ones that fit, and skip the rest. Your operating system should begin with your choices instead of somebody else's pile of software.",
        "Optional should really mean optional. Follow Dagric OS for more clear setup demos. https://dagric.com #DagricOS #LinuxDesktop #OpenSource",
        (
            Segment(21.2, 3.0, 720),
            Segment(22.2, 3.0, 300),
            Segment(24.2, 3.0, 700),
            Segment(25.2, 3.0, 720),
            Segment(26.2, 3.0, 500),
        ),
    ),
)


def run(args: list[str], *, capture: bool = False) -> str:
    completed = subprocess.run(
        args,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return ((completed.stdout or "") + (completed.stderr or "")) if capture else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_iso() -> tuple[Path, str]:
    candidates = sorted(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No named Dagric build exists in out/")
    return candidates[0], sha256(candidates[0])


def validate_source(video: Video, iso_path: Path, iso_hash: str) -> dict:
    source = video.source
    receipt_path = source.with_suffix(".capture.json")
    if not source.is_file() or not receipt_path.is_file():
        raise FileNotFoundError(source if not source.is_file() else receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checks = {
        "continuous_capture": receipt.get("captureMode") == "continuous-vnc-stream",
        "continuous_encoding": receipt.get("continuousFrameEncoding") is True,
        "no_snapshot_inputs": receipt.get("snapshotInputs") == [],
        "source_hash": receipt.get("sha256") == sha256(source),
        "newest_build_path": Path(receipt.get("iso", "")).resolve() == iso_path.resolve(),
        "newest_build_hash": receipt.get("isoSha256", "").lower() == iso_hash.lower(),
        "matching_profile": receipt.get("visualProfile") == video.profile,
        "source_long_enough": max(s.start + s.duration for s in video.segments)
        <= float(receipt.get("durationSeconds", 0)) + 0.01,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"{video.slug}: source validation failed: {', '.join(failed)}")
    return {"path": str(source), "receipt": str(receipt_path), "checks": checks}


def speech_parts(kokoro: Kokoro, text: str, speed: float) -> np.ndarray:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    chunks: list[np.ndarray] = []
    for index, sentence in enumerate(sentences):
        samples, rate = kokoro.create(sentence, voice=VOICE, speed=speed, lang="en-us")
        if rate != SAMPLE_RATE:
            raise RuntimeError(f"Unexpected Kokoro sample rate: {rate}")
        part = np.asarray(samples, dtype=np.float32)
        fade = min(int(SAMPLE_RATE * 0.025), len(part) // 3)
        if fade:
            ramp = np.linspace(0, 1, fade, dtype=np.float32)
            part[:fade] *= ramp
            part[-fade:] *= ramp[::-1]
        chunks.append(part)
        if index + 1 < len(sentences):
            chunks.append(np.zeros(int(SAMPLE_RATE * 0.11), dtype=np.float32))
    return np.concatenate(chunks)


def synthesize(kokoro: Kokoro, video: Video) -> tuple[Path, dict]:
    target_speech = video.duration - 0.42
    speech = speech_parts(kokoro, video.narration, BASE_SPEED)
    first_duration = len(speech) / SAMPLE_RATE
    adjusted_speed = min(1.24, max(0.92, BASE_SPEED * first_duration / target_speech))
    if abs(adjusted_speed - BASE_SPEED) >= 0.015:
        speech = speech_parts(kokoro, video.narration, adjusted_speed)
    speech_duration = len(speech) / SAMPLE_RATE
    if speech_duration > video.duration - 0.20:
        adjusted_speed *= speech_duration / (video.duration - 0.26)
        speech = speech_parts(kokoro, video.narration, adjusted_speed)
        speech_duration = len(speech) / SAMPLE_RATE
    if speech_duration > video.duration - 0.18:
        raise RuntimeError(f"{video.slug}: narration does not fit the video window")

    rms = float(np.sqrt(np.mean(np.square(speech))) + 1e-12)
    speech *= min(4.0, (10 ** (-20.0 / 20.0)) / rms)
    master = np.zeros((int(round(video.duration * SAMPLE_RATE)), 2), dtype=np.float32)
    start = int(0.08 * SAMPLE_RATE)
    master[start : start + len(speech), 0] = speech
    master[start : start + len(speech), 1] = speech
    peak = float(np.max(np.abs(master)))
    if peak > 0.92:
        master *= 0.92 / peak
    path = WORK / f"{video.number:02d}-{video.slug}-narration.wav"
    sf.write(path, master, SAMPLE_RATE, subtype="PCM_24")
    return path, {
        "voice": VOICE,
        "voiceName": VOICE_NAME,
        "baseSpeed": BASE_SPEED,
        "renderSpeed": round(adjusted_speed, 4),
        "speechStartSeconds": 0.08,
        "speechDurationSeconds": round(speech_duration, 3),
        "trailingSeconds": round(video.duration - 0.08 - speech_duration, 3),
        "wordCount": len(re.findall(r"\b[\w'-]+\b", video.narration)),
        "wordsPerMinute": round(
            len(re.findall(r"\b[\w'-]+\b", video.narration)) * 60 / video.duration,
            2,
        ),
    }


def render(video: Video, audio: Path) -> Path:
    platform_dir = OUTPUT_ROOT / video.platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    output = platform_dir / f"{video.number:02d}-{video.slug}-1080x1920.mp4"
    chains: list[str] = []
    labels: list[str] = []
    for index, segment in enumerate(video.segments):
        if not 0 <= segment.crop_x <= SOURCE_WIDTH - PORTRAIT_CROP_WIDTH:
            raise ValueError(f"{video.slug}: invalid crop x={segment.crop_x}")
        label = f"v{index}"
        chains.append(
            f"[0:v]trim=start={segment.start:.3f}:duration={segment.duration:.3f},"
            "setpts=PTS-STARTPTS,"
            f"crop={PORTRAIT_CROP_WIDTH}:{SOURCE_HEIGHT}:{segment.crop_x}:0,"
            "scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p"
            f"[{label}]"
        )
        labels.append(f"[{label}]")
    chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[outv]")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video.source),
            "-i",
            str(audio),
            "-filter_complex",
            ";".join(chains),
            "-map",
            "[outv]",
            "-map",
            "1:a:0",
            "-t",
            f"{video.duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            "highpass=f=70,lowpass=f=15500,acompressor=threshold=0.125:ratio=2:attack=20:release=160:makeup=1.35,loudnorm=I=-16:LRA=7:TP=-1.5",
            "-movflags",
            "+faststart",
            "-metadata",
            "artist=Dagric OS",
            "-metadata",
            f"title={video.slug.replace('-', ' ').title()}",
            "-metadata",
            "comment=Single-layer continuous Dagric OS screen recording with disclosed local synthetic narration; no still images or captions",
            str(output),
        ]
    )
    return output


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,channels,sample_rate",
                "-of",
                "json",
                str(path),
            ],
            capture=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        type=int,
        action="append",
        choices=range(1, 10),
        help="Render only the selected numbered video and preserve other manifest records.",
    )
    args = parser.parse_args()
    for required in (MODEL, VOICES):
        if not required.is_file():
            raise FileNotFoundError(required)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    iso_path, iso_hash = latest_iso()
    kokoro = Kokoro(str(MODEL), str(VOICES))
    manifest_path = OUTPUT_ROOT / "daily-nine-starter-manifest.json"
    selected_numbers = set(args.only or range(1, 10))
    record_map: dict[int, dict] = {}
    if args.only and manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        record_map = {int(record["number"]): record for record in existing.get("records", [])}
    for video in (item for item in VIDEOS if item.number in selected_numbers):
        print(f"Preparing {video.number:02d}/09 {video.slug}", flush=True)
        source = validate_source(video, iso_path, iso_hash)
        transcript = TRANSCRIPTS / f"{video.number:02d}-{video.slug}.txt"
        transcript.write_text(video.narration + "\n", encoding="utf-8")
        audio, narration = synthesize(kokoro, video)
        output = render(video, audio)
        info = probe(output)
        video_streams = [s for s in info["streams"] if s["codec_type"] == "video"]
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
        picture = video_streams[0]
        sound = audio_streams[0]
        if len(video_streams) != 1 or len(audio_streams) != 1:
            raise RuntimeError(f"{video.slug}: unexpected stream layout")
        if (picture["width"], picture["height"]) != (1080, 1920):
            raise RuntimeError(f"{video.slug}: unexpected output dimensions")
        record_map[video.number] = {
                "number": video.number,
                "slug": video.slug,
                "platform": video.platform,
                "scheduledAtAmericaChicago": video.scheduled_at,
                "status": "READY_FOR_AUTOMATED_AUDIT",
                "output": str(output),
                "sha256": sha256(output),
                "durationSeconds": round(float(info["format"]["duration"]), 3),
                "width": picture["width"],
                "height": picture["height"],
                "frameRate": picture["avg_frame_rate"],
                "videoCodec": picture["codec_name"],
                "pixelFormat": picture.get("pix_fmt"),
                "audioCodec": sound["codec_name"],
                "audioChannels": sound["channels"],
                "audioSampleRate": int(sound["sample_rate"]),
                "transcript": str(transcript),
                "narration": narration,
                "publicCaption": video.caption,
                "source": source,
                "visualProfile": video.profile,
                "segments": [segment.__dict__ for segment in video.segments],
                "visibleProductVideoLayers": 1,
                "snapshotInputs": [],
                "captionPolicy": "none",
            }
    records = [record_map[number] for number in sorted(record_map)]
    manifest = {
        "schema": "dagric-daily-nine-starter-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "newestBuild": str(iso_path),
        "newestBuildSha256": iso_hash,
        "format": {"width": 1080, "height": 1920, "aspectRatio": "9:16", "fps": 30},
        "visualPolicy": {
            "continuousLiveFootageOnly": True,
            "snapshotsAllowed": False,
            "editorCameraMotionAllowed": False,
            "hardCutsAtRealActionsAllowed": True,
            "maximumSimultaneousProductVideoLayers": 1,
            "burnedCaptionsAllowed": False,
            "persistentBannersAllowed": False,
        },
        "voice": {
            "provider": "local Kokoro-82M",
            "model": "hexgrad/Kokoro-82M v1.0",
            "voice": VOICE,
            "voiceName": VOICE_NAME,
            "syntheticMediaDisclosureRequired": True,
            "humanListeningReviewRequired": True,
        },
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest now contains {len(records)} portrait videos in {OUTPUT_ROOT}", flush=True)
    print(f"Manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
