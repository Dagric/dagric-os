#!/usr/bin/env python3
"""Render caption-free social replacements from receipt-backed live Dagric VM footage."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
CLEAN_SOURCE_ROOT = DELIVERY / "Real VM Footage" / "raw-realtime-clean-v3"
NEW_SOURCE_ROOT = DELIVERY / "Real VM Footage" / "raw-realtime-next"
OUT = DELIVERY / "Realtime Replacement Batch" / "batch-01"
WORK = OUT / "work"
TRANSCRIPTS = OUT / "audit-transcripts"
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
VOICE_ID = "af_heart"
VOICE_NAME = "Heart"
VOICE_SPEED = 1.18
SOURCE_SPEED = 1.85
CAPTURE_MODE = "continuous-vnc-stream"

VISUAL_PROFILES = {
    "open-horizon": {
        "label": "Open Horizon",
        "source": CLEAN_SOURCE_ROOT / "09-real-full-walkthrough-open-horizon.mp4",
        "canvas": "241B21",
        "panel": (38, 22, 29, 238),
        "accent": (226, 104, 76, 255),
        "soft": (249, 190, 139, 255),
        "ink": (31, 18, 23, 255),
    },
    "night-orbit": {
        "label": "Night Orbit",
        "source": CLEAN_SOURCE_ROOT / "09-real-full-walkthrough-night-orbit.mp4",
        "canvas": "160E25",
        "panel": (28, 13, 43, 240),
        "accent": (220, 70, 180, 255),
        "soft": (244, 160, 218, 255),
        "ink": (26, 12, 35, 255),
    },
    "wild-meadow": {
        "label": "Wild Meadow",
        "source": CLEAN_SOURCE_ROOT / "09-real-full-walkthrough-wild-meadow.mp4",
        "canvas": "182317",
        "panel": (25, 38, 23, 240),
        "accent": (105, 145, 74, 255),
        "soft": (210, 221, 151, 255),
        "ink": (20, 31, 18, 255),
    },
    "open-coast": {
        "label": "Open Coast",
        "source": CLEAN_SOURCE_ROOT / "09-real-full-walkthrough-open-coast.mp4",
        "canvas": "102A2A",
        "panel": (14, 40, 40, 240),
        "accent": (232, 93, 84, 255),
        "soft": (244, 205, 160, 255),
        "ink": (16, 42, 42, 255),
    },
}
PROFILE_SEQUENCE = tuple(VISUAL_PROFILES)

STORY_SOURCE_SPEEDS = {
    # The opening appearance picker and browser load include short natural UI
    # pauses. Keep both moving fast enough for the four-second social hold gate.
    20: 2.35,
    23: 2.35,
    24: 2.00,
    25: 3.00,
    27: 2.75,
    # Accessibility includes a few visually static settings panels. Keep the
    # walkthrough moving fast enough that no individual hold exceeds the
    # social-video freeze gate while retaining the complete interaction.
    28: 2.60,
    30: 2.35,
    31: 2.45,
    32: 1.00,
    33: 1.00,
    34: 1.00,
    35: 1.00,
    36: 1.00,
    37: 1.00,
    38: 1.00,
    39: 1.00,
    40: 1.00,
    41: 1.00,
    42: 1.00,
    43: 1.00,
    44: 1.00,
}


@dataclass(frozen=True)
class Story:
    number: int
    slug: str
    hook: str
    support: str
    source_start: float
    duration: float
    narration: str
    use_profile_capture: bool = False
    exact_duration: bool = False


@dataclass(frozen=True)
class Platform:
    slug: str
    label: str
    action: str
    handle: str


STORIES = [
    Story(
        20,
        "choose-the-look-live",
        "WATCH FIRST RUN IN MOTION",
        "Live footage of setup choices",
        0.0,
        19.0,
        "Watch Dagric move through appearance, readability, panel layout, and optional apps before the desktop opens. The controls respond as each choice is made. This is continuous live footage of the setup experience. Follow Dagric OS here, then try Free at dagric.com.",
    ),
    Story(
        21,
        "readable-from-the-start",
        "CAN YOU READ YOUR OWN DESKTOP?",
        "Set text size during first run",
        8.5,
        17.0,
        "Can you read your desktop without leaning closer? Dagric puts sizing in the first-run flow, and this live recording shows the control responding before the desktop opens. Follow Dagric OS here, and test the Free edition at dagric.com.",
    ),
    Story(
        22,
        "desktop-layout-choice",
        "ONE DESKTOP DOESN'T FIT EVERYONE",
        "Choose a familiar panel layout",
        15.0,
        17.0,
        "Why should every desktop force the same layout? Start with a desktop arrangement that feels familiar instead of rebuilding it later. The interface responds as each choice is made. Follow Dagric OS here, then try Free at dagric.com.",
    ),
    Story(
        23,
        "optional-apps-not-bloat",
        "APPS SHOULD BE A CHOICE",
        "Review optional tools before finishing",
        22.0,
        18.0,
        "Why install apps you never asked for? Dagric shows optional tools before setup finishes, so they stay a choice instead of a surprise. This live pass moves through the app screen and reaches the desktop in one recording. Follow Dagric OS here, and get Free at dagric.com.",
    ),
    Story(
        24,
        "desktop-to-app-search",
        "FROM FIRST RUN TO REAL DESKTOP",
        "Open the launcher and find tools fast",
        36.0,
        18.0,
        "Watch setup become a working desktop. The live footage follows the transition into the dock and search-ready app menu. Follow Dagric OS, then try Free at dagric.com.",
    ),
    Story(
        25,
        "dagric-hub-in-motion",
        "THE TOOLS HAVE ONE HOME",
        "Dagric Hub, shown live",
        51.0,
        18.0,
        "What if every important system tool had one front door? Dagric Hub opens from the running desktop and gathers practical tools in one searchable place. The live menu moves through hardware, appearance, migration, security, support, and recovery. Follow Dagric OS, then visit dagric.com.",
    ),
    Story(
        26,
        "honest-hardware-check",
        "A HARDWARE CHECK SHOULD BE HONEST",
        "A straightforward hardware report",
        71.0,
        18.0,
        "Would your current computer pass this check? Check This PC shows the hardware Dagric can use and clearly identifies missing Wi-Fi or storage. Try Dagric from a USB drive on your own computer before installing. Follow Dagric OS for more hardware tests.",
    ),
    Story(
        27,
        "browse-files-before-install",
        "EXPLORE THE LIVE DESKTOP FIRST",
        "Move from files into system settings",
        95.0,
        18.0,
        "Want to explore Dagric before installing anything? Open Files, move through familiar folders, then continue into System Settings. The same live footage follows the entire feature tour. Follow Dagric OS here, and try Free at dagric.com.",
    ),
    Story(
        28,
        "accessibility-and-display",
        "SETTINGS THAT MATTER ON DAY ONE",
        "Accessibility and display, live",
        118.0,
        20.0,
        "Can you reach the settings that matter on day one? Watch accessibility and display controls respond inside System Settings. The useful question is whether you can find and test them. Try your own screen from a USB drive, and follow Dagric OS for more feature tours.",
    ),
    Story(
        29,
        "sound-bluetooth-connect",
        "CHECK THE DEVICES YOU DEPEND ON",
        "Sound, Bluetooth, and KDE Connect",
        137.0,
        17.0,
        "Will your sound, Bluetooth, and phone connection work? Watch the settings pages move through each tool. Then test the devices you depend on from a USB drive because your own hardware provides the final answer. Follow Dagric OS for the next compatibility check.",
    ),
    Story(
        30,
        "browser-to-dagric-dot-com",
        "THE WALKTHROUGH ENDS ON THE REAL SITE",
        "Firefox opens and loads dagric.com",
        153.0,
        19.0,
        "Watch Dagric open its own website without a cut. Firefox loads dagric.com and scrolls through the real page. The footage stays continuous from desktop to browser, so you can compare the product with its public information. Review the details, start with Free, and follow Dagric OS for more live walkthroughs.",
    ),
    Story(
        31,
        "dagric-hub-security-live",
        "ONE HUB. PRACTICAL SYSTEM TOOLS.",
        "Browse Dagric Hub and Check This PC",
        42.0,
        17.0,
        "Need practical system tools in one clear place? Watch the desktop open Dagric Hub, move through its categories, and highlight Check This PC without cutting away from the product. Follow Dagric OS for more real feature tours, then try Free at dagric.com.",
        False,
    ),
    Story(
        32, "first-run-fifteen", "START WITH YOUR OWN DESKTOP", "First-run choices in 15 seconds",
        0.0, 15.0,
        "Choose how your desktop looks before it opens. Watch every first-run choice respond on screen, then follow Dagric OS and try the Free edition at dagric.com.",
        False, True,
    ),
    Story(
        33, "readability-first-thirty", "READABILITY IS A FIRST-RUN CHOICE", "Text size before the desktop opens",
        8.0, 30.0,
        "Can you read your desktop without fighting it? Dagric brings text sizing into first run, alongside appearance and layout, so the starting point fits you before daily work begins. Watch the controls respond live inside the operating system. Follow Dagric OS for more clear walkthroughs, and test the Free edition at dagric.com.",
        False, True,
    ),
    Story(
        34, "layout-and-app-choice-thirty", "CHOOSE THE LAYOUT. CHOOSE THE APPS.", "A cleaner first-run experience",
        15.0, 30.0,
        "Choose the layout and reject apps you do not want. Dagric puts both decisions before setup finishes, which means fewer surprises and less cleanup later. Watch the choices happen in one continuous recording while the interface stays visible throughout. Follow Dagric OS here, then try the Free edition from dagric.com on your own hardware.",
        False, True,
    ),
    Story(
        35, "desktop-arrives-fifteen", "FROM SETUP TO A WORKING DESKTOP", "The transition happens live",
        32.0, 15.0,
        "Watch setup turn into a working Dagric desktop. The system completes first run in one continuous shot, and you see it happen now. Follow Dagric OS and test it free.",
        False, True,
    ),
    Story(
        36, "hub-organizes-tools-thirty", "SYSTEM TOOLS NEED A CLEAR FRONT DOOR", "Dagric Hub in continuous motion",
        42.0, 30.0,
        "Need seven system jobs in one clear place? Dagric Hub gathers hardware checks, migration, appearance, security, recovery, support, and guidance in one searchable view. Watch the actual categories move on screen. Every category stays easy to scan and understand. Follow Dagric OS for the next walkthrough, then start with Free at dagric.com.",
        False, True,
    ),
    Story(
        37, "honest-hardware-thirty", "CHECK THE COMPUTER BEFORE INSTALLING", "Useful results include limitations",
        64.0, 30.0,
        "What does Dagric detect before installation? Check This PC reports what the current machine provides and clearly identifies missing Wi-Fi or storage. Test Dagric from a USB drive on your own computer to check sound, graphics, wireless access, and storage. Follow Dagric OS for honest compatibility testing and start free at dagric.com.",
        False, True,
    ),
    Story(
        38, "files-before-commitment-thirty", "EXPLORE YOUR FILES BEFORE COMMITTING", "A familiar file manager, shown live",
        94.0, 30.0,
        "Open your files before installing anything. Watch the file manager move through Home, Downloads, and Pictures. Compare views and folders before you decide. A safe trial should let you understand the everyday workflow, not only admire a wallpaper. Follow Dagric OS for more real demonstrations, and try the Free edition at dagric.com.",
        False, True,
    ),
    Story(
        39, "settings-full-minute", "CAN YOU FIND THE SETTINGS THAT MATTER?", "Accessibility, display, sound, and connections",
        118.0, 60.0,
        "Can you find the settings that matter? This live minute stays inside Dagric as System Settings opens. It moves through access tools, display, sound, Bluetooth, and KDE Connect. Each page is easy to reach and responds on screen. The video proves the menu path and basic workflow. It cannot prove how your own speakers, Wi-Fi, monitor, or battery will work. For that, boot Dagric Free from a USB drive and test your real computer before you install. We say this clearly because support should be based on facts. Follow Dagric OS for more live feature tours. Share this with someone testing an older computer, and visit dagric.com to start free.",
        False, True,
    ),
    Story(
        40, "accessibility-thirty", "ACCESSIBILITY SHOULD NOT BE HIDDEN", "Reach important controls quickly",
        123.0, 30.0,
        "Why are accessibility controls so often buried? Watch Dagric open the right pages and move to display controls. You can see the menu path and each page respond, with no hunting required. Follow Dagric OS for more useful demos, then get Dagric Free at dagric.com and test the settings on your own screen.",
        False, True,
    ),
    Story(
        41, "devices-thirty", "TEST THE DEVICES YOU ACTUALLY USE", "Sound, Bluetooth, and KDE Connect",
        137.0, 30.0,
        "Test the devices you actually use. Watch sound, Bluetooth, and KDE Connect open in one clear pass and see each page respond. Your own computer must still prove its speakers, wireless parts, and phone link. Try Dagric from USB before you install. Follow Dagric OS for more tests, and get the Free edition at dagric.com.",
        False, True,
    ),
    Story(
        42, "feature-journey-minute", "ONE MINUTE ACROSS THE REAL DESKTOP", "Desktop, Hub, and hardware evidence",
        36.0, 60.0,
        "Watch one minute go from setup to hardware proof. The Dagric desktop appears, the app menu opens Dagric Hub, and the Hub shows hardware, moving help, themes, safety, repair, and support. This same recording then opens Check This PC. Its report clearly shows the parts the system can see and calls out what is missing instead of hiding limits. You can follow every click without a cut. Your own computer still needs a USB test. Check Wi-Fi, sound, graphics, and storage before you install. Follow Dagric OS for more full tours, tell us which computer to test next, and visit dagric.com to start free.",
        False, True,
    ),
    Story(
        43, "website-proof-minute", "THE PRODUCT AND ITS PUBLIC PROOF", "From system settings to dagric.com",
        138.0, 60.0,
        "Can the public claims match the running system? Watch Dagric settings open Firefox and load dagric.com in the same session. Compare the product with its public facts, editions, test record, and known limits. The browser scrolls through the page while the operating system remains visible, connecting each promise to a place you can verify clearly and without guesswork. A slogan is not enough. Your own USB test proves how Wi-Fi, sound, graphics, storage, and other devices respond. Follow Dagric OS for more open tests and full tours. Share Dagric with someone whose computer still has life, then visit dagric.com and start free today.",
        False, True,
    ),
    Story(
        44, "complete-opening-minute", "THE FIRST MINUTE OF DAGRiC", "Personalize, finish setup, and find the tools",
        0.0, 60.0,
        "Watch one minute personalize Dagric and open its core tools. First run asks about the look, text size, panel layout, and optional apps. Each choice responds before the desktop opens. The guide ends, your chosen workspace appears, and Dagric Hub opens as a clear home for hardware checks, moving help, themes, repair, safety, guides, and support. The tour stays on the real interface from start to finish, so every transition remains easy to follow. See where each tool lives before you decide. Follow Dagric OS for more live tours. Share this with someone who wants a different desktop, and try Dagric Free at dagric.com before you install.",
        False, True,
    ),
]


PLATFORMS = [
    Platform("tiktok", "TIKTOK", "FOLLOW", "@dagricosofficial"),
    Platform("instagram", "INSTAGRAM REELS", "FOLLOW", "@dagricosofficial"),
    Platform("youtube-shorts", "YOUTUBE SHORTS", "SUBSCRIBE", "@DagricOS"),
    Platform("snapchat", "SNAPCHAT", "FOLLOW", "@dagricos"),
]

PUBLIC_LANGUAGE_BLOCKLIST = (
    re.compile(r"\bVM\b", re.IGNORECASE),
    re.compile(r"\bISO\b", re.IGNORECASE),
    re.compile(r"\bQEMU\b", re.IGNORECASE),
    re.compile(r"virtual machine", re.IGNORECASE),
    re.compile(r"virtual hardware", re.IGNORECASE),
    re.compile(r"test environment", re.IGNORECASE),
)


def validate_public_language(stories: list[Story]) -> None:
    violations: list[str] = []
    for story in stories:
        public_text = " ".join((story.hook, story.support, story.narration))
        matches = sorted({pattern.pattern for pattern in PUBLIC_LANGUAGE_BLOCKLIST if pattern.search(public_text)})
        if matches:
            violations.append(f"story {story.number}: {', '.join(matches)}")
    if violations:
        raise RuntimeError("Public video language gate failed: " + "; ".join(violations))


FUTURE_CAPTURE_TOPICS = [
    "Free edition boot from USB",
    "Pro edition boot from USB",
    "Installer disk-selection safety",
    "Installer confirmation and progress",
    "First reboot after installation",
    "Update workflow",
    "Security tools inside Dagric Hub",
    "Migration tools inside Dagric Hub",
    "Recovery tools inside Dagric Hub",
    "Owner guide and support path",
    "Privacy controls and network disclosure",
    "Physical Wi-Fi compatibility test",
    "Physical audio compatibility test",
    "Physical display compatibility test",
    "Older Windows 10 hardware test",
]


def run(args: list[str], capture: bool = False) -> str:
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


def probe(path: Path) -> dict:
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,channels,sample_rate",
                "-of",
                "json",
                str(path),
            ],
            capture=True,
        )
    )


def representative_frame(path: Path, at_seconds: float = 64.5) -> np.ndarray:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{at_seconds:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=160:100:flags=lanczos",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    expected_bytes = 160 * 100 * 3
    if len(completed.stdout) != expected_bytes:
        raise RuntimeError(f"Could not decode representative frame from {path}")
    return np.frombuffer(completed.stdout, dtype=np.uint8).reshape((100, 160, 3))


def latest_iso() -> tuple[Path, str]:
    candidates = sorted(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No named Dagric ISO in out/")
    return candidates[0], sha256(candidates[0])


def profile_for(story: Story, platform: Platform) -> tuple[str, dict]:
    story_index = next(index for index, item in enumerate(STORIES) if item.number == story.number)
    platform_index = next(index for index, item in enumerate(PLATFORMS) if item.slug == platform.slug)
    profile_id = PROFILE_SEQUENCE[(story_index + platform_index) % len(PROFILE_SEQUENCE)]
    return profile_id, VISUAL_PROFILES[profile_id]


def source_for(story: Story, profile_id: str, profile: dict) -> Path:
    if story.use_profile_capture:
        return NEW_SOURCE_ROOT / f"{story.number:02d}-real-hub-security-{profile_id}.mp4"
    return Path(profile["source"])


def validate_sources() -> dict:
    for required in (MODEL, VOICES):
        if not required.is_file():
            raise FileNotFoundError(required)
    iso, iso_hash = latest_iso()
    required_duration = max(
        story.source_start
        + story.duration * STORY_SOURCE_SPEEDS.get(story.number, SOURCE_SPEED)
        for story in STORIES
    )
    evidence: dict[str, dict] = {}
    representative_frames: dict[str, np.ndarray] = {}
    for profile_id, profile in VISUAL_PROFILES.items():
        source = Path(profile["source"])
        receipt_path = source.with_suffix(".capture.json")
        for required in (source, receipt_path):
            if not required.is_file():
                raise FileNotFoundError(required)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        source_info = probe(source)
        source_duration = float(source_info["format"]["duration"])
        checks = {
            "continuousVncStream": receipt.get("captureMode") == CAPTURE_MODE,
            "continuousFrameEncoding": receipt.get("continuousFrameEncoding") is True,
            "noSnapshotInputs": receipt.get("snapshotInputs") == [],
            "sourceHash": receipt.get("sha256") == sha256(source),
            "newestIsoPath": Path(receipt.get("iso", "")).resolve() == iso.resolve(),
            "newestIsoHash": receipt.get("isoSha256") == iso_hash,
            "visualProfile": receipt.get("visualProfile") == profile_id,
            "visualProfileAppliedInGuest": receipt.get("visualProfileAppliedInGuest") is True,
            "visualProfileApplicationTiming": receipt.get("visualProfileApplicationTiming")
            == "during-continuous-capture-after-first-run",
            "oneSourceVideoStream": len(
                [stream for stream in source_info["streams"] if stream["codec_type"] == "video"]
            )
            == 1,
            "sourceDuration": source_duration >= required_duration - 0.1,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError(
                f"Source validation failed for {profile_id}: " + ", ".join(failed)
            )
        evidence[profile_id] = {
            "label": profile["label"],
            "source": str(source),
            "sourceSha256": sha256(source),
            "captureReceipt": str(receipt_path),
            "checks": checks,
            "iso": str(iso),
            "isoSha256": iso_hash,
            "sourceDurationSeconds": source_duration,
        }
        representative_frames[profile_id] = representative_frame(source)
        evidence[profile_id]["representativeFrameAtSeconds"] = 64.5
        evidence[profile_id]["representativeFrameMeanRgb"] = [
            round(float(value), 2)
            for value in representative_frames[profile_id].mean(axis=(0, 1))
        ]
    story_source_evidence: dict[str, dict] = {}
    for story in (item for item in STORIES if item.use_profile_capture):
        for profile_id, profile in VISUAL_PROFILES.items():
            source = source_for(story, profile_id, profile)
            receipt_path = source.with_suffix(".capture.json")
            for required in (source, receipt_path):
                if not required.is_file():
                    raise FileNotFoundError(required)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            source_info = probe(source)
            source_duration = float(source_info["format"]["duration"])
            required_story_duration = (
                story.source_start
                + story.duration * STORY_SOURCE_SPEEDS.get(story.number, SOURCE_SPEED)
            )
            checks = {
                "continuousVncStream": receipt.get("captureMode") == CAPTURE_MODE,
                "continuousFrameEncoding": receipt.get("continuousFrameEncoding") is True,
                "noSnapshotInputs": receipt.get("snapshotInputs") == [],
                "sourceHash": receipt.get("sha256") == sha256(source),
                "newestIsoPath": Path(receipt.get("iso", "")).resolve() == iso.resolve(),
                "newestIsoHash": receipt.get("isoSha256") == iso_hash,
                "visualProfile": receipt.get("visualProfile") == profile_id,
                "visualProfileAppliedInGuest": receipt.get("visualProfileAppliedInGuest") is True,
                "visualProfileApplicationTiming": receipt.get("visualProfileApplicationTiming")
                in {"before-frame-zero", "during-continuous-capture-after-first-run"},
                "oneSourceVideoStream": len(
                    [stream for stream in source_info["streams"] if stream["codec_type"] == "video"]
                )
                == 1,
                "sourceDuration": source_duration >= required_story_duration - 0.1,
            }
            failed = [name for name, passed in checks.items() if not passed]
            if failed:
                raise RuntimeError(
                    f"Story source validation failed for {story.number}/{profile_id}: "
                    + ", ".join(failed)
                )
            story_source_evidence[f"{story.number:02d}-{profile_id}"] = {
                "source": str(source),
                "sourceSha256": sha256(source),
                "captureReceipt": str(receipt_path),
                "sourceDurationSeconds": source_duration,
                "checks": checks,
            }
    pairwise_deltas = {}
    for left, right in itertools.combinations(PROFILE_SEQUENCE, 2):
        delta = np.abs(
            representative_frames[left].astype(np.float32)
            - representative_frames[right].astype(np.float32)
        ).mean() / 255.0
        pairwise_deltas[f"{left}__{right}"] = round(float(delta), 4)
    minimum_delta = min(pairwise_deltas.values())
    if minimum_delta < 0.10:
        raise RuntimeError(
            "Visual-profile validation failed: representative live frames are too similar "
            f"(minimum normalized difference {minimum_delta:.4f})"
        )
    return {
        "iso": str(iso),
        "isoSha256": iso_hash,
        "profileCount": len(evidence),
        "profiles": evidence,
        "storySources": story_source_evidence,
        "representativeFramePairwiseNormalizedDifferences": pairwise_deltas,
        "minimumRepresentativeFrameDifference": minimum_delta,
        "representativeFramesMateriallyDifferent": True,
    }


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / filename), size=size)


def wrap_text(text: str, draw: ImageDraw.ImageDraw, selected_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and draw.textbbox((0, 0), candidate, font=selected_font)[2] > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def make_intro_overlay(story: Story, platform: Platform, profile_id: str, profile: dict) -> Path:
    prefix = f"{story.number:02d}-{story.slug}-{platform.slug}"
    intro_path = WORK / f"{prefix}-intro.png"
    intro_path.parent.mkdir(parents=True, exist_ok=True)

    intro = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(intro)
    # Keep the optional title in unused letterbox space. It never covers the
    # Dagric screen, never identifies the capture as a VM, and is gone by 3s.
    draw.rounded_rectangle((48, 1118, 1032, 1328), radius=30, fill=profile["panel"])
    draw.rectangle((48, 1118, 60, 1328), fill=profile["accent"])
    hook_font = font(43, True)
    hook_lines = wrap_text(story.hook, draw, hook_font, 900)[:2]
    y = 1142
    for line in hook_lines:
        draw.text((82, y), line, font=hook_font, fill="white")
        y += 50
    draw.text((84, 1278), story.support, font=font(22), fill=profile["soft"])
    intro.save(intro_path)
    return intro_path


def synthesize(kokoro: Kokoro, story: Story) -> tuple[Path, dict]:
    sample_rate = 24000
    segments = [part.strip() for part in re.split(r"(?<=[.!?])\s+", story.narration) if part.strip()]
    lead = 0.28
    maximum_speech = story.duration - lead - 0.16

    def create_speech(speed: float) -> np.ndarray:
        pieces: list[np.ndarray] = []
        for index, segment in enumerate(segments):
            samples, actual_rate = kokoro.create(
                segment,
                voice=VOICE_ID,
                speed=speed,
                lang="en-us",
            )
            if actual_rate != sample_rate:
                raise RuntimeError(f"Unexpected Kokoro sample rate: {actual_rate}")
            samples = np.asarray(samples, dtype=np.float32)
            fade = min(int(sample_rate * 0.035), len(samples) // 3)
            if fade:
                ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
                samples[:fade] *= ramp
                samples[-fade:] *= ramp[::-1]
            pieces.append(samples)
            if index + 1 < len(segments):
                pause = 0.18 if index < len(segments) - 2 else 0.24
                pieces.append(np.zeros(int(sample_rate * pause), dtype=np.float32))
        return np.concatenate(pieces)

    actual_voice_speed = VOICE_SPEED
    speech = create_speech(actual_voice_speed)
    speech_duration = len(speech) / sample_rate
    if speech_duration > maximum_speech:
        actual_voice_speed = min(
            1.28,
            round(actual_voice_speed * speech_duration / maximum_speech * 1.01, 3),
        )
        speech = create_speech(actual_voice_speed)
        speech_duration = len(speech) / sample_rate
    if speech_duration > maximum_speech:
        raise RuntimeError(
            f"{story.slug}: {speech_duration:.2f}s narration does not fit {story.duration:.2f}s"
        )
    rms = float(np.sqrt(np.mean(np.square(speech))) + 1e-12)
    speech *= min(4.0, (10 ** (-20.0 / 20.0)) / rms)
    word_count = len(re.findall(r"\b[\w'-]+\b", story.narration))
    render_duration = (
        story.duration
        if story.exact_duration
        else min(
            story.duration,
            max(speech_duration + lead + 0.92, word_count * 60.0 / 178.0),
        )
    )
    master = np.zeros((int(render_duration * sample_rate), 2), dtype=np.float32)
    if story.exact_duration:
        # A quiet, original ambient pad keeps exact-length editions alive
        # between spoken phrases without competing with the narrator.
        t = np.arange(len(master), dtype=np.float32) / sample_rate
        fade = np.minimum(np.minimum(t / 0.8, (render_duration - t) / 0.8), 1.0)
        fade = np.clip(fade, 0.0, 1.0)
        left_pad = (
            np.sin(2.0 * np.pi * 110.0 * t)
            + np.sin(2.0 * np.pi * 164.81 * t + 0.7)
            + np.sin(2.0 * np.pi * 220.0 * t + 1.4)
        ) * 0.0075 * fade
        right_pad = (
            np.sin(2.0 * np.pi * 110.0 * t + 0.25)
            + np.sin(2.0 * np.pi * 164.81 * t + 1.05)
            + np.sin(2.0 * np.pi * 220.0 * t + 1.75)
        ) * 0.0075 * fade
        master[:, 0] = left_pad
        master[:, 1] = right_pad
    start = int(lead * sample_rate)
    master[start : start + len(speech), 0] += speech
    master[start : start + len(speech), 1] += speech
    peak = float(np.max(np.abs(master)))
    if peak > 0.94:
        master *= 0.94 / peak
    audio_path = WORK / f"{story.number:02d}-{story.slug}-voice.wav"
    sf.write(audio_path, master, sample_rate, subtype="PCM_24")
    transcript_path = TRANSCRIPTS / f"{story.number:02d}-{story.slug}-narration.txt"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(story.narration.strip() + "\n", encoding="utf-8")
    return audio_path, {
        "transcript": str(transcript_path),
        "wordCount": word_count,
        "wordsPerMinuteByVideoWindow": round(word_count * 60.0 / render_duration, 2),
        "speechDurationSeconds": round(speech_duration, 3),
        "renderDurationSeconds": round(render_duration, 3),
        "leadSeconds": lead,
        "voiceSpeed": actual_voice_speed,
    }


def render(story: Story, platform: Platform, audio_path: Path, narration: dict) -> dict:
    output_dir = OUT / platform.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{story.number:02d}-{story.slug}-{platform.slug}-vertical.mp4"
    profile_id, profile = profile_for(story, platform)
    source = source_for(story, profile_id, profile)
    receipt_path = source.with_suffix(".capture.json")
    intro = make_intro_overlay(story, platform, profile_id, profile)
    render_duration = float(narration["renderDurationSeconds"])
    source_speed = STORY_SOURCE_SPEEDS.get(story.number, SOURCE_SPEED)
    intro_out = min(3.0, render_duration * 0.23)
    filters = (
        f"color=c=0x{profile['canvas']}:s=1080x1920:r=30:d={render_duration:.3f}[bg];"
        f"[0:v]trim=start={story.source_start:.3f}:duration={render_duration * source_speed:.3f},"
        f"setpts=(PTS-STARTPTS)/{source_speed:.4f},fps=30,scale=1140:713:flags=lanczos,"
        "crop=1080:675:x='30+30*sin(t*0.50)':y='19+19*cos(t*0.41)',format=yuv420p[screen];"
        "[bg][screen]overlay=0:300:shortest=1[base];"
        f"[2:v]format=rgba,fade=t=in:st=0:d=0.20:alpha=1,fade=t=out:st={intro_out - 0.40:.3f}:d=0.40:alpha=1[intro];"
        "[base][intro]overlay=0:0:shortest=1[outv]"
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
            "-i",
            str(audio_path),
            "-loop",
            "1",
            "-i",
            str(intro),
            "-filter_complex",
            filters,
            "-map",
            "[outv]",
            "-map",
            "1:a:0",
            "-t",
            f"{render_duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
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
            "highpass=f=72,lowpass=f=15800,acompressor=threshold=0.12:ratio=1.8:attack=15:release=140:makeup=1.25,loudnorm=I=-16:LRA=7:TP=-1.5",
            "-movflags",
            "+faststart",
            "-metadata",
            f"title={story.hook.title()}",
            "-metadata",
            "artist=Dagric OS",
            "-metadata",
            "comment=Receipt-backed continuous Dagric footage; one product-video layer; no captions or subtitle track; local synthetic narration",
            str(output),
        ]
    )
    info = probe(output)
    video_streams = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
    audio_streams = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
    subtitle_streams = [stream for stream in info["streams"] if stream["codec_type"] == "subtitle"]
    return {
        "number": story.number,
        "slug": story.slug,
        "platform": platform.slug,
        "output": str(output),
        "sha256": sha256(output),
        "durationSeconds": round(float(info["format"]["duration"]), 3),
        "width": video_streams[0]["width"],
        "height": video_streams[0]["height"],
        "frameRate": video_streams[0]["avg_frame_rate"],
        "videoStreamCount": len(video_streams),
        "audioStreamCount": len(audio_streams),
        "subtitleStreamCount": len(subtitle_streams),
        "source": str(source),
        "sourceSha256": sha256(source),
        "sourceStartSeconds": story.source_start,
        "sourceDurationSeconds": round(render_duration * source_speed, 3),
        "sourcePlaybackSpeed": source_speed,
        "captureReceipt": str(receipt_path),
        "visualProfile": profile_id,
        "visualProfileLabel": profile["label"],
        "visualProfileAppliedInGuest": True,
        "visibleProductVideoLayers": 1,
        "snapshotInputs": [],
        "generatedProductVisuals": False,
        "captionPolicy": "none",
        "transcriptForAuditOnly": narration["transcript"],
        "introLabel": {
            "maximumVisibleSeconds": 3.0,
            "overlapsProductFootage": False,
        },
    }


def write_queue(outputs: list[dict]) -> Path:
    rendered = {
        (record["number"], record["platform"]): record
        for record in outputs
    }
    entries: list[dict] = []
    for story in STORIES:
        for platform in PLATFORMS:
            profile_id, profile = profile_for(story, platform)
            rendered_record = rendered.get((story.number, platform.slug))
            entries.append(
                {
                    "slot": len(entries) + 1,
                    "topic": story.hook,
                    "platform": platform.slug,
                    "status": "rendered" if rendered_record else "ready-to-render",
                    "requiresNewCapture": False,
                    "visualProfile": profile_id,
                    "visualProfileLabel": profile["label"],
                    "source": str(profile["source"]),
                }
            )
    for topic in FUTURE_CAPTURE_TOPICS:
        for platform in PLATFORMS:
            profile_id = PROFILE_SEQUENCE[len(entries) % len(PROFILE_SEQUENCE)]
            entries.append(
                {
                    "slot": len(entries) + 1,
                    "topic": topic,
                    "platform": platform.slug,
                    "status": "capture-required",
                    "requiresNewCapture": True,
                    "plannedVisualProfile": profile_id,
                }
            )
    queue = {
        "schema": "dagric-caption-free-production-queue-v1",
        "targetVideoCount": 100,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "continuousScreenRecordingOnly": True,
            "snapshotsAllowed": False,
            "captionPolicy": "none",
            "oneProductVideoLayer": True,
            "platformBannerRequired": False,
            "maximumIntroLabelSeconds": 3.0,
            "overlaysOnProductFootageAllowed": False,
            "voiceSpeed": VOICE_SPEED,
            "defaultSourcePlaybackSpeed": SOURCE_SPEED,
            "perStorySourcePlaybackSpeeds": STORY_SOURCE_SPEEDS,
            "visualProfileRotation": list(PROFILE_SEQUENCE),
            "maximumSharePerProfile": 0.25,
            "adjacentProfileRepeatsAllowed": False,
            "profilesAppliedInsideGuestDuringContinuousCapture": True,
        },
        "entries": entries,
    }
    path = OUT / "production-queue-100.json"
    path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    validate_public_language(STORIES)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=len(STORIES))
    parser.add_argument(
        "--story",
        action="append",
        type=int,
        choices=[story.number for story in STORIES],
        help="Repeat to rebuild selected story numbers and preserve other manifest records.",
    )
    parser.add_argument(
        "--platform",
        action="append",
        choices=[platform.slug for platform in PLATFORMS],
        help="Repeat to render selected platforms; omit for all four.",
    )
    args = parser.parse_args()
    selected_stories = (
        [story for story in STORIES if story.number in args.story]
        if args.story
        else STORIES[: max(0, min(args.limit, len(STORIES)))]
    )
    selected_platforms = [
        platform for platform in PLATFORMS if not args.platform or platform.slug in args.platform
    ]
    source_evidence = validate_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(MODEL), str(VOICES))
    existing_manifest = {}
    manifest_path = OUT / "replacement-batch-manifest.json"
    if args.story and manifest_path.is_file():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs: list[dict] = []
    narration_records: list[dict] = []
    for story in selected_stories:
        print(f"Narrating {story.number:02d} {story.slug}", flush=True)
        audio_path, narration = synthesize(kokoro, story)
        narration_records.append({"story": asdict(story), **narration})
        for platform in selected_platforms:
            print(f"Rendering {story.number:02d} for {platform.label}", flush=True)
            outputs.append(render(story, platform, audio_path, narration))
    if existing_manifest:
        rebuilt_numbers = {story.number for story in selected_stories}
        rebuilt_platforms = {platform.slug for platform in selected_platforms}
        outputs = [
            record
            for record in existing_manifest.get("outputs", [])
            if not (
                record.get("number") in rebuilt_numbers
                and record.get("platform") in rebuilt_platforms
            )
        ] + outputs
        narration_records = [
            record
            for record in existing_manifest.get("narration", [])
            if record.get("story", {}).get("number") not in rebuilt_numbers
        ] + narration_records
        platform_order = {platform.slug: index for index, platform in enumerate(PLATFORMS)}
        outputs.sort(
            key=lambda record: (record["number"], platform_order[record["platform"]])
        )
        narration_records.sort(key=lambda record: record["story"]["number"])
    queue_path = write_queue(outputs)
    manifest = {
        "schema": "dagric-caption-free-replacement-batch-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(outputs),
        "sources": [
            {
                "visualProfile": profile_id,
                "visualProfileLabel": profile["label"],
                "source": str(profile["source"]),
                "sourceSha256": sha256(Path(profile["source"])),
                "captureReceipt": str(Path(profile["source"]).with_suffix(".capture.json")),
            }
            for profile_id, profile in VISUAL_PROFILES.items()
        ],
        "sourceEvidence": source_evidence,
        "visualPolicy": {
            "continuousFootageRequired": True,
            "snapshotsAllowed": False,
            "generatedProductVideoAllowed": False,
            "maximumSimultaneousProductVideoLayers": 1,
            "captionPolicy": "none",
            "platformSpecificBanners": False,
            "publicCaptureDescription": "live footage",
            "publicInfrastructureLabelsAllowed": False,
            "maximumIntroLabelSeconds": 3.0,
            "overlaysOnProductFootageAllowed": False,
            "animatedProgressRail": False,
            "profilesAppliedInsideGuestDuringContinuousCapture": True,
            "profileApplicationTiming": "after first-run, before the desktop feature tour",
            "profileRotation": list(PROFILE_SEQUENCE),
            "maximumSharePerProfile": 0.25,
            "adjacentProfileRepeatsAllowed": False,
            "postProductionWallpaperReplacement": False,
        },
        "voice": {
            "provider": "local Kokoro-82M",
            "model": "hexgrad/Kokoro-82M v1.0",
            "voiceId": VOICE_ID,
            "voiceName": VOICE_NAME,
            "speed": VOICE_SPEED,
            "defaultSourcePlaybackSpeed": SOURCE_SPEED,
            "syntheticVoiceDisclosureInMetadata": True,
            "manualNaturalnessReviewRequired": True,
        },
        "narration": narration_records,
        "productionQueue": str(queue_path),
        "outputs": outputs,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Completed {len(outputs)} caption-free replacements in {OUT}")
    print(f"Manifest: {manifest_path}")
    print(f"100-video queue: {queue_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
