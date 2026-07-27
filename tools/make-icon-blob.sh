#!/bin/sh
# Dagric OS — bake the logo into the raw pixel form X11 wants for a window icon.
#
#   sh tools/make-icon-blob.sh
#
# WHY A BLOB AND NOT THE PNG. /usr/lib/dagric/set-window-icon has to hand X11
# an array of 32-bit ARGB pixels for _NET_WM_ICON. Python's standard library
# cannot decode a PNG, and the image deliberately ships no Pillow, no
# ImageMagick and no netpbm — none of which are worth adding to a lean OS to
# draw one 64x64 icon. Pre-rendering it here means the runtime helper is a
# file read and nothing more, with no image library anywhere in the chain.
#
# Format: 64x64, straight RGBA, 8 bits per channel, top-to-bottom — 16384 bytes
# exactly. The helper converts RGBA to the ARGB word order the spec wants; that
# swap lives in the helper because it is X11's convention, not the file's.
#
# Regenerate this whenever the logo changes. It is committed because the build
# chroot has no way to produce it.
set -e

# Repo root as $1, same convention as branding/wallpaper/make-wallpapers.sh.
# Deriving it from $0 alone breaks the usual way these get run — copied to /srv
# to strip CRLF first, at which point $0's parent is /srv and the root is "/".
REPO=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
SRC=$REPO/config/includes.chroot/usr/share/dagric/logo/dagric-logo.png
OUTDIR=$REPO/config/includes.chroot/usr/share/dagric/icon
OUT=$OUTDIR/dagric-64.rgba

[ -f "$SRC" ] || { echo "no logo at $SRC" >&2; exit 1; }
command -v magick >/dev/null 2>&1 || { echo "ImageMagick (magick) required" >&2; exit 1; }

mkdir -p "$OUTDIR"

# -background none keeps the rounded corners transparent instead of filling
# them black, which is what a title bar would otherwise show.
magick "$SRC" -background none -resize 64x64 -gravity center -extent 64x64 \
    -depth 8 RGBA:"$OUT"

SIZE=$(stat -c%s "$OUT")
if [ "$SIZE" != 16384 ]; then
    echo "ERROR: expected 16384 bytes (64*64*4), got $SIZE" >&2
    exit 1
fi
echo "wrote $OUT ($SIZE bytes)"
