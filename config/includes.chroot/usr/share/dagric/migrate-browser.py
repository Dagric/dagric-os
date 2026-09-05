#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recover browser data from a Windows install, for the Dagric Migration Assistant.

Handles three things the bookmarks importer doesn't:

  tabs       the pages that were open when they last used Windows
  passwords  saved logins (Firefox + exported Chromium CSV)
  reading    everything is read-only; the Windows partition is never written

WHY CHROME-FAMILY PASSWORDS CANNOT BE RECOVERED HERE
----------------------------------------------------
Chrome, Edge, Brave, and DuckDuckGo encrypt saved passwords with a platform key
for that Windows account. From Linux those files are opaque ciphertext -- this is
a deliberate security boundary, not a missing feature, and no tool can decrypt
them here. The supported route is each browser's own export flow (Settings >
Passwords > Export), done BEFORE switching; this script can find a CSV export if
it exists and pass it through.

Firefox is different: it protects logins with NSS, whose key material travels with
the profile, so those DO decrypt here -- unless a Primary Password is set, in
which case we ask for it rather than guess.

Usage:  migrate-browser.py <windows-user-profile-dir> <output-dir> [--tabs] [--passwords]

With neither optional flag it keeps the historical all-data behavior for direct
callers.  Dagric's front end passes only the categories the owner ticked.
"""
import base64
import atexit
import ctypes as ct
import csv
import glob
import json
import os
import re
import shutil
import sqlite3
import struct
import sys
import tempfile

OUT_TABS = "Windows-open-tabs.html"
OUT_PASS = "Windows-passwords.csv"
OUT_META = "Windows-browser-context.json"

CHROMIUM_BROWSERS = [
    ("Chrome", r"AppData/Local/Google/Chrome/User Data"),
    ("Chrome Beta", r"AppData/Local/Google/Chrome Beta/User Data"),
    ("Chrome Dev", r"AppData/Local/Google/Chrome Dev/User Data"),
    ("Chrome Canary", r"AppData/Local/Google/Chrome SxS/User Data"),
    ("Edge", r"AppData/Local/Microsoft/Edge/User Data"),
    ("Edge Beta", r"AppData/Local/Microsoft/Edge Beta/User Data"),
    ("Edge Dev", r"AppData/Local/Microsoft/Edge Dev/User Data"),
    ("Edge Canary", r"AppData/Local/Microsoft/Edge SxS/User Data"),
    ("Brave", r"AppData/Local/BraveSoftware/Brave-Browser/User Data"),
    ("Brave", r"AppData/Local/BraveSoftware/Brave-Browser-Beta/User Data"),
    ("Brave", r"AppData/Local/BraveSoftware/Brave-Browser-Dev/User Data"),
    ("Brave", r"AppData/Local/BraveSoftware/Brave-Browser-Nightly/User Data"),
]

# The same metadata is useful even when login recovery fails; keep it compact so
# it can be shared safely and read quickly on first boot.
MAX_EXTENSIONS = 40

# Every glob pattern below is built from a REAL path the caller handed us --
# ultimately /media/<user>/<NTFS volume label>/Users/<name>. Windows happily
# accepts '[' and ']' in a volume label ("Windows [SSD]"), and glob reads those
# as a character class, so an unescaped prefix silently matches nothing and the
# migration reports zero tabs, zero passwords and no exported CSV while claiming
# success. glob.escape() the fixed prefix; only the '*' we wrote stays a wildcard.


# ---------------------------------------------------------------- utilities
_PRIVATE_TEMP_DIRS = set()


def private_temp_dir():
    """Create a 0700 work directory and register it for guaranteed cleanup."""
    path = tempfile.mkdtemp(prefix="dagric-browser-")
    _PRIVATE_TEMP_DIRS.add(path)
    return path


def remove_private_temp_dir(path):
    shutil.rmtree(path, ignore_errors=True)
    _PRIVATE_TEMP_DIRS.discard(path)


def cleanup_private_temp_dirs():
    for path in tuple(_PRIVATE_TEMP_DIRS):
        remove_private_temp_dir(path)


atexit.register(cleanup_private_temp_dirs)


def copy_out(path):
    """Copy a file off the read-only mount so sqlite/NSS can open it freely."""
    try:
        tmp = os.path.join(private_temp_dir(), os.path.basename(path))
        shutil.copy2(path, tmp)
        # Bring the sqlite sidecars too, or recent writes are invisible.
        for ext in ("-wal", "-shm"):
            if os.path.exists(path + ext):
                try:
                    shutil.copy2(path + ext, tmp + ext)
                except OSError:
                    pass
        return tmp
    except OSError:
        return None


def mozlz4(path):
    """Decompress Firefox's mozLz4 session file (pure python -- no lz4 module
    ships in the image, and pulling one in for a migration tool isn't worth it)."""
    try:
        with open(path, "rb") as fh:
            magic = fh.read(8)
            if not magic.startswith(b"mozLz4"):
                return None
            hdr = fh.read(4)
            if len(hdr) < 4:
                return None      # truncated header -- an unclean Windows shutdown
            (size,) = struct.unpack("<I", hdr)
            src = fh.read()
    except (OSError, struct.error):
        return None

    dst = bytearray()
    i = 0
    n = len(src)
    try:
        while i < n:
            token = src[i]; i += 1
            lit = token >> 4
            if lit == 15:
                while True:
                    b = src[i]; i += 1
                    lit += b
                    if b != 255:
                        break
            dst += src[i:i + lit]; i += lit
            if i >= n:
                break
            off = src[i] | (src[i + 1] << 8); i += 2
            if off == 0:
                break
            mlen = token & 0x0F
            if mlen == 15:
                while True:
                    b = src[i]; i += 1
                    mlen += b
                    if b != 255:
                        break
            mlen += 4
            start = len(dst) - off
            if start < 0:
                break
            for k in range(mlen):          # byte-wise: overlapping copies are legal
                dst.append(dst[start + k])
    except IndexError:
        pass
    return bytes(dst[:size]) if size else bytes(dst)


# -------------------------------------------------------------------- tabs
def firefox_tabs(prof_root):
    """Open tabs from Firefox's session store."""
    out = []
    pats = ["sessionstore-backups/recovery.jsonlz4",
            "sessionstore-backups/previous.jsonlz4",
            "sessionstore.jsonlz4"]
    for prof in glob.glob(os.path.join(glob.escape(prof_root), "*")):
        for p in pats:
            f = os.path.join(prof, p)
            if not os.path.exists(f):
                continue
            # A half-written session file is exactly what an unclean Windows
            # shutdown leaves behind -- the case where this matters most. It
            # must never sink the other candidates, the other profiles, or the
            # password recovery that runs after us.
            try:
                raw = mozlz4(f)
                if not raw:
                    continue
                data = json.loads(raw.decode("utf-8", "replace"))
                for win in data.get("windows") or []:
                    for tab in win.get("tabs") or []:
                        entries = tab.get("entries") or []
                        if not entries:
                            continue
                        # "index" is 1-based, but may be absent or JSON null.
                        idx = tab.get("index")
                        idx = idx - 1 if isinstance(idx, int) else len(entries) - 1
                        e = entries[min(max(idx, 0), len(entries) - 1)]
                        url = e.get("url") or ""
                        if isinstance(url, str) and url.startswith(("http://", "https://")):
                            out.append(("Firefox", e.get("title") or url, url))
            except Exception:
                pass             # keep whatever was salvaged, move on
            if out:
                return out           # newest recovery file wins
    return out


def chromium_tabs(user_data_dir, label):
    """Open tabs from a Chromium-family browser.

    Their session files use Chromium's SNSS container, whose record layout has
    changed repeatedly across versions. Rather than pin to one revision, pull
    the URLs out directly -- they are stored as plain UTF-8 runs. Best-effort by
    design: a missed tab is a small loss, a crash would be a bigger one.
    """
    found, seen = [], set()
    cands = []
    for prof in glob.glob(os.path.join(glob.escape(user_data_dir), "*")):
        for name in ("Current Session", "Current Tabs", "Last Session", "Last Tabs"):
            cands.append(os.path.join(prof, "Sessions", name))
            cands.append(os.path.join(prof, name))
        sess = os.path.join(glob.escape(prof), "Sessions")
        cands += glob.glob(os.path.join(sess, "Session_*"))
        cands += glob.glob(os.path.join(sess, "Tabs_*"))
    # Restrict to characters actually legal in a URL. A looser class (e.g. all
    # printable ASCII) swallows the binary padding between records and glues
    # several URLs into one -- caught in testing.
    url_re = re.compile(rb"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]{4,2000}")
    for f in cands:
        if not os.path.exists(f):
            continue
        try:
            with open(f, "rb") as fh:
                blob = fh.read()
        except Exception:
            continue
        for m in url_re.finditer(blob):
            url = m.group(0).decode("utf-8", "ignore").rstrip("/?&.,;:!")
            # Skip Chrome's own bookkeeping and obvious asset requests.
            if len(url) < 12 or url.endswith((".js", ".css", ".png", ".jpg", ".svg", ".woff", ".woff2")):
                continue
            if "/gen_204" in url or "clients" in url and "google.com" in url:
                continue
            if url not in seen:
                seen.add(url)
                found.append((label, url, url))
    return found


# ---------------------------------------------------------------- passwords
class SECItem(ct.Structure):
    # data MUST be a real pointer, not c_char_p: the payload is binary and
    # contains NUL bytes, and c_char_p makes ctypes treat it as a C string.
    # With c_char_p every PK11SDR_Decrypt returns SEC_ERROR_BAD_DATA (-8183) --
    # verified by round-tripping encrypt->decrypt in one process.
    _fields_ = [("type", ct.c_uint), ("data", ct.POINTER(ct.c_ubyte)), ("len", ct.c_uint)]


def _sec_in(b):
    """Wrap bytes as a SECItem. Returns (item, buffer) -- keep the buffer
    referenced for as long as the item is used, or it gets collected."""
    buf = (ct.c_ubyte * max(len(b), 1)).from_buffer_copy(b or b"\0")
    return SECItem(0, ct.cast(buf, ct.POINTER(ct.c_ubyte)), len(b)), buf


def _sec_bytes(item):
    if not item.data or not item.len:
        return b""
    return bytes(bytearray(item.data[i] for i in range(item.len)))


def firefox_passwords(prof_root, primary_pw=""):
    """Decrypt Firefox logins via NSS. Returns (rows, note)."""
    profiles = [p for p in glob.glob(os.path.join(glob.escape(prof_root), "*"))
                if os.path.exists(os.path.join(p, "logins.json"))]
    if not profiles:
        return [], "no Firefox logins found"

    try:
        nss = ct.CDLL("libnss3.so")
    except OSError:
        return [], "NSS library unavailable"

    # Declare signatures rather than relying on ctypes' int-sized defaults.
    nss.NSS_Init.argtypes = [ct.c_char_p]
    nss.NSS_Init.restype = ct.c_int
    nss.PK11_GetInternalKeySlot.restype = ct.c_void_p
    nss.PK11_Authenticate.argtypes = [ct.c_void_p, ct.c_int, ct.c_void_p]
    nss.PK11_Authenticate.restype = ct.c_int
    nss.PK11_CheckUserPassword.argtypes = [ct.c_void_p, ct.c_char_p]
    nss.PK11_CheckUserPassword.restype = ct.c_int
    nss.PK11SDR_Decrypt.argtypes = [ct.POINTER(SECItem), ct.POINTER(SECItem), ct.c_void_p]
    nss.PK11SDR_Decrypt.restype = ct.c_int

    rows, note = [], ""
    for prof in profiles:
        # key4.db and logins.json are enough to recover every saved password.
        # They must not survive as forgotten copies under /tmp after migration.
        work = private_temp_dir()
        for f in ("key4.db", "key3.db", "logins.json", "cert9.db", "pkcs11.txt"):
            src = os.path.join(prof, f)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, work)
                except OSError:
                    pass
        # "sql:" is NOT optional, and without it this recovered nothing from any
        # Firefox made since 2018. NSS picks its database format from the prefix
        # on the config dir: "sql:" means the cert9.db/key4.db SQLite store,
        # "dbm:" the legacy Berkeley-DB one. With no prefix it falls back to
        # NSS_DEFAULT_DB_TYPE, and Debian sets that nowhere, so it defaulted to
        # the legacy format and went looking for key3.db. Every Firefox profile
        # since v58 ships only key4.db — the very file copied in above — so NSS
        # opened an empty legacy store, found no master key, and PK11SDR_Decrypt
        # failed for every login. The helper then reported PASSWORDS=0 and
        # dagric-migrate told the owner "No Firefox logins were recovered", with
        # no hint that the store had simply never been read. The headline
        # "bring your saved passwords across from Windows" feature returned
        # nothing, on essentially every real profile, while looking like success.
        #
        # The in-process encrypt->decrypt round-trip this file uses as its only
        # decryption self-test uses an ephemeral key and never touches a profile,
        # which is why it passed the whole time the real path was dead.
        if nss.NSS_Init(b"sql:" + work.encode()) != 0:
            note = "could not open the Firefox key store"
            remove_private_temp_dir(work)
            continue
        try:
            slot = nss.PK11_GetInternalKeySlot()
            if not slot:
                note = "no key slot"
                continue
            if nss.PK11_CheckUserPassword(slot, primary_pw.encode()) != 0:
                note = ("this Firefox profile has a Primary Password set - "
                        "re-run and supply it to recover these logins")
                continue
            nss.PK11_Authenticate(slot, 1, None)
            try:
                with open(os.path.join(work, "logins.json"), encoding="utf-8") as fh:
                    logins = json.load(fh).get("logins", [])
            except (OSError, ValueError):
                logins = []

            def dec(b64):
                if not b64:
                    return ""
                raw = base64.b64decode(b64)
                inp, keep = _sec_in(raw)          # keep: anchors the buffer
                out = SECItem(0, None, 0)
                if nss.PK11SDR_Decrypt(ct.byref(inp), ct.byref(out), None) != 0:
                    return ""
                del keep
                return _sec_bytes(out).decode("utf-8", "replace")

            for l in logins:
                try:
                    u = dec(l.get("encryptedUsername", ""))
                    p = dec(l.get("encryptedPassword", ""))
                except Exception:
                    continue
                if p:
                    rows.append((l.get("hostname", ""), u, p))
        finally:
            nss.NSS_Shutdown()
            remove_private_temp_dir(work)
    return rows, note


def find_exported_csv(prof):
    """Chromium-family passwords can only come from browser exports."""
    hits = []
    roots = [os.path.join(prof, d) for d in ("Downloads", "Desktop", "Documents")]
    for _, rel in CHROMIUM_BROWSERS:
        roots.append(os.path.join(prof, rel))

    # DuckDuckGo's local path varies by build.
    for folder in glob.glob(os.path.join(prof, "AppData/Local/*")):
        if not os.path.isdir(folder):
            continue
        low = os.path.basename(folder).lower()
        if "duck" in low or "ddg" in low:
            roots.append(folder)
            roots.append(os.path.join(folder, "User Data"))
            roots.append(os.path.join(folder, "Browser"))
            roots.append(os.path.join(folder, "Browser", "User Data"))

    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for f in glob.glob(os.path.join(glob.escape(root), "*.csv")):
            if f in seen:
                continue
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    head = fh.readline().lower()
                if "password" in head and ("url" in head or "origin" in head):
                    hits.append(f)
                    seen.add(f)
            except OSError:
                pass
    return hits


# ---------------------------------------------------------------- metadata
def _safe_load_json(path):
    """Load JSON if possible, else return {}."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, ValueError, TypeError):
        return {}


def _read_chrome_profiles(user_data_dir):
    """Return Chromium profile directories under this browser profile root."""
    out = []
    skip = {"System Profile", "Crashpad", "ShaderCache", "GrShaderCache", "CertificateTransparency",
            "Safe Browsing", "VisualElements", "VideoDecodeStats", "SwReporter", "Wallet"}
    try:
        for p in sorted(glob.glob(os.path.join(glob.escape(user_data_dir), "*"))):
            if os.path.isdir(p):
                label = os.path.basename(p)
                if label in skip:
                    continue
                # Keep only things that look like profiles; this skips browser
                # internals that are not session/profile folders.
                if not (os.path.isfile(os.path.join(p, "Preferences")) or
                        os.path.isfile(os.path.join(p, "Bookmarks")) or
                        any(glob.glob(os.path.join(glob.escape(p), "*", "Bookmarks")))):
                    continue
                out.append(p)
    except OSError:
        return []
    return out


def _read_firefox_profiles(meta_root):
    """Parse Firefox profiles.ini when present and return profile descriptors."""
    ini = os.path.join(meta_root, "profiles.ini")
    profiles = []
    if not os.path.exists(ini):
        return profiles

    current = {}
    def flush():
        nonlocal current
        if not current:
            return
        path = current.get("Path", "").strip()
        if path:
            profiles.append({
                "name": current.get("Name", path),
                "path": path,
                "relative": current.get("IsRelative", "1") == "1",
                "default": current.get("Default", "0") == "1",
            })
        current = {}

    try:
        for raw in open(ini, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                flush()
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()
            if key.strip() == "Default":
                # Firefox profiles.ini writes default in its own section line;
                # keep parsing to include all keys.
                current["Default"] = value.strip()
                continue
    except OSError:
        return []
    finally:
        flush()
    return profiles


def _read_prefs_js(profile_root):
    """Pull a few non-sensitive preferences from Firefox prefs.js."""
    prefs = {}
    path = os.path.join(profile_root, "prefs.js")
    if not os.path.exists(path):
        return prefs
    rx = re.compile(r'^user_pref\("(?P<k>[^"]+)",\s*(?P<v>.+)\);$')
    try:
        for raw in open(path, encoding="utf-8", errors="replace"):
            m = rx.match(raw.strip())
            if not m:
                continue
            key = m.group("k")
            if key in {"browser.startup.homepage", "browser.startup.page", "browser.startup.homepage_override.mstone",
                       "extensions.activeThemeID", "browser.theme.content-theme"}:
                val = m.group("v")
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                prefs[key] = val
    except OSError:
        return {}
    return prefs


def _collect_firefox_addons(profile_root):
    """Collect a compact list of add-ons from extensions.json."""
    data = _safe_load_json(os.path.join(profile_root, "extensions.json"))
    raw_addons = data.get("addons", []) if isinstance(data, dict) else []
    out = []
    for item in raw_addons:
        if not isinstance(item, dict):
            continue
        manifest = item.get("defaultLocale") or {}
        name = manifest.get("name") or item.get("id") or "Unknown"
        active = item.get("active", False)
        out.append({
            "id": item.get("id", ""),
            "name": name,
            "active": bool(active),
        })
        if len(out) >= MAX_EXTENSIONS:
            break
    return out


def _collect_chromium_profile_state(profile_dir, profile_info=None):
    """Pull startup/homepage/extensions metadata from a Chromium profile."""
    prefs = _safe_load_json(os.path.join(profile_dir, "Preferences"))
    session = prefs.get("session", {}) if isinstance(prefs, dict) else {}
    provider = prefs.get("default_search_provider", {}) if isinstance(prefs, dict) else {}
    extension_root = prefs.get("extensions") or {} if isinstance(prefs, dict) else {}
    ext_map = extension_root.get("settings") or {} if isinstance(extension_root, dict) else {}

    ext_rows = []
    if isinstance(ext_map, dict):
        for ext_id, details in ext_map.items():
            if not isinstance(details, dict):
                continue
            if details.get("state", 1) == 0:
                continue
            manifest = details.get("manifest") or {}
            ext_rows.append({
                "id": ext_id,
                "name": manifest.get("name", ext_id),
                "active": bool(details.get("state", 1)),
            })
            if len(ext_rows) >= MAX_EXTENSIONS:
                break

    theme = ""
    theme_meta = extension_root.get("theme") if isinstance(extension_root, dict) else {}
    theme_id = theme_meta.get("id", "") if isinstance(theme_meta, dict) else ""
    if theme_id and isinstance(ext_map.get(theme_id), dict):
        theme = (ext_map[theme_id].get("manifest") or {}).get("name", theme_id)
    elif theme_id:
        theme = theme_id

    out = {
        "profile": os.path.basename(profile_dir),
        "name": profile_info.get("name") if isinstance(profile_info, dict) else "",
        "homepage": prefs.get("homepage", "") if isinstance(prefs, dict) else "",
        "startup_mode": session.get("restore_on_startup", 0) if isinstance(session, dict) else 0,
        "startup_urls": session.get("startup_urls", []) if isinstance(session, dict) else [],
        "search_engine": provider.get("name", "") if isinstance(provider, dict) else "",
        "theme": theme,
        "extensions": ext_rows,
    }
    if not out["name"] and os.path.basename(profile_dir) == "Default":
        out["name"] = "Default"
    return out


def _collect_chromium_roots_metadata(user_data_dir, label):
    """Collect compact metadata for each Chromium profile under a user data dir."""
    meta = {"label": label, "profiles": []}
    local_state = _safe_load_json(os.path.join(user_data_dir, "..", "Local State"))
    info_cache = {}
    if isinstance(local_state, dict):
        info_cache = (local_state.get("profile", {}) or {}).get("info_cache", {})
        if not isinstance(info_cache, dict):
            info_cache = {}

    for prof in _read_chrome_profiles(user_data_dir):
        p_id = os.path.basename(prof)
        info = info_cache.get(p_id)
        if not isinstance(info, dict):
            info = {}
        meta["profiles"].append(_collect_chromium_profile_state(prof, info))
    return meta


def write_metadata(data, path):
    """Write compact continuation metadata for easier setup after boot."""
    with open_private_text(path) as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return 1


# ------------------------------------------------------------------- output
def open_private_text(path, *, newline=None):
    """Open a migration output with mode 0600, including an existing file."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "w", newline=newline, encoding="utf-8")
    except Exception:
        os.close(fd)
        raise


def write_tabs(tabs, path):
    seen, rows = set(), []
    for src, title, url in tabs:
        if url not in seen:
            seen.add(url)
            # A title is not always a string (sites can put a number there);
            # keep it one, or sorted() and the slice below both blow up.
            rows.append((src, title if isinstance(title, str) else str(title), url))
    import html as H
    with open_private_text(path) as fh:
        fh.write("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
                 '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
                 "<TITLE>Bookmarks</TITLE>\n<H1>Tabs open in Windows</H1>\n<DL><p>\n")
        cur = None
        for src, title, url in sorted(rows):
            if src != cur:
                if cur is not None:
                    fh.write("</DL><p>\n")
                fh.write("<DT><H3>%s - open tabs</H3>\n<DL><p>\n" % H.escape(src))
                cur = src
            fh.write('<DT><A HREF="%s">%s</A>\n'
                     % (H.escape(url, quote=True), H.escape(title[:300])))
        if cur is not None:
            fh.write("</DL><p>\n")
        fh.write("</DL><p>\n")
    return len(rows)


def chromium_profile_roots(profile_root):
    """Chromium-family profile roots we can read from this Windows profile."""
    roots = []
    seen = set()

    for label, rel in CHROMIUM_BROWSERS:
        path = os.path.join(profile_root, rel)
        if os.path.isdir(path) and path not in seen:
            roots.append((label, path))
            seen.add(path)

    app_local = os.path.join(profile_root, "AppData", "Local")
    if not os.path.isdir(app_local):
        return roots

    # DuckDuckGo path has changed across versions; probe candidate folders and
    # require a visible profile-like Bookmarks file before treating it as real.
    for folder in glob.glob(os.path.join(app_local, "*")):
        if not os.path.isdir(folder):
            continue
        low = os.path.basename(folder).lower()
        if "duck" not in low and "ddg" not in low:
            continue
        for rel in ("", "Browser", "Browser/User Data", "User Data"):
            candidate = os.path.join(folder, rel)
            if not os.path.isdir(candidate):
                continue
            if any(glob.glob(os.path.join(glob.escape(candidate), "*", "Bookmarks"))):
                if candidate not in seen:
                    roots.append(("DuckDuckGo", candidate))
                    seen.add(candidate)
                break

    return roots


def write_passwords(rows, path):
    # Chrome, Firefox and KeePassXC all accept this header.
    with open_private_text(path, newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "url", "username", "password"])
        for host, user, pw in rows:
            name = re.sub(r"^https?://", "", host).split("/")[0]
            w.writerow([name, host, user, pw])
    return len(rows)


def _normalize_csv_col(name):
    """Normalize a CSV column name for tolerant matching."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _read_export_rows(path):
    """Parse one exported Chromium-family CSV, returning (host, user, password)."""
    out = []
    aliases = {
        "url": ("url", "website", "origin", "domain", "loginuri", "site", "name"),
        "user": ("username", "login", "user", "userid", "email", "accountname", "account"),
        "pass": ("password", "passwd", "secret", "pwd", "pass"),
    }

    def pick(row, wanted):
        for want in wanted:
            target = _normalize_csv_col(want)
            for k, v in row.items():
                if _normalize_csv_col(k) == target and isinstance(v, str):
                    vv = v.strip()
                    if vv:
                        return vv
        return ""

    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                return out
            for row in reader:
                host = pick(row, aliases["url"])
                user = pick(row, aliases["user"])
                pw = pick(row, aliases["pass"])
                if pw and (host or user):
                    out.append((host, user, pw))
    except (OSError, csv.Error):
        return []

    return out


def read_exported_csv_files(paths):
    """Parse and dedupe all exported password CSV files."""
    seen, out = set(), []
    for path in paths:
        for host, user, pw in _read_export_rows(path):
            key = (host, user, pw)
            if key in seen:
                continue
            seen.add(key)
            out.append((host, user, pw))
    return out


def _step(what, fn, fallback, failures):
    """Run one recovery step. A step that fails must not take the others with
    it, and must never leave the caller unable to tell failure from 'found
    nothing' -- dagric-migrate reads only our stdout."""
    try:
        return fn()
    except Exception as exc:
        failures.append(what)
        print("dagric-migrate: %s failed: %s: %s" % (what, type(exc).__name__, exc),
              file=sys.stderr)
        return fallback


def main():
    if len(sys.argv) < 3:
        print("usage: migrate-browser.py <windows-profile> <output-dir>")
        print("       the Firefox Primary Password is read from stdin, not argv")
        return 2
    prof, outdir = sys.argv[1], sys.argv[2]
    options = set(sys.argv[3:])
    unknown = options - {"--tabs", "--passwords"}
    if unknown:
        print("unknown option(s): %s" % ", ".join(sorted(unknown)), file=sys.stderr)
        return 2
    # Backwards-compatible direct use: no selector means recover both.  The
    # Migration Assistant itself never uses this mode; it passes deliberate
    # check-box choices so unselected password recovery cannot happen.
    want_tabs = "--tabs" in options or not options
    want_passwords = "--passwords" in options or not options

    # THE PRIMARY PASSWORD ARRIVES ON STDIN AND MUST NEVER BE AN ARGUMENT.
    #
    # It used to be sys.argv[3]. On Linux /proc/<pid>/cmdline is world-readable
    # — Dagric sets no hidepid — so for as long as this process ran, the owner's
    # Firefox Primary Password was legible to every other user on the machine
    # through a plain `ps aux`, and to any unprivileged process that cared to
    # look. Migration is exactly when someone is carrying their whole password
    # store across, and Pro is sold into schools and libraries where "every
    # other user on the machine" is not a hypothetical.
    #
    # stdin has no such window: the bytes go down a pipe that only this process
    # can read, and nothing in the process table records them. dagric-migrate
    # feeds it with `printf '%s\n' "$PRIMARY" | ...`.
    #
    # isatty guards the case of someone running this helper by hand to debug:
    # without it, the read would block forever on a terminal and look like a
    # hang. A blank password is normal — most people never set one.
    primary = ""
    if not sys.stdin.isatty():
        try:
            primary = sys.stdin.readline().rstrip("\n")
        except (OSError, UnicodeDecodeError):
            primary = ""
    ff_root = os.path.join(prof, "AppData/Roaming/Mozilla/Firefox/Profiles")
    chromium_roots = chromium_profile_roots(prof)
    firefox_root_parent = os.path.dirname(ff_root)
    failures = []

    tabs = []
    if want_tabs:
        tabs += _step("reading Firefox tabs", lambda: firefox_tabs(ff_root), [], failures)
        for label, browser_path in chromium_roots:
            tabs += _step("reading %s tabs" % label,
                          lambda p=browser_path, l=label: chromium_tabs(p, l),
                          [], failures)
    n_tabs = _step("writing the tab list",
                   lambda: write_tabs(tabs, os.path.join(outdir, OUT_TABS)) if tabs else 0,
                   0, failures) if want_tabs else 0

    note, exported, n_pw = "", [], 0
    if want_passwords:
        rows, note = _step("reading Firefox logins",
                           lambda: firefox_passwords(ff_root, primary),
                           ([], "the Firefox login store could not be read"), failures)
        exported = _step("looking for an exported password file",
                         lambda: find_exported_csv(prof), [], failures)
        exp_rows = _step("reading exported password files",
                         lambda: read_exported_csv_files(exported), [], failures)
        merged = []
        seen = set()
        for host, user, pw in (rows + exp_rows):
            key = (host, user, pw)
            if key in seen:
                continue
            seen.add(key)
            merged.append((host, user, pw))
        n_pw = _step("writing the login list",
                     lambda: write_passwords(merged, os.path.join(outdir, OUT_PASS)) if merged else 0,
                     0, failures)

    # Always generate a continuity context file: safe, no passwords, just enough
    # structure for a "start where you left off" workflow on the new install.
    ff_profiles = _step("reading Firefox profile metadata", lambda: _read_firefox_profiles(firefox_root_parent), [], failures)
    ff_items = []
    for item in ff_profiles:
        profile_dir = os.path.join(ff_root, item.get("path", ""))
        if not profile_dir or not os.path.isdir(profile_dir):
            continue
        profile = dict(item)
        profile["prefs"] = _read_prefs_js(profile_dir)
        profile["addons"] = _collect_firefox_addons(profile_dir)
        ff_items.append(profile)

    browser_meta = []
    for label, browser_root in chromium_roots:
        browser_meta.append(_collect_chromium_roots_metadata(browser_root, label))

    context = {
        "windows_user": os.path.basename(prof),
        "windows_profile": prof,
        "tabs": n_tabs,
        "logins": n_pw,
        "exported_password_csvs": exported,
        "firefox": {
            "profiles": ff_items,
        },
        "chromium": browser_meta,
        "notes": [note] if note else [],
    }
    _step("writing browser context metadata",
         lambda: write_metadata(context, os.path.join(outdir, OUT_META)),
         0, failures)

    # These five lines are the contract with dagric-migrate: always print them.
    has_chromium = 1 if ((1 if chromium_roots else 0) or bool(exported)) else 0
    print("TABS=%d" % n_tabs)
    print("PASSWORDS=%d" % n_pw)
    print("PWNOTE=%s" % note)
    print("CHROMEISH=%d" % has_chromium)
    print("EXPORTED=%s" % ("|".join(exported)))
    print("EXPORTED_COUNT=%d" % len(exported))
    print("FAILED=%s" % ("; ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
