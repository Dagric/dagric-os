#!/usr/bin/env python3
"""Build a small, proof-led social campaign from genuine Dagric UI captures."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro


REPO = Path(r"C:\Users\1248n\Documents\ChatGPT\Dagric Os")
DELIVERY = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos")
ROOT = DELIVERY / "Human Campaign"
RAW = ROOT / "raw"
DOCKER_FRAMES = RAW / "docker-frames"
WORK = ROOT / "work"
OUT = ROOT / "finished"
WAV = ROOT / "audio-masters"
MODEL_DIR = DELIVERY / "_tts-model"
MODEL = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
LOGO = REPO / "site" / "assets" / "dagric-logo.png"
FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def load_audio_engine():
    path = REPO / "promo" / "remaster-social-audio.py"
    spec = importlib.util.spec_from_file_location("dagric_audio_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIO = load_audio_engine()


@dataclass(frozen=True)
class Concept:
    slug: str
    title: str
    subline: str
    source: Path
    start: float
    duration: float
    script: str
    note: str
    cta: str
    voice: int
    aspects: tuple[str, ...] = ("vertical",)


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


def ffpath(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


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
                "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,channels,sample_rate",
                "-of", "json", str(path),
            ],
            capture=True,
        )
    )


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {"regular": FONT, "semibold": FONT_SEMIBOLD, "bold": FONT_BOLD}[weight]
    return ImageFont.truetype(str(path), size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    face: ImageFont.FreeTypeFont,
    width: int,
    fill: tuple[int, int, int, int],
    spacing: int = 10,
) -> int:
    x, y = xy
    for line in wrapped(draw, text, face, width):
        draw.text((x, y), line, font=face, fill=fill)
        box = draw.textbbox((x, y), line, font=face)
        y += box[3] - box[1] + spacing
    return y


def overlay(concept: Concept, aspect: str, outro: bool = False) -> Path:
    width, height = ((1080, 1920) if aspect == "vertical" else (1920, 1080))
    suffix = "outro" if outro else "overlay"
    path = WORK / "overlays" / aspect / f"{concept.slug}-{suffix}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (width, height), (5, 16, 29, 255) if outro else (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cyan = (73, 190, 238, 255)
    soft = (205, 225, 239, 255)
    white = (250, 252, 255, 255)

    if outro:
        logo = Image.open(LOGO).convert("RGBA")
        side = 144 if aspect == "vertical" else 116
        logo.thumbnail((side, side), Image.Resampling.LANCZOS)
        image.alpha_composite(logo, ((width - logo.width) // 2, 420 if aspect == "vertical" else 235))
        y = 620 if aspect == "vertical" else 395
        cta_face = font(54 if aspect == "vertical" else 48, "bold")
        lines = wrapped(draw, concept.cta, cta_face, width - 160)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=cta_face)
            draw.text(((width - (bbox[2] - bbox[0])) // 2, y), line, font=cta_face, fill=white)
            y += bbox[3] - bbox[1] + 15
        strap = "Like • Follow • Subscribe" if "subscribe" not in concept.cta.lower() else "Follow the test • Share the proof"
        strap_face = font(32 if aspect == "vertical" else 28, "semibold")
        bbox = draw.textbbox((0, 0), strap, font=strap_face)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, y + 28), strap, font=strap_face, fill=cyan)
        social = "TikTok / Instagram  @dagricosofficial   •   Snapchat  @dagricos   •   dagric.com"
        social_face = font(21 if aspect == "vertical" else 24)
        bbox = draw.textbbox((0, 0), social, font=social_face)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, height - 115), social, font=social_face, fill=soft)
    elif aspect == "vertical":
        draw.rounded_rectangle((38, 40, 1042, 245), radius=28, fill=(5, 18, 31, 226), outline=(73, 190, 238, 235), width=3)
        draw.text((66, 62), "REAL DAGRIC OS • TODAY'S PRO ISO", font=font(24, "semibold"), fill=cyan)
        draw_wrapped(draw, (66, 105), concept.title, font(47, "bold"), 940, white, 6)
        draw.rounded_rectangle((38, 1030, 1042, 1250), radius=25, fill=(5, 18, 31, 226), outline=(255, 255, 255, 36), width=2)
        draw.text((68, 1055), "What I noticed", font=font(25, "semibold"), fill=cyan)
        draw_wrapped(draw, (68, 1095), concept.note, font(31), 920, soft, 7)
        draw.rounded_rectangle((38, 1795, 1042, 1888), radius=24, fill=(5, 18, 31, 232))
        draw.text((66, 1815), "@dagricosofficial  •  @dagricos  •  dagric.com", font=font(27, "semibold"), fill=white)
    else:
        draw.rounded_rectangle((38, 34, 1882, 178), radius=24, fill=(5, 18, 31, 222), outline=(73, 190, 238, 230), width=3)
        draw.text((66, 50), "REAL DAGRIC OS • TODAY'S PRO ISO", font=font(22, "semibold"), fill=cyan)
        draw.text((66, 87), concept.title, font=font(44, "bold"), fill=white)
        draw.rounded_rectangle((38, 895, 1882, 1036), radius=22, fill=(5, 18, 31, 226))
        draw.text((66, 918), concept.note, font=font(28), fill=soft)
        draw.text((66, 980), "@dagricosofficial  •  Snapchat @dagricos  •  dagric.com", font=font(23, "semibold"), fill=cyan)
    image.save(path)
    return path


def srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def make_srt(concept: Concept, duration: float, path: Path) -> int:
    words = re.findall(r"\S+", concept.script)
    groups: list[list[str]] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= 8 or (len(current) >= 5 and re.search(r"[.!?]$", word)):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    spoken_start = 0.55
    spoken_end = max(spoken_start + 1.0, duration - 3.2)
    weights = [len(group) for group in groups]
    total = sum(weights) or 1
    cursor = spoken_start
    lines: list[str] = []
    for index, (group, weight) in enumerate(zip(groups, weights), start=1):
        span = (spoken_end - spoken_start) * weight / total
        end = min(spoken_end, cursor + span)
        lines.extend([str(index), f"{srt_time(cursor)} --> {srt_time(end)}", " ".join(group), ""])
        cursor = end
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return len(groups)


def make_docker_source() -> Path:
    output = WORK / "sources" / "docker-proof.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = [DOCKER_FRAMES / f"{index:02d}-{name}.jpg" for index, name in [
        (1, "containers-list"), (2, "container-logs"), (3, "container-inspect"), (4, "container-stats")
    ]]
    for frame in frames:
        if not frame.exists():
            raise FileNotFoundError(frame)
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for frame in frames:
        args.extend(["-loop", "1", "-t", "5", "-i", str(frame)])
    chains: list[str] = []
    refs: list[str] = []
    for index in range(len(frames)):
        chains.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x07111F,fps=30,"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st=4.65:d=0.35,setpts=PTS-STARTPTS[v{index}]"
        )
        refs.append(f"[v{index}]")
    chains.append(f"{''.join(refs)}concat=n={len(frames)}:v=1:a=0[outv]")
    args.extend([
        "-filter_complex", ";".join(chains), "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])
    run(args)
    return output


def make_proof_montage(docker_source: Path) -> Path:
    output = WORK / "sources" / "proof-before-pitch.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    clips = [
        (RAW / "02-latest-pro-onboarding-human.mp4", 4.0, 6.0),
        (RAW / "03-latest-pro-everyday-desktop.mp4", 3.0, 6.0),
        (RAW / "04-latest-check-this-pc.mp4", 8.0, 8.0),
        (docker_source, 0.0, 7.0),
    ]
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path, start, duration in clips:
        args.extend(["-ss", str(start), "-t", str(duration), "-i", str(path)])
    chains: list[str] = []
    refs: list[str] = []
    for index in range(len(clips)):
        chains.append(
            f"[{index}:v]fps=30,scale=1280:800:force_original_aspect_ratio=decrease,"
            f"pad=1280:800:(ow-iw)/2:(oh-ih)/2:color=0x07111F,setpts=PTS-STARTPTS[v{index}]"
        )
        refs.append(f"[v{index}]")
    chains.append(f"{''.join(refs)}concat=n={len(clips)}:v=1:a=0[outv]")
    args.extend([
        "-filter_complex", ";".join(chains), "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])
    run(args)
    return output


def concepts(docker_source: Path, montage: Path) -> list[Concept]:
    onboarding = RAW / "02-latest-pro-onboarding-human.mp4"
    everyday = RAW / "03-latest-pro-everyday-desktop.mp4"
    hardware = RAW / "04-latest-check-this-pc.mp4"
    return [
        Concept(
            "onboarding-first-look", "I changed the look before I installed anything",
            "A real first-run session, not a motion-design mockup", onboarding, 0, 31,
            "I booted today's Pro image in the test VM, and this is the first screen I got. I clicked through the appearance choices slowly: dark mode, a couple of accent colors, then a wallpaper. The useful part is that none of this pretends to test hardware. For Wi-Fi, graphics, sleep, and printers, I would still use the live USB on the actual PC.",
            "The choices respond immediately, and the live-session warning stays visible.",
            "Would you keep the default look? Comment below.", 0, ("vertical", "landscape"),
        ),
        Concept(
            "onboarding-no-pressure", "The setup lets you look around without committing",
            "Try the interface first", onboarding, 2, 26,
            "This is the part I wanted to see before making any big claim. The first-run flow lets me change the look, but the screen also says this is a live trial and the changes disappear at shutdown. That is the right expectation: explore the interface now, then test the real computer before installing.",
            "A reversible live session is a better first step than a sales promise.",
            "Save this before you make a bootable USB.", 2,
        ),
        Concept(
            "everyday-files-settings", "My first five minutes on the real desktop",
            "Files, folders, and sound settings", everyday, 0, 42,
            "After skipping setup, I wanted to know whether the desktop felt obvious without a tutorial. Files is already on the panel. Home, Downloads, and Pictures are where I expected. Then I opened system settings and checked sound. Dagric is not trying to hide KDE underneath; it is configuring a familiar starting point on top of it.",
            "The test is deliberately ordinary: can I find what I need without hunting?",
            "Like the real footage? Follow the next test.", 4, ("vertical", "landscape"),
        ),
        Concept(
            "familiar-not-windows", "Familiar does not have to mean fake Windows",
            "A short, honest desktop tour", everyday, 4, 28,
            "My small test was simple: could I find my files and settings without somebody explaining the desktop? I could. The panel, folders, browser, and system controls are visible. Familiar is not the same as Windows, but it can lower the first-hour friction.",
            "This is KDE Plasma with Dagric's defaults—not a Windows clone.",
            "What should I test next? Leave one real task.", 5,
        ),
        Concept(
            "hardware-check-honest", "The hardware check did not say everything was perfect",
            "That is exactly why I trust this screen", hardware, 3, 42,
            "This is the part I trust more than a slogan. Check This PC does not say everything is perfect. In this virtual machine it reports no install drive, legacy BIOS, no Wi-Fi card, and no sound device, then explains why. A pre-install check should show the result, including the awkward parts, before you touch the disk.",
            "Real reports should include limitations, not hide them behind a green checkmark.",
            "Share this with someone replacing Windows 10.", 1, ("vertical", "landscape"),
        ),
        Concept(
            "vm-is-not-hardware-proof", "A VM is not proof your laptop will work",
            "What this test can—and cannot—show", hardware, 8, 30,
            "A virtual machine is useful for repeatable boot tests. It is not proof that your laptop's Wi-Fi, graphics, suspend, or printer will work. Every Dagric demo should say what you are seeing and what it does not prove. That is why the live USB test stays in the call to action.",
            "VM proof covers the software path; physical hardware still needs a live USB.",
            "Try it live first. Full notes at dagric.com/review.", 8,
        ),
        Concept(
            "docker-behind-the-test", "Behind the Dagric test VM",
            "Docker Desktop, QEMU, logs, configuration, and live stats", docker_source, 0, 20,
            "Behind the screen recording, Docker Desktop is running the Dagric test container with hardware-accelerated QEMU. I checked the container list, boot logs, live configuration, and resource charts. This proves the automated VM session is real. It still does not replace a physical hardware test.",
            "The VM is a repeatable lab, not a substitute for a real-PC compatibility check.",
            "Subscribe for the next real boot test.", 3, ("vertical", "landscape"),
        ),
        Concept(
            "proof-before-pitch", "Proof before the pitch",
            "What a reviewer should be able to verify", montage, 0, 27,
            "Before asking reviewers to cover Dagric, I want the proof in one place: real boot footage, current checksums, test notes, known limits, and a path to report bugs. The review page is the handoff. The video is only an invitation to verify it.",
            "The strongest story is not perfection. It is a testable trail from ISO to result.",
            "Review the evidence at dagric.com/review.", 7,
        ),
    ]


def render(concept: Concept, aspect: str, kokoro: Kokoro, seed: int) -> dict:
    width, height = ((1080, 1920) if aspect == "vertical" else (1920, 1080))
    output = OUT / aspect / f"{concept.slug}-{aspect}.mp4"
    audio_path = WAV / aspect / f"{concept.slug}-{aspect}.wav"
    srt = output.with_suffix(".srt")
    output.parent.mkdir(parents=True, exist_ok=True)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    duration = concept.duration

    narration, sample_rate, credits, speed = AUDIO.fit_narration(
        kokoro, [concept.script], [concept.voice], duration - 2.7
    )
    mixed, levels = AUDIO.mix_audio(narration, sample_rate, duration, seed)
    sf.write(audio_path, mixed, sample_rate, subtype="PCM_16")
    caption_count = make_srt(concept, duration, srt)
    regular = overlay(concept, aspect, outro=False)
    endcard = overlay(concept, aspect, outro=True)
    subtitle = ffpath(srt)
    outro_start = duration - 2.7

    if aspect == "vertical":
        visual = (
            "[0:v]fps=30,format=yuv420p,split=2[bg][main];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "gblur=sigma=28,eq=brightness=-0.36:saturation=0.72[bgv];"
            "[main]scale=1010:-2:flags=lanczos,pad=iw+10:ih+10:5:5:color=0x49BEEE[mainv];"
            "[bgv][mainv]overlay=(W-w)/2:300[base];"
            "[2:v]format=rgba[ov];[base][ov]overlay=0:0[laid];"
            f"[laid]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,FontSize=15,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,BackColour=&H9A101A24,"
            "Outline=1,Shadow=0,Alignment=2,MarginV=300'[captioned];"
            f"[3:v]format=rgba[end];[captioned][end]overlay=0:0:enable='gte(t,{outro_start:.3f})'[outv]"
        )
    else:
        visual = (
            "[0:v]fps=30,format=yuv420p,split=2[bg][main];"
            "[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            "gblur=sigma=24,eq=brightness=-0.37:saturation=0.72[bgv];"
            "[main]scale=-2:870:flags=lanczos,pad=iw+10:ih+10:5:5:color=0x49BEEE[mainv];"
            "[bgv][mainv]overlay=(W-w)/2:175[base];"
            "[2:v]format=rgba[ov];[base][ov]overlay=0:0[laid];"
            f"[laid]subtitles=filename='{subtitle}':force_style='FontName=Segoe UI Semibold,FontSize=17,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A24,BorderStyle=3,BackColour=&H9A101A24,"
            "Outline=1,Shadow=0,Alignment=2,MarginV=170'[captioned];"
            f"[3:v]format=rgba[end];[captioned][end]overlay=0:0:enable='gte(t,{outro_start:.3f})'[outv]"
        )

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{concept.start:.3f}", "-t", f"{duration:.3f}", "-i", str(concept.source),
        "-i", str(audio_path), "-loop", "1", "-i", str(regular), "-loop", "1", "-i", str(endcard),
        "-filter_complex", visual, "-map", "[outv]", "-map", "1:a:0",
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-af", "loudnorm=I=-16:LRA=8:TP=-1.5", "-movflags", "+faststart",
        "-metadata", f"title={concept.title}", "-metadata", "artist=Dagric OS",
        "-metadata", "comment=Actual Dagric OS or Docker Desktop test footage; human-directed edit; synthetic Kokoro narration disclosed; original synthesized sound bed",
        str(output),
    ])

    info = probe(output)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    return {
        "slug": concept.slug,
        "title": concept.title,
        "aspect": aspect,
        "source": str(concept.source),
        "output": str(output),
        "captions": str(srt),
        "durationSeconds": round(float(info["format"]["duration"]), 3),
        "width": video["width"],
        "height": video["height"],
        "frameRate": video["avg_frame_rate"],
        "videoCodec": video["codec_name"],
        "audioCodec": audio["codec_name"],
        "audioChannels": audio["channels"],
        "audioSampleRate": int(audio["sample_rate"]),
        "voice": credits[0]["voiceName"],
        "script": concept.script,
        "note": concept.note,
        "cta": concept.cta,
        "captionEvents": caption_count,
        "generationSpeed": round(speed, 3),
        **levels,
        "sha256": sha256(output),
    }


def main() -> int:
    required = [MODEL, VOICES, LOGO, RAW / "02-latest-pro-onboarding-human.mp4", RAW / "03-latest-pro-everyday-desktop.mp4", RAW / "04-latest-check-this-pc.mp4"]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    ROOT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    docker_source = make_docker_source()
    montage = make_proof_montage(docker_source)
    items = concepts(docker_source, montage)
    kokoro = Kokoro(str(MODEL), str(VOICES))

    records: list[dict] = []
    total = sum(len(item.aspects) for item in items)
    position = 0
    for index, item in enumerate(items):
        for aspect in item.aspects:
            position += 1
            print(f"[{position:02d}/{total:02d}] {item.slug} ({aspect})", flush=True)
            records.append(render(item, aspect, kokoro, seed=101 + index * 7 + (0 if aspect == "vertical" else 3)))

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "sourceDisclosure": "Primary footage is actual Dagric OS Pro live-ISO UI captured from the QEMU framebuffer. Docker frames are actual Docker Desktop state from the same running test container.",
        "audioDisclosure": "Narration is locally synthesized with Kokoro-82M (Apache-2.0) and must be disclosed with each platform's synthetic-media controls where required.",
        "musicRights": "The sound bed is generated locally from original synthesized tones; no downloaded music, samples, or stock audio are used.",
        "editorialPrinciples": [
            "real UI action leads every story",
            "conversational scripts describe exactly what was tested",
            "VM limitations are stated instead of hidden",
            "each concept has a distinct hook, note, voice, duration, and outro",
            "no claim that synthetic narration is a human recording",
        ],
        "videos": records,
    }
    (OUT / "human-campaign-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Dagric OS human campaign\n\n"
        "A proof-led set built from actual Dagric VM and Docker Desktop captures. The videos use conversational, locally synthesized narration, original sound beds, sidecar captions, varied hooks, and different calls to action.\n\n"
        "Platform disclosure remains required where a service asks whether audio or media was synthetically generated. The edit never claims that the narration is a human recording.\n",
        encoding="utf-8",
    )
    print(f"Built {len(records)} videos in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
