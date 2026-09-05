#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build Dagric's local, non-secret Windows Migration State Pack.

This is deliberately a *description* of the old desktop, not a copy of its
private databases.  It reads a mounted Windows user profile and writes one
0600 JSON file in the new user's home.  It does not execute .lnk files, parse
credential stores, copy cookies, or write to the Windows volume.
"""
import datetime as dt
import html
import json
import os
import re
import stat
import sys

OUT_NAME = "Dagric-Migration-State-Pack.json"
MAX_SHORTCUTS = 120
MAX_RECENT = 100
MAX_SIGNALS = 80
SHELL_FOLDERS = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
                 "Saved Games", "Favorites", "Links", "Contacts", "Searches")
URL_RE = re.compile(r"https?://[^\x00\s\"<>]{4,500}", re.I)
# Do not let the concatenated ASCII/UTF-16 decoding pass bleed across a line
# boundary; Jump List blobs often put independent strings side by side.
PATH_RE = re.compile(r"(?:[A-Za-z]:\\|\\\\)[^\x00\r\n<>|?*]{3,400}")


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _mtime(path):
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc).isoformat()
    except OSError:
        return ""


def _strings(path, limit=32768):
    """Return URLs and Windows-looking paths from a binary artifact.

    The LNK / Jump List formats are version-specific binary structures.  The
    human-facing destinations remain stored as UTF-16 or ASCII strings, so a
    bounded string pass is more reliable than pretending this is a complete
    parser.  The cap keeps a malformed artifact from consuming memory.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read(limit)
    except OSError:
        return []
    text = raw.decode("utf-16le", "ignore") + "\n" + raw.decode("utf-8", "ignore")
    found = []
    for rx in (URL_RE, PATH_RE):
        found.extend(m.group(0).strip() for m in rx.finditer(text))
    out, seen = [], set()
    for value in found:
        if value and value not in seen:
            seen.add(value)
            out.append(value[:500])
    return out[:12]


def _relative(root, path):
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return os.path.basename(path)


def _files_under(root, suffixes, maximum):
    rows = []
    if not os.path.isdir(root):
        return rows
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(dirs)[:100]
        for name in sorted(files):
            if not name.lower().endswith(suffixes):
                continue
            path = os.path.join(base, name)
            rows.append((path, _relative(root, path)))
            if len(rows) >= maximum:
                return rows
    return rows


def _shortcut_manifest(profile):
    users_root = os.path.dirname(os.path.normpath(profile))
    windows_root = os.path.dirname(users_root)
    roots = [
        ("Desktop", os.path.join(profile, "Desktop")),
        ("Start menu", os.path.join(profile, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")),
        # These two locations contain shortcuts installed for every Windows
        # account, rather than only the account being migrated.
        ("Shared desktop", os.path.join(users_root, "Public", "Desktop")),
        ("Shared Start menu", os.path.join(windows_root, "ProgramData", "Microsoft", "Windows", "Start Menu", "Programs")),
    ]
    out = []
    for source, root in roots:
        for path, rel in _files_under(root, (".lnk", ".url", ".website"), MAX_SHORTCUTS - len(out)):
            out.append({
                "source": source,
                "name": os.path.splitext(os.path.basename(path))[0],
                "kind": os.path.splitext(path)[1].lower().lstrip("."),
                "relative_path": rel,
                "modified_utc": _mtime(path),
                "signals": _strings(path),
            })
            if len(out) >= MAX_SHORTCUTS:
                return out
    return out


def _recent_artifacts(profile):
    root = os.path.join(profile, "AppData", "Roaming", "Microsoft", "Windows", "Recent")
    links = []
    for path, rel in _files_under(root, (".lnk", ".url"), MAX_RECENT):
        links.append({"name": os.path.splitext(os.path.basename(path))[0], "relative_path": rel,
                      "modified_utc": _mtime(path), "signals": _strings(path)})
    destinations = []
    for sub in ("AutomaticDestinations", "CustomDestinations"):
        subroot = os.path.join(root, sub)
        for path, rel in _files_under(subroot, (".automaticdestinations-ms", ".customdestinations-ms"), MAX_SIGNALS - len(destinations)):
            destinations.append({"kind": sub, "relative_path": rel, "modified_utc": _mtime(path),
                                 "signals": _strings(path)})
            if len(destinations) >= MAX_SIGNALS:
                break
    return {"recent_links": links, "jump_list_signals": destinations}


def _shell_folders(profile):
    out = []
    for name in SHELL_FOLDERS:
        path = os.path.join(profile, name)
        if os.path.isdir(path):
            out.append({"name": name, "present": True, "items": _count_items(path)})
    return out


def _count_items(path):
    try:
        return len(os.listdir(path))
    except OSError:
        return None


def main():
    if len(sys.argv) != 4:
        print("usage: migrate-state-pack.py <windows-profile> <browser-context-json> <output-dir>", file=sys.stderr)
        return 2
    profile, browser_context, outdir = sys.argv[1:]
    browser = {}
    try:
        with open(browser_context, encoding="utf-8") as fh:
            browser = json.load(fh)
    except (OSError, ValueError, TypeError):
        browser = {"notes": ["Browser context was unavailable when this state pack was created."]}

    pack = {
        "format": "dagric-migration-state-pack",
        "version": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "privacy": "Local-only migration notes. Contains no passwords, cookies, browser sessions, or file contents.",
        "windows_user": os.path.basename(os.path.normpath(profile)),
        "shell_folders": _shell_folders(profile),
        "desktop_shortcuts": _shortcut_manifest(profile),
        "recent_activity": _recent_artifacts(profile),
        "browser_context": browser,
    }
    os.makedirs(outdir, exist_ok=True)
    output = os.path.join(outdir, OUT_NAME)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("STATE_PACK=%s" % output)
    print("STATE_SHORTCUTS=%d" % len(pack["desktop_shortcuts"]))
    print("STATE_RECENT=%d" % len(pack["recent_activity"]["recent_links"]))
    print("STATE_JUMPLISTS=%d" % len(pack["recent_activity"]["jump_list_signals"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
