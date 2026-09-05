#!/usr/bin/env python3
"""Create human-paced narration beds for the Dagric duration ladder.

This script creates audio only. Video assembly is delegated to Adobe's video
timeline tools so the source screen recording remains continuous and traceable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
OUT = DELIVERY / "Duration Ladder" / "audio"
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
SAMPLE_RATE = 24000
VOICE = "af_heart"
PUBLIC_LANGUAGE_BLOCKLIST = (
    re.compile(r"\bVM\b", re.IGNORECASE),
    re.compile(r"\bISO\b", re.IGNORECASE),
    re.compile(r"\bQEMU\b", re.IGNORECASE),
    re.compile(r"virtual machine", re.IGNORECASE),
    re.compile(r"virtual hardware", re.IGNORECASE),
    re.compile(r"test environment", re.IGNORECASE),
)


@dataclass(frozen=True)
class Segment:
    start: float
    text: str


@dataclass(frozen=True)
class Edition:
    slug: str
    duration: int
    source_start: int
    voice_speed: float
    segments: tuple[Segment, ...]


EDITIONS = (
    Edition(
        "15-second-personalize-live", 15, 230, 1.16,
        (Segment(0.35, "Watch the whole desktop change in two seconds. Dagric switches from a bright workspace to Night Orbit while your work stays open. Follow Dagric OS at dagric.com."),),
    ),
    Edition(
        "30-second-wild-meadow-files", 30, 437, 1.14,
        (
            Segment(0.4, "Watch Dagric turn Wild Meadow without closing your work. The wallpaper, window colors, and highlights update together in motion while the desktop stays ready to use."),
            Segment(14.8, "Next, the app menu opens Files and moves through familiar folders. One running desktop responds in real time. Follow Dagric OS and start free at dagric.com."),
        ),
    ),
    Edition(
        "1-minute-open-coast-hub", 60, 676, 1.12,
        (
            Segment(0.5, "Can one click change the entire desktop? Watch Dagric apply Open Coast while the system keeps running. The wallpaper, accent color, and windows change together clearly on screen."),
            Segment(18.0, "Now the Dagric Hub opens. This is one place for checking hardware, moving files from Windows, changing appearance, reviewing security, recovering the system, and finding help without hunting through separate menus. The layout stays organized even when the desktop looks completely different."),
            Segment(41.0, "That is the idea behind Dagric: personal where you want choice, and consistent where you need help. Follow Dagric OS for more live demonstrations, or test the free edition from dagric.com before you install."),
        ),
    ),
    Edition(
        "5-minute-first-run-to-night-orbit", 300, 0, 1.09,
        (
            Segment(1, "Can Dagric reach a working desktop without hiding the important choices? Watch the complete path in one continuous recording from the current Pro release."),
            Segment(30, "The first-run guide puts appearance, text size, panel layout, and optional applications up front. You can make a readable, familiar workspace before settling in—and every choice can still be changed later."),
            Segment(58, "Dagric Hub is the front door to the system’s practical tools. The interface groups setup, migration, appearance, security, recovery, and human help so a new owner does not have to memorize Linux utilities."),
            Segment(91, "Check This PC reports what the running system can actually detect. Missing Wi-Fi, audio, or an installation drive is stated plainly instead of being turned into a marketing claim."),
            Segment(126, "Files moves through Downloads, Pictures, and Home using the familiar Dolphin file manager. The point is not to disguise the desktop. The point is to make daily work understandable while keeping the power underneath."),
            Segment(165, "System Settings exposes accessibility, displays, sound, Bluetooth, and device connection tools. A feature only helps when a person can find it, understand it, and test it on the hardware they actually own."),
            Segment(215, "Now the workspace changes character. Open Horizon gives way to Night Orbit, with a dark palette and brighter magenta energy. It is still Dagric, but it no longer feels like everybody else’s machine."),
            Segment(262, "The tour returns to Dagric Hub because customization should not make support harder to find. Follow Dagric OS for the next real walkthrough, and test the free edition at dagric.com before deciding whether it belongs on your computer."),
        ),
    ),
    Edition(
        "10-minute-freedom-and-tools", 600, 230, 1.07,
        (
            Segment(1, "Watch Dagric change its entire look without closing your work. Night Orbit updates the wallpaper, palette, and accent inside the running system."),
            Segment(43, "Dagric Hub remains consistent across every look. The list brings hardware checks, migration, appearance, recovery, security, and support into one searchable launch point."),
            Segment(88, "A terminal is available when you want direct proof. Here the system shows its kernel, release identity, and available disk space. Friendly defaults do not remove the underlying Linux tools."),
            Segment(134, "The software store opens next and performs a real search. People can add creative, development, communication, or entertainment tools without accepting a huge fixed bundle at installation time."),
            Segment(185, "Wild Meadow changes the mood completely. Warm grass, restrained green accents, and a light workspace create a calmer environment while the same files and applications remain available."),
            Segment(235, "Files and System Settings repeat on the new profile to show that the visual choice is not a fragile demo. Navigation, accessibility, display, sound, Bluetooth, and KDE Connect continue working in the personalized session."),
            Segment(302, "Firefox opens from Dagric and loads the project website. The public promises and downloads belong in the same evidence trail as the operating system footage, so viewers can check details rather than relying on a slogan."),
            Segment(365, "Open Coast arrives with turquoise water, coral cliffs, and a brighter window treatment. It is deliberately different from Dagric’s old blue-heavy presentation and from the dark Night Orbit profile."),
            Segment(420, "Dagric Hub opens again, this time over Open Coast. Consistency where it matters and freedom where it is personal—that is the design principle behind these profiles."),
            Segment(472, "The hardware check returns for a final honest reading. This footage proves the software path; your Wi-Fi card, speakers, display, and battery still need a live USB test on the physical computer."),
            Segment(530, "The closing browser pass returns to dagric.com. Review the editions, verify the claims, and start with the free option. Follow Dagric OS for more continuous hardware and workflow tests."),
        ),
    ),
    Edition(
        "15-minute-complete-live-tour", 900, 0, 1.12,
        (
            Segment(1, "What does a complete Dagric session actually feel like? This continuous tour starts at first run and moves through everyday tools, technical checks, four visual profiles, and the project website. There is room between explanations so you can watch the interface respond."),
            Segment(42, "The first-run guide is finished and Dagric Hub opens. Instead of asking a new owner to know package names or hidden settings, the Hub organizes common goals: setup, migration, appearance, recovery, security, accessibility, and support."),
            Segment(80, "Check This PC reads the machine Dagric is running on and calls out missing physical devices honestly. The right next step is always a USB test on your own computer."),
            Segment(122, "Dolphin handles files with familiar places for Home, Documents, Downloads, Pictures, Music, and Videos. View modes change live, and the installation media remains visible as a removable source."),
            Segment(168, "System Settings moves through accessibility, display, sound, Bluetooth, and KDE Connect. Dagric does not invent replacements for solid upstream tools; it gives them a clearer path and a coherent starting experience."),
            Segment(228, "Now the tone changes. Night Orbit replaces the warm opening landscape with a dark aubergine workspace and a vivid magenta horizon. The change happens inside Dagric, not in post-production."),
            Segment(276, "Dagric Hub still looks and behaves like the same control center. Personal freedom should change how your computer feels without making help, recovery, or security harder to locate."),
            Segment(320, "The terminal provides direct evidence of the running kernel, the operating-system release record, and disk availability. You can use the friendly interface, direct Linux tools, or both. There is no requirement to pretend the foundation does not exist."),
            Segment(380, "The software store performs a real search and returns real packages. Optional applications stay optional. That keeps a new installation lighter while leaving creative tools, developer tools, games, and communication software within reach."),
            Segment(438, "Wild Meadow shifts the desktop into soft greens, warm gold, and open countryside. This profile is intentionally calm. Files and Settings continue operating normally, proving that the personalization is more than a static showcase image."),
            Segment(510, "Accessibility and device settings are revisited under the new look. Repetition here serves a purpose: it shows that the same important controls remain readable and reachable after the visual identity changes."),
            Segment(580, "Firefox opens and loads dagric.com from the same live session. The footage connects what the product says publicly with what the running release is actually doing."),
            Segment(652, "The tour returns to the top of the website, then switches to Open Coast. Turquoise water, coral landforms, and a light interface replace both the meadow and the cosmic night. One system does not have to force one mood on everyone."),
            Segment(706, "Dagric Hub opens over Open Coast and moves through its categories again. The visual personality is different; the support structure is stable. That balance is what makes customization feel safe instead of temporary."),
            Segment(758, "A final Check This PC pass reinforces the testing rule. This recording shows workflow and interface proof, while physical compatibility belongs to a live USB session on the actual device."),
            Segment(824, "The last browser pass returns to the Dagric website and its download path. Review the evidence, choose the edition that fits, and begin with the free version if you want to test first."),
            Segment(875, "Follow Dagric OS for the next live test, and share this tour."),
        ),
    ),
)

# Extra chapter detail keeps the long editions informative instead of leaving
# long stretches of dead air. Each paragraph follows the action at that point
# in the continuous source and uses short, plain sentences for spoken clarity.
CHAPTER_DETAILS = (
    "The opening guide keeps the choices small and clear. Color, text size, panel shape, and extra apps appear in a useful order. A new owner can make a few choices, see the result, and move forward without learning special terms. Every setting remains available after setup, so this is a starting point rather than a lock.",
    "The Hub is meant for tasks people can name in everyday words. Check the computer, move personal files, change the look, review safety tools, find help, or prepare recovery. Each group leads to a real tool in the system. This keeps the desktop open and flexible while giving first-time users a place to begin.",
    "A hardware report is most useful when it also shows what is absent. This run has limits because it does not include every physical device. Dagric says that on screen. A real USB test on the target computer remains the best way to check wireless access, sound, graphics, storage, sleep, and battery behavior.",
    "The file manager uses familiar places and simple controls. Home holds the main folders. Downloads and Pictures are one click away. Detail view helps compare names, dates, and sizes. Icon view is better for quick visual browsing. The workflow stays close to standard KDE, so guides and community knowledge remain useful.",
    "System Settings puts important controls in one searchable window. Access tools help with sight, hearing, and input needs. Display controls handle size and screens. Sound shows active devices. Bluetooth and KDE Connect cover nearby gear and phones. The tour shows the route, while your own hardware test proves the final result.",
    "Night Orbit is a full desktop choice, not a picture placed over the recording. The darker colors can reduce glare in a dim room. Magenta accents keep selected items easy to spot. Windows, panels, and wallpaper change as one theme. The apps underneath stay the same, so style does not break the daily workflow.",
    "The second Hub visit shows why a stable tool center matters. A person can change the whole mood of the desktop and still find support in the same place. Recovery, safety, migration, and hardware checks do not move around. Personal style stays free, while key paths remain familiar and easy to explain.",
    "The terminal gives a direct view of the system when a user wants it. The kernel line identifies the running Linux core. The release file names Dagric. The disk command shows available space. None of this is required for normal use, but it provides clear evidence and leaves advanced control available.",
    "The software store gives people a visual way to add tools. Search can find creative apps, work apps, games, and developer tools. Dagric does not need to bundle every choice on day one. A smaller starting set is easier to understand, while the wider Linux software library stays within reach when it is needed.",
    "Wild Meadow changes the mood again with softer greens and a brighter work area. It is designed for people who want calm rather than a dark or blue-heavy screen. The same folders and apps remain in place. The live file tour shows that the theme is part of the system, not a separate marketing scene.",
    "The settings pages are repeated under Wild Meadow so viewers can compare more than wallpaper. Text remains readable. Selected items keep clear contrast. Device pages open in the same order. This repeat also gives time to judge spacing and color during real use. A good theme must support work, not only look good in a still image.",
    "Firefox opens as a normal desktop app and loads the public Dagric site. That connection matters because product claims should be easy to check. Visitors can compare editions, read the test record, and review known limits. The browser chapter also proves that common web work fits naturally into the same running session.",
    "Open Coast brings in bright water, warm land, and a lighter window style. It feels very different from Night Orbit and Wild Meadow. The switch shows that Dagric does not force one visual identity on every owner. People can choose a mood that suits their room, screen, eyesight, and way of working.",
    "Dagric Hub opens again under Open Coast and keeps the same clear structure. This is the balance the system aims for. Personal parts can change widely, while help and key tools stay predictable. A family member or support person can still describe the right path even when two Dagric desktops look very different.",
    "The final hardware check returns to evidence. Software menus can be recorded and reviewed, but physical support depends on the exact computer. A USB test should cover Wi-Fi, speakers, microphone, screen brightness, graphics, storage, touch, sleep, and battery. Testing first protects the user and makes any later install decision easier.",
    "The closing website view points to the next safe step. Start with the free edition, read the current notes, and keep important files backed up. People who want Pro can compare its added support and tools after the basic test. Clear information is part of the product experience, not an extra page hidden after download.",
    "The final message is simple. Dagric is built around choice, clear proof, and a desktop that can feel personal. Follow the project for more live tests, feature tours, and hardware results. Share the work with someone who wants more control over an existing computer, and use dagric.com as the source for current downloads and facts.",
)

DETAIL_MAP = {
    "5-minute-first-run-to-night-orbit": (0, 0, 1, 2, 3, 4, 5, 6),
    "10-minute-freedom-and-tools": (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    "15-minute-complete-live-tour": tuple(range(17)),
}

DETAIL_WORD_LIMIT = {
    "5-minute-first-run-to-night-orbit": 35,
    "10-minute-freedom-and-tools": 60,
    "15-minute-complete-live-tour": 58,
}


def expanded_segment_text(edition: Edition, index: int, text: str) -> str:
    mapping = DETAIL_MAP.get(edition.slug)
    if mapping is None:
        return text
    if edition.slug == "15-minute-complete-live-tour" and index == len(edition.segments) - 1:
        return text
    limit = DETAIL_WORD_LIMIT[edition.slug]
    sentences = re.findall(r"[^.!?]+[.!?]", CHAPTER_DETAILS[mapping[index]])
    selected: list[str] = []
    selected_words = 0
    for sentence in sentences:
        sentence_words = len(re.findall(r"\b[\w'-]+\b", sentence))
        if selected and selected_words + sentence_words > limit:
            break
        selected.append(sentence.strip())
        selected_words += sentence_words
    detail = " ".join(selected)
    return f"{text} {detail}"


def validate_public_language(editions: tuple[Edition, ...]) -> None:
    violations: list[str] = []
    for edition in editions:
        for index, segment in enumerate(edition.segments, start=1):
            public_text = expanded_segment_text(edition, index - 1, segment.text)
            matches = sorted({pattern.pattern for pattern in PUBLIC_LANGUAGE_BLOCKLIST if pattern.search(public_text)})
            if matches:
                violations.append(f"{edition.slug} segment {index}: {', '.join(matches)}")
    if violations:
        raise RuntimeError("Public narration language gate failed: " + "; ".join(violations))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def synthesize(kokoro: Kokoro, edition: Edition) -> dict:
    master = np.zeros((edition.duration * SAMPLE_RATE, 2), dtype=np.float32)
    t = np.arange(len(master), dtype=np.float32) / SAMPLE_RATE
    fade = np.minimum(np.minimum(t / 0.8, (edition.duration - t) / 0.8), 1.0)
    fade = np.clip(fade, 0.0, 1.0)
    master[:, 0] = (
        np.sin(2 * np.pi * 110.0 * t) + np.sin(2 * np.pi * 164.81 * t + 0.7)
        + np.sin(2 * np.pi * 220.0 * t + 1.4)
    ) * 0.0075 * fade
    master[:, 1] = (
        np.sin(2 * np.pi * 110.0 * t + 0.25) + np.sin(2 * np.pi * 164.81 * t + 1.05)
        + np.sin(2 * np.pi * 220.0 * t + 1.75)
    ) * 0.0075 * fade
    segment_records = []
    for index, segment in enumerate(edition.segments):
        segment_text = expanded_segment_text(edition, index, segment.text)
        audio, rate = kokoro.create(segment_text, voice=VOICE, speed=edition.voice_speed, lang="en-us")
        if rate != SAMPLE_RATE:
            raise RuntimeError(f"Unexpected Kokoro sample rate: {rate}")
        audio = np.asarray(audio, dtype=np.float32)
        fade = min(int(0.04 * SAMPLE_RATE), len(audio) // 3)
        if fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            audio[:fade] *= ramp
            audio[-fade:] *= ramp[::-1]
        rms = float(np.sqrt(np.mean(np.square(audio))) + 1e-12)
        audio *= min(4.0, (10 ** (-20.0 / 20.0)) / rms)
        start = int(segment.start * SAMPLE_RATE)
        end = start + len(audio)
        next_start = (
            int(edition.segments[index + 1].start * SAMPLE_RATE)
            if index + 1 < len(edition.segments)
            else len(master)
        )
        if end > min(next_start, len(master)):
            raise RuntimeError(f"Narration overlap in {edition.slug} segment {index + 1}")
        master[start:end, 0] += audio
        master[start:end, 1] += audio
        segment_records.append({
            "startSeconds": segment.start,
            "durationSeconds": round(len(audio) / SAMPLE_RATE, 3),
            "text": segment_text,
        })
    peak = float(np.max(np.abs(master)))
    if peak > 0.94:
        master *= 0.94 / peak
    output = OUT / f"{edition.slug}.wav"
    sf.write(output, master, SAMPLE_RATE, subtype="PCM_24")
    words = len(re.findall(r"\b[\w'-]+\b", " ".join(record["text"] for record in segment_records)))
    return {
        "slug": edition.slug,
        "durationSeconds": edition.duration,
        "sourceStartSeconds": edition.source_start,
        "voice": "Kokoro Heart",
        "voiceSpeed": edition.voice_speed,
        "wordCount": words,
        "averageWordsPerVideoMinute": round(words * 60 / edition.duration, 2),
        "audio": str(output),
        "sha256": sha256(output),
        "segments": segment_records,
    }


def main() -> int:
    validate_public_language(EDITIONS)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--slug",
        action="append",
        choices=[edition.slug for edition in EDITIONS],
        help="Regenerate selected narration masters and preserve the others.",
    )
    parser.add_argument(
        "--repair-last-segment",
        action="store_true",
        help="Replace only the final segment in one existing selected master.",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(MODEL), str(VOICES))
    selected = [edition for edition in EDITIONS if not args.slug or edition.slug in args.slug]
    path = OUT.parent / "duration-ladder-audio-manifest.json"
    if args.repair_last_segment:
        if len(selected) != 1 or not args.slug or not path.is_file():
            raise RuntimeError("--repair-last-segment requires exactly one --slug and an existing manifest")
        edition = selected[0]
        existing = json.loads(path.read_text(encoding="utf-8"))
        record = next(item for item in existing["editions"] if item["slug"] == edition.slug)
        output = Path(record["audio"])
        master, rate = sf.read(output, dtype="float32", always_2d=True)
        if rate != SAMPLE_RATE or len(master) != edition.duration * SAMPLE_RATE:
            raise RuntimeError("Existing master does not match the selected edition")
        segment = edition.segments[-1]
        segment_text = expanded_segment_text(edition, len(edition.segments) - 1, segment.text)
        audio, generated_rate = kokoro.create(
            segment_text, voice=VOICE, speed=edition.voice_speed, lang="en-us"
        )
        if generated_rate != SAMPLE_RATE:
            raise RuntimeError(f"Unexpected Kokoro sample rate: {generated_rate}")
        audio = np.asarray(audio, dtype=np.float32)
        edge = min(int(0.04 * SAMPLE_RATE), len(audio) // 3)
        if edge:
            ramp = np.linspace(0.0, 1.0, edge, dtype=np.float32)
            audio[:edge] *= ramp
            audio[-edge:] *= ramp[::-1]
        rms = float(np.sqrt(np.mean(np.square(audio))) + 1e-12)
        audio *= min(4.0, (10 ** (-20.0 / 20.0)) / rms)
        start = int(segment.start * SAMPLE_RATE)
        if start + len(audio) > len(master):
            raise RuntimeError("Replacement closing narration does not fit")
        t = np.arange(start, len(master), dtype=np.float32) / SAMPLE_RATE
        fade = np.minimum(np.minimum(t / 0.8, (edition.duration - t) / 0.8), 1.0)
        fade = np.clip(fade, 0.0, 1.0)
        master[start:, 0] = (
            np.sin(2 * np.pi * 110.0 * t) + np.sin(2 * np.pi * 164.81 * t + 0.7)
            + np.sin(2 * np.pi * 220.0 * t + 1.4)
        ) * 0.012 * fade
        master[start:, 1] = (
            np.sin(2 * np.pi * 110.0 * t + 0.25) + np.sin(2 * np.pi * 164.81 * t + 1.05)
            + np.sin(2 * np.pi * 220.0 * t + 1.75)
        ) * 0.012 * fade
        master[start : start + len(audio), 0] += audio
        master[start : start + len(audio), 1] += audio
        sf.write(output, master, SAMPLE_RATE, subtype="PCM_24")
        replacement_record = {
            "startSeconds": segment.start,
            "durationSeconds": round(len(audio) / SAMPLE_RATE, 3),
            "text": segment_text,
        }
        if len(record["segments"]) < len(edition.segments):
            record["segments"].append(replacement_record)
        else:
            record["segments"][-1] = replacement_record
        joined = " ".join(item["text"] for item in record["segments"])
        record["wordCount"] = len(re.findall(r"\b[\w'-]+\b", joined))
        record["averageWordsPerVideoMinute"] = round(record["wordCount"] * 60 / edition.duration, 2)
        record["sha256"] = sha256(output)
        existing["generatedAtUtc"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"manifest": str(path), "edition": record}, indent=2))
        return 0
    records = [synthesize(kokoro, edition) for edition in selected]
    if args.slug and path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        replaced = {record["slug"] for record in records}
        records = [
            record for record in existing.get("editions", [])
            if record.get("slug") not in replaced
        ] + records
        order = {edition.slug: index for index, edition in enumerate(EDITIONS)}
        records.sort(key=lambda record: order[record["slug"]])
    manifest = {
        "schema": "dagric-duration-ladder-audio-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "captionPolicy": "none",
        "syntheticVoiceDisclosureInMetadata": True,
        "manualNaturalnessReviewRequired": True,
        "editions": records,
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(path), "editions": records}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
