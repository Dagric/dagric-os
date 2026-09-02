#!/usr/bin/env python3
"""Add licensed local neural narration and an original sound bed to scheduled videos.

The script reads the three September scheduling manifests, produces one remastered
MP4 for every scheduled source asset, and writes an auditable manifest. Video is
stream-copied; only the audio track is replaced.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


REPO = Path(r"C:\Users\1248n\Documents\ChatGPT\Dagric Os")
PROMO = REPO / "promo"
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES_FILE = MODEL_DIR / "voices-v1.0.bin"
OUTPUT = DELIVERY / "Narrated Replacements"
WAV_DIR = OUTPUT / "_audio-masters"

VOICE_POOL = [
    ("af_heart", "Heart", 1.00),
    ("am_michael", "Michael", 0.98),
    ("bf_emma", "Emma", 1.02),
    ("bm_george", "George", 0.97),
    ("af_bella", "Bella", 1.04),
    ("am_liam", "Liam", 1.00),
    ("bf_isabella", "Isabella", 1.01),
    ("bm_lewis", "Lewis", 0.99),
    ("af_sarah", "Sarah", 1.03),
    ("am_adam", "Adam", 0.98),
    ("bf_lily", "Lily", 1.02),
    ("bm_daniel", "Daniel", 0.99),
]

TOPIC_COPY = {
    "windows-10-pc-still-works": (
        "That Windows 10 computer may still have years left. Try Dagric O S from a live USB before changing anything on your drive.",
        "Run the hardware check, test Wi-Fi and graphics, and decide from the results on your own machine.",
    ),
    "zero-dagric-telemetry": (
        "Dagric O S sends no product analytics, telemetry, or crash reports to Dagric.",
        "Update checks and optional services are documented separately in the privacy policy, so you can see what connects and why.",
    ),
    "no-dagric-account": (
        "Your Dagric desktop works without a Dagric account, an advertising I D, or a server granting permission.",
        "The machine keeps working locally, with your own login and your own files.",
    ),
    "check-this-pc": (
        "Before installing, boot the live USB and run Check This PC. It checks networking, graphics, sound, storage, firmware, and more without changing your disk.",
        "Use that report to decide whether this exact computer is ready.",
    ),
    "try-live-usb-first": (
        "Try Dagric O S before you install it. Test Wi-Fi, browse, and open files from the live USB while Windows remains untouched.",
        "Remove the USB and the computer returns to its previous system.",
    ),
    "read-only-windows-migration": (
        "Migration Assistant copies only the folders you choose while mounting the Windows partition read-only. Your source files are read, not rewritten.",
        "Review the destination, copy what matters, and keep the original drive as your fallback.",
    ),
    "familiar-start-menu": (
        "Search, favorites, and shutdown are where you expect. It feels familiar without pretending that Dagric is Windows.",
        "Open the launcher, find an app, and get moving without relearning the entire desktop.",
    ),
    "dagric-hub": (
        "Dagric Hub brings drivers, printers, security, layouts, and owner guides into one clear window. Less hunting, more doing.",
        "It keeps the common maintenance tasks close without hiding the underlying tools.",
    ),
    "seven-installer-steps": (
        "The installer shows all seven steps up front. Review the disk, partitions, and final summary carefully before anything is written.",
        "That summary is the last checkpoint, so stop and verify every choice before selecting install.",
    ),
    "encryption-and-btrfs": (
        "B-tree F S supports snapshots by default. Full-disk encryption is an explicit choice, so review every partition before confirming the installation.",
        "Snapshots help with recovery, while encryption protects data when the computer is powered off.",
    ),
    "boot-menu-rollback": (
        "Dagric creates snapshots before updates on the default B-tree F S setup. If trouble appears, choose an earlier state from the boot menu.",
        "Try recovery before reinstalling, and keep a separate backup for files that cannot be replaced.",
    ),
    "updates-without-forced-restarts": (
        "Security updates can install automatically, but the computer does not hijack your restart. You choose when to reboot.",
        "That keeps maintenance moving without interrupting the middle of your work.",
    ),
    "seven-desktop-layouts": (
        "Choose from seven desktop layouts without moving your files or reinstalling apps. Pick the arrangement that feels comfortable, and change it later.",
        "Three layouts ship with Free, and four more are included with Pro.",
    ),
    "free-edition": (
        "Dagric Free has no Dagric account requirement and no expiration. It includes the desktop, Hub, hardware check, migration, rollback, and everyday apps.",
        "Download it, test it from USB, and decide based on your own computer.",
    ),
    "pro-one-time-purchase": (
        "Dagric Pro costs thirty-nine dollars once for one machine, not every month. Try the Free edition first, then decide.",
        "Pro adds the curated creator, gaming, developer, and Windows-app toolkit, with updates included.",
    ),
    "windows-apps-with-bottles": (
        "Bottles can run many Windows programs inside separate containers. Compatibility still depends on the individual app, so test the software you actually need.",
        "A familiar logo is not proof of compatibility, and some applications will still need an alternative.",
    ),
    "gaming-tools": (
        "Dagric Free includes one-click gaming helpers. Pro adds a tuned gaming and Wine runtime. Always test each game on your own hardware.",
        "Anti-cheat, graphics drivers, and individual game updates can change compatibility.",
    ),
    "creator-toolkit": (
        "Dagric Pro groups graphics, audio, video, publishing, and media tools into a curated creator setup. Review the exact package list before installing.",
        "The goal is a useful starting point that you can still change as your workflow grows.",
    ),
    "developer-stack": (
        "Dagric Pro adds containers, editors, databases, and language tools, while the Debian base remains available in every edition. Inspect the package manifest first.",
        "You can see what is included instead of trusting a vague developer-ready claim.",
    ),
    "signed-release-proof": (
        "Before booting an eye-so file, compare its S H A two fifty-six checksum, then verify the checksum file with Dagric's public G P G key.",
        "The published verification guide shows each command, so the download can be checked before it touches a computer.",
    ),
    "measured-accessibility": (
        "Dagric publishes which accessibility features are supported, partially supported, and not yet supported. Known limitations belong in the report, not behind marketing language.",
        "Read the current conformance report and test the live desktop with the tools you depend on.",
    ),
    "human-support": (
        "Common fixes stay public. If you still need help, use the contact form or email support at Dagric dot com for a human route.",
        "Include the hardware report and the exact step that failed so support has something concrete to investigate.",
    ),
    "secure-boot": (
        "Secure Boot and legacy bye-oss are both supported paths. Use the live USB to confirm your exact firmware and hardware combination before installing.",
        "Broad compatibility is never a substitute for testing the machine in front of you.",
    ),
    "debian-kde-foundation": (
        "Dagric O S uses Debian thirteen underneath and K D E Plasma on the desktop. The open-source foundation stays visible.",
        "Dagric integrates, configures, and supports those established components rather than claiming they were invented here.",
    ),
    "upgrade-free-to-pro": (
        "Start with Dagric Free and decide later. A Pro license upgrades the installed system through Dagric Hub while keeping your files and settings.",
        "Download the Pro packages before installation begins, then keep the receipt code with your records.",
    ),
}

EXTENDED_DIALOGUE = {
    "dagric-promo": [
        "This is Dagric O S: a privacy-first desktop built on Debian thirteen and K D E Plasma for Windows 10 computers that still work.",
        "Start with a live USB. Test Wi-Fi, graphics, sound, storage, and your everyday workflow before installing anything.",
        "If the machine checks out, Dagric adds a familiar desktop, a hardware report, read-only Windows migration, snapshots, and practical owner tools.",
        "The Free edition needs no Dagric account and does not expire. Pro is a one-time purchase for the curated creator, gaming, developer, and Windows-app toolkit.",
        "The promise is simple: test the real computer, read the known limits, and keep control of the decision.",
    ],
    "installation-walkthrough": [
        "Before installing Dagric O S, boot the live USB and spend a few minutes testing the computer you actually own.",
        "Run Check This PC, confirm networking, graphics, sound, storage, and firmware, then back up every important file to a separate drive.",
        "The installer walks through welcome, location, keyboard, partitions, users, summary, and install. The partition screen is where careful attention matters most.",
        "Read the final summary line by line before approving any write to disk. If anything looks unfamiliar, stop, take a photo, and check the guide first.",
        "A clean install begins with a verified download, a tested USB, and a backup you know how to restore.",
    ],
    "dagric-short": [
        "Here is Dagric O S in under thirty seconds: Debian thirteen and K D E Plasma, configured as a familiar privacy-first desktop for a working Windows 10 P C.",
        "Try it from USB, run Check This PC, test the apps and hardware you rely on, and install only when the results make sense for you.",
    ],
    "desktop-looks": [
        "A desktop should meet you where you are. Dagric offers multiple layouts, including a familiar classic launcher, a modern dock-style arrangement, and a focused top-bar workspace.",
        "Changing the layout does not move your documents or reinstall your apps. It only changes how the desktop is organized.",
        "Start with the layout that feels comfortable, adjust the text size and taskbar position, and change it again later if your workflow changes.",
    ],
    "real-vm-onboarding": [
        "This is real Dagric O S onboarding inside a virtual machine, not a motion-design mockup.",
        "The setup walks through appearance, text size, taskbar placement, and optional app choices in plain steps.",
        "Nothing forces a single layout. Choose what feels familiar, skip anything you do not need, and revisit those settings later from Dagric Hub or K D E settings.",
        "A virtual machine cannot prove compatibility with your Wi-Fi card, graphics hardware, or printer, so use the live USB for that final check on the real P C.",
    ],
    "real-vm-settings": [
        "Here is Dagric O S running in a real virtual machine. Open Firefox, browse the application launcher, and move through K D E settings without a staged interface.",
        "The desktop keeps familiar controls close while leaving the Debian and K D E foundation visible.",
        "Use settings to change appearance, accessibility options, displays, sound, networking, and input devices. Then open Dagric Hub for the owner-focused tools and guides.",
        "This demonstrates the software experience. Hardware support still needs to be tested from the live USB on the actual computer.",
    ],
}


@dataclass
class Item:
    number: int
    batch: str
    source: Path
    topic: str
    title: str
    caption: str
    publish_at: str
    slot: str = ""


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    if capture:
        return (result.stdout or "") + (result.stderr or "")
    return ""


def duration_seconds(path: Path) -> float:
    text = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture=True,
    )
    return float(text.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def infer_topic_from_second_slug(slug: str) -> str:
    return re.sub(r"-(common-question|claim-and-proof)$", "", slug)


def load_items() -> list[Item]:
    items: list[Item] = []

    launch_dir = PROMO / "launch-batch"
    launch = read_json(launch_dir / "schedule.json")
    for post in launch["posts"]:
        items.append(
            Item(
                number=len(items) + 1,
                batch="launch",
                source=launch_dir / post["file"],
                topic=post["topic"],
                title=post["youtubeTitle"],
                caption=post["caption"],
                publish_at=post["publishAt"],
            )
        )

    daily_dir = PROMO / "daily-fill-batch"
    daily_manifest = read_json(daily_dir / "manifest.json")
    topic_by_name = {entry["file"]: entry["topic"] for entry in daily_manifest["videos"]}
    for post in read_json(daily_dir / "september-2026-daily-buffer-plan.json"):
        source = Path(post["video"])
        name = source.name
        topic = topic_by_name.get(name)
        if not topic:
            stem = re.sub(r"-vertical-\d+s-final$", "", source.stem)
            stem = re.sub(r"^\d+-", "", stem)
            topic = stem
        items.append(
            Item(
                number=len(items) + 1,
                batch="daily",
                source=source,
                topic=topic,
                title=post["title"],
                caption=post["caption"],
                publish_at=post["date"],
            )
        )

    second_dir = PROMO / "second-wave-batch"
    second_manifest = read_json(second_dir / "manifest.json")
    manifest_by_name = {entry["file"]: entry for entry in second_manifest["videos"]}
    for post in read_json(second_dir / "second-wave-plan.json"):
        source = Path(post["video"])
        meta = manifest_by_name[source.name]
        topic = meta["slug"] if meta["slot"] == "third" else infer_topic_from_second_slug(meta["slug"])
        items.append(
            Item(
                number=len(items) + 1,
                batch="second",
                source=source,
                topic=topic,
                title=post["title"],
                caption=post["caption"],
                publish_at=post["date"],
                slot=meta["slot"],
            )
        )

    return items


def question_text(title: str) -> str:
    return re.sub(r"\s*\|\s*Dagric OS\s*$", "", title).strip()


def script_parts(item: Item, duration: float) -> list[str]:
    if item.slot == "third" or item.topic.startswith("engagement-"):
        return [question_text(item.title), "Tell us below. We are listening."]
    if item.topic in EXTENDED_DIALOGUE:
        return EXTENDED_DIALOGUE[item.topic]
    short, detail = TOPIC_COPY.get(
        item.topic,
        (question_text(item.title), "Learn more and check the current test notes at Dagric dot com."),
    )
    if duration >= 23.0:
        return [short, detail]
    return [short]


def chunks(text: str, limit: int = 210) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    result: list[str] = []
    current = ""
    for sentence in sentences:
        proposed = f"{current} {sentence}".strip()
        if current and len(proposed) > limit:
            result.append(current)
            current = sentence
        else:
            current = proposed
    if current:
        result.append(current)
    return result or [text]


def synthesize(kokoro: Kokoro, text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
    pieces: list[np.ndarray] = []
    sample_rate = 24000
    for index, chunk in enumerate(chunks(text)):
        samples, sample_rate = kokoro.create(chunk, voice=voice, speed=speed, lang="en-us")
        pieces.append(np.asarray(samples, dtype=np.float32))
        if index + 1 < len(chunks(text)):
            pieces.append(np.zeros(int(sample_rate * 0.18), dtype=np.float32))
    return np.concatenate(pieces), sample_rate


def synthesize_parts(
    kokoro: Kokoro,
    parts: list[str],
    voice_indexes: list[int],
    base_speed: float,
) -> tuple[np.ndarray, int, list[dict]]:
    audio: list[np.ndarray] = []
    credits: list[dict] = []
    sample_rate = 24000
    for part_index, text in enumerate(parts):
        voice_id, voice_name, voice_speed = VOICE_POOL[voice_indexes[part_index % len(voice_indexes)]]
        samples, sample_rate = synthesize(kokoro, text, voice_id, base_speed * voice_speed)
        audio.append(samples)
        credits.append({"voiceId": voice_id, "voiceName": voice_name, "text": text})
        if part_index + 1 < len(parts):
            audio.append(np.zeros(int(sample_rate * 0.24), dtype=np.float32))
    return np.concatenate(audio), sample_rate, credits


def fit_narration(
    kokoro: Kokoro,
    parts: list[str],
    voice_indexes: list[int],
    duration: float,
) -> tuple[np.ndarray, int, list[dict], float]:
    speed = 1.0
    samples, sample_rate, credits = synthesize_parts(kokoro, parts, voice_indexes, speed)
    maximum = max(1.0, duration - 1.15)
    actual = len(samples) / sample_rate
    if actual > maximum:
        speed = min(1.28, max(1.05, actual / maximum * 1.02))
        samples, sample_rate, credits = synthesize_parts(kokoro, parts, voice_indexes, speed)
        actual = len(samples) / sample_rate
    if actual > maximum:
        target = int(maximum * sample_rate)
        positions = np.linspace(0, len(samples) - 1, target)
        samples = np.interp(positions, np.arange(len(samples)), samples).astype(np.float32)
    return samples, sample_rate, credits, speed


def add_tone(target: np.ndarray, start: int, length: int, sample_rate: int, frequency: float, amplitude: float, pan: float):
    if start >= len(target):
        return
    length = min(length, len(target) - start)
    t = np.arange(length, dtype=np.float32) / sample_rate
    sine_envelope = np.sin(np.linspace(0, math.pi, length, dtype=np.float32))
    envelope = np.clip(sine_envelope, 0.0, None) ** 1.6
    wave = np.sin(2 * math.pi * frequency * t) * envelope * amplitude
    left = math.sqrt((1.0 - pan) / 2.0)
    right = math.sqrt((1.0 + pan) / 2.0)
    target[start : start + length, 0] += wave * left
    target[start : start + length, 1] += wave * right


def original_bed(duration: float, sample_rate: int, seed: int) -> np.ndarray:
    frames = int(round(duration * sample_rate))
    bed = np.zeros((frames, 2), dtype=np.float32)
    roots = [130.81, 146.83, 164.81, 174.61, 196.00]
    root = roots[seed % len(roots)]
    segment_seconds = 4.0
    segment_frames = int(segment_seconds * sample_rate)
    chord_steps = [1.0, 1.12246, 0.89090, 1.0]
    for segment, start in enumerate(range(0, frames, segment_frames)):
        length = min(segment_frames, frames - start)
        base = root * chord_steps[segment % len(chord_steps)]
        add_tone(bed, start, length, sample_rate, base, 0.010, -0.25)
        add_tone(bed, start, length, sample_rate, base * 1.4983, 0.007, 0.28)
        add_tone(bed, start, length, sample_rate, base * 2.0, 0.0035, 0.05)

    beat_seconds = [0.0, 0.75, 1.5, 2.25]
    for bar_start in np.arange(0.5, duration, 3.0):
        for beat in beat_seconds:
            start_time = bar_start + beat
            if start_time >= duration:
                continue
            start = int(start_time * sample_rate)
            length = min(int(0.075 * sample_rate), frames - start)
            t = np.arange(length, dtype=np.float32) / sample_rate
            pulse = np.sin(2 * math.pi * (520 + 35 * (seed % 4)) * t)
            pulse *= np.exp(-42 * t) * 0.005
            bed[start : start + length, 0] += pulse * 0.75
            bed[start : start + length, 1] += pulse * 0.65

    for offset, ratio in [(0.14, 1.0), (0.34, 1.25), (0.54, 1.5)]:
        add_tone(bed, int(offset * sample_rate), int(0.5 * sample_rate), sample_rate, root * 2 * ratio, 0.026, (ratio - 1.25) * 0.5)

    fade = min(int(0.6 * sample_rate), frames // 2)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        bed[:fade] *= ramp[:, None]
        bed[-fade:] *= ramp[::-1, None]
    return bed


def mix_audio(narration: np.ndarray, sample_rate: int, duration: float, seed: int) -> tuple[np.ndarray, dict]:
    frames = int(round(duration * sample_rate))
    bed = original_bed(duration, sample_rate, seed)

    narration = narration.astype(np.float32)
    voice_rms = float(np.sqrt(np.mean(np.square(narration))) + 1e-12)
    narration *= min(8.0, 0.155 / voice_rms)
    narration_peak = float(np.max(np.abs(narration)) + 1e-12)
    if narration_peak > 0.82:
        narration *= 0.82 / narration_peak

    offset = int(0.48 * sample_rate)
    usable = min(len(narration), max(0, frames - offset))
    duck_end = min(frames, offset + usable + int(0.20 * sample_rate))
    bed[offset:duck_end] *= 0.54

    mix = bed
    if usable:
        center = narration[:usable]
        mix[offset : offset + usable, 0] += center * 0.71
        mix[offset : offset + usable, 1] += center * 0.71

    peak = float(np.max(np.abs(mix)) + 1e-12)
    if peak > 0.94:
        mix *= 0.94 / peak
        peak = 0.94
    rms = float(np.sqrt(np.mean(np.square(mix))) + 1e-12)
    return mix, {
        "voiceDurationSeconds": round(usable / sample_rate, 3),
        "mixPeakDbfs": round(20 * math.log10(peak), 2),
        "mixRmsDbfs": round(20 * math.log10(rms), 2),
    }


def remux(source: Path, wav: Path, output: Path, duration: float):
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-i",
            str(wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            "loudnorm=I=-16:LRA=8:TP=-1.5",
            "-t",
            f"{duration:.6f}",
            "-movflags",
            "+faststart",
            "-metadata:s:a:0",
            "title=Original synthetic narration and sound bed",
            "-metadata",
            "comment=Synthetic narration: Kokoro-82M v1.0 (Apache-2.0); original locally synthesized sound bed",
            str(output),
        ]
    )


def main() -> int:
    missing = [path for path in (MODEL, VOICES_FILE) if not path.exists()]
    if missing:
        print("Missing TTS files:", *missing, sep="\n", file=sys.stderr)
        return 2

    items = load_items()
    if len(items) != 74:
        raise RuntimeError(f"Expected 74 scheduled video assets, found {len(items)}")
    for item in items:
        if not item.source.exists():
            raise FileNotFoundError(item.source)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(MODEL), str(VOICES_FILE))
    available = set(kokoro.get_voices())
    unavailable = [voice_id for voice_id, _, _ in VOICE_POOL if voice_id not in available]
    if unavailable:
        raise RuntimeError(f"Voice pack is missing: {unavailable}")

    records = []
    for zero_index, item in enumerate(items):
        duration = duration_seconds(item.source)
        parts = script_parts(item, duration)
        primary = zero_index % len(VOICE_POOL)
        if len(parts) > 1:
            secondary = (primary + 5) % len(VOICE_POOL)
            voice_indexes = [primary, secondary]
        else:
            voice_indexes = [primary]

        narration, sample_rate, credits, generation_speed = fit_narration(
            kokoro, parts, voice_indexes, duration
        )
        mixed, levels = mix_audio(narration, sample_rate, duration, zero_index + 11)

        safe_stem = item.source.stem
        wav = WAV_DIR / item.batch / f"{safe_stem}-audio.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(wav, mixed, sample_rate, subtype="PCM_16")

        output = OUTPUT / item.batch / item.source.name
        remux(item.source, wav, output, duration)
        output_duration = duration_seconds(output)
        if abs(output_duration - duration) > 0.12:
            raise RuntimeError(f"Duration changed for {item.source.name}: {duration} -> {output_duration}")

        record = {
            "number": item.number,
            "batch": item.batch,
            "topic": item.topic,
            "title": item.title,
            "publishAt": item.publish_at,
            "source": str(item.source),
            "output": str(output),
            "audioMaster": str(wav),
            "durationSeconds": round(duration, 3),
            "generationSpeed": round(generation_speed, 3),
            "voices": credits,
            **levels,
            "sha256": sha256(output),
        }
        records.append(record)
        print(
            f"[{item.number:02d}/74] {item.batch:<6} {item.source.name} | "
            f"voices={','.join(credit['voiceName'] for credit in credits)} | "
            f"voice={levels['voiceDurationSeconds']}s rms={levels['mixRmsDbfs']}dBFS",
            flush=True,
        )

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": "hexgrad/Kokoro-82M v1.0",
        "modelLicense": "Apache-2.0",
        "inference": "thewh1teagle/kokoro-onnx 0.4.7",
        "soundBed": "Original locally synthesized tones; no sampled or downloaded music",
        "syntheticVoiceDisclosure": True,
        "count": len(records),
        "videos": records,
    }
    (OUTPUT / "narration-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Completed {len(records)} narrated replacements in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
