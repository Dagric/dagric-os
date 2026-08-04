#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-align translated guides to the English section order, without retranslating.

WHY THIS EXISTS. The English guide was reordered for a good reason — "Bringing
your files from Windows" moved from position 12 to position 3, and "When
something goes wrong" from 20 to 14, because that is the order a frightened
switcher actually needs — and the five translations were left in the old order.
Nothing broke: each locale is a self-contained page and every in-page fragment
still resolves. But the guide now tells a German reader to do things in one
order and an English reader another, and that is the drift this project spends
its time preventing.

RETRANSLATING WOULD BE THE WRONG FIX AND THE EXPENSIVE ONE. The sections did not
change; only their sequence did. Every <section id="..."> is a flat sibling with
a stable id (verified: 21 opens, 21 closes, maximum nesting depth 1), so the
correct repair is to move blocks, not to regenerate prose that five catalogues
of review work already went into.

WHAT THIS DOES NOT TOUCH. Not one character inside any section, and not one
character of any language's own words. It reorders <section> blocks and the
sidebar links that point at them, and it refuses outright if a locale's set of
ids is not exactly the English set — a mismatch there means a section really was
added or removed, which is a translation job and not this script's business.

Usage:
  python tools/i18n-guide-align.py --check
  python tools/i18n-guide-align.py --apply
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "config/includes.chroot/usr/share/dagric/guide")
LOCALES = ["de", "es", "fr", "it", "pt_BR"]

SEC_RE = re.compile(r'([ \t]*)<section\b[^>]*\bid="([^"]+)"[^>]*>.*?</section>\s*\n?',
                    re.S)
TOC_RE = re.compile(r'(<nav class="toc"[^>]*>)(.*?)(</nav>)', re.S)
LINK_RE = re.compile(r'[ \t]*<a href="#([^"]+)"[^>]*>.*?</a>\s*\n?', re.S)


def read(p):
    return io.open(p, encoding="utf-8").read()


def section_order(html):
    return [m.group(2) for m in SEC_RE.finditer(html)]


def reorder_sections(html, order):
    blocks, ids = {}, []
    for m in SEC_RE.finditer(html):
        blocks[m.group(2)] = m.group(0)
        ids.append(m.group(2))
    if set(ids) != set(order):
        return None, "id set differs from English"
    if ids == order:
        return html, "already aligned"
    first = SEC_RE.search(html)
    # Splice from the start of the first section to the end of the last, so
    # everything around them — hero, langbar, langnote, footer — is untouched.
    last_end = 0
    for m in SEC_RE.finditer(html):
        last_end = m.end()
    body = "".join(blocks[i] for i in order)
    return html[:first.start()] + body + html[last_end:], "reordered"


def reorder_toc(html, order):
    """Sort the sidebar links into the section order, keeping group headings put.

    Group headings (.navgroup) stay where they are and the links between them
    are refilled in English order. That is deliberate: a heading is a piece of
    translated prose, and moving one would need a translator. Refilling the
    links under it does not.
    """
    m = TOC_RE.search(html)
    if not m:
        return html, "no toc"
    inner = m.group(2)
    links = LINK_RE.findall(inner)
    if not links:
        return html, "no toc links"
    rank = {sid: i for i, sid in enumerate(order)}
    if any(l not in rank for l in links):
        return html, "toc points at an unknown section"
    wanted = sorted(links, key=lambda s: rank[s])
    if wanted == links:
        return html, "toc already aligned"
    it = iter(wanted)
    out = LINK_RE.sub(
        lambda mm: re.sub(r'href="#[^"]+"', 'href="#%s"' % next(it), mm.group(0), count=1),
        inner)
    return html[:m.start(2)] + out + html[m.end(2):], "toc reordered"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    en = read(os.path.join(SRC, "index.html"))
    order = section_order(en)
    print("English order: %d sections" % len(order))

    rc = 0
    for loc in LOCALES:
        p = os.path.join(SRC, loc, "index.html")
        if not os.path.exists(p):
            print("  %-6s missing" % loc)
            continue
        html = read(p)
        before = section_order(html)
        new, why = reorder_sections(html, order)
        if new is None:
            print("  %-6s REFUSED: %s" % (loc, why))
            rc = 1
            continue
        new, why2 = reorder_toc(new, order)
        moved = sum(1 for x, y in zip(before, order) if x != y)
        print("  %-6s %-12s %-20s (%d of %d sections were out of place)"
              % (loc, why, why2, moved, len(order)))
        if a.apply and new != html:
            io.open(p, "w", encoding="utf-8", newline="\n").write(new)

    if not a.apply:
        print("\n(dry run — pass --apply to write)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
