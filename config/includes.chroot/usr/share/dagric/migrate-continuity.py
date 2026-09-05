#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventory and opt-in continuity transfer for Dagric migration.

This utility stays read-only on Windows data and only copies explicit categories.
It produces:

* app inventory + replacement hints
* game handoff metadata (Steam libraries and allowlisted user-created content)
* developer and creative profile copies
* network/peripherals/cloud notes
* optional Windows companion metadata when supplied
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import stat
import sys

OUT_JSON = "Dagric-Continuity-Report.json"
OUT_HTML = "Dagric-Continuity-Report.html"
MAX_FILES = 160000

# Steam's userdata and config trees mix user-created files with account state,
# web caches, login/session material, and machine-specific configuration.  They
# must never be copied wholesale.  Gaming migration starts only from the narrow
# leaf directories discovered below, then applies these file-level filters as a
# second line of defence.
STEAM_SENSITIVE_MARKERS = (
    "auth",
    "cookie",
    "credential",
    "htmlcache",
    "login",
    "logon",
    "machineid",
    "machine_id",
    "oauth",
    "passwd",
    "password",
    "session",
    "ssfn",
    "token",
    "webcache",
)
SECRET_FILE_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
SCREENSHOT_SUFFIXES = (".bmp", ".jpeg", ".jpg", ".png", ".webp")
CONTROLLER_LAYOUT_SUFFIXES = (".json", ".vdf")

APP_REPLACEMENTS = {
    "chrome": {
        "name": "Firefox",
        "source": "Debian",
        "source_key": "debian",
        "install_hint": "sudo apt install firefox",
        "next_step": "Use Firefox startup/settings from continuity checklist.",
    },
    "edge": {
        "name": "Firefox",
        "source": "Debian",
        "source_key": "debian",
        "install_hint": "sudo apt install firefox",
        "next_step": "Use browser metadata in the continuity checklist.",
    },
    "office": {
        "name": "LibreOffice",
        "source": "Debian",
        "source_key": "debian",
        "install_hint": "sudo apt install libreoffice",
        "next_step": "Use Calc/Writer/Impress as replacements.",
    },
    "photoshop": {
        "name": "Krita",
        "source": "Debian",
        "source_key": "debian",
        "install_hint": "sudo apt install krita",
        "next_step": "Import templates if present.",
    },
    "discord": {
        "name": "Discord",
        "source": "Flathub",
        "source_key": "flathub",
        "install_hint": "flatpak install flathub com.discordapp.Discord",
        "next_step": "Re-login with existing account.",
    },
    "steam": {
        "name": "Steam",
        "source": "Dagric helper",
        "source_key": "dagric",
        "install_hint": "dagric-get-steam",
        "next_step": "Review the third-party notice, install, sign in, then add an existing library if needed.",
    },
    "visual studio code": {
        "name": "VSCodium",
        "source": "Flathub",
        "source_key": "flathub",
        "install_hint": "flatpak install flathub com.vscodium.codium",
        "next_step": "Restore extension list from copied profile data.",
    },
    "obs": {
        "name": "OBS Studio",
        "source": "Debian",
        "source_key": "debian",
        "install_hint": "sudo apt install obs-studio",
        "next_step": "Copy copied scenes/config folders over.",
    },
}


def path(profile, relative):
    return os.path.join(profile, *relative.split("/"))


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _read_companion(path):
    if not path:
        return {}
    return _read_json(path)


def _iter_shortest_dirs(root, limit=128):
    try:
        return sorted(os.listdir(root))[:limit]
    except OSError:
        return []


def _pick_plan(name):
    key = (name or "").casefold()
    for needle, plan in APP_REPLACEMENTS.items():
        if needle in key:
            return plan
    return {
        "name": "No automatic replacement",
        "source": "Dagric",
        "source_key": "dagric",
        "install_hint": "",
        "next_step": "Search the Software Store or keep app manually as needed.",
    }


def app_inventory(profile):
    roots = [
        ("Program Files", os.path.dirname(os.path.dirname(profile)) + "/Program Files"),
        ("Program Files (x86)", os.path.dirname(os.path.dirname(profile)) + "/Program Files (x86)"),
        ("User Start Menu", path(profile, "AppData/Roaming/Microsoft/Windows/Start Menu/Programs")),
    ]
    items = []
    for source, root in roots:
        if not os.path.isdir(root):
            continue
        for name in _iter_shortest_dirs(root, 800):
            if name:
                items.append({"name": name, "source": source, "dagric_plan": _pick_plan(name)})

    for base, _, files in os.walk(path(profile, "AppData/Roaming/Microsoft/Windows/Start Menu/Programs"), topdown=True):
        files = files[:400]
        for f in files:
            if not f.lower().endswith((".lnk", ".url")):
                continue
            n = os.path.splitext(f)[0]
            items.append({"name": n, "source": "User Start Menu", "dagric_plan": _pick_plan(n)})
        dirs = []
        break  # keep runtime cheap: top-level links are enough

    return items[:3000]


def _parse_steam_vdf(path_text):
    out = []
    for m in re.finditer(r'"path"\s+"([^"]+)"', path_text):
        p = m.group(1).replace("\\\\", "\\")
        if p not in out:
            out.append(p)
    return out


def _parse_steam_manifest(manifest):
    game = {"name": "Unknown game", "appid": "", "install_dir": ""}
    try:
        with open(manifest, encoding="utf-8", errors="replace") as fh:
            text = fh.read(60000)
    except OSError:
        return game
    for key in ("name", "appid", "installdir"):
        m = re.search(rf'"{key}"\s+"([^"]+)"', text)
        if m:
            game["appid" if key == "appid" else key if key != "installdir" else "install_dir"] = m.group(1)
    return game


def _within_root(candidate, root):
    """True when candidate resolves inside root (never trust a library VDF path)."""
    try:
        resolved_candidate = os.path.normcase(os.path.realpath(candidate))
        resolved_root = os.path.normcase(os.path.realpath(root))
        return os.path.commonpath((resolved_candidate, resolved_root)) == resolved_root
    except (OSError, ValueError):
        return False


def _steam_roots(profile):
    """Return existing Steam installation roots visible on the Windows volume."""
    volume = os.path.dirname(os.path.dirname(profile))
    candidates = [
        path(profile, "AppData/Local/Steam"),
        os.path.join(volume, "Program Files (x86)", "Steam"),
        os.path.join(volume, "Program Files", "Steam"),
    ]
    roots = []
    for candidate in candidates:
        if (
            os.path.isdir(candidate)
            and not os.path.islink(candidate)
            and _within_root(candidate, volume)
            and candidate not in roots
        ):
            roots.append(candidate)
    return roots


def _steam_libraries(profile):
    roots = _steam_roots(profile)
    volume = os.path.dirname(os.path.dirname(profile))
    libs = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        lib_file = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(lib_file) and not os.path.islink(lib_file):
            try:
                with open(lib_file, "r", encoding="utf-8", errors="replace") as fh:
                    candidates = _parse_steam_vdf(fh.read(200000))
                for candidate in candidates:
                    if (
                        os.path.isdir(candidate)
                        and not os.path.islink(candidate)
                        and _within_root(candidate, volume)
                        and candidate not in libs
                    ):
                        libs.append(candidate)
            except OSError:
                pass
        if root not in libs:
            libs.append(root)
    return libs


def _numeric_directories(root):
    """List numeric Steam account/app directories without walking arbitrary data."""
    if os.path.islink(root):
        return []
    result = []
    for name in _iter_shortest_dirs(root, 10000):
        candidate = os.path.join(root, name)
        if name.isdecimal() and os.path.isdir(candidate) and not os.path.islink(candidate):
            result.append(candidate)
    return result


def _steam_user_content(profile, libraries):
    """Discover only well-defined leaves that normally hold user-created data.

    In particular, this deliberately does not return Steam ``config``, a whole
    ``userdata`` account directory, ``appcache``, ``htmlcache``, or any root
    containing login/session state.
    """
    volume = os.path.dirname(os.path.dirname(profile))
    roots = []
    for candidate in _steam_roots(profile) + list(libraries):
        if (
            os.path.isdir(candidate)
            and not os.path.islink(candidate)
            and _within_root(candidate, volume)
            and candidate not in roots
        ):
            roots.append(candidate)

    cloud_saves = []
    screenshots = []
    controller_layouts = []

    for root in roots:
        userdata = os.path.join(root, "userdata")
        for account in _numeric_directories(userdata):
            # Per-game Steam Cloud payloads are stored below <appid>/remote.
            # App 760 is Steam's screenshot area and is handled separately.
            for app_dir in _numeric_directories(account):
                if os.path.basename(app_dir) == "760":
                    continue
                remote = os.path.join(app_dir, "remote")
                if os.path.isdir(remote) and not os.path.islink(remote) and remote not in cloud_saves:
                    cloud_saves.append(remote)

            screenshot_root = os.path.join(account, "760", "remote")
            for app_dir in _numeric_directories(screenshot_root):
                folder = os.path.join(app_dir, "screenshots")
                if os.path.isdir(folder) and not os.path.islink(folder) and folder not in screenshots:
                    screenshots.append(folder)

        # Steam's legacy personal controller-layout export uses this isolated
        # tree.  Only per-app leaf folders are returned; copy_source further
        # permits only .vdf/.json layout files.
        layout_root = os.path.join(root, "steamapps", "common", "Steam Controller Configs")
        for account in _numeric_directories(layout_root):
            config_root = os.path.join(account, "config")
            for app_dir in _numeric_directories(config_root):
                if app_dir not in controller_layouts:
                    controller_layouts.append(app_dir)

    general_saves = []
    for candidate in (path(profile, "Saved Games"), path(profile, "Documents/My Games")):
        if os.path.isdir(candidate) and candidate not in general_saves:
            general_saves.append(candidate)

    return {
        "general_save_locations": general_saves,
        "steam_cloud_save_locations": cloud_saves,
        "screenshot_locations": screenshots,
        "controller_layout_locations": controller_layouts,
    }


def steam_inventory(profile):
    libs = _steam_libraries(profile)
    games = []
    for lib in libs:
        steamapps = os.path.join(lib, "steamapps")
        if not os.path.isdir(steamapps):
            continue
        for f in sorted(os.listdir(steamapps))[:10000]:
            if f.startswith("appmanifest_") and f.endswith(".acf"):
                manifest = os.path.join(steamapps, f)
                if not os.path.isfile(manifest) or os.path.islink(manifest):
                    continue
                g = _parse_steam_manifest(manifest)
                g["steam_library"] = lib
                games.append(g)
    user_content = _steam_user_content(profile, libs)
    return {
        "libraries": libs,
        "games": games[:500],
        "save_folders": user_content["general_save_locations"],
        "steam_cloud_save_locations": user_content["steam_cloud_save_locations"],
        "screenshot_locations": user_content["screenshot_locations"],
        "controller_layout_locations": user_content["controller_layout_locations"],
    }


def _steam_appid_from_leaf(folder):
    parent = os.path.dirname(folder) if os.path.basename(folder).casefold() in {"remote", "screenshots"} else folder
    if os.path.basename(parent).casefold() == "screenshots":
        parent = os.path.dirname(parent)
    appid = os.path.basename(parent)
    return appid if appid.isdecimal() else "unknown"


def source_groups(choice, profile, ask_ssh=False):
    if choice == "gaming":
        data = steam_inventory(profile)
        rows = [
            ("Windows Saved Games" if os.path.basename(p).casefold() == "saved games" else "Documents My Games", p)
            for p in data["save_folders"]
        ]
        rows.extend([
            ("Steam cloud save app %s set %d" % (_steam_appid_from_leaf(p), index), p)
            for index, p in enumerate(data["steam_cloud_save_locations"], 1)
        ])
        rows.extend([
            ("Steam screenshots app %s set %d" % (_steam_appid_from_leaf(p), index), p)
            for index, p in enumerate(data["screenshot_locations"], 1)
        ])
        rows.extend([
            ("Controller layouts app %s set %d" % (_steam_appid_from_leaf(p), index), p)
            for index, p in enumerate(data["controller_layout_locations"], 1)
        ])
        return rows
    if choice == "developer":
        rows = [
            ("VS Code settings", path(profile, "AppData/Roaming/Code/User")),
            ("Git config", path(profile, ".gitconfig")),
        ]
        if ask_ssh:
            rows.append(("SSH config (no private keys)", path(profile, ".ssh")))
        return rows
    if choice == "creative":
        return [
            ("OBS configuration", path(profile, "AppData/Roaming/obs-studio")),
            ("Blender configuration", path(profile, "AppData/Roaming/Blender Foundation")),
            ("Krita configuration", path(profile, "AppData/Roaming/krita")),
            ("LibreOffice templates", path(profile, "AppData/Roaming/LibreOffice/4/user/template")),
            ("Audacity settings", path(profile, "AppData/Roaming/audacity")),
        ]
    if choice == "mail":
        return [("Thunderbird profile", path(profile, "AppData/Roaming/Thunderbird"))]
    if choice == "fonts":
        return [("Personal fonts", path(profile, "AppData/Local/Microsoft/Windows/Fonts"))]
    return []


def excluded(choice, source, rel):
    low = rel.replace("\\", "/").casefold()
    if choice == "gaming":
        if any(marker in low for marker in STEAM_SENSITIVE_MARKERS):
            return True
        if low.endswith(SECRET_FILE_SUFFIXES):
            return True
    if choice == "developer" and "ssh" in source.casefold() and not os.path.basename(low) in {"config", "known_hosts"}:
        return True
    if choice in {"developer", "creative"} and any(x in low for x in ("password", "token", "credential", "cookie")):
        return True
    if choice == "mail" and "cookies" in low:
        return True
    return False


def allowed(choice, label, rel):
    """File allowlist applied after the source-directory allowlist."""
    if excluded(choice, label, rel):
        return False
    if choice != "gaming":
        return True
    low_label = label.casefold()
    low_rel = rel.casefold()
    if low_label.startswith("steam screenshots app "):
        return low_rel.endswith(SCREENSHOT_SUFFIXES)
    if low_label.startswith("controller layouts app "):
        return low_rel.endswith(CONTROLLER_LAYOUT_SUFFIXES)
    return low_label.startswith(("windows saved games", "documents my games", "steam cloud save app "))


def _private_makedirs(directory, private_root=None):
    """Create a destination path and make every directory below its root private."""
    os.makedirs(directory, mode=stat.S_IRWXU, exist_ok=True)
    root = os.path.abspath(private_root or directory)
    current = os.path.abspath(directory)
    try:
        if os.path.commonpath((root, current)) != root:
            raise ValueError("private destination escaped its root")
    except ValueError:
        raise ValueError("private destination escaped its root")
    while True:
        try:
            os.chmod(current, stat.S_IRWXU)
        except OSError:
            # Some destination filesystems do not implement POSIX modes. Files
            # are still set owner-only below wherever the filesystem supports it.
            pass
        if current == root:
            break
        current = os.path.dirname(current)


def copy_source(choice, label, src, destination):
    result = {
        "category": choice,
        "label": label,
        "source": src,
        "destination": destination,
        "copied_files": 0,
        "copied_bytes": 0,
        "filtered_paths": 0,
        "errors": [],
    }
    if not os.path.exists(src):
        result["status"] = "not present"
        return result
    if os.path.islink(src):
        result["filtered_paths"] = 1
        result["status"] = "filtered"
        return result
    if os.path.isfile(src):
        if os.path.islink(src) or not allowed(choice, label, os.path.basename(src)):
            result["filtered_paths"] = 1
            result["status"] = "filtered"
            return result
        _private_makedirs(destination, destination)
        target = os.path.join(destination, os.path.basename(src))
        if not os.path.exists(target):
            try:
                shutil.copy2(src, target)
                os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
                result["copied_files"] = 1
                result["copied_bytes"] = os.path.getsize(target)
            except OSError as exc:
                result["errors"].append(str(exc))
        result["status"] = "copied"
        return result

    for base, dirs, files in os.walk(src):
        kept_dirs = []
        for name in dirs[:150]:
            candidate = os.path.join(base, name)
            rel_dir = os.path.relpath(candidate, src)
            if os.path.islink(candidate) or excluded(choice, label, rel_dir):
                result["filtered_paths"] += 1
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in files[:3000]:
            source_file = os.path.join(base, name)
            rel = os.path.relpath(source_file, src)
            if os.path.islink(source_file) or not allowed(choice, label, rel):
                result["filtered_paths"] += 1
                continue
            if result["copied_files"] >= MAX_FILES:
                result["errors"].append("limit reached; rerun with narrower selection")
                result["status"] = "partial"
                return result
            target = os.path.join(destination, rel)
            try:
                _private_makedirs(os.path.dirname(target), destination)
                if not os.path.exists(target):
                    shutil.copy2(source_file, target)
                    os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
                    result["copied_files"] += 1
                    result["copied_bytes"] += os.path.getsize(target)
            except OSError as exc:
                result["errors"].append("%s: %s" % (rel, exc))

    if result["errors"]:
        result["status"] = "partial"
    elif result["copied_files"] == 0 and result["filtered_paths"]:
        result["status"] = "filtered"
    else:
        result["status"] = "copied"
    return result


def report_html(report):
    def entries(rows, render):
        if not rows:
            return "<li>None found</li>"
        return "".join("<li>%s</li>" % render(r) for r in rows)

    app_rows = entries(
        report.get("apps", []),
        lambda r: "%s — %s (%s)" % (html.escape(r.get("name", "")),
                                    html.escape((r.get("dagric_plan") or {}).get("name", "")),
                                    html.escape((r.get("dagric_plan") or {}).get("source", ""))),
    )

    game_rows = entries(
        report.get("gaming", {}).get("steam_games", []),
        lambda r: "%s (appid %s) from %s" % (
            html.escape(r.get("name", "")),
            html.escape(r.get("appid", "")),
            html.escape(r.get("steam_library", "")),
        ),
    )

    copy_rows = []
    for key in ["gaming", "developer", "creative", "mail", "fonts"]:
        for item in report.get("copies", {}).get(key, []):
            copy_rows.append(
                "%s: %s (%d copied; %d filtered)"
                % (
                    item.get("label"),
                    item.get("status"),
                    item.get("copied_files", 0),
                    item.get("filtered_paths", 0),
                )
            )

    copy_rows_html = entries(copy_rows, lambda r: html.escape(r))

    network_rows = entries(report.get("network", []), lambda r: html.escape(str(r)))
    peripheral_rows = entries(report.get("peripherals", []), lambda r: html.escape(str(r)))
    cloud_rows = entries(report.get("cloud", []), lambda r: html.escape(str(r)))
    privacy = html.escape(report.get("privacy", ""))

    return """<!doctype html><meta charset=utf-8><title>Dagric Continuity Report</title><style>
body{max-width:980px;margin:3rem auto;padding:0 1rem;font:16px system-ui;color:#e8edf5;background:#121821}
section{background:#1c2633;padding:1rem 1.25rem;margin:1rem 0;border-radius:12px}
li{margin:.45rem 0;overflow-wrap:anywhere}
</style><h1>Dagric Continuity Report</h1>
<section><h2>Privacy boundary</h2><p>%s</p></section>
<section><h2>Apps & recommendations</h2><ul>%s</ul></section>
<section><h2>Steam / game handoff</h2><ul>%s</ul></section>
<section><h2>Network</h2><ul>%s</ul></section>
<section><h2>Peripherals</h2><ul>%s</ul></section>
<section><h2>Cloud notes</h2><ul>%s</ul></section>
<section><h2>Copy summary</h2><ul>%s</ul></section>
""" % (privacy, app_rows, game_rows, network_rows, peripheral_rows, cloud_rows, copy_rows_html)


def _network_notes(companion):
    net = companion.get("network") or {}
    peripherals = companion.get("peripherals") or {}
    out = []
    if net.get("wifi_ssids"):
        out.append({"wifi": net.get("wifi_ssids")})
    if net.get("adapters"):
        out.append({"adapters": net.get("adapters")})
    if peripherals.get("printers"):
        out.append({"printers": peripherals.get("printers")})
    if peripherals.get("bluetooth"):
        out.append({"bluetooth_devices": peripherals.get("bluetooth")})
    if not out:
        out.append({"note": "No companion metadata detected; optional Windows companion can enrich this section."})
    return out


def _cloud_notes(profile, companion):
    notes = [{"title": "OneDrive placeholder folders are not automatically downloaded."}]
    od_root = os.path.join(profile, "OneDrive")
    if os.path.isdir(od_root):
        notes.append({"one_drive_root": od_root})
    if companion:
        cloud = companion.get("cloud") or {}
        if cloud.get("onedrive_roots"):
            notes.append({"companion_onedrive_roots": cloud.get("onedrive_roots")})
        if cloud.get("note"):
            notes.append({"note": cloud.get("note")})
    return notes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("windows_profile")
    parser.add_argument("output_dir")
    parser.add_argument("--copy", action="append", choices=("gaming", "developer", "creative", "mail", "fonts"), default=[])
    parser.add_argument("--ssh-config", action="store_true")
    parser.add_argument("--companion", default="")
    args = parser.parse_args()

    profile = args.windows_profile
    outdir = args.output_dir
    companion = _read_companion(args.companion)

    copies = {"gaming": [], "developer": [], "creative": [], "mail": [], "fonts": []}
    for choice in args.copy:
        for label, src in source_groups(choice, profile, args.ssh_config):
            dest = os.path.join(outdir, "Dagric-Migration", choice.title(), label.replace(" ", "_"))
            copies[choice].append(copy_source(choice, label, src, dest))

    gaming_selected = "gaming" in args.copy
    steam = steam_inventory(profile) if gaming_selected else {
        "libraries": [],
        "games": [],
        "save_folders": [],
        "steam_cloud_save_locations": [],
        "screenshot_locations": [],
        "controller_layout_locations": [],
    }
    report = {
        "format": "dagric-continuity-report",
        "version": 3,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "windows_user": os.path.basename(profile),
        "privacy": (
            "Opt-in copies use narrow source allowlists and skip paths named like logins, sessions, "
            "cookies, credentials, tokens, web caches, authentication material, or private keys. "
            "The filter is conservative and best effort; review migrated files before sharing them."
        ),
        "apps": app_inventory(profile),
        "gaming": {
            "selected": gaming_selected,
            "steam_libraries": steam["libraries"],
            "steam_games": steam["games"],
            "steam_cloud_save_locations": steam["steam_cloud_save_locations"],
            "screenshot_locations": steam["screenshot_locations"],
            "controller_layout_locations": steam["controller_layout_locations"],
            "save_folders": steam["save_folders"],
        },
        "developer": {"copies": copies.get("developer", [])},
        "creative": {"copies": copies.get("creative", [])},
        "mail": {"copies": copies.get("mail", [])},
        "fonts": {"copies": copies.get("fonts", [])},
        "copies": copies,
        "network": _network_notes(companion),
        "peripherals": _network_notes(companion),
        "cloud": _cloud_notes(profile, companion),
    }
    if companion:
        report["companion"] = {
            "path": os.path.abspath(args.companion),
            "format": companion.get("format", "dagric-windows-companion"),
        }

    os.makedirs(outdir, exist_ok=True)
    output_json = os.path.join(outdir, OUT_JSON)
    output_html = os.path.join(outdir, OUT_HTML)
    with os.fdopen(os.open(output_json, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with os.fdopen(os.open(output_html, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR), "w", encoding="utf-8") as fh:
        fh.write(report_html(report))

    print("CONTINUITY_REPORT=%s" % output_html)
    print("CONTINUITY_COPIES=%d" % sum(x["copied_files"] for group in copies.values() for x in group))
    print("CONTINUITY_ERRORS=%d" % sum(len(x["errors"]) for group in copies.values() for x in group))
    return 0


if __name__ == "__main__":
    sys.exit(main())
