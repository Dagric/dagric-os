#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Prove that neither edition can be downloaded while fixed live keys change.
set -eu

cd "$(dirname "$0")/.."

ORIGINS=infra/release-public-origins.txt
SITE_URL=https://dagric.com/download
PRO_URL=https://dagric-gate.dagric.workers.dev/
VERSION=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["version"])')
FREE_ISO="dagric-os-$VERSION-amd64.iso"
[ -f "$ORIGINS" ] || {
    echo "release-hold: missing authoritative Free-origin inventory: $ORIGINS" >&2
    exit 1
}
command -v curl >/dev/null 2>&1 || {
    echo "release-hold: curl is required." >&2
    exit 1
}
[ -n "${R2_ACCOUNT_ID:-}" ] && [ -n "${CLOUDFLARE_R2_AUDIT_TOKEN:-}" ] || {
    echo "release-hold: R2_ACCOUNT_ID and CLOUDFLARE_R2_AUDIT_TOKEN are required." >&2
    exit 1
}

# Query Cloudflare's authoritative managed/custom-domain settings, not only
# the URLs currently written in this repository. The live Free bucket must
# have r2.dev disabled and every attached custom domain disabled.
python3 tools/check-private-r2-staging.py --live-hold \
    --account "$R2_ACCOUNT_ID" --bucket dagric-downloads

TMP=$(mktemp) || exit 1
trap 'rm -f "$TMP"' EXIT HUP INT TERM
SITE_STATUS=$(curl -sS --max-time 30 -o "$TMP" -w '%{http_code}' "$SITE_URL") || {
    echo "release-hold: cannot verify the live download-page hold." >&2
    exit 1
}
[ "$SITE_STATUS" = 200 ] || {
    echo "release-hold: live download page returned HTTP $SITE_STATUS, not 200." >&2
    exit 1
}
grep -Fq 'downloads and new Pro sales are temporarily paused' "$TMP" || {
    echo "release-hold: live download page lacks the required release-hold notice." >&2
    exit 1
}
if grep -Eiq 'href="[^"]*\.iso[^"]*"' "$TMP" || \
   grep -Eiq "href='[^']*\\.iso[^']*'" "$TMP"; then
    echo "release-hold: live download page still links an ISO." >&2
    exit 1
fi

PRO_STATUS=$(curl -sS --max-time 30 -o /dev/null -w '%{http_code}' "$PRO_URL") || {
    echo "release-hold: cannot prove the live Pro worker is held." >&2
    exit 1
}
[ "$PRO_STATUS" = 503 ] || {
    echo "release-hold: Pro delivery is not held (HTTP $PRO_STATUS; expected 503)." >&2
    exit 1
}

COUNT=0
while IFS= read -r ORIGIN || [ -n "$ORIGIN" ]; do
    case "$ORIGIN" in
        ''|'#'*) continue ;;
    esac
    printf '%s\n' "$ORIGIN" | grep -Eq '^https://[A-Za-z0-9.-]+$' || {
        echo "release-hold: invalid Free origin in $ORIGINS: $ORIGIN" >&2
        exit 1
    }
    COUNT=$((COUNT + 1))
    # HEAD avoids transferring a multi-gigabyte previous release. Anything
    # except an explicit unavailable/held status is a failed proof.
    STATUS=$(curl -sS -I --max-time 30 -o /dev/null -w '%{http_code}' \
        "$ORIGIN/$FREE_ISO") || STATUS=000
    case "$STATUS" in
        401|403|404|410|423|451|503)
            echo "release-hold: Free origin held: $ORIGIN (HTTP $STATUS)"
            ;;
        *)
            echo "release-hold: Free origin can serve or cannot prove hold:" >&2
            echo "              $ORIGIN/$FREE_ISO returned HTTP $STATUS" >&2
            exit 1
            ;;
    esac
done < "$ORIGINS"
[ "$COUNT" -gt 0 ] || {
    echo "release-hold: Free-origin inventory is empty." >&2
    exit 1
}

echo "release-hold: live site, Free origins and Pro worker are held"
