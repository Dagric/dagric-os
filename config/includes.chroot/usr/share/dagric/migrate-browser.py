#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recover browser data from a Windows install, for the Dagric Migration Assistant.

Handles three things the bookmarks importer doesn't:

  tabs       the pages that were open when they last used Windows
  passwords  saved logins -- Firefox only, see the note below
  reading    everything is read-only; the Windows partition is never written

WHY CHROME/EDGE PASSWORDS CANNOT BE RECOVERED HERE
--------------------------------------------------
Chrome and Edge encrypt saved passwords with Windows DPAPI. The key is derived
from the Windows user account and machine, and is only available to a process
running as that logged-in Windows user. From Linux those files are opaque
ciphertext -- this is a deliberate security boundary, not a missing feature, and
no tool can cross it offline. The supported route is Chrome's own password
export (Settings > Autofill > Passwords > Export), done BEFORE switching; this
script finds that CSV if it exists and passes it through.

Firefox is different: it protects logins with NSS, whose key material travels
with the profile, so those DO decrypt here -- unless a Primary Password is set,
in which case we ask for it rather than guess.

Usage:  migrate-browser.py <windows-user-profile-dir> <output-dir> [primary-password]
"""
import base64
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


# ---------------------------------------------------------------- utilities
def copy_out(path):
    """Copy a file off the read-only mount so sqlite/NSS can open it freely."""
    try:
        tmp = os.path.join(tempfile.mkdtemp(), os.path.basename(path))
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
            (size,) = struct.unpack("<I", fh.read(4))
            src = fh.read()
    except OSError:
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
    for prof in glob.glob(os.path.join(prof_root, "*")):
        for p in pats:
            f = os.path.join(prof, p)
            if not os.path.exists(f):
                continue
            raw = mozlz4(f)
            if not raw:
                continue
            try:
                data = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            for win in data.get("windows", []):
                for tab in win.get("tabs", []):
                    entries = tab.get("entries", [])
                    if not entries:
                        continue
                    idx = min(tab.get("index", len(entries)) - 1, len(entries) - 1)
                    e = entries[max(idx, 0)]
                    url = e.get("url", "")
                    if url.startswith(("http://", "https://")):
                        out.append(("Firefox", e.get("title") or url, url))
            if out:
                return out           # newest recovery file wins
    return out


def chromium_tabs(user_data_dir, label):
    """Open tabs from Chrome/Edge.

    Their session files use Chromium's SNSS container, whose record layout has
    changed repeatedly across versions. Rather than pin to one revision, pull
    the URLs out directly -- they are stored as plain UTF-8 runs. Best-effort by
    design: a missed tab is a small loss, a crash would be a bigger one.
    """
    found, seen = [], set()
    cands = []
    for prof in glob.glob(os.path.join(user_data_dir, "*")):
        for name in ("Current Session", "Current Tabs", "Last Session", "Last Tabs"):
            cands.append(os.path.join(prof, "Sessions", name))
            cands.append(os.path.join(prof, name))
        cands += glob.glob(os.path.join(prof, "Sessions", "Session_*"))
        cands += glob.glob(os.path.join(prof, "Sessions", "Tabs_*"))
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
        except OSError:
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
    profiles = [p for p in glob.glob(os.path.join(prof_root, "*"))
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
        work = tempfile.mkdtemp()
        for f in ("key4.db", "key3.db", "logins.json", "cert9.db", "pkcs11.txt"):
            src = os.path.join(prof, f)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, work)
                except OSError:
                    pass
        if nss.NSS_Init(work.encode()) != 0:
            note = "could not open the Firefox key store"
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
    return rows, note


def find_exported_csv(prof):
    """Chrome/Edge passwords can only come from the user's own export.
    Look where Chrome puts it by default."""
    hits = []
    for d in ("Downloads", "Desktop", "Documents"):
        for f in glob.glob(os.path.join(prof, d, "*.csv")):
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    head = fh.readline().lower()
                if "password" in head and ("url" in head or "origin" in head):
                    hits.append(f)
            except OSError:
                pass
    return hits


# ------------------------------------------------------------------- output
def write_tabs(tabs, path):
    seen, rows = set(), []
    for src, title, url in tabs:
        if url not in seen:
            seen.add(url)
            rows.append((src, title, url))
    import html as H
    with open(path, "w", encoding="utf-8") as fh:
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


def write_passwords(rows, path):
    # Chrome, Firefox and KeePassXC all accept this header.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "url", "username", "password"])
        for host, user, pw in rows:
            name = re.sub(r"^https?://", "", host).split("/")[0]
            w.writerow([name, host, user, pw])
    return len(rows)


def main():
    if len(sys.argv) < 3:
        print("usage: migrate-browser.py <windows-profile> <output-dir> [primary-password]")
        return 2
    prof, outdir = sys.argv[1], sys.argv[2]
    primary = sys.argv[3] if len(sys.argv) > 3 else ""

    tabs = []
    tabs += firefox_tabs(os.path.join(prof, "AppData/Roaming/Mozilla/Firefox/Profiles"))
    tabs += chromium_tabs(os.path.join(prof, "AppData/Local/Google/Chrome/User Data"), "Chrome")
    tabs += chromium_tabs(os.path.join(prof, "AppData/Local/Microsoft/Edge/User Data"), "Edge")
    n_tabs = write_tabs(tabs, os.path.join(outdir, OUT_TABS)) if tabs else 0

    rows, note = firefox_passwords(
        os.path.join(prof, "AppData/Roaming/Mozilla/Firefox/Profiles"), primary)
    n_pw = write_passwords(rows, os.path.join(outdir, OUT_PASS)) if rows else 0

    chrome_present = os.path.isdir(os.path.join(prof, "AppData/Local/Google/Chrome/User Data"))
    edge_present = os.path.isdir(os.path.join(prof, "AppData/Local/Microsoft/Edge/User Data"))
    exported = find_exported_csv(prof)

    print("TABS=%d" % n_tabs)
    print("PASSWORDS=%d" % n_pw)
    print("PWNOTE=%s" % note)
    print("CHROMEISH=%d" % (1 if (chrome_present or edge_present) else 0))
    print("EXPORTED=%s" % ("|".join(exported)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
