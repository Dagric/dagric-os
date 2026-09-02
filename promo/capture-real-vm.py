#!/usr/bin/env python3
"""Record the live Dagric VM directly from its VNC framebuffer."""

from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from vncdotool import api


WIDTH = 1280
HEIGHT = 800
# Forced framebuffer refreshes keep captures deterministic even when the guest
# is visually idle. Ten frames per second is enough for clear UI motion while
# avoiding the VNC timeouts seen with incremental-update requests.
FPS = 10


@dataclass
class Action:
    at: float
    label: str
    run: Callable[[object], None]


def click(x: int, y: int) -> Callable[[object], None]:
    def action(client: object) -> None:
        client.mouseMove(x, y)
        client.mousePress(1)

    return action


def double_click(x: int, y: int) -> Callable[[object], None]:
    def action(client: object) -> None:
        client.mouseMove(x, y)
        client.mousePress(1)
        time.sleep(0.16)
        client.mousePress(1)

    return action


def key(name: str) -> Callable[[object], None]:
    return lambda client: client.keyPress(name)


def text(value: str) -> Callable[[object], None]:
    def action(client: object) -> None:
        for character in value:
            client.keyPress(character)

    return action


def sequence(*steps: Callable[[object], None]) -> Callable[[object], None]:
    def action(client: object) -> None:
        for step in steps:
            step(client)

    return action


def scenario(name: str) -> tuple[float, list[Action]]:
    if name == "observe":
        return 8, []
    if name == "test":
        return 6, [Action(2, "open Accessibility", click(300, 502))]
    if name == "fresh-onboarding":
        # Keep this first clip on the reversible appearance page. It shows the
        # real current wizard responding to several human-paced choices without
        # saving a full setup or pretending a VM proves hardware compatibility.
        return 31, [
            Action(2, "continue from Welcome", click(1180, 758)),
            Action(6, "preview Dark", click(620, 268)),
            Action(10, "try teal highlight", click(856, 260)),
            Action(14, "try orange highlight", click(954, 260)),
            Action(18, "preview Aurora wallpaper", click(1125, 458)),
            Action(24, "return to Dagric wallpaper", click(405, 458)),
        ]
    if name == "fresh-everyday":
        return 45, [
            Action(2, "open Files from the panel", click(185, 770)),
            Action(8, "open Downloads", click(360, 329)),
            Action(14, "open Pictures", click(350, 380)),
            Action(20, "return Home", click(360, 245)),
            Action(26, "close Files", key("alt-f4")),
            Action(30, "open System Settings", click(82, 770)),
            Action(38, "open Sound settings", click(270, 435)),
        ]
    if name == "fresh-hardware":
        return 50, [
            Action(2, "close the current window", key("alt-f4")),
            Action(5, "open Check This PC", double_click(58, 48)),
            Action(18, "focus the hardware report", click(700, 400)),
            Action(21, "read the next report section", key("pgdn")),
            Action(29, "continue through the report", key("pgdn")),
            Action(37, "return to the summary", key("pgup")),
            Action(45, "finish reading the report", key("enter")),
        ]
    if name == "settings":
        return 38, [
            Action(2, "Accessibility", click(300, 502)),
            Action(9, "Display and Monitor", click(300, 469)),
            Action(16, "Sound", click(270, 435)),
            Action(23, "Bluetooth", click(270, 572)),
            Action(30, "KDE Connect", click(270, 675)),
        ]
    if name == "hub":
        return 52, [
            Action(1, "close current window", click(1120, 87)),
            Action(4, "open launcher", click(35, 40)),
            Action(6, "focus search", click(450, 30)),
            Action(7, "search Dagric Hub", text("dagric hub")),
            Action(9, "open Dagric Hub", key("enter")),
            Action(15, "select Check This PC", click(550, 128)),
            Action(17, "run Check This PC", click(775, 770)),
            Action(29, "close hardware report", click(1015, 720)),
            Action(33, "open launcher", click(35, 40)),
            Action(35, "focus search", click(450, 30)),
            Action(36, "search Dagric Hub", text("dagric hub")),
            Action(38, "open Dagric Hub", key("enter")),
        ]
    if name == "appearance":
        return 52, [
            Action(1, "close current window", click(905, 40)),
            Action(4, "open launcher", click(35, 40)),
            Action(6, "focus search", click(450, 30)),
            Action(7, "search Dagric Hub", text("dagric hub")),
            Action(9, "open Dagric Hub", key("enter")),
            Action(14, "select Appearance gallery", click(550, 245)),
            Action(16, "open Appearance gallery", click(775, 770)),
            Action(23, "preview Midnight", click(970, 350)),
            Action(32, "show Layouts", click(905, 205)),
            Action(38, "preview Focus layout", click(670, 350)),
        ]
    if name == "everyday":
        return 45, [
            Action(1, "close current window", click(1125, 83)),
            Action(4, "open launcher", click(35, 40)),
            Action(7, "open Files", click(470, 90)),
            Action(14, "Downloads", click(360, 329)),
            Action(20, "Pictures", click(350, 380)),
            Action(26, "close Files", click(1035, 146)),
            Action(30, "open System Settings", click(35, 103)),
        ]
    raise ValueError(f"Unknown scenario: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=[
            "observe", "test", "fresh-onboarding", "fresh-everyday", "fresh-hardware",
            "settings", "hub", "appearance", "everyday",
        ],
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--server", default="localhost::5914")
    args = parser.parse_args()
    duration, actions = scenario(args.scenario)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    frame_period = 1 / FPS
    frame_count = int(duration * FPS)
    completed: set[int] = set()
    started = time.monotonic()
    ffmpeg: subprocess.Popen[bytes] | None = None
    try:
        with api.connect(args.server, timeout=15) as client:
            client.refreshScreen(False)
            if client.screen is None:
                raise RuntimeError("VNC server returned no framebuffer")
            width, height = client.screen.size
            ffmpeg = subprocess.Popen(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "-video_size", f"{width}x{height}",
                    "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(args.output),
                ],
                stdin=subprocess.PIPE,
            )
            for frame_number in range(frame_count):
                elapsed = time.monotonic() - started
                acted = False
                for index, item in enumerate(actions):
                    if index not in completed and elapsed >= item.at:
                        item.run(client)
                        completed.add(index)
                        acted = True
                        print(f"{elapsed:6.2f}s | {item.label}", flush=True)
                # A full framebuffer request is expensive. Refresh after each
                # scripted action and once per second for animation; repeat the
                # last received image for the intervening encoded frames.
                if acted or frame_number % FPS == 0:
                    client.refreshScreen(False)
                image = client.screen.convert("RGB")
                assert ffmpeg is not None and ffmpeg.stdin is not None
                ffmpeg.stdin.write(image.tobytes())
                target = started + (frame_number + 1) * frame_period
                delay = target - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
    finally:
        api.shutdown()
        if ffmpeg is not None and ffmpeg.stdin:
            ffmpeg.stdin.close()
        return_code = ffmpeg.wait() if ffmpeg is not None else 1
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with {return_code}")
    print(f"Recorded {args.output} ({duration}s, {FPS} fps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
