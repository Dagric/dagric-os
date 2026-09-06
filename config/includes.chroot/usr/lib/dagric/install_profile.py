#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Allowlisted installer personalization; no passwords, shell or disk operations."""
import configparser
import io
import itertools
import json
import os
from pathlib import Path
import re
import stat

CHOICES = {
    "mode": ("dark", "light"),
    "layout": ("classic", "eleven"),
    "icons": ("modern", "classic", "old-school"),
    "text": ("normal", "bigger", "biggest"),
    "wallpaper": ("obsidian", "arctic", "aurora"),
}
LABELS = {
    "mode": ("Dark", "Light"), "layout": ("Familiar", "Centered"),
    "icons": ("Modern icons", "Classic icons", "Old school icons"),
    "text": ("100% text", "125% text", "150% text"),
    "wallpaper": ("Obsidian", "Arctic", "Aurora"),
}
DEFAULT = "Dark · Centered · Modern icons · 100% text · Obsidian"
WALLPAPERS = {"obsidian": "DagricObsidianPulse", "arctic": "DagricArcticClean", "aurora": "DagricAurora"}
ICONS = {"modern": "DagricModern", "classic": "DagricClassic", "old-school": "DagricOldSchool"}
GS_KEY = "packagechooser_dagricdesktop"


def profiles():
    return [" · ".join(parts) for parts in itertools.product(*LABELS.values())]


def parse_profile(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError("Missing desktop choices; return to Your desktop and choose a profile.")
    parts = value.split(" · ")
    if len(parts) != len(CHOICES):
        raise ValueError("Incomplete desktop choices.")
    result = dict(zip(CHOICES, parts))
    if any(result[key] not in allowed for key, allowed in LABELS.items()):
        raise ValueError("Unsupported desktop choice.")
    return {key: CHOICES[key][LABELS[key].index(label)] for key, label in result.items()}


def directory(parent, name, uid=None, gid=None):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name) or name in (".", ".."):
        raise ValueError("Unsafe directory name")
    created = False
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)
        created = True
    except FileExistsError:
        pass
    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    if created and uid is not None:
        os.fchown(child, uid, gid)
    if uid is not None and (os.fstat(child).st_uid, os.fstat(child).st_gid) != (uid, gid):
        os.close(child)
        raise ValueError("Existing account configuration has unexpected ownership")
    return child


def write_private(parent, name, content, uid, gid):
    """Atomic replacement through an already validated directory descriptor."""
    temp = name + ".dagric-new"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    try:
        os.fchown(fd, uid, gid)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, name, src_dir_fd=parent, dst_dir_fd=parent)
    finally:
        try:
            os.unlink(temp, dir_fd=parent)
        except FileNotFoundError:
            pass


def read_config(parent, name):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        return config
    with os.fdopen(fd, encoding="utf-8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Configuration is not a regular file")
        config.read_file(stream)
    return config


def apply_to_target(root, username, value):
    prefs = parse_profile(value)
    root = Path(root)
    if not root.is_absolute() or root == Path("/") or root.resolve() != root:
        raise ValueError("Refusing an unsafe installation target")
    if not isinstance(username, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username):
        raise ValueError("Invalid installed account name")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened = [root_fd]
    try:
        etc = directory(root_fd, "etc"); opened.append(etc)
        fd = os.open("passwd", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=etc)
        with os.fdopen(fd, encoding="utf-8") as stream:
            records = [line.strip().split(":") for line in stream if line.split(":", 1)[0] == username]
        if len(records) != 1 or len(records[0]) != 7:
            raise ValueError("The installer has not created the requested account")
        record = records[0]
        uid, gid = int(record[2]), int(record[3])
        if uid < 1000 or gid < 1000 or record[5] != "/home/" + username:
            raise ValueError("Unsupported account ownership or home path")
        home = directory(root_fd, "home"); opened.append(home)
        user = directory(home, username, uid, gid); opened.append(user)
        conf = directory(user, ".config", uid, gid); opened.append(conf)
        dagric = directory(conf, "dagric", uid, gid); opened.append(dagric)
        cfg = read_config(conf, "kdeglobals")
        scheme = "DagricLight" if prefs["mode"] == "light" else "DagricDark"
        scheme_path = root / "usr/share/color-schemes" / (scheme + ".colors")
        palette = configparser.ConfigParser(interpolation=None, strict=False)
        palette.optionxform = str
        with scheme_path.open(encoding="utf-8") as stream:
            palette.read_file(stream)
        for section in palette.sections():
            if section.startswith("Colors:") or section in ("ColorEffects:Disabled", "ColorEffects:Inactive"):
                cfg[section] = dict(palette[section])
        for section in ("General", "Icons", "KDE"):
            if not cfg.has_section(section): cfg.add_section(section)
        cfg["General"]["ColorScheme"] = scheme
        cfg["Icons"]["Theme"] = ICONS[prefs["icons"]]
        cfg["KDE"]["widgetStyle"] = "Breeze"
        point = {"normal": 10, "bigger": 12.5, "biggest": 15}[prefs["text"]]
        for key in ("font", "menuFont", "toolBarFont", "smallestReadableFont"):
            cfg["General"][key] = f"Noto Sans,{point},-1,5,50,0,0,0,0,0"
        cfg["General"]["fixed"] = f"Noto Sans Mono,{point},-1,5,50,0,0,0,0,0"
        output = io.StringIO(); cfg.write(output, space_around_delimiters=False)
        write_private(conf, "kdeglobals", output.getvalue(), uid, gid)
        layout = "[Desktop]\nLayout=" + prefs["layout"] + "\nWallpaper=" + WALLPAPERS[prefs["wallpaper"]] + "\n"
        write_private(dagric, "installed-desktoprc", layout, uid, gid)
        write_private(dagric, "installed-personalization.json", json.dumps({"schema": 1, "profile": value, "choices": prefs}, indent=2) + "\n", uid, gid)
        # Written last, only after every preference is installed. The owner can
        # reopen personalization later; first login does not repeat this wizard.
        write_private(dagric, "firstrun-done", "# Personalization completed inside the installer.\n", uid, gid)
    finally:
        for fd in reversed(opened): os.close(fd)


def chooser_config():
    return {"mode": "required", "method": "legacy", "packageChoice": DEFAULT,
            "qmlSearch": "branding", "qmlFilename": "dagricdesktop",
            "labels": {"step": "Your desktop"}}
