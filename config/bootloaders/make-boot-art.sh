#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Dagric OS — regenerate the boot-menu artwork.
#
# Run this by hand after editing splash.svg or splash-wide.svg; it writes into
# config/includes.chroot/usr/share/dagric/boot/, and those files are what ship.
# It is NOT run during the build. A binary hook runs on the assembled ISO tree
# inside the build container, where there is no ImageMagick and no rsvg-convert
# and no fonts — anything generated there would have to be generated on every
# build machine, and the first one missing a tool ships a menu with no theme.
# Pre-rendered assets in the repo are the only version that is the same
# everywhere.
#
# Needs: rsvg-convert, ImageMagick 7 (magick), grub-mkfont, DejaVu fonts.
#   sh config/bootloaders/make-boot-art.sh [repo-root]
set -e

REPO=${1:-.}
SRC="$REPO/config/bootloaders"
OUT="$REPO/config/includes.chroot/usr/share/dagric/boot"
THEME="$OUT/grub-theme"
DJ=/usr/share/fonts/truetype/dejavu

for t in rsvg-convert magick grub-mkfont; do
    command -v "$t" >/dev/null 2>&1 || { echo "missing: $t" >&2; exit 1; }
done

# "f", not "fonts", and the one-letter name is load-bearing rather than terse.
# On an installed machine nothing writes explicit loadfont lines the way
# 0950-boot-branding does for the ISO: grub-mkconfig's 00_header auto-loads a
# theme's fonts with exactly two non-recursive globs and no others,
# "$themedir"/*.pf2 and "$themedir"/f/*.pf2 — the theme root, and a directory
# literally named f, which is the name upstream's starfield theme established.
# A fonts/ subdirectory matched neither, so every face built below was shipped
# and never loaded, theme.txt's names matched nothing, and the installed menu
# fell back to gfxterm's 16px unicode.pf2 while the USB it was installed from
# rendered correctly. Renaming this directory is what fixes that; if it ever
# moves back, move the loadfont lines in 0950-boot-branding.hook.binary with it.
mkdir -p "$THEME/f" "$OUT/isolinux"

# GRUB's PNG decoder is narrower than ImageMagick's writer and it fails SILENTLY
# — a 16-bit or sub-byte-palette PNG draws as rainbow moire or as nothing at
# all, with no error anywhere. magick picks both of those encodings on its own:
# 16-bit whenever it composites with alpha, palette whenever an image has few
# colours, which is exactly what a flat-filled 9-slice tile is. Every PNG below
# is therefore forced to 8-bit RGBA, non-interlaced, and checked afterwards.
P32="-depth 8 -define png:color-type=6 -define png:bit-depth=8 -interlace none"

# One tile of a styled box. GRUB looks for exactly these nine suffixes.
slice() {
    magick "$1" -crop "$3" +repage $P32 PNG32:"$THEME/$2.png"
}

mk9() {
    _src=$1; _p=$2; _k=$3; _s=$4
    _m=$((_s - 2 * _k))
    _f=$((_s - _k))
    slice "$_src" "${_p}_nw" "${_k}x${_k}+0+0"
    slice "$_src" "${_p}_ne" "${_k}x${_k}+${_f}+0"
    slice "$_src" "${_p}_sw" "${_k}x${_k}+0+${_f}"
    slice "$_src" "${_p}_se" "${_k}x${_k}+${_f}+${_f}"
    slice "$_src" "${_p}_n"  "${_m}x${_k}+${_k}+0"
    slice "$_src" "${_p}_s"  "${_m}x${_k}+${_k}+${_f}"
    slice "$_src" "${_p}_w"  "${_k}x${_m}+0+${_k}"
    slice "$_src" "${_p}_e"  "${_k}x${_m}+${_f}+${_k}"
    slice "$_src" "${_p}_c"  "${_m}x${_m}+${_k}+${_k}"
}

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# --- backgrounds ------------------------------------------------------------
rsvg-convert --format png --width 1920 --height 1080 \
    "$SRC/splash-wide.svg" -o "$T/bg.png"
magick "$T/bg.png" $P32 PNG32:"$THEME/background.png"

# The background gfxterm keeps drawing after the menu exits — same file would be
# ideal, but gfxterm's background_image can only stretch, never crop, so at 4:3
# the monogram renders as an ellipse and the wordmark as narrow. This variant
# drops the brand block and keeps only the gradient, the glow, the band and the
# contours, all of which are vertical or soft and squash invisibly. What it
# replaces is a large black rectangle, so losing the mark for the few seconds
# before Plymouth draws its own is a straight trade up.
printf '.brand { display: none; }\n' > "$T/noBrand.css"
rsvg-convert --format png --width 1920 --height 1080 --stylesheet "$T/noBrand.css" \
    "$SRC/splash-wide.svg" -o "$T/term.png"
magick "$T/term.png" $P32 PNG32:"$THEME/terminal.png"

# vesamenu does not scale its background by even one pixel, so this has to be
# authored at exactly the resolution isolinux.cfg asks for.
rsvg-convert --format png --width 1024 --height 768 \
    "$SRC/splash.svg" -o "$T/fg.png"
magick "$T/fg.png" $P32 PNG32:"$OUT/isolinux/splash.png"

# --- styled boxes -----------------------------------------------------------
# A styled box is drawn AROUND its component, not inside it: the rendered height
# is item_height + north + south. The corner sizes below are load-bearing and
# theme.txt's item_spacing is set from them; changing one means changing both.

# menu panel — 20px corners
magick -size 120x120 xc:none -fill 'rgba(11,21,38,0.86)' \
    -stroke 'rgba(140,180,232,0.22)' -strokewidth 2 \
    -draw 'roundrectangle 1,1 118,118 18,18' $P32 PNG32:"$T/panel.png"
mk9 "$T/panel.png" panel 20 120

# selection pill — 10px corners, so item_spacing must be >= 20
magick -size 60x60 xc:none -fill 'rgba(63,169,245,0.95)' \
    -draw 'roundrectangle 0,0 59,59 10,10' $P32 PNG32:"$T/sel.png"
mk9 "$T/sel.png" select 10 60

# countdown track and fill — 10px corners
magick -size 60x60 xc:none -fill 'rgba(255,255,255,0.10)' \
    -stroke 'rgba(150,190,240,0.18)' -strokewidth 2 \
    -draw 'roundrectangle 1,1 58,58 10,10' $P32 PNG32:"$T/pbbg.png"
mk9 "$T/pbbg.png" pbbg 10 60
# Kept low on purpose: the fill sweeps left to right UNDERNEATH the countdown
# text, and at full strength its leading edge visibly cuts whichever word it is
# passing through.
magick -size 60x60 xc:none -fill 'rgba(63,169,245,0.40)' \
    -draw 'roundrectangle 0,0 59,59 10,10' $P32 PNG32:"$T/pbfg.png"
mk9 "$T/pbfg.png" pbfg 10 60

# --- fonts ------------------------------------------------------------------
# theme.txt matches fonts by NAME among fonts already loaded by grub.cfg; a name
# that matches nothing falls back WITHOUT WARNING. Keep these names in step with
# theme.txt and with the loadfont lines the hook writes into boot/grub/theme.cfg.
#
# `-n` SETS THE FAMILY, NOT THE NAME, and theme.txt has to quote the NAME.
# grub-mkfont composes NAME as "<family> <style> <size>", so `-n "Dagric Body
# 24"` on a 24px regular face writes NAME "Dagric Body 24 Regular 24" and FAMI
# "Dagric Body 24". theme.txt asked for the family, matched nothing, and got the
# fallback: grub_font_get() returns the head of the font list rather than
# erroring, and since the list is prepended that is small.pf2 — so the whole
# menu rendered at 17px with no bold selection, on both editions. (The old
# comment here said the fallback was the built-in 16px Unifont. It is not; it is
# whichever face loaded last, which is why nothing looked obviously broken.)
# Verify the strings after any change to this line:
#   for f in body sel small; do
#     dd if=$THEME/f/$f.pf2 bs=1 skip=16 count=48 2>/dev/null | tr -d '\0'; echo
#   done
#
# Ranged to Latin-1 plus the punctuation a menu actually uses. The full DejaVu
# glyph set converts to ~300 KB per face, and three faces of that sit in the ISO
# root where the firmware reads them, to render about sixty distinct characters.
# unicode.pf2 is already loaded by config.cfg and covers anything that misses.
# Every entry has to be a FROM-TO pair; a bare codepoint is "invalid font range".
R='0x20-0x7e,0xa0-0xff,0x2010-0x2015,0x2018-0x201d,0x2022-0x2026,0x2039-0x203a,0x20ac-0x20ac,0x2190-0x2193'
grub-mkfont -r "$R" -s 24 -o "$THEME/f/body.pf2"  -n "Dagric Body 24"  "$DJ/DejaVuSans.ttf"
grub-mkfont -r "$R" -s 24 -o "$THEME/f/sel.pf2"   -n "Dagric Sel 24"   "$DJ/DejaVuSans-Bold.ttf"
grub-mkfont -r "$R" -s 17 -o "$THEME/f/small.pf2" -n "Dagric Small 17" "$DJ/DejaVuSans.ttf"

# --- verify the encoding, because GRUB will not tell you -------------------
# identify(1) reports the decoded image, not what is on disk, so read the IHDR.
BAD=$(python3 - "$THEME" "$OUT/isolinux" <<'PY'
import struct, sys, pathlib
bad = []
for root in sys.argv[1:]:
    for p in sorted(pathlib.Path(root).rglob("*.png")):
        w, h, depth, ctype, comp, filt, inter = struct.unpack(
            ">IIBBBBB", p.read_bytes()[16:29])
        if (depth, ctype, inter) != (8, 6, 0):
            bad.append(f"{p} depth={depth} colour-type={ctype} interlace={inter}")
print("\n".join(bad))
PY
)
if [ -n "$BAD" ]; then
    echo "ERROR: PNGs GRUB cannot decode:" >&2
    echo "$BAD" >&2
    exit 1
fi

echo "Boot art regenerated into $OUT"
