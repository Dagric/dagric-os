#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Publish the in-OS user guide to the website.

WHY THIS EXISTS. The guide that ships inside the OS is by some distance the most
useful thing written about Dagric: 21 sections answering what a Windows switcher
actually asks — will my printer work, where did my files go, what do I press
instead of Ctrl+Esc, what do I do when something breaks. The website's "Guide"
link pointed at getting-started.html, which is four sections of install steps.

So the best sales material on the whole project was invisible until AFTER
someone had already installed. That is backwards: those 21 sections are exactly
what a person reads while deciding whether to risk leaving Windows.

WHY A SCRIPT AND NOT A COPY. Copied files drift. The guide inside the image is
the source of truth — it is the one an owner reads offline with no internet, and
it must never be worse than the marketing copy of it. This regenerates the web
version from that source, so editing the guide once updates both.

Run:  python3 tools/publish-guide.py     (then deploy the site)
"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "config/includes.chroot/usr/share/dagric/guide")
DST  = os.path.join(ROOT, "site/guide")
SITE = "https://dagric-os.web.app"

# Web-only additions. The offline copy must not carry these: a canonical URL and
# an og:image are meaningless to a reader with no internet, and a link back to
# the website is worse than meaningless — it is a dead end on a machine that may
# be offline precisely because the Wi-Fi is what they are trying to fix.
HEAD_EXTRA = """<link rel="canonical" href="{site}/guide{suffix}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/guide{suffix}">
<meta property="og:image" content="{site}/assets/dagric-logo.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a111c">
<link rel="icon" href="/favicon.ico" sizes="32x32">
"""

BACK_LINK = ('<a class="back-to-site" href="/" '
             'style="display:block;margin-top:.75rem;font-size:.85rem;opacity:.75">'
             '&larr; {label}</a>')

PAGES = {
    "index.html": dict(
        suffix="", label="dagric.com",
        title="Dagric OS User Guide — your first week, answered",
        desc=("The guide that ships inside Dagric OS: coming from Windows, your first "
              "day, printers, Wi-Fi, shortcuts, running Windows programs, and what to "
              "do when something goes wrong.")),
    os.path.join("de", "index.html"): dict(
        suffix="/de", label="dagric.com",
        title="Dagric OS Handbuch — Ihre erste Woche",
        desc=("Das Handbuch aus Dagric OS: Umstieg von Windows, der erste Tag, Drucker, "
              "WLAN, Tastenkürzel, Windows-Programme und was zu tun ist, wenn etwas "
              "nicht funktioniert.")),
}


def publish():
    if not os.path.isdir(SRC):
        sys.exit("guide source not found: " + SRC)
    os.makedirs(os.path.join(DST, "de"), exist_ok=True)

    # Assets copy verbatim — the styling is the thing being published.
    for asset in ("guide.css", "guide.js"):
        s = os.path.join(SRC, asset)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(DST, asset))
            print("  asset   %s" % asset)

    for rel, meta in PAGES.items():
        s = os.path.join(SRC, rel)
        if not os.path.exists(s):
            print("  SKIP    %s (not in source)" % rel)
            continue
        html = open(s, encoding="utf-8").read()

        # Idempotent: strip any previously injected block before adding it again,
        # so re-running does not stack duplicate canonicals.
        html = re.sub(r'<link rel="canonical" href="[^"]*/guide[^"]*">\n?', "", html)
        html = re.sub(r'<meta property="og:[^>]*>\n?', "", html)
        html = re.sub(r'<meta name="twitter:card"[^>]*>\n?', "", html)
        html = re.sub(r'<meta name="theme-color"[^>]*>\n?', "", html)
        html = re.sub(r'<link rel="icon" href="/favicon\.ico"[^>]*>\n?', "", html)
        html = re.sub(r'<a class="back-to-site".*?</a>\n?', "", html, flags=re.S)

        extra = HEAD_EXTRA.format(site=SITE, **meta)
        if "</head>" not in html:
            sys.exit("no </head> in " + rel)
        html = html.replace("</head>", extra + "</head>", 1)

        # A route home, in the sidebar just above the search box. Web-only, for
        # the reason in the comment at the top of this file.
        #
        # Matched by regex rather than an exact string: the source is
        # hand-indented and the leading whitespace on that line is not something
        # to depend on. An exact-match anchor silently inserted nothing the first
        # time this ran, which is the failure mode worth designing out — it looks
        # like success.
        html, n = re.subn(
            r'([ \t]*)<div class="gsearch"',
            lambda m: m.group(1) + BACK_LINK.format(label=meta["label"]) + "\n"
                      + m.group(1) + '<div class="gsearch"',
            html, count=1)
        if n != 1:
            sys.exit("could not place the back-link in %s — sidebar markup changed" % rel)

        out = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8", newline="\n").write(html)
        print("  page    %s  (%d KB)" % (rel, len(html) // 1024))

    print("\n  published to site/guide/ — deploy the site to make it live")


if __name__ == "__main__":
    publish()
