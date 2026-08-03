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
# The brand domain, not the Firebase name. Both hosts serve this same site, but
# dagric.com is the one the product itself hands out — HOME_URL, SUPPORT_URL and
# BUG_REPORT_URL in /etc/os-release, /etc/motd, the Calamares branding and the
# back-link two lines below all say dagric.com. Canonicals pointing anywhere else
# tell Google to index the preview hostname and drop the one every owner is sent
# to. The APT update channel is a separate matter and still lives on
# dagric-os.web.app (config/includes.chroot/etc/apt/sources.list.d/dagric.list);
# do not "fix" that one to match this.
SITE = "https://dagric.com"

# Web-only additions. The offline copy must not carry these: a canonical URL and
# an og:image are meaningless to a reader with no internet, and a link back to
# the website is worse than meaningless — it is a dead end on a machine that may
# be offline precisely because the Wi-Fi is what they are trying to fix.
HEAD_EXTRA = """<link rel="canonical" href="{site}/guide{suffix}">
{alternates}<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/guide{suffix}">
<meta property="og:image" content="{site}/assets/dagric-logo.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a111c">
<link rel="icon" href="/favicon.ico" sizes="32x32">
"""

# WHY hreflang. Six pages that say the same thing in six languages look to a
# search engine like one page duplicated six times unless they declare each
# other, and the usual outcome is that five get filtered out of the index. The
# whole point of translating the guide is that a Spanish speaker searching in
# Spanish finds the Spanish one; without this they find the English one or
# nothing. x-default points at English because that is the copy that is complete
# and reviewed — the four new translations are machine-assisted and unreviewed,
# which the pages themselves say in their own language.
#
# Every page carries the FULL set including a self-reference, which is what the
# spec requires: a set of alternates that does not list itself is ignored.

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
    # The OS ships five locales — de, es, fr, it, pt_BR — and the guide had two
    # of them. A Spanish or French owner got the whole desktop in their language
    # and then the single most useful document in English, which is the point
    # where "it speaks my language" stops being true.
    #
    # pt_BR maps to the URL /guide/pt-br: the directory keeps the POSIX locale
    # name because that is what /usr/share/locale uses and what the offline copy
    # is found under, but a URL with an underscore and a capital is neither
    # idiomatic nor reliably handled. The suffix and the directory are allowed
    # to differ precisely because publish() takes them from here rather than
    # deriving one from the other.
    #
    # Each description is written in its own language rather than translated
    # mechanically from the English one: it is the snippet a search engine shows
    # to a speaker of that language, and it is the only line of this file a
    # visitor sees before deciding whether to click.
    os.path.join("es", "index.html"): dict(
        suffix="/es", label="dagric.com",
        title="Guía de Dagric OS — su primera semana, resuelta",
        desc=("La guía que viene dentro de Dagric OS: llegar desde Windows, el primer "
              "día, impresoras, Wi-Fi, atajos de teclado, programas de Windows y qué "
              "hacer cuando algo va mal.")),
    os.path.join("fr", "index.html"): dict(
        suffix="/fr", label="dagric.com",
        title="Guide de Dagric OS — votre première semaine",
        desc=("Le guide fourni dans Dagric OS : venir de Windows, le premier jour, "
              "imprimantes, Wi-Fi, raccourcis clavier, programmes Windows et que faire "
              "quand quelque chose ne va pas.")),
    os.path.join("it", "index.html"): dict(
        suffix="/it", label="dagric.com",
        title="Guida di Dagric OS — la tua prima settimana",
        desc=("La guida inclusa in Dagric OS: arrivare da Windows, il primo giorno, "
              "stampanti, Wi-Fi, scorciatoie da tastiera, programmi Windows e cosa fare "
              "quando qualcosa non funziona.")),
    os.path.join("pt_BR", "index.html"): dict(
        suffix="/pt-br", label="dagric.com",
        title="Guia do Dagric OS — sua primeira semana",
        desc=("O guia que vem dentro do Dagric OS: vindo do Windows, o primeiro dia, "
              "impressoras, Wi-Fi, atalhos de teclado, programas do Windows e o que "
              "fazer quando algo dá errado.")),
}


# The offline copy is a directory of relative links, which is right for file://
# and wrong for the web. firebase.json sets trailingSlash:false, so the page is
# served at /guide with NO trailing slash and "guide.css" resolves to
# /guide.css — a 404. Site-absolute paths are right at every URL shape, and only
# the web copy gets them.
#
# DERIVED FROM PAGES, NOT HAND-WRITTEN. The previous version of this table was
# six literal strings that knew about exactly one translation, and adding four
# more languages would have published four pages whose language switcher pointed
# at ../es/index.html — a path that does not exist on the web, since every guide
# is served from a flat /guide/<lang>. Four dead links per page, on the one
# control whose entire job is getting a reader to a language they can read.
# Deriving it means the PAGES dict above is the only place a language is
# declared, which is also what keeps /guide/pt-br and the pt_BR/ source
# directory from drifting apart.
#
# No collisions between the two forms: the search strings carry their own
# `href="` prefix, so 'href="es/index.html"' cannot match inside
# 'href="../es/index.html"' — the character after the quote differs.
def _link_rewrites():
    out = [('href="guide.css"',      'href="/guide/guide.css"'),
           ('src="guide.js"',        'src="/guide/guide.js"'),
           ('href="../guide.css"',   'href="/guide/guide.css"'),
           ('src="../guide.js"',     'src="/guide/guide.js"'),
           # English, linked from a translation and from itself.
           ('href="../index.html"',  'href="/guide"'),
           ('href="index.html"',     'href="/guide"')]
    for _rel, _m in PAGES.items():
        _d = os.path.dirname(_rel)
        if not _d:
            continue
        _url = "/guide" + _m["suffix"]
        out.append(('href="%s/index.html"' % _d,    'href="%s"' % _url))
        out.append(('href="../%s/index.html"' % _d, 'href="%s"' % _url))
    return tuple(out)


LINK_REWRITES = _link_rewrites()

# The hreflang tag for each entry, derived from the URL suffix rather than the
# source directory: "/pt-br" is already the BCP-47 shape ("pt-BR" case-
# insensitively), while the source directory "pt_BR" is the POSIX locale name
# and is not valid in an hreflang at all.
ALTERNATES = "".join(
    '<link rel="alternate" hreflang="%s" href="%s/guide%s">\n'
    % (m["suffix"].lstrip("/") or "en", SITE, m["suffix"])
    for m in PAGES.values()
) + '<link rel="alternate" hreflang="x-default" href="%s/guide">\n' % SITE


def _lastmod(rel):
    """The date this language's guide was last actually edited.

    From git, not from the filesystem: a fresh clone stamps every file with the
    checkout time, so mtime would tell a crawler that all six translations
    changed today, every time CI runs. `%cs` is the committer date as a bare
    YYYY-MM-DD, which is exactly the sitemap format. Falls back to mtime when
    git is unavailable or the file is not committed yet.
    """
    src = os.path.join(SRC, rel)
    try:
        import subprocess
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", src],
                             cwd=ROOT, capture_output=True, text=True, timeout=15)
        d = out.stdout.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            return d
    except Exception:
        pass
    import time
    return time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(src)))


def sync_sitemap():
    """Rewrite the guide block of site/sitemap.xml from PAGES.

    The block used to be hand-written, under a comment asking whoever adds a
    language to add its URL here too. That instruction survived exactly one
    language: four translations shipped and the sitemap still listed two, so
    the pages existed, cross-linked and carried hreflang — and nothing told a
    crawler they were there. An instruction in a comment is not a mechanism.
    """
    path = os.path.join(ROOT, "site/sitemap.xml")
    if not os.path.exists(path):
        print("  SKIP    sitemap.xml (not found)")
        return
    xml = open(path, encoding="utf-8").read()
    begin = "  <!-- BEGIN guide urls -->"
    end = "  <!-- END guide urls -->"
    if begin not in xml or end not in xml:
        print("  SKIP    sitemap.xml (markers absent — add them once by hand)")
        return
    rows = []
    for rel, meta in PAGES.items():
        if not os.path.exists(os.path.join(SRC, rel)):
            continue                       # never advertise a page we did not write
        # English is the reviewed, complete copy and the one that ranks; the
        # translations are worth indexing but should not outrank it.
        pri = "0.8" if not meta["suffix"] else "0.6"
        rows.append('  <url><loc>%s/guide%s</loc><lastmod>%s</lastmod>'
                    '<priority>%s</priority></url>'
                    % (SITE, meta["suffix"], _lastmod(rel), pri))
    head, _, rest = xml.partition(begin)
    _, _, tail = rest.partition(end)
    open(path, "w", encoding="utf-8", newline="\n").write(
        head + begin + "\n" + "\n".join(rows) + "\n" + end + tail)
    print("  sitemap %d guide URL%s" % (len(rows), "" if len(rows) == 1 else "s"))


def publish():
    if not os.path.isdir(SRC):
        sys.exit("guide source not found: " + SRC)
    # One directory per translation. Derived from each entry's `suffix` rather
    # than from its source directory, because the two are deliberately allowed
    # to differ: the source is pt_BR/ (the POSIX locale name, matching
    # /usr/share/locale and the offline copy) while the URL is /guide/pt-br.
    for _m in PAGES.values():
        if _m["suffix"]:
            os.makedirs(os.path.join(DST, _m["suffix"].lstrip("/")), exist_ok=True)

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
        html = re.sub(r'<link rel="alternate" hreflang="[^"]*"[^>]*>\n?', "", html)
        html = re.sub(r'<meta property="og:[^>]*>\n?', "", html)
        html = re.sub(r'<meta name="twitter:card"[^>]*>\n?', "", html)
        html = re.sub(r'<meta name="theme-color"[^>]*>\n?', "", html)
        html = re.sub(r'<link rel="icon" href="/favicon\.ico"[^>]*>\n?', "", html)
        html = re.sub(r'<a class="back-to-site".*?</a>\n?', "", html, flags=re.S)

        # WHY REWRITE PATHS. The offline copy is a directory of relative links,
        # which is right for file:// and wrong for the web. firebase.json sets
        # trailingSlash:false, so this page is served at /guide with NO trailing
        # slash and "guide.css" resolves to /guide.css — a 404. The published
        # guide rendered with no stylesheet and no JavaScript at all, and the
        # German page's "../index.html" language switch landed on the marketing
        # homepage instead of the English guide. Site-absolute paths are right at
        # every URL shape, and only the web copy gets them — the offline copy is
        # still opened as a file and must keep its relative links.
        #
        # Not <base href>: that would also rebase the guide's 22 fragment-only
        # TOC links and break in-page navigation.
        for was, now in LINK_REWRITES:
            html = html.replace(was, now)

        # THE ONE LINK THAT CANNOT BE REWRITTEN, ONLY REMOVED. The German guide
        # offers the 95-page manual as ../../manual/index.html, which is correct
        # offline — it resolves to /usr/share/dagric/manual/, which is in the
        # image — and a hard 404 on the web, where the manual is not published at
        # all. The table above rewrote every other relative path and left this one
        # alone, so it survived into site/guide/de/index.html and was the only
        # broken internal link on the site.
        #
        # There is nothing to point it at, so unwrap the anchor and keep every
        # word: the sentence immediately before it already says to open the
        # manual from the start menu or with `dagric-manual`, which is exactly
        # what the English guide's #manual section does without linking anywhere.
        # Line-break tolerant (the anchor spans two source lines) and it will
        # catch the same link if another translation grows one.
        html, n_manual = re.subn(r'<a href="\.\./\.\./manual/[^"]*"[^>]*>(.*?)</a>',
                                 r'<em>\1</em>', html, flags=re.S)
        if n_manual:
            print("  unlink  %s  (%d offline-only manual link%s)"
                  % (rel, n_manual, "" if n_manual == 1 else "s"))

        extra = HEAD_EXTRA.format(site=SITE, alternates=ALTERNATES, **meta)
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

        # Published under the URL directory, not the source directory. For four
        # of the five these are the same string; for pt_BR they are not, and
        # writing to the source name would publish /guide/pt_BR — an underscore
        # and a capital in a URL, which is neither idiomatic nor reliably
        # handled once a CDN or a mail client gets hold of it.
        out = os.path.join(DST, meta["suffix"].lstrip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8", newline="\n").write(html)
        print("  page    %-22s -> /guide%-8s (%d KB)"
              % (rel.replace(os.sep, "/"), meta["suffix"] or "", len(html) // 1024))

    sync_sitemap()
    print("\n  published to site/guide/ — deploy the site to make it live")


if __name__ == "__main__":
    publish()
