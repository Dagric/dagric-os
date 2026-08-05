#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Dagric OS — build the bundle that turns a free machine's appearance gallery
# into a Pro one.
#
# WHAT GOES IN, AND WHY IT IS EXACTLY THIS. The free build does not merely hide
# the Pro layouts and styles, it DELETES them, and build.sh says why: a flag is
# one line of text for a free owner to edit. That decision is right and it is
# what creates this file's reason to exist — dagric-upgrade-to-pro has to get
# them from somewhere, and the only somewhere left is a licence-gated download.
#
# THE CONTENTS ARE DERIVED, NEVER LISTED. Every file here is selected by the
# same test build.sh uses to decide what to strip:
#
#     grep -rlx 'EDITION=pro' .../looks .../styles
#
# so the bundle cannot drift from the edition split by someone adding a Pro
# layout and forgetting this script. A hardcoded list would have been shorter
# and would have been wrong within a month. The .desktop entries are found the
# same way, by their X-Dagric-Edition=pro line.
#
# Thumbnails come along because the gallery lists what it has thumbnails for;
# shipping a layout with no preview would put a blank tile in the window a
# customer just paid to fill.
set -e

cd "$(dirname "$0")/.."
SRC=config/includes.chroot/usr/share/dagric
APPS=config/includes.chroot/usr/share/applications
OUT=${1:-out/dagric-pro-assets.tar.gz}

command -v tar >/dev/null 2>&1 || { echo "assets: tar is missing" >&2; exit 1; }

WORK=$(mktemp -d) || exit 1
trap 'rm -rf "$WORK"' EXIT
trap 'exit 130' INT TERM HUP

mkdir -p "$WORK/looks" "$WORK/styles" "$WORK/thumbs" "$WORK/applications"

n_look=0; n_style=0; n_thumb=0; n_app=0
for f in $(grep -rlx 'EDITION=pro' "$SRC/looks" "$SRC/styles" 2>/dev/null | sort); do
    base=${f##*/}
    case "$f" in
        */looks/*)  cp "$f" "$WORK/looks/";  n_look=$((n_look + 1)) ;;
        */styles/*) cp "$f" "$WORK/styles/"; n_style=$((n_style + 1)) ;;
    esac
    thumb="$SRC/appearance/thumbs/${base%.*}.png"
    if [ -f "$thumb" ]; then
        cp "$thumb" "$WORK/thumbs/"
        n_thumb=$((n_thumb + 1))
    else
        # Loud, but NOT because it breaks anything. Thumbnails are optional by
        # design: dagric-appearance:37-38 says a missing one draws "a tile in
        # that style's own accent colour instead of a broken image", and
        # highcontrast.style ships with no thumbnail on the free edition for
        # exactly that reason. So this is a quality note, not a fault — the
        # gallery is most of what the paid layouts ARE, and a purchased layout
        # deserves a real preview rather than a coloured square.
        echo "assets: NOTE no thumbnail for $base (gallery will draw its accent" >&2
        echo "        colour instead; harmless, but a paid layout deserves art)" >&2
    fi
done

for f in $(grep -rl 'X-Dagric-Edition=pro' "$APPS" 2>/dev/null | sort); do
    cp "$f" "$WORK/applications/"
    n_app=$((n_app + 1))
done

if [ "$n_look" -eq 0 ] && [ "$n_style" -eq 0 ]; then
    echo "assets: found no EDITION=pro layouts or styles at all." >&2
    echo "        Either the edition split changed, or this was run against a" >&2
    echo "        tree a free build had already stripped. Refusing to write an" >&2
    echo "        empty bundle, which would upgrade a paying customer to nothing." >&2
    exit 1
fi

mkdir -p "$(dirname "$OUT")"
# Sorted, no timestamps, no owner: two runs of the same tree produce the same
# bytes, so "did the bundle change" is answerable by comparing hashes rather
# than by trusting a date.
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2026-01-01' \
    -czf "$OUT" -C "$WORK" looks styles thumbs applications 2>/dev/null \
  || tar -czf "$OUT" -C "$WORK" looks styles thumbs applications

echo "assets: $OUT"
echo "  layouts     $n_look"
echo "  styles      $n_style"
echo "  thumbnails  $n_thumb"
echo "  launchers   $n_app"
echo "  size        $(wc -c < "$OUT") bytes"
echo "  sha256      $(sha256sum "$OUT" | cut -d' ' -f1)"
