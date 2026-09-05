#!/usr/bin/env python3
"""Record the live Dagric VM directly from its VNC framebuffer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from vncdotool import api
from PIL import Image, ImageOps, ImageStat


# Capture a fresh full framebuffer continuously. This is intentionally not a
# screenshot sampler: every encoded frame comes from a new VNC refresh request.
# Twenty frames per second is a practical continuous-capture target for this
# local VM. A background VNC update pump keeps the framebuffer live while a
# real-time encoder runs independently; static UI may naturally yield identical
# adjacent frames, exactly as it would in OBS or another screen recorder.
# Final delivery is normalized to 30 fps by the editor.
FPS = 20
CAPTURE_MODE = "continuous-vnc-stream"
REPO = Path(__file__).resolve().parents[1]
VISUAL_PROFILES = {
    "current": None,
    "open-horizon": "open-horizon",
    "night-orbit": "night-orbit",
    "wild-meadow": "wild-meadow",
    "open-coast": "open-coast",
}


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


def move(x: int, y: int) -> Callable[[object], None]:
    return lambda client: client.mouseMove(x, y)


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


def launcher_actions(at: float, query: str, label: str) -> list[Action]:
    """Use KRunner with visible settling time between search interactions."""

    return [
        Action(at, "open application search", key("alt-f2")),
        Action(at + 2, f"search for {label}", text(query)),
        Action(at + 3, f"open {label}", key("enter")),
    ]


def profile_actions(at: float, profile: str) -> list[Action]:
    """Apply a shipped look with enough visible time for the terminal to open."""

    return [
        Action(at, f"open the {profile} profile terminal", key("ctrl-alt-t")),
        Action(at + 2, f"enter the {profile} profile command", text(f"dagric-style --apply {profile}")),
        Action(at + 3, f"apply the {profile} visual profile", key("enter")),
        Action(at + 8, f"close the {profile} profile terminal", text("exit")),
        Action(at + 9, f"show the {profile} desktop", key("enter")),
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_vm_iso() -> tuple[Path, str]:
    candidates = sorted(
        (REPO / "out").glob("dagric-os-*-amd64.iso"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No edition-named Dagric ISO exists in out/")
    latest = candidates[0]
    digest = sha256(latest)
    testing = REPO / "out" / "_testing.iso"
    if not testing.is_file() or sha256(testing) != digest:
        raise RuntimeError(
            "The running VM copy does not match the newest named ISO. Run test/boot-test.ps1 first."
        )
    return latest, digest


def apply_visual_profile(client: object, profile: str) -> None:
    """Ask Dagric itself to apply a packaged style before recording starts."""

    style_id = VISUAL_PROFILES[profile]
    if style_id is None:
        return
    # KRunner's Alt+F2 shortcut is not reliable while the first-run window is
    # active. A real guest terminal provides a visible, deterministic route to
    # the same owner-facing command without touching the host-side pixels.
    client.keyPress("ctrl-alt-t")
    time.sleep(2.0)
    text(f"dagric-style --apply {style_id}")(client)
    client.keyPress("enter")
    # Plasma changes its color scheme, wallpaper and compositor settings in
    # separate calls. Give all of them time to settle before frame zero so the
    # resulting source begins on the promised look instead of showing a setup
    # flash or edit-time replacement.
    time.sleep(5.0)
    text("exit")(client)
    client.keyPress("enter")
    time.sleep(1.5)


def wait_for_guest_ready(client: object, timeout: float = 120.0) -> tuple[int, int]:
    """Wait past firmware/Plymouth transitions for the scripted Plasma canvas."""

    started = time.monotonic()
    last_wake = started - 10.0
    stable_frames = 0
    last_size: tuple[int, int] | None = None
    while time.monotonic() - started < timeout:
        client.refreshScreen(False)
        screen = client.screen
        if screen is None:
            stable_frames = 0
            time.sleep(0.5)
            continue
        size = screen.size
        if size != last_size:
            print(f"guest framebuffer is {size[0]}x{size[1]}; waiting for Plasma", flush=True)
            last_size = size
        luminance = ImageStat.Stat(screen.convert("L")).mean[0]
        # The long-running capture VM can be fully healthy while Plasma has
        # blanked the virtual monitor. Periodic benign input wakes DPMS before
        # the readiness timeout, avoiding a failed recording or a black lead-in.
        now = time.monotonic()
        if luminance < 20.0 and now - last_wake >= 5.0:
            client.keyPress("shift")
            client.mouseMove(max(1, size[0] // 2), max(1, size[1] // 2))
            last_wake = now
        if size[0] >= 1200 and size[1] >= 720 and luminance >= 20.0:
            stable_frames += 1
            if stable_frames >= 8:
                return size
        else:
            stable_frames = 0
        time.sleep(0.5)
    raise TimeoutError("Dagric Plasma desktop did not reach its scripted capture resolution")


def stop_vnc_reactor(timeout: float = 5.0) -> bool:
    """Stop vncdotool's process-wide reactor without letting the CLI hang.

    Twisted can occasionally stall while shutting down after the guest changes
    its display session. Run the supported shutdown in a daemon helper and give
    it a bounded window; the caller may then exit after all media and receipt
    files have been flushed.
    """
    completed = threading.Event()

    def shutdown() -> None:
        try:
            api.shutdown()
        finally:
            completed.set()

    worker = threading.Thread(target=shutdown, name="Dagric VNC reactor shutdown", daemon=True)
    worker.start()
    worker.join(timeout=timeout)
    return completed.is_set()


def scenario(name: str, visual_profile: str = "current") -> tuple[float, list[Action]]:
    if name == "observe":
        return 8, []
    if name == "test":
        return 6, [Action(2, "open Accessibility", click(300, 502))]
    if name == "fresh-onboarding":
        # Record the real first-run path through the ready screen. Clicking the
        # final button changes the guest display session, so that handoff is
        # deliberately performed after this MP4 has been finalized.
        appearance_actions = (
            [
                Action(7, "preview Dark", click(735, 268)),
                Action(11, "preview teal highlight", click(856, 260)),
                Action(15, "preview Aurora wallpaper", click(1125, 458)),
            ]
            if visual_profile == "current"
            else []
        )
        return 48, [
            Action(2, "continue from Welcome", click(1180, 758)),
            *appearance_actions,
            Action(20, "continue to text size", click(1180, 758)),
            Action(26, "continue to taskbar layouts", click(1180, 758)),
            Action(32, "select Unity taskbar", click(1110, 610)),
            Action(37, "continue to optional apps", click(1180, 758)),
            Action(44, "continue to ready screen", click(1180, 758)),
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
            Action(5, "open Check This PC", double_click(130, 84)),
            Action(18, "focus the hardware report", click(700, 400)),
            Action(21, "read the next report section", key("pgdn")),
            Action(29, "continue through the report", key("pgdn")),
            Action(37, "return to the summary", key("pgup")),
            Action(45, "finish reading the report", key("enter")),
        ]
    if name == "settings":
        return 30, [
            Action(1, "close the current window", key("alt-f4")),
            Action(2, "open launcher", click(35, 40)),
            Action(3, "focus search", click(450, 30)),
            Action(4, "search System Settings", text("system settings")),
            Action(5, "open System Settings", key("enter")),
            Action(8, "Accessibility", click(300, 502)),
            Action(12, "Display and Monitor", click(300, 469)),
            Action(16, "Sound", click(270, 435)),
            Action(20, "Bluetooth", click(270, 572)),
            Action(24, "KDE Connect", click(270, 675)),
        ]
    if name == "hub":
        # This is a dedicated Hub take. The hardware report is recorded in its
        # own source instead of being reused as misleading Hub footage. Keep
        # the selection moving every few seconds so the social cut remains an
        # active tour instead of lingering on a static list.
        return 42, [
            Action(1, "close current window", key("alt-f4")),
            Action(4, "open launcher", click(35, 40)),
            Action(6, "focus search", click(450, 30)),
            Action(7, "search Dagric Hub", text("dagric hub")),
            Action(9, "open Dagric Hub", key("enter")),
            Action(11, "browse the first Hub tool", key("down")),
            Action(13, "browse the next Hub tool", key("down")),
            Action(15, "continue through Hub tools", key("down")),
            Action(17, "continue through Hub tools", key("down")),
            Action(19, "move through Hub categories", key("pgdn")),
            Action(21, "browse the current Hub category", key("down")),
            Action(23, "browse another Hub tool", key("down")),
            Action(25, "move through more Hub categories", key("pgdn")),
            Action(27, "compare the previous Hub tool", key("up")),
            Action(29, "compare another Hub tool", key("up")),
            Action(31, "return to the top of Dagric Hub", key("home")),
            Action(33, "highlight Check This PC", key("down")),
            Action(35, "highlight the next practical tool", key("down")),
            Action(37, "finish on Check This PC", key("home")),
        ]
    if name == "appearance":
        return 42, [
            Action(1, "close current window", key("alt-f4")),
            Action(4, "open launcher", click(35, 40)),
            Action(6, "focus search", click(450, 30)),
            Action(7, "search Dagric Hub", text("dagric hub")),
            Action(9, "open Dagric Hub", key("enter")),
            Action(12, "move to Appearance gallery", sequence(
                key("home"), key("down"), key("down"), key("down"),
                key("down"), key("down"), key("down")
            )),
            Action(14, "open Appearance gallery", key("enter")),
            Action(18, "preview Midnight", click(360, 600)),
            Action(23, "show Layouts", click(905, 205)),
            Action(27, "preview Focus layout", click(670, 350)),
            Action(34, "preview another taskbar layout", click(1040, 350)),
        ]
    if name == "everyday":
        return 45, [
            Action(1, "close current window", key("alt-f4")),
            Action(4, "open launcher", click(35, 40)),
            Action(6, "focus search", click(450, 30)),
            Action(7, "search Files", text("dolphin")),
            Action(9, "open Files", key("enter")),
            Action(14, "Downloads", click(360, 329)),
            Action(20, "Pictures", click(350, 380)),
            Action(26, "close Files", key("alt-f4")),
            Action(29, "open launcher", click(35, 40)),
            Action(31, "focus search", click(450, 30)),
            Action(32, "search System Settings", text("system settings")),
            Action(34, "open System Settings", key("enter")),
        ]
    if name == "website":
        return 45, [
            Action(1, "close current window", key("alt-f4")),
            Action(2, "open launcher", click(35, 40)),
            Action(4, "focus search", click(450, 30)),
            Action(5, "search Firefox", text("firefox")),
            Action(7, "open Firefox", key("enter")),
            Action(14, "focus address bar", key("ctrl-l")),
            Action(15, "enter Dagric website", text("https://dagric.com")),
            Action(16, "load Dagric website", key("enter")),
            Action(24, "scroll through the live page", key("pgdn")),
            Action(29, "continue down the live page", key("pgdn")),
            Action(34, "return to the page top", key("home")),
            Action(40, "show the next website section", key("pgdn")),
        ]
    if name == "full-walkthrough":
        # One uninterrupted, proof-led journey from first-run setup through the
        # live desktop, Hub, hardware report, files, settings, and dagric.com.
        appearance_actions = (
            [
                Action(5, "preview Dark", click(735, 268)),
                Action(8, "choose the teal accent", click(856, 260)),
            ]
            if visual_profile == "current"
            else []
        )
        # The ISO is still a live evaluation environment, but feature-focused
        # marketing footage must not leave the installer icon visible after
        # first-run and imply that an installed desktop needs reinstalling.
        # Move only the live desktop shortcut into the user's local data area;
        # the installer remains available from the application menu.
        # Keep this command deliberately ASCII/simple. The VNC key injector can
        # mistranslate shell punctuation such as `~`, quotes and redirection.
        hide_installer = "rm -f /home/live/Desktop/calamares-install-debian.desktop"
        post_setup_profile_actions = (
            [
                Action(33, "open the profile terminal", key("ctrl-alt-t")),
                Action(
                    35,
                    f"enter the {visual_profile} visual profile command",
                    text(f"{hide_installer}; dagric-style --apply {visual_profile}"),
                ),
                Action(36, f"apply the {visual_profile} visual profile", key("enter")),
                Action(40, "close the profile terminal", text("exit")),
                Action(41, "return to the personalized desktop", key("enter")),
            ]
            if visual_profile != "current"
            else [
                Action(33, "open the recording-preparation terminal", key("ctrl-alt-t")),
                Action(35, "hide the live installer shortcut for the feature tour", text(hide_installer)),
                Action(36, "apply the recording preparation", key("enter")),
                Action(40, "close the recording-preparation terminal", text("exit")),
                Action(41, "return to the uncluttered desktop", key("enter")),
            ]
        )
        return 198, [
            Action(2, "begin first-run setup", click(1180, 758)),
            *appearance_actions,
            Action(11, "continue to text size", click(1180, 758)),
            Action(15, "continue to taskbar layouts", click(1180, 758)),
            Action(19, "select Unity taskbar", click(1110, 610)),
            Action(22, "continue to optional apps", click(1180, 758)),
            Action(26, "continue to ready screen", click(1180, 758)),
            Action(30, "finish first-run setup", click(1180, 758)),
            # Leave the freshly personalized desktop unobstructed here. Plasma
            # uses single-click activation, so the old "select" clicks opened
            # two windows and left the installer behind every later feature.
            *post_setup_profile_actions,
            Action(44, "open the app launcher", click(35, 40)),
            Action(46, "focus launcher search", click(450, 30)),
            Action(47, "search Dagric Hub", text("dagric hub")),
            Action(49, "open Dagric Hub", key("enter")),
            Action(54, "browse Hub tools", key("down")),
            Action(57, "browse more Hub tools", key("pgdn")),
            Action(61, "return through Hub", key("home")),
            Action(64, "close Dagric Hub", key("alt-f4")),
            Action(65, "open Check This PC", double_click(130, 84)),
            Action(70, "focus the hardware report", click(700, 400)),
            Action(77, "read the next report section", key("pgdn")),
            Action(82, "continue through the report", key("pgdn")),
            Action(87, "return toward the summary", key("pgup")),
            Action(91, "close the hardware report", key("alt-f4")),
            Action(93, "close the report follow-up", key("alt-f4")),
            Action(96, "open the app launcher", click(35, 40)),
            Action(98, "focus launcher search", click(450, 30)),
            Action(99, "search Files", text("dolphin")),
            Action(101, "open Files", key("enter")),
            Action(107, "open Downloads", click(360, 329)),
            Action(111, "open Pictures", click(350, 380)),
            Action(115, "return Home", click(360, 245)),
            Action(118, "close Files", key("alt-f4")),
            Action(120, "open the app launcher", click(35, 40)),
            Action(122, "focus launcher search", click(450, 30)),
            Action(123, "search System Settings", text("system settings")),
            Action(125, "open System Settings", key("enter")),
            Action(131, "open Accessibility", click(300, 502)),
            Action(136, "open Display and Monitor", click(300, 469)),
            Action(141, "open Sound", click(270, 435)),
            Action(146, "open Bluetooth", click(270, 572)),
            Action(151, "open KDE Connect", click(270, 675)),
            Action(156, "close System Settings", key("alt-f4")),
            Action(158, "open the app launcher", click(35, 40)),
            Action(160, "focus launcher search", click(450, 30)),
            Action(161, "search Firefox", text("firefox")),
            Action(163, "open Firefox", key("enter")),
            Action(170, "focus the address bar", key("ctrl-l")),
            Action(171, "enter the Dagric website", text("https://dagric.com")),
            Action(172, "load the Dagric website", key("enter")),
            Action(181, "scroll through the live page", key("pgdn")),
            Action(186, "continue through the live page", key("pgdn")),
            Action(191, "return to the page top", key("home")),
            Action(195, "finish on the download section", key("pgdn")),
        ]
    if name == "long-showcase":
        # A full 15-minute source for long-form explainers. Every section is a
        # real guest interaction and the visual profiles are changed by Dagric
        # itself. Frequent, purposeful motion avoids padding a short source or
        # disguising still frames as a walkthrough.
        # See full-walkthrough: avoid punctuation the VNC key injector maps
        # inconsistently across keyboard layouts.
        hide_installer = "rm -f /home/live/Desktop/calamares-install-debian.desktop"
        actions = [
            Action(2, "begin first-run setup", click(1180, 758)),
            Action(11, "continue to text size", click(1180, 758)),
            Action(15, "continue to taskbar layouts", click(1180, 758)),
            Action(19, "select Unity taskbar", click(1110, 610)),
            Action(22, "continue to optional apps", click(1180, 758)),
            Action(26, "continue to ready screen", click(1180, 758)),
            Action(30, "finish first-run setup", click(1180, 758)),
            Action(31, "close the completed first-run guide", key("alt-f4")),
            Action(33, "open the opening-profile terminal", key("ctrl-alt-t")),
            Action(35, f"prepare the desktop and enter the {visual_profile} opening profile", text(f"{hide_installer}; dagric-style --apply {visual_profile}")),
            Action(36, f"apply the {visual_profile} opening profile", key("enter")),
            Action(40, "close the opening-profile terminal", text("exit")),
            Action(41, "show the personalized desktop", key("enter")),
            *launcher_actions(44, "dagric hub", "Dagric Hub"),
            Action(50, "browse the first Hub tool", key("down")),
            Action(52, "move through Hub categories", key("pgdn")),
            Action(54, "close Dagric Hub", key("alt-f4")),
            *launcher_actions(55, "check this pc", "Check This PC"),
            Action(60, "focus the hardware report", click(700, 400)),
            Action(69, "read the next hardware section", key("pgdn")),
            Action(78, "continue through the hardware report", key("pgdn")),
            Action(87, "return toward the hardware summary", key("pgup")),
            Action(96, "finish the hardware check", key("enter")),
            Action(101, "close the hardware follow-up", key("alt-f4")),
            *launcher_actions(106, "dolphin", "Files"),
            Action(116, "show Downloads", click(360, 329)),
            Action(126, "show Pictures", click(350, 380)),
            Action(136, "return to Home", click(360, 245)),
            Action(146, "switch Files to detail view", key("ctrl-2")),
            Action(154, "switch Files to icon view", key("ctrl-1")),
            Action(162, "close Files", key("alt-f4")),
            *launcher_actions(167, "system settings", "System Settings"),
            Action(178, "open Accessibility", click(300, 502)),
            Action(188, "open Display and Monitor", click(300, 469)),
            Action(198, "open Sound", click(270, 435)),
            Action(208, "open Bluetooth", click(270, 572)),
            Action(218, "open KDE Connect", click(270, 675)),
            Action(226, "close System Settings", key("alt-f4")),
            *profile_actions(230, "night-orbit"),
            Action(246, "open the application launcher", click(35, 40)),
            Action(251, "browse launcher applications", key("down")),
            Action(257, "browse more launcher applications", key("down")),
            Action(263, "close the launcher", key("esc")),
            *launcher_actions(268, "dagric hub", "Dagric Hub"),
            Action(278, "move down the Hub list", key("down")),
            Action(286, "move farther through Hub", key("pgdn")),
            Action(294, "move through another Hub section", key("pgdn")),
            Action(302, "return to the beginning of Hub", key("home")),
            Action(310, "close Dagric Hub", key("alt-f4")),
            Action(315, "open a guest terminal", key("ctrl-alt-t")),
            Action(321, "show the running kernel", text("uname -a")),
            Action(322, "run the kernel query", key("enter")),
            Action(333, "show the Dagric release file", text("cat /etc/os-release")),
            Action(334, "run the release query", key("enter")),
            Action(347, "show disk availability", text("df -h /")),
            Action(348, "run the disk query", key("enter")),
            Action(360, "clear the terminal", text("clear")),
            Action(361, "show the clean terminal", key("enter")),
            Action(370, "close the terminal", text("exit")),
            Action(371, "return to the desktop", key("enter")),
            *launcher_actions(378, "discover", "the software store"),
            Action(392, "focus software-store search", key("ctrl-l")),
            Action(395, "search for creative applications", text("creative")),
            Action(396, "run the software search", key("enter")),
            Action(410, "browse software results", key("pgdn")),
            Action(424, "return to the software-store top", key("home")),
            Action(432, "close the software store", key("alt-f4")),
            *profile_actions(437, "wild-meadow"),
            *launcher_actions(454, "dolphin", "Files on Wild Meadow"),
            Action(466, "show Downloads again", click(360, 329)),
            Action(478, "show Pictures again", click(350, 380)),
            Action(490, "return Home again", click(360, 245)),
            Action(502, "close Files", key("alt-f4")),
            *launcher_actions(508, "system settings", "System Settings"),
            Action(520, "review Accessibility again", click(300, 502)),
            Action(532, "review Display and Monitor again", click(300, 469)),
            Action(544, "review Sound again", click(270, 435)),
            Action(556, "review Bluetooth again", click(270, 572)),
            Action(568, "review KDE Connect again", click(270, 675)),
            Action(578, "close System Settings", key("alt-f4")),
            *launcher_actions(584, "firefox", "Firefox"),
            Action(598, "focus the browser address bar", key("ctrl-l")),
            Action(600, "enter the Dagric website", text("https://dagric.com")),
            Action(601, "load the Dagric website", key("enter")),
            Action(616, "scroll through the website", key("pgdn")),
            Action(630, "continue through the website", key("pgdn")),
            Action(644, "show another website section", key("pgdn")),
            Action(658, "return to the website top", key("home")),
            Action(670, "close Firefox", key("alt-f4")),
            *profile_actions(676, "open-coast"),
            *launcher_actions(694, "dagric hub", "Dagric Hub on Open Coast"),
            Action(706, "browse Hub tools on Open Coast", key("down")),
            Action(718, "move through Hub categories on Open Coast", key("pgdn")),
            Action(730, "move through more Hub categories on Open Coast", key("pgdn")),
            Action(742, "return to the top of Hub", key("home")),
            Action(752, "close Dagric Hub", key("alt-f4")),
            *launcher_actions(758, "check this pc", "Check This PC again"),
            Action(770, "focus the final hardware report", click(700, 400)),
            Action(782, "read the next final report section", key("pgdn")),
            Action(794, "continue through the final report", key("pgdn")),
            Action(806, "return toward the final summary", key("pgup")),
            Action(818, "finish the final hardware report", key("enter")),
            Action(824, "close the final hardware follow-up", key("alt-f4")),
            *launcher_actions(830, "firefox", "Firefox for the closing view"),
            Action(842, "focus the closing address bar", key("ctrl-l")),
            Action(844, "enter the Dagric website for the close", text("https://dagric.com")),
            Action(845, "load the closing website", key("enter")),
            Action(861, "show the product page", key("pgdn")),
            Action(876, "show the download section", key("pgdn")),
            Action(890, "return to the top for the closing frame", key("home")),
        ]
        # Keep the pointer alive between deliberate interactions. Hovering the
        # persistent panel produces subtle native feedback and prevents a long
        # tutorial from looking like a frozen screenshot while the viewer is
        # reading a page. This changes only the real guest UI; it adds no edit-
        # time visual layer and never clicks or changes application focus.
        hover_points = [(35, 40), (35, 105), (35, 170), (35, 235), (35, 300), (35, 365)]
        for index, at in enumerate(range(4, 899, 7)):
            x, y = hover_points[index % len(hover_points)]
            actions.append(Action(float(at), "move the live pointer", move(x, y)))
        return 900, sorted(actions, key=lambda item: item.at)
    raise ValueError(f"Unknown scenario: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=[
            "observe", "test", "fresh-onboarding", "fresh-everyday", "fresh-hardware",
            "settings", "hub", "appearance", "everyday", "website",
            "full-walkthrough", "long-showcase",
        ],
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--server", default="localhost::5914")
    parser.add_argument(
        "--visual-profile",
        choices=sorted(VISUAL_PROFILES),
        default="current",
        help="Dagric style applied inside the VM before frame zero",
    )
    args = parser.parse_args()
    iso_path, iso_hash = latest_vm_iso()
    duration, actions = scenario(args.scenario, args.visual_profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    frame_period = 1 / FPS
    frame_count = int(duration * FPS)
    completed: set[int] = set()
    ffmpeg: subprocess.Popen[bytes] | None = None
    capture_client: object | None = None
    control_client: object | None = None
    stop_refresh = threading.Event()
    refresh_responses = [0]
    refresh_thread: threading.Thread | None = None
    framebuffer_resize_events: list[dict] = []
    transient_missing_frames = 0
    try:
        capture_client = api.connect(args.server, timeout=5)
        wait_for_guest_ready(capture_client)
        control_client = api.connect(args.server, timeout=5)
        if args.scenario not in {"full-walkthrough", "long-showcase"}:
            apply_visual_profile(control_client, args.visual_profile)
        capture_client.refreshScreen(False)
        width, height = capture_client.screen.size
        last_frame = capture_client.screen.copy().convert("RGB")

        def refresh_continuously() -> None:
            while not stop_refresh.is_set():
                try:
                    assert capture_client is not None
                    capture_client.refreshScreen(False)
                    refresh_responses[0] += 1
                except TimeoutError:
                    # The encoder keeps real time even if a full VNC response is
                    # delayed while the guest redraws or changes a wizard page.
                    continue

        refresh_thread = threading.Thread(
            target=refresh_continuously,
            name="Dagric VNC framebuffer update pump",
            daemon=True,
        )
        refresh_thread.start()
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
        started = time.monotonic()
        for frame_number in range(frame_count):
            elapsed = time.monotonic() - started
            for index, item in enumerate(actions):
                if index not in completed and elapsed >= item.at:
                    assert control_client is not None
                    item.run(control_client)
                    completed.add(index)
                    print(f"{elapsed:6.2f}s | {item.label}", flush=True)
            screen = capture_client.screen
            if screen is None:
                # Display-session handoffs can briefly clear vncdotool's current
                # framebuffer. Preserve real time on the fixed encoder canvas
                # with the last live frame until the next VNC update arrives.
                transient_missing_frames += 1
                image = last_frame.copy()
            else:
                image = screen.copy().convert("RGB")
                if image.size != (width, height):
                    event = {
                        "atSeconds": round(elapsed, 3),
                        "sourceWidth": image.width,
                        "sourceHeight": image.height,
                        "encodedWidth": width,
                        "encodedHeight": height,
                    }
                    if not framebuffer_resize_events or (
                        framebuffer_resize_events[-1]["sourceWidth"],
                        framebuffer_resize_events[-1]["sourceHeight"],
                    ) != image.size:
                        framebuffer_resize_events.append(event)
                        print(
                            f"{elapsed:6.2f}s | normalize framebuffer "
                            f"{image.width}x{image.height} to {width}x{height}",
                            flush=True,
                        )
                    image = ImageOps.pad(
                        image,
                        (width, height),
                        method=Image.Resampling.LANCZOS,
                        color=(0, 0, 0),
                        centering=(0.5, 0.5),
                    )
                last_frame = image.copy()
            assert ffmpeg.stdin is not None
            ffmpeg.stdin.write(image.tobytes())
            target = started + (frame_number + 1) * frame_period
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)
    finally:
        # Finalize the MP4 before touching the background Twisted reactor. The
        # API's blocking shutdown/join can stall after the guest changes its
        # display layout during first-run setup, leaving an unplayable MP4 with
        # no moov atom. The reactor thread is daemonized by vncdotool, and the
        # connection context above already closes the VNC client.
        stop_refresh.set()
        if ffmpeg is not None and ffmpeg.stdin:
            ffmpeg.stdin.close()
        return_code = ffmpeg.wait() if ffmpeg is not None else 1
        if refresh_thread is not None:
            refresh_thread.join(timeout=1)
        if control_client is not None:
            control_client.disconnect()
        if capture_client is not None:
            capture_client.disconnect()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with {return_code}")
    receipt = {
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "captureMode": CAPTURE_MODE,
        "scenario": args.scenario,
        "visualProfile": args.visual_profile,
        "visualProfileAppliedInGuest": args.visual_profile != "current",
        "visualProfileApplicationTiming": (
            "during-continuous-capture-after-first-run"
            if args.visual_profile != "current" and args.scenario in {"full-walkthrough", "long-showcase"}
            else "before-frame-zero"
            if args.visual_profile != "current"
            else "unchanged"
        ),
        "visualProfileSequence": (
            [
                {"profile": args.visual_profile, "atSeconds": 36},
                {"profile": "night-orbit", "atSeconds": 230},
                {"profile": "wild-meadow", "atSeconds": 437},
                {"profile": "open-coast", "atSeconds": 676},
            ]
            if args.scenario == "long-showcase"
            else [{"profile": args.visual_profile, "atSeconds": 0}]
        ),
        "output": str(args.output.resolve()),
        "durationSeconds": duration,
        "targetFramesPerSecond": FPS,
        "encodedFrames": frame_count,
        "continuousFrameEncoding": True,
        "asynchronousFramebufferRefresh": True,
        "framebufferRefreshResponses": refresh_responses[0],
        "framebufferResizeEvents": framebuffer_resize_events,
        "framebufferResizeNormalization": "aspect-preserving-pad-to-initial-canvas",
        "transientMissingFramebufferFrames": transient_missing_frames,
        "freshFramebufferRequestPerEncodedFrame": False,
        "snapshotInputs": [],
        "source": "Dagric QEMU live-ISO VNC framebuffer",
        "iso": str(iso_path.resolve()),
        "isoSha256": iso_hash,
        "audioCaptured": False,
        "sha256": sha256(args.output),
    }
    receipt_path = args.output.with_suffix(".capture.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {args.output} ({duration}s, {FPS} fps)", flush=True)
    print(f"Wrote continuous-capture receipt {receipt_path}", flush=True)
    if not stop_vnc_reactor():
        print("VNC shutdown timed out after finalized output; exiting cleanly.", flush=True)
        # All deliverables are already closed and hashed. os._exit prevents a
        # stuck third-party reactor thread from holding the recorder process.
        os._exit(0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
