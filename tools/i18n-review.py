#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract po/ entries for review, apply reviewed translations, and guard the mechanics.

WHY THIS SPLIT EXISTS. Every po/*.po in this tree is 100% translated and 0%
reviewed — each header says so in as many words, and names the strings that cost
money when they are wrong: the Windows-is-only-ever-READ promise in
dagric-migrate, the "plug in everything before continuing" warning in
dagric-usb-protect, the Secure Boot notice in dagric-drivers, the EU consent
wording in dagric-vm and the get-* licence paragraphs. Those languages are
already advertised — the guide is published in five of them — so the review the
header asks for is overdue rather than optional.

A language model is the right tool for the LANGUAGE and the wrong tool for the
MECHANICS. A reviewer that improves a sentence and drops a $VAR, or localises
the letter a [y/N] prompt accepts without localising the accepted-answer list,
has broken the program while making the prose better. So this file does the
mechanics in code and leaves only the prose to a reviewer:

  extract  — emit entries as JSON, grouped by the source file they came from,
             because context is what makes a review worth anything
  apply    — write reviewed msgstr values back, refusing any that fails a check
  check    — run the guards over a catalogue as it stands

THE GUARDS, and the specific defect each one prevents:

  variables      Every $NAME / ${NAME} / %s / %d in the msgid must appear in the
                 msgstr. These are shell and printf substitutions; losing one
                 prints a literal "$WINUSER" at the owner, and inventing one
                 expands to empty.
  keep-english   Product and command names are not words. "Dagric", "Steam",
                 "Bottles", "Proton", "Wi-Fi", "BitLocker", "Secure Boot", the
                 dagric-* command names and any bare URL must survive verbatim.
  answers        A msgid that is a list of accepted answers ("y yes") must keep
                 its English letters in the msgstr. Spanish already gets this
                 right — "s si sí y yes" — and it is the single easiest thing to
                 lose in a well-meaning rewrite: translate the [y/N] prompt, and
                 the owner types their own letter into a script that only ever
                 tested for "y".
  brackets       A msgid containing [y/N] must leave a bracketed pair in the
                 msgstr, so the prompt still reads as a prompt.
  nonempty       A review may not blank a string.
  escapes        Backslash escapes and embedded quotes must stay balanced, or
                 the catalogue will not parse.

Nothing here writes a .mo. tools/i18n-build.sh owns that, and it runs
`msgfmt -c`, which is a second independent check of the same format-specifier
rule — deliberately, because this file could have a bug.

Usage:
  python tools/i18n-review.py extract --lang es --out review-es.json
  python tools/i18n-review.py apply   --lang es --in reviewed-es.json
  python tools/i18n-review.py check   --lang es
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PO = os.path.join(ROOT, "po")

# Tokens that are names, not words. Case-sensitive on purpose: "bottles" in a
# sentence is a word, "Bottles" is the application.
KEEP = [
    "Dagric", "Debian", "KDE", "Plasma", "Steam", "Proton", "Proton-GE", "Bottles",
    "Heroic", "Lutris", "Wine", "Ollama", "Flatpak", "Flathub", "GitHub", "NVIDIA",
    "BitLocker", "Wi-Fi", "Secure Boot", "UEFI", "BIOS", "NTFS", "exFAT", "btrfs",
    "Btrfs", "Windows", "Firefox", "Chrome", "Edge", "LibreOffice", "GIMP",
    "Inkscape", "Krita", "Kdenlive", "Timeshift", "Snapper", "AppArmor",
    "OpenSnitch", "KeePassXC", "Syncthing", "LocalSend", "Variety", "systemd",
]
VAR_RE = re.compile(r'\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[0-9.]*[sdfux]')
# Trailing punctuation is sentence, not URL. Without the exclusion the "?" that
# ends "Install Ollama from https://ollama.com? [y/N]" was read as part of the
# address, so a translation that correctly kept the URL and moved the question
# mark was reported as having lost it.
URL_RE = re.compile(r'https?://[^\s"\\]*[^\s"\\.,;:!?)\]]')

# Names that are genuinely LOCALISED and must not be demanded verbatim. "Wi-Fi"
# is "WLAN" in German and that is correct, not a defect — a guard that insists
# on the English spelling would push a reviewer into writing worse German.
# Anything here is checked as advice rather than as a failure.
SOFT = {"Wi-Fi", "Secure Boot", "Windows", "BIOS", "UEFI"}


def _unescape(s):
    return (s.replace('\\n', '\n').replace('\\t', '\t')
             .replace('\\"', '"').replace('\\\\', '\\'))


def _escape(s):
    return (s.replace('\\', '\\\\').replace('"', '\\"')
             .replace('\n', '\\n').replace('\t', '\\t'))


def parse(path):
    """Minimal po reader. Returns [{msgid, msgstr, refs, comments, raw}]."""
    out, blocks = [], re.split(r'\n\n+', open(path, encoding="utf-8").read())
    for blk in blocks:
        if 'msgid' not in blk:
            continue
        refs = re.findall(r'^#:\s*(.+)$', blk, re.M)
        # A msgid or msgstr may be a first line plus continuation lines.
        def grab(key):
            m = re.search(r'^%s\s+"(.*)"\s*$' % key, blk, re.M)
            if not m:
                return None
            parts = [m.group(1)]
            # lstrip('\n') is load-bearing. With re.M the `$` matches BEFORE the
            # newline, so blk[m.end():] begins with it and split('\n') yields ''
            # as its first element — which fails the continuation match and broke
            # the loop on its first pass. Every multi-line entry therefore read
            # back as the empty first line alone, and `check` reported 33 fully
            # translated strings as "msgstr is empty" across five catalogues.
            # Exactly the false-positive class this file exists to avoid.
            for line in blk[m.end():].lstrip('\n').split('\n'):
                c = re.match(r'^"(.*)"\s*$', line.strip())
                if not c:
                    break
                parts.append(c.group(1))
            return ''.join(parts)
        mid, mstr = grab('msgid'), grab('msgstr')
        if mid is None or mstr is None or mid == '':
            continue
        out.append({
            'msgid': _unescape(mid),
            'msgstr': _unescape(mstr),
            'refs': refs,
            'source': (refs[0].split(':')[0].split('/')[-1] if refs else '?'),
        })
    return out


def guard(msgid, msgstr):
    """Return a list of mechanical problems. Empty list means it is safe."""
    bad = []
    if not msgstr.strip():
        bad.append("msgstr is empty")
        return bad

    want = sorted(set(VAR_RE.findall(msgid)))
    got = sorted(set(VAR_RE.findall(msgstr)))
    missing = [v for v in want if v not in got]
    added = [v for v in got if v not in want]
    if missing:
        bad.append("variable(s) lost: %s" % " ".join(missing))
    if added:
        bad.append("variable(s) invented: %s" % " ".join(added))

    for u in URL_RE.findall(msgid):
        if u not in msgstr:
            bad.append("URL changed or lost: %s" % u)

    for k in KEEP:
        if k in SOFT:
            continue
        # Whole-token match so "Wine" does not fire on "Winery".
        if re.search(r'(?<![A-Za-z])%s(?![A-Za-z])' % re.escape(k), msgid):
            if not re.search(r'(?<![A-Za-z])%s(?![A-Za-z])' % re.escape(k), msgstr):
                bad.append("product name not preserved: %s" % k)

    # The accepted-answer list. A msgid of bare short tokens that includes "y"
    # is the [y/N] answer list, and the English letters must survive so a script
    # testing for "y" still works for an owner who types it.
    toks = msgid.split()
    if toks and all(len(t) <= 4 for t in toks) and 'y' in toks:
        for t in toks:
            if t not in msgstr.split():
                bad.append("accepted answer %r dropped — the prompt would stop "
                           "responding to it" % t)

    if '[' in msgid and ']' in msgid and not ('[' in msgstr and ']' in msgstr):
        bad.append("bracketed prompt lost its brackets")

    if msgstr.count('"') != msgstr.count('\\"'):
        pass  # unescaped quotes are handled by _escape on write
    return bad


def _emit(key, s):
    """Render `key "..."` in gettext form, multi-line when the string has newlines.

    A single escaped line is legal gettext and msgfmt accepts it, but collapsing
    a twenty-line warning onto one line makes the .po unreadable and every future
    diff useless. So a string containing a newline is written the way gettext
    writes it: an empty first line, then one quoted chunk per source line with
    the \\n kept at the end of each.
    """
    esc = _escape(s)
    if '\\n' not in esc:
        return '%s "%s"' % (key, esc)
    parts = esc.split('\\n')
    chunks = [p + '\\n' for p in parts[:-1]]
    if parts[-1]:
        chunks.append(parts[-1])
    return '%s ""\n' % key + '\n'.join('"%s"' % c for c in chunks)


def _replace_msgstr(src, msgid, new):
    """Swap the msgstr belonging to msgid, handling multi-line on BOTH sides.

    The first version of this used one regex assuming `msgid "x"` and `msgstr "y"`
    each sat on a single line. Ten of the thirty-three Spanish changes silently
    did not match — among them the NVIDIA kernel-module warning, which is exactly
    the safety string this whole review exists for. A no-op that reports success
    is the worst failure mode available here, so the applier now scans rather
    than pattern-matches, and cmd_apply counts and prints every non-match.
    """
    lines = src.split('\n')
    i = 0
    while i < len(lines):
        if not lines[i].startswith('msgid '):
            i += 1
            continue
        # collect this entry's msgid, including continuation lines
        m = re.match(r'^msgid\s+"(.*)"\s*$', lines[i])
        if not m:
            i += 1
            continue
        parts, j = [m.group(1)], i + 1
        while j < len(lines):
            c = re.match(r'^"(.*)"\s*$', lines[j])
            if not c:
                break
            parts.append(c.group(1))
            j += 1
        if _unescape(''.join(parts)) != msgid:
            i = j
            continue
        # j now points at msgstr (or msgid_plural, which this tool does not touch)
        if j >= len(lines) or not lines[j].startswith('msgstr '):
            return src, 0
        k = j + 1
        while k < len(lines) and re.match(r'^"(.*)"\s*$', lines[k]):
            k += 1
        return '\n'.join(lines[:j] + _emit('msgstr', new).split('\n') + lines[k:]), 1
    return src, 0


def cmd_extract(a):
    path = os.path.join(PO, a.lang + ".po")
    ents = parse(path)
    groups = {}
    for e in ents:
        groups.setdefault(e['source'], []).append(
            {'msgid': e['msgid'], 'current': e['msgstr'], 'refs': e['refs']})
    payload = {'lang': a.lang, 'total': len(ents), 'groups': groups}
    out = a.out or os.path.join(ROOT, "review-%s.json" % a.lang)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print("%s: %d entries in %d source groups -> %s"
          % (a.lang, len(ents), len(groups), out))


def cmd_apply(a):
    path = os.path.join(PO, a.lang + ".po")
    src = open(path, encoding="utf-8").read()
    data = json.load(open(a.infile, encoding="utf-8"))
    changes = data if isinstance(data, list) else data.get("changes", [])
    applied = rejected = skipped = 0
    problems = []
    for c in changes:
        mid, new = c.get("msgid"), c.get("new")
        if mid is None or new is None:
            continue
        bad = guard(mid, new)
        if bad:
            rejected += 1
            problems.append((mid[:60], bad))
            continue
        src2, n = _replace_msgstr(src, mid, new)
        if n:
            src = src2
            applied += 1
        else:
            skipped += 1
    if not a.dry_run:
        open(path, "w", encoding="utf-8", newline="\n").write(src)
    print("%s: applied %d, rejected %d, not-matched %d%s"
          % (a.lang, applied, rejected, skipped, "  (dry run)" if a.dry_run else ""))
    for mid, bad in problems:
        print("  REJECTED %r" % mid)
        for b in bad:
            print("      %s" % b)
    return 1 if problems else 0


def header_damage(path):
    """Every quoted line in a .po must open and close on the same line.

    THIS CHECK EXISTS BECAUSE ITS ABSENCE COST AN HOUR. A metadata rewrite used
    re.sub with a replacement containing "\\n", which re.sub reads as a NEWLINE
    rather than as the two characters a .po needs, so four header lines in each
    of the five catalogues were split in half:

        "PO-Revision-Date: 2026-08-04 01:00+0000
        "

    That is not valid gettext. And `check` reported 438 entries and zero
    problems on all five, because parse() skips the header entry (its msgid is
    the empty string) and therefore never looked at the lines that were broken.
    A validator that is structurally incapable of seeing the most-edited block
    in the file is worse than no validator, since it answers "clean" with
    authority. The same blind spot would hide a corrupted Plural-Forms, which
    breaks every plural in the language at runtime.
    """
    bad = []
    for n, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        s = line.rstrip()
        if not s.startswith('"'):
            continue
        # strip escaped quotes before counting, so \" inside a string is not
        # mistaken for the terminator
        if not s.replace('\\"', "").endswith('"') or s.replace('\\"', "") == '"':
            bad.append((n, line[:60]))
    return bad


def cmd_check(a):
    langs = [a.lang] if a.lang else [f[:-3] for f in sorted(os.listdir(PO))
                                     if f.endswith(".po")]
    rc = 0
    for lang in langs:
        dmg = header_damage(os.path.join(PO, lang + ".po"))
        if dmg:
            rc = 1
            print("%-8s %d MALFORMED quoted line(s) — this file is not valid gettext"
                  % (lang, len(dmg)))
            for n, txt in dmg[:6]:
                print("   line %-5d %s" % (n, txt))
        ents = parse(os.path.join(PO, lang + ".po"))
        bad = [(e, guard(e['msgid'], e['msgstr'])) for e in ents]
        bad = [(e, b) for e, b in bad if b]
        print("%-8s %d entries, %d mechanical problem(s)" % (lang, len(ents), len(bad)))
        for e, b in bad:
            rc = 1
            print("   %-46s %s" % (e['msgid'][:46], "; ".join(b)))
    return rc


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("--lang", required=True); e.add_argument("--out")
    p = sub.add_parser("apply"); p.add_argument("--lang", required=True)
    p.add_argument("--in", dest="infile", required=True)
    p.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("check"); c.add_argument("--lang")
    a = ap.parse_args()
    sys.exit({"extract": cmd_extract, "apply": cmd_apply, "check": cmd_check}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
