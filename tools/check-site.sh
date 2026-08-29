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
# Every href="/..." must resolve to something that will exist on the DEPLOYED
# site. cleanUrls is on, so /foo is served by foo.html.
#
# "EXISTS ON DISK" IS THE WRONG TEST, AND THIS FILE MADE IT ANYWAY. The first
# version resolved each link against the local filesystem and never consulted
# is_ignored — the very function twenty lines above that decides what actually
# gets uploaded. So a deployed page linking to /family passed, because
# site/family.html exists here, even though firebase.json excludes it from the
# upload and the link would 404 for every visitor. That is precisely the case
# this gate was written for, and the comment at this spot used to claim it was
# handled. Proven with a replica tree: one page whose only link was /family,
# exit 0, "no placeholders, no tunnels, links and sitemap agree."
#
# The sentinel also moved out of /tmp. A fixed world-writable path is not a
# safe place to signal failure from — a stale file from an interrupted run
# failed the next one for no reason, and anyone on the machine could create it.
# The count comes back through the subshell's stdout instead, which needs no
# file at all.
_broken=$(
    for f in $DEPLOYED; do
        grep -o 'href="/[^"#?]*"' "$f" 2>/dev/null | sed 's/href="//; s/"$//' | sort -u |
        while IFS= read -r href; do
            [ -n "$href" ] || continue
            case "$href" in
                /) continue ;;
                */) continue ;;
            esac
            # Does a local file back this link at all?
            _target=""
            [ -e "site$href" ]      && _target="site$href"
            [ -e "site$href.html" ] && _target="site$href.html"
            if [ -z "$_target" ]; then
                echo "check-site: $f links to $href — nothing backs it" >&2
                echo x
                continue
            fi
            # It exists here. Will it be UPLOADED? A file firebase.json ignores
            # is a broken link on the deployed site however present it is locally.
            if is_ignored "$_target"; then
                echo "check-site: $f links to $href, but $_target is in firebase.json's" >&2
                echo "  ignore list, so that link will 404 on the deployed site" >&2
                echo x
            fi
        done
    done | grep -c x || true
)
# `|| true` is load-bearing: grep -c exits 1 when the count is ZERO, this file
# runs under set -e, and a command substitution that exits non-zero aborts the
# script. Without it the gate died silently on a CLEAN site — exit 1, no output,
# no explanation — which is the worst possible behaviour for a release gate and
# is the same grep -c trap this repo has now hit three times.
if [ "${_broken:-0}" -gt 0 ]; then
    FAIL=1
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
