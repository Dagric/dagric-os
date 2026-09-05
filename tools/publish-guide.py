#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
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
import os, re, sys

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
{alternates}<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/guide{suffix}">
<meta property="og:image" content="{site}/assets/dagric-logo.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a111c">
<script src="/assets/theme.js"></script>
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

# ── THE ROUTE BACK, AND THE ROUTE ONWARD ────────────────────────────────────
#
# WHAT WAS HERE. A single anchor injected into the sidebar above the search box:
# `&larr; dagric.com`, .85rem, opacity .75, no border, no padding. Measured in a
# browser against the published guide it was a 224x23px target on desktop and
# 101x23px on a 360px phone — under half the 44px minimum this project rebuilt
# both the site nav and the site footer to meet, styled to recede, and it was
# the ONLY route back to dagric.com from six pages.
#
# It was also breaking the phone header. The sidebar collapses to a two-column
# grid below 900px (brand | search, then the section strip across both), and an
# extra child injected between .brand and .gsearch took the cell the search box
# was laid out for and pushed the search onto a row of its own. A third row on a
# sticky header, on the surface most likely to be read on a phone.
#
# WHAT REPLACES IT, AND WHY IT IS A BAR RATHER THAN A BETTER LINK. The file's
# own opening argument is that these 21 sections are "exactly what a person
# reads while deciding whether to risk leaving Windows" — i.e. this is the
# project's best sales material and it is indexed. A visitor who lands on
# /guide from a search result could not reach /download or /pro at all: no nav,
# no in-content links to either, and one 23px footnote to the homepage. That is
# a funnel with no exit, on the page most likely to be somebody's first contact
# with the product.
#
# So the published copy gets a real header bar: the home control at 44px with a
# border, and the three site destinations that matter from here, with Download
# as the filled one — the same order and the same words the site's own nav uses,
# so nothing new is claimed and nothing is renamed.
#
# THE OFFLINE COPY GETS NEITHER, and that is the whole reason this lives in the
# publisher. Every one of these links is dead on a machine with no internet —
# which is the machine reading the offline guide, quite possibly because the
# Wi-Fi is the thing being fixed. Same split, same reason, as the canonical URL
# and the og:image above.
#
# lang="en" ON THE NAV IS NOT DECORATION. Five of the six published pages are
# not in English, but "Features", "Pro" and "Download" are the names of English
# pages on an English website — translating the labels would promise a
# translated destination that does not exist. Marking the run as English is what
# stops a German screen reader pronouncing them as German.
#
# The footer row carries the same links again as plain text, not a landmark: the
# bar is sticky on desktop but static on a phone (a second sticky bar over the
# guide's own sticky section strip would eat a quarter of the screen), so on a
# phone the route back has to exist at the end of an 11,000px page too. Written
# as a <div> of links rather than a <nav> for the same reason the site's own
# footer uses a <span>: two navigation landmarks with the same purpose need two
# distinguishable names, and the honest fix is to only claim the landmark once.
SITE_BAR = (
    '<header class="sitebar"><div class="sitebar-in">\n'
    '<a class="sitebar-home" href="/"><span aria-hidden="true">&larr;</span> {label}</a>\n'
    '<nav class="sitebar-nav" lang="en" aria-label="Dagric OS website">'
    '<a href="/features">Features</a>'
    '<a href="/pro">Pro</a>'
    '<a class="sitebar-cta" href="/download">Download</a>'
    '</nav>\n'
    '</div></header>')

SITE_FOOT = (
    '<div class="sitefoot" lang="en">'
    '<a href="/">{label}</a>'
    '<a href="/features">Features</a>'
    '<a href="/pro">Pro</a>'
    '<a href="/download">Download</a>'
    '<a href="/support">Support</a>'
    '</div>')

# Appended to the PUBLISHED guide.css only. Written entirely against the
# guide's own tokens, so it follows whatever palette that file resolves to
# (dark, the light block, or the print block) with no second set of colours to
# keep in step — and so it cannot drift from the guide the way a hand-copied
# palette would. The one measured pair worth recording: the filled Download
# control is var(--accent) under var(--bg). Measured in a browser on the
# published /guide at 1440px, not derived from the token table:
#   dark   #0a111c on #3fa9f5 = 7.39:1
#   light  #f3f6fa on #1c6ea8 = 5.04:1
# Both clear WCAG 1.4.3 AA at any size. There is deliberately no print figure:
# guide.css's print block lists .sitebar and .sitefoot in its display:none
# furniture rule, so this control does not appear on paper at all — an earlier
# version of this comment quoted 8.49:1 for a print palette the bar never
# renders in.
#
# NOT site.css. Loading the marketing sheet here would be a second stylesheet,
# a foreign visual language, and — decisively — a token collision: guide.css
# and site.css both define --bg, --line, --muted and --accent with different
# meanings, so whichever loaded second would repaint the other's components.
SITE_CSS = """

/* ── WEB-ONLY, APPENDED BY tools/publish-guide.py ─────────────────────────
   The site bar and the footer link row. The offline copy has neither: see the
   comment on SITE_BAR in that script for why the split exists at all.
   --sitebar-h IS MEASURED, NOT ESTIMATED: 44px of control plus 2x8px of
   padding plus the 1px bottom rule = 61px, confirmed in a browser at 1280px
   and at 901px, the narrowest width at which the bar is sticky. Two things
   below are derived from it and would silently land a heading under the bar if
   it were wrong, which is exactly the drift site.css's --nav-h token exists to
   prevent — so it is one number here too. */
:root { --sitebar-h:61px; }

.sitebar {
  background:var(--bg);
  border-bottom:1px solid var(--line-soft);
}
.sitebar-in {
  max-width:1120px; margin:0 auto; padding:8px 32px;
  display:flex; align-items:center; gap:4px 16px; flex-wrap:wrap;
}
/* 44px on every control in this bar, which is the whole point of replacing
   what was here: the old back-link was 23px tall. min-height rather than
   padding so the number is stated rather than arrived at. */
.sitebar a {
  display:inline-flex; align-items:center; min-height:44px;
  padding:0 12px; border-radius:8px;
  font-size:.9rem; font-weight:500; color:var(--ink-soft);
  border:1px solid transparent;
}
.sitebar a:hover { color:var(--ink); background:var(--line-soft); text-decoration:none; }
/* WHY BOTH MODIFIERS ARE WRITTEN `.sitebar a.<mod>` AND NOT `.<mod>`.
   The base rule above is `.sitebar a` — (0,1,1), a class plus a type. A bare
   `.sitebar-cta` is (0,1,0) and LOSES to it, so every declaration these two
   rules share was being thrown away no matter where they sat in the file.
   Measured in a browser against the published /guide before this was written:
     Download control, dark  — rgb(195,207,221) on rgb(63,169,245) = 1.62:1
     Download control, light — rgb(44,60,80)   on rgb(28,110,168) = 2.06:1
   i.e. --ink-soft on --accent, the filled call to action rendering accent text
   on an accent fill, failing WCAG 1.4.3 AA (4.5:1) on both themes. The same
   loss silently took font-weight (600 -> 500) and padding (18px -> 12px) off
   the CTA and font-weight and colour off the home control, and on :hover
   `.sitebar a:hover` at (0,2,1) beat `.sitebar-cta:hover` at (0,2,0) as well,
   so pointing at Download turned the filled button into a grey ghost.
   Qualifying each modifier with the same `.sitebar a` it has to override makes
   it (0,2,1) — one step above the base and below nothing — and the :hover
   forms (0,3,1) above the base's (0,2,1). Do not "tidy" these back to bare
   class selectors: the whole bar depends on this. */
/* The route home is the one control in this bar a reader is looking for, so it
   is the one drawn as a control. Fill plus rule rather than rule alone: --line
   is 12% alpha and on its own it read as a bold word rather than as a button —
   which is the exact criticism the footnote it replaces earned. This is the
   same treatment .langbar a already uses (--bg-raise fill, --line-soft edge),
   so the bar borrows the guide's existing pill rather than inventing one.
   The border is not this control's sole affordance — it carries the word
   "dagric.com" and an arrow — so it is not held to WCAG 1.4.11's 3:1. */
.sitebar a.sitebar-home { background:var(--bg-raise); border-color:var(--line);
                          color:var(--ink); font-weight:600; }
.sitebar a.sitebar-home:hover { border-color:var(--accent-brd); background:var(--panel-2); }
.sitebar-home span { margin-right:7px; color:var(--accent); }
.sitebar-nav { display:flex; align-items:center; gap:4px; flex-wrap:wrap; margin-left:auto; }
.sitebar a.sitebar-cta { background:var(--accent); color:var(--bg); font-weight:600; padding:0 18px; }
.sitebar a.sitebar-cta:hover { background:var(--accent); color:var(--bg); filter:brightness(1.08); }

/* At 360px the four controls need 419px and get 360, so the row wraps — which
   is correct and is what the site's own nav does rather than hiding links
   behind a menu. margin-left:auto would then push the wrapped row hard right
   and leave a ragged gap under the home control; on one line it is alignment,
   on two it is a hole. Zeroed below 640 so the second row starts where the
   first one does. */
@media (max-width:640px) {
  .sitebar-in { padding:6px 16px; gap:2px 6px; }
  .sitebar-nav { margin-left:0; }
}

/* Sticky only where there is room for it. On desktop the route home has to
   stay where the old sidebar link was — permanently on screen — or this is a
   regression dressed as a fix. On a phone the guide already pins its own
   search-and-sections header, measured at up to 134.8px; a second sticky bar
   above it would take the pair past a quarter of the screen, which is the
   exact defect the phone block in this file was written to end. Below 901px
   the bar simply sits at the top of the document and scrolls away, and the
   footer row is what carries the reader home from the bottom. */
@media (min-width:901px) {
  .sitebar { position:sticky; top:0; z-index:10; }
  /* Both derived from --sitebar-h. The sidebar used to stick at 24px and the
     scrollport used to inset by 28px; each keeps its original clearance,
     measured from underneath the bar instead of from the top of the window. */
  .sidebox { top:calc(var(--sitebar-h) + 24px);
             max-height:calc(100vh - var(--sitebar-h) - 48px); }
  html { scroll-padding-top:calc(var(--sitebar-h) + 28px); }
  .side { padding-top:24px; }
}

/* Plain links, no landmark — see the SITE_FOOT comment. It sits under the
   colophon and inherits its hairline, so it costs one row and no new rule. */
.sitefoot {
  display:flex; flex-wrap:wrap; gap:2px 4px;
  margin-top:6px;
}
.sitefoot a {
  display:inline-flex; align-items:center; min-height:44px;
  padding:0 10px; margin-left:-10px; border-radius:7px;
  font-size:.85rem; color:var(--muted);
}
.sitefoot a + a { margin-left:0; }
.sitefoot a:hover { color:var(--ink); background:var(--line-soft); text-decoration:none; }

/* ── the light/dark switch ────────────────────────────────────────────────
   WEB COPY ONLY, and only because the site gained a light mode. Before that
   the guide correctly had no switch: assets/theme.js's own comment said the
   guide "does not host the switch ... if the guide is ever given the control,
   it needs .themebox/.themetog in guide.css first", because those classes are
   declared in site.css and the guide loads this file instead. This is that
   prerequisite; theme.js now mounts the control in .sitebar-in when it finds
   one.
   Leaving it out stopped making sense the moment the site had two modes. A
   reader in light mode clicked Guide, got a guide that correctly followed
   their choice, and then had no way to change it without navigating to a
   different page to find the control. The theme was never the problem —
   apply() runs before any mount — the missing control was.
   Written entirely against this file's OWN tokens, so it follows whatever
   palette guide.css resolves to and there is no second set of colours to keep
   in step. The offline copy has no .sitebar and therefore no switch, which is
   right: it follows the desktop's own setting through prefers-color-scheme
   and has no second preference to store.
   44px because this bar is the one place a phone reader can reach it, and the
   guide's own sidebar links and language pills were both rebuilt to that
   height — a 31px control beside them would be the odd one out again. */
.themebox-bar { display:flex; align-items:center; margin-left:auto; }
.themebox-bar .themetog {
  min-height:44px; padding:9px 14px;
  background:var(--bg-raise); cursor:pointer;
  border:1px solid var(--line-soft); border-radius:99px;
  color:var(--muted); font:500 .85rem/1 inherit;
}
.themebox-bar .themetog:hover {
  color:var(--ink); border-color:var(--accent-brd);
}
/* The bar is a flex row whose home link is already pushed left; on a phone it
   wraps, and the switch must not land alone on a third row above an 11,000px
   document. */
@media (max-width:640px) {
  .themebox-bar { margin-left:0; }
  .themebox-bar .themetog { padding:9px 12px; font-size:.8rem; }
}
"""

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


# ── light-mode re-scoping ───────────────────────────────────────────────────
# Rewrites `@media (prefers-color-scheme: light){ ... }` into rules scoped by
# the website's own `:root[data-theme="light"]`, preserving any EXTRA media
# conditions that were ANDed onto the colour-scheme test.
#
#   @media (prefers-color-scheme: light){ :root{--bg:#fff} .mark{...} }
#     ->  :root[data-theme="light"] {--bg:#fff}
#         :root[data-theme="light"] .mark {...}
#
#   @media (prefers-color-scheme: light) and (max-width:900px){ .sidebox{...} }
#     ->  @media (max-width:900px) {
#           :root[data-theme="light"] .sidebox {...}
#         }
#
# Braces are matched by counting, not by regex: the band contains nested rules
# and a non-greedy `.*?` would stop at the first inner `}`. The walker raises
# rather than emitting silent garbage if it ever runs off the end of the file
# or meets a nested at-rule it cannot scope.
#
# NOTE ON SPECIFICITY, because it decides whether this works at all: the source
# rules are things like `:root`, `code`, `.tip::before` at (0,1,0) or less, and
# each becomes `:root[data-theme="light"] <sel>` at (0,2,0)+, so every rescoped
# rule outranks the dark default it has to override no matter where it lands in
# the file. That is the property the old media-query form got for free and the
# reason this rewrite is safe to do positionally in place.
#
# ...AND IT IS ALSO WHY THE RESULT MUST BE WRAPPED IN `@media screen`.
# The lift from (0,1,x) to (0,2,x) is not free: guide.css ends with an
# `@media print` block whose palette is `:root { ... }` at (0,1,0) and whose
# component overrides are `code`, `.tip`, `.tip::before`, `kbd`, `.mark` at
# (0,1,0)/(0,1,1). OFFLINE those two bands tie and the print block wins on
# source order, because it is last — which is the only reason the offline copy
# is correct. Rescoping breaks that tie in the light band's favour on every
# selector at once, so a visitor who had chosen the light page and pressed
# Ctrl+P would have printed the light SCREEN palette instead of the ink one.
# The worst of it was not the palette: `.tip::before` is `background:#1c6ea8;
# color:#ffffff` in the light band and browsers drop background-color when
# printing, so every "Tip" badge in the guide would have printed white on
# white — invisible — on the one document in this project people actually put
# on paper, and for exactly the readers who had used the theme control.
# `@media screen` restores the original arrangement by matching, not by
# specificity: in print media the band cannot apply at all and the print block
# is once again the last word on colour. site.css solves the identical problem
# from the other side (`:root,:root[data-theme]` in its own print block); it is
# already correct there and needs no change.
ROOT_SEL = ':root[data-theme="light"]'
_LIGHT_AT = re.compile(
    r'@media\s*\(\s*prefers-color-scheme:\s*light\s*\)\s*'
    r'(?P<rest>(?:and\s*\([^)]*\)\s*)*)\{')


def _scope_selector(sel):
    """`:root`/`html` become the attribute itself; everything else nests under it."""
    out = []
    for part in sel.split(','):
        part = part.strip()
        if not part:
            continue
        if part in (':root', 'html', ':root, html'):
            out.append(ROOT_SEL)
        else:
            out.append(ROOT_SEL + ' ' + part)
    return ', '.join(out)


# A comment sitting BETWEEN two rules inside the light band, which is where
# anybody would put one, lands in the text this walker reads as a selector —
# and _scope_selector then splits that text on every comma the prose contains
# and prefixes each fragment with the attribute. The first comment written that
# way published this:
#     :root[data-theme="light"] /* THE PRO BADGE ... --accent-bg is
#     8% alpha here, :root[data-theme="light"] and .pro sets it ... */
#     .pro { color:#155d8e; }
# which happens to still parse to the right selector only because the CSS
# tokenizer treats /* ... */ as one comment and throws the injected fragments
# away with it. That is luck, not correctness: a comment containing a `*/`
# earlier than expected, or a `{`, would emit a rule that either matches
# nothing or matches everything, silently, in a file nobody reads because it is
# generated. Comments are lifted out here and re-emitted ahead of the rule, so
# the reasoning survives into the published copy and the selector is only ever
# a selector.
_CSS_COMMENT = re.compile(r'/\*.*?\*/', re.S)
_HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)


def _strip_long_publish_comments(source):
    """Drop implementation essays from generated web assets.

    The offline guide remains the readable source of truth.  The published
    copies should not duplicate multi-paragraph maintenance notes into every
    page or ship them to visitors, while short structural and licence comments
    remain useful.  This mirrors the 320-character public-source gate.
    """
    for pattern in (_HTML_COMMENT, _CSS_COMMENT):
        source = pattern.sub(
            lambda match: match.group(0) if len(match.group(0)) <= 320 else "",
            source,
        )
    had_final_newline = source.endswith("\n")
    source = "\n".join(line.rstrip() for line in source.splitlines())
    return source + ("\n" if had_final_newline else "")


def _split_rules(body):
    """Yield (leading_comments, selector, declarations) per top-level rule."""
    rules, i, n = [], 0, len(body)
    while i < n:
        brace = body.find('{', i)
        if brace == -1:
            break
        head = body[i:brace]
        comments = "\n".join(c.strip() for c in _CSS_COMMENT.findall(head))
        sel = _CSS_COMMENT.sub('', head).strip()
        depth, j = 1, brace + 1
        while j < n and depth:
            if body[j] == '{':
                depth += 1
            elif body[j] == '}':
                depth -= 1
            j += 1
        rules.append((comments, sel, body[brace + 1:j - 1]))
        i = j
    return rules


def _rescope_light(css):
    """Return (rewritten_css, count). A no-op when nothing matches."""
    n = 0
    while True:
        m = _LIGHT_AT.search(css)
        if not m:
            break
        depth, j = 1, m.end()
        while j < len(css) and depth:
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
            j += 1
        if depth:
            raise ValueError("unbalanced @media block in guide.css")
        body = css[m.end():j - 1]
        rest = (m.group('rest') or '').strip()

        parts = []
        for comments, sel, decls in _split_rules(body):
            if sel.startswith('@'):
                raise ValueError("nested at-rule inside light band: %r" % sel)
            if not sel:
                raise ValueError("empty selector in light band near: %r" % comments[:60])
            if comments:
                parts.append(comments)
            parts.append("%s {%s}" % (_scope_selector(sel), decls.rstrip()))
        out = "\n".join(parts)

        # `screen`, always — see the long note above ROOT_SEL. Any extra
        # conditions that were ANDed onto the colour-scheme test are ANDed onto
        # `screen` instead, so a phone-only override stays phone-only and also
        # stops applying to a printed page (print media has a width, so a bare
        # `(max-width:900px)` matches on paper).
        cond = "screen"
        if rest:
            extra = rest[3:].strip() if rest.startswith('and') else rest
            cond = "screen and " + extra
        out = "@media %s {\n%s\n}" % (cond, out)

        css = css[:m.start()] + out + css[j:]
        n += 1
    return css, n


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

    # guide.js copies verbatim. guide.css does not, and the exception is the
    # light-mode band.
    #
    # THE OFFLINE COPY MUST KEEP IT. Its comment is right: the guide was the one
    # part of Dagric that ignored the light/dark choice the first-run wizard asks
    # for on its opening screen. Plasma hands the desktop's scheme to Firefox and
    # Firefox hands it to the page, so following prefers-color-scheme makes the
    # in-OS guide match the desktop with no toggle to maintain. That is correct
    # and it stays.
    #
    # THE WEB COPY MUST NOT FOLLOW THE SYSTEM EITHER, but for a new reason: the
    # website now HAS a light theme and it is opt-in, driven by a data-theme
    # attribute that assets/theme.js stamps from a footer control. A guide that
    # followed prefers-color-scheme would disagree with the site for exactly the
    # visitors who used that control — the same "one nav click, two identities"
    # defect the old code was written to prevent, just pointed the other way.
    # So the web copy is re-scoped to the site's attribute rather than disabled.
    #
    # WHAT WAS HERE BEFORE WAS INVERTED, AND IT WAS LIVE. The old transform
    # emitted `@media not all and (prefers-color-scheme: light)` and its comment
    # called that "the standard idiom for a block that must never match". It is
    # not. `not` negates the WHOLE query, so the block means "whenever the scheme
    # is NOT light" — i.e. dark, plus no-preference. Verified in a browser
    # against the exact published string:
    #     system dark  -> query matches   -> visitors got the LIGHT guide
    #     system light -> query does not  -> visitors got the DARK guide
    # Precisely backwards, on both counts, for every visitor to /guide.
    # The `and (max-width:900px)` variant was worse still: `not (light and
    # <=900px)` is TRUE on a dark desktop at 1440px, so a phone-only override of
    # .sidebox was applying at every desktop width.
    # (`not all` on its own really would never match — the bug is that a second
    # condition turns it into a negation instead of a kill switch. Note also
    # that `(width:0)` is NOT a safe substitute: it evaluates true in some
    # contexts. This is why the block is rewritten rather than disabled.)
    for asset in ("guide.js",):
        s = os.path.join(SRC, asset)
        if os.path.exists(s):
            source = open(s, encoding="utf-8").read()
            open(os.path.join(DST, asset), "w", encoding="utf-8", newline="\n").write(
                _strip_long_publish_comments(source)
            )
            print("  asset   %s" % asset)

    s = os.path.join(SRC, "guide.css")
    if os.path.exists(s):
        css = open(s, encoding="utf-8").read()
        css, n_light = _rescope_light(css)
        if n_light:
            css = ('/* PUBLISHED COPY — generated by tools/publish-guide.py.\n'
                   '   Edit config/includes.chroot/usr/share/dagric/guide/guide.css,\n'
                   '   not this file.\n'
                   '   %d light-mode block(s) re-scoped from\n'
                   '   `@media (prefers-color-scheme: light)` to the website\'s own\n'
                   '   `:root[data-theme="light"]`, so the guide follows the light/dark\n'
                   '   control in the site footer rather than the visitor\'s OS setting.\n'
                   '   Following the OS here would leave the guide in one theme and the\n'
                   '   rest of dagric.com in the other for anyone who used that control.\n'
                   '   The offline copy inside the OS keeps the media query, deliberately:\n'
                   '   in Plasma the desktop scheme IS an expressed preference. */\n'
                   % n_light) + css
        # Appended, never merged into the source: these rules style elements
        # that do not exist offline, so putting them in guide.css itself would
        # ship dead selectors inside the ISO and invite somebody to "use" them.
        open(os.path.join(DST, "guide.css"), "w",
             encoding="utf-8", newline="\n").write(
                 _strip_long_publish_comments(css + SITE_CSS)
             )
        print("  asset   guide.css  (%d light-mode block(s) re-scoped to data-theme,"
              " + site bar)" % n_light)

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
        # back-to-site is the retired sidebar footnote; the two after it are what
        # replaced it. All three are stripped so a tree published by an older
        # version of this script re-publishes clean rather than carrying both.
        html = re.sub(r'<a class="back-to-site".*?</a>\n?', "", html, flags=re.S)
        html = re.sub(r'<header class="sitebar">.*?</header>\n?', "", html, flags=re.S)
        html = re.sub(r'<div class="sitefoot".*?</div>\n?', "", html, flags=re.S)

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

        # The site bar goes ABOVE the shell, not inside the sidebar. That is the
        # correction: the old sidebar link was a child of .sidebox, which is a
        # two-column grid below 900px, so it took the search box's cell and gave
        # the phone header a third row. Outside the shell it is a sibling of the
        # whole layout and cannot disturb either column at any width.
        #
        # Matched by regex rather than an exact string, and asserted afterwards:
        # the source is hand-indented and the leading whitespace on that line is
        # not something to depend on. An exact-match anchor silently inserted
        # nothing the first time this ran, which is the failure mode worth
        # designing out — it looks like success.
        html, n = re.subn(
            r'([ \t]*)<div class="shell">',
            lambda m: m.group(1) + SITE_BAR.format(label=meta["label"]) + "\n"
                      + m.group(1) + '<div class="shell">',
            html, count=1)
        if n != 1:
            sys.exit("could not place the site bar in %s — shell markup changed" % rel)

        # ...and the same links again under the colophon, because the bar is
        # sticky only above 901px. A phone reader who has just finished 11,000px
        # of guide is at the bottom of the page, and the bar is 11,000px away.
        html, n = re.subn(
            r'(<footer class="colophon">.*?</footer>)',
            lambda m: m.group(1) + "\n    " + SITE_FOOT.format(label=meta["label"]),
            html, count=1, flags=re.S)
        if n != 1:
            sys.exit("could not place the footer links in %s — colophon markup changed" % rel)

        # Published under the URL directory, not the source directory. For four
        # of the five these are the same string; for pt_BR they are not, and
        # writing to the source name would publish /guide/pt_BR — an underscore
        # and a capital in a URL, which is neither idiomatic nor reliably
        # handled once a CDN or a mail client gets hold of it.
        out = os.path.join(DST, meta["suffix"].lstrip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8", newline="\n").write(
            _strip_long_publish_comments(html)
        )
        print("  page    %-22s -> /guide%-8s (%d KB)"
              % (rel.replace(os.sep, "/"), meta["suffix"] or "", len(html) // 1024))

    sync_sitemap()
    print("\n  published to site/guide/ — deploy the site to make it live")


if __name__ == "__main__":
    publish()
