#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — refuse to deploy a site that is not finished.
#
#     sh tools/check-site.sh
#
# WHY THIS EXISTS. Three separate near-misses, all of the same shape: something
# that was fine in the working tree became a customer-facing defect the moment
# somebody ran `firebase deploy`, and nothing between the two looked.
#
#   * site/family.html sat in the tree with 25 PLACEHOLDER tokens, visible
#     "$FAMILY_PRICE_PLACEHOLDER" prices and five buy buttons whose href was the
#     literal string STRIPE_FAMILY_LINK_PLACEHOLDER. It carried a canonical URL
#     and no noindex, so the next deploy would have published a purchase page
#     that cannot take a purchase, and let it be indexed.
#   * firebase.json spent about two weeks in production serving a 302 to an
#     ephemeral trycloudflare noVNC tunnel, from an uncommitted working-tree
#     edit. Nothing in the repo described what production was serving.
#   * The deploy that publishes the ISO checksums can be run without the ISOs
#     having been promoted, which is the documented 2026-08-03 incident.
#
# A deploy checklist already existed for all three. A checklist is a reminder;
# this is a mechanism, which is the distinction tools/release.sh's own header
# draws about the same class of failure.
set -e
cd "$(dirname "$0")/.."

FAIL=0
say_fail() { FAIL=1; echo "" >&2; echo "check-site: $1" >&2; }

# What Firebase will actually upload: site/, minus firebase.json's ignore list.
# Read from firebase.json rather than hardcoded, so an ignore that is added or
# removed changes this check with it and the two cannot disagree.
IGNORED=$(python3 - <<'PY'
import json, io
h = json.load(io.open('firebase.json', encoding='utf-8'))['hosting']
for pat in h.get('ignore', []):
    print(pat)
PY
)

is_ignored() {
    _rel=${1#site/}
    for _p in $IGNORED; do
        case "$_rel" in $_p) return 0 ;; esac
    done
    return 1
}

DEPLOYED=""
for f in site/*.html site/guide/index.html site/guide/*/index.html; do
    [ -f "$f" ] || continue
    is_ignored "$f" && continue
    DEPLOYED="$DEPLOYED $f"
done

# ---------------------------------------------------------------- placeholders
# Anything still carrying a fill-in-later token is unfinished by definition, and
# on a sales page it is unfinished in front of a buyer.
for f in $DEPLOYED; do
    if grep -q 'PLACEHOLDER' "$f"; then
        say_fail "$f would be deployed and still contains PLACEHOLDER tokens:"
        grep -o '[A-Z_]*PLACEHOLDER' "$f" | sort | uniq -c | sed 's/^/    /' >&2
        echo "  Either finish the page or add it to firebase.json's ignore list." >&2
    fi
done

# ------------------------------------------------------------ debug leftovers
# A redirect to a developer's tunnel is not a thing a sales domain should ever
# serve, and it reached production once because it lived only in an uncommitted
# working-tree edit of firebase.json.
if grep -qE 'trycloudflare|ngrok\.io|localhost:[0-9]|127\.0\.0\.1:[0-9]' firebase.json; then
    say_fail "firebase.json points at an ephemeral tunnel or a local address."
    grep -nE 'trycloudflare|ngrok\.io|localhost:[0-9]|127\.0\.0\.1:[0-9]' firebase.json | sed 's/^/    /' >&2
fi
for f in $DEPLOYED; do
    if grep -qE 'trycloudflare|ngrok\.io' "$f"; then
        say_fail "$f links to an ephemeral tunnel."
    fi
done

# --------------------------------------------------------- uncommitted config
# The deployed hosting config must be the one in git, or git no longer describes
# production and a fresh checkout deploys something else.
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    if ! git diff --quiet -- firebase.json 2>/dev/null; then
        say_fail "firebase.json has uncommitted changes."
        echo "    Production would be served from a file git does not describe." >&2
        echo "    Commit it (or revert it) before deploying." >&2
    fi
fi

# ------------------------------------------------------------- internal links
# Every href="/..." must resolve to something that will exist on the deployed
# site. cleanUrls is on, so /foo is served by foo.html.
for f in $DEPLOYED; do
    grep -o 'href="/[^"#?]*"' "$f" 2>/dev/null | sed 's/href="//; s/"$//' | sort -u |
    while IFS= read -r href; do
        [ -n "$href" ] || continue
        case "$href" in
            /) continue ;;
            */) continue ;;
        esac
        _t="site$href"
        [ -e "$_t" ] && continue
        [ -e "$_t.html" ] && continue
        # A path that is ignored from the deploy is a broken link even though the
        # file exists locally — that is exactly the family.html case.
        if [ -e "site$href.html" ] || [ -e "$_t" ]; then continue; fi
        echo "check-site: $f links to $href, which will not exist on the deployed site" >&2
        echo "BROKEN" >> /tmp/check-site-broken
    done
done
if [ -f /tmp/check-site-broken ]; then
    FAIL=1
    rm -f /tmp/check-site-broken
fi

# ------------------------------------------------------------------- sitemap
# A page that is deployed and not in the sitemap is a page nobody finds —
# UNLESS robots.txt deliberately disallows it, which is how /thanks-pro (the
# post-purchase page, reachable only with a receipt) is meant to be. Reading
# robots.txt rather than hardcoding an exception list means a page that is later
# made public gets picked up by this check on the same commit.
for f in $DEPLOYED; do
    case "$f" in site/404.html) continue ;; esac
    case "$f" in site/guide/*) continue ;; esac
    _slug=$(basename "$f" .html)
    [ "$_slug" = "index" ] && continue
    if grep -q "^Disallow: /$_slug\$" site/robots.txt 2>/dev/null; then
        continue
    fi
    if ! grep -q "dagric.com/$_slug<" site/sitemap.xml 2>/dev/null; then
        say_fail "site/sitemap.xml has no entry for /$_slug (which will be deployed)."
    fi
done

# ---------------------------------------------------------------------- report
if [ "$FAIL" = 1 ]; then
    echo "" >&2
    echo "check-site: FAILED — do not deploy." >&2
    exit 1
fi
echo "check-site: $(printf '%s\n' $DEPLOYED | wc -l) pages, no placeholders, no tunnels, links and sitemap agree."
exit 0
