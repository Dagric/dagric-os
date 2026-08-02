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

# Every glob pattern below is built from a REAL path the caller handed us --
# ultimately /media/<user>/<NTFS volume label>/Users/<name>. Windows happily
# accepts '[' and ']' in a volume label ("Windows [SSD]"), and glob reads those
# as a character class, so an unescaped prefix silently matches nothing and the
# migration reports zero tabs, zero passwords and no exported CSV while claiming
# success. glob.escape() the fixed prefix; only the '*' we wrote stays a wildcard.


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
    """Open tabs from Chrome/Edge.

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
        for f in glob.glob(os.path.join(glob.escape(prof), d, "*.csv")):
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
            # A title is not always a string (sites can put a number there);
            # keep it one, or sorted() and the slice below both blow up.
            rows.append((src, title if isinstance(title, str) else str(title), url))
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
    chrome_dir = os.path.join(prof, "AppData/Local/Google/Chrome/User Data")
    edge_dir = os.path.join(prof, "AppData/Local/Microsoft/Edge/User Data")
    failures = []

    tabs = []
    tabs += _step("reading Firefox tabs", lambda: firefox_tabs(ff_root), [], failures)
    tabs += _step("reading Chrome tabs", lambda: chromium_tabs(chrome_dir, "Chrome"), [], failures)
    tabs += _step("reading Edge tabs", lambda: chromium_tabs(edge_dir, "Edge"), [], failures)
    n_tabs = _step("writing the tab list",
                   lambda: write_tabs(tabs, os.path.join(outdir, OUT_TABS)) if tabs else 0,
                   0, failures)

    rows, note = _step("reading Firefox logins",
                       lambda: firefox_passwords(ff_root, primary),
                       ([], "the Firefox login store could not be read"), failures)
    n_pw = _step("writing the login list",
                 lambda: write_passwords(rows, os.path.join(outdir, OUT_PASS)) if rows else 0,
                 0, failures)

    chrome_present = os.path.isdir(chrome_dir)
    edge_present = os.path.isdir(edge_dir)
    exported = _step("looking for an exported password file",
                     lambda: find_exported_csv(prof), [], failures)

    # These five lines are the contract with dagric-migrate: always print them.
    print("TABS=%d" % n_tabs)
    print("PASSWORDS=%d" % n_pw)
    print("PWNOTE=%s" % note)
    print("CHROMEISH=%d" % (1 if (chrome_present or edge_present) else 0))
    print("EXPORTED=%s" % ("|".join(exported)))
    print("FAILED=%s" % ("; ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
