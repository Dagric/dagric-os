#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — regenerate the appearance gallery preview thumbnails.
#
# Renders one 480x270 PNG per style (.style) and per layout (.look) into
#   config/includes.chroot/usr/share/dagric/appearance/thumbs/<id>.png
# so the gallery can show what you are about to get before you click it.
#
# STYLE thumbs are a miniature desktop: the style's real wallpaper with a mock
# window painted in that style's real color-scheme colors and ACCENT, made
# glassy when the style turns BLUR/TRANSLUCENCY on.
#
# LAYOUT thumbs are a miniature desktop showing WHERE THE PANELS SIT, derived
# from the SCRIPT= line of each .look (panel edge, height, and which widgets
# sit where), over a dimmed wallpaper so the bars read instantly.
#
# Needs ImageMagick 7 (`magick`). Run it after editing a .style/.look, a
# color scheme, or a wallpaper:  sh tools/make-appearance-thumbs.sh
set -e

ROOT=${1:-$(cd "$(dirname "$0")/.." && pwd)}
SHARE="$ROOT/config/includes.chroot/usr/share"
STYLES="$SHARE/dagric/styles"
LOOKS="$SHARE/dagric/looks"
WALLS="$SHARE/wallpapers"
SCHEMES="$SHARE/color-schemes"
OUT="$SHARE/dagric/appearance/thumbs"

command -v magick >/dev/null 2>&1 || { echo "ImageMagick 7 (magick) is required"; exit 1; }

# How every thumbnail is written. ImageMagick is built Q16, so a plain
# `magick ... out.png` emits a 16-bit RGBA PNG — 360 KB for a 480x270 gradient,
# six times the budget. Forcing 8-bit opaque truecolor gets the same image
# under 30 KB with no palette quantization, so the smooth wallpaper gradients
# keep their full 24-bit range instead of banding or dithering into speckle.
PNGOPTS="-alpha off -depth 8 -strip
    -define png:color-type=2 -define png:bit-depth=8
    -define png:compression-level=9 -define png:compression-filter=5"
mkdir -p "$OUT"
WORK=$(mktemp -d /srv/dagric-thumbs.XXXXXX) || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

W=480
H=270

# ---------------------------------------------------------------- key readers
# One key out of a .style/.look file (same format the shipped tools parse).
skey() { sed -n "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*//p" "$1" | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//'; }

# One key out of one section of a Plasma .colors file.
ckey() {
    awk -v sec="[$2]" -v key="$3" '
        $0 == sec { ins = 1; next }
        /^\[/     { ins = 0 }
        ins && index($0, key "=") == 1 { sub(/^[^=]*=/, ""); gsub(/\r/, ""); print; exit }
    ' "$1"
}

# Perceived luminance of an "r,g,b" triple, so overlaid controls stay legible
# on both a pale amber titlebar and a deep blue one.
lum() { echo "$1" | awk -F, '{ printf "%d", 0.2126*$1 + 0.7152*$2 + 0.0722*$3 }'; }

# Full-bleed 480x270 crop of a wallpaper.
desktop_base() {  # <wallpaper-dir-or-path> <dest>
    src=""
    for res in 1920x1080 3840x2160; do
        [ -f "$WALLS/$1/contents/images/$res.png" ] && { src="$WALLS/$1/contents/images/$res.png"; break; }
    done
    [ -n "$src" ] || { [ -f "$1" ] && src="$1"; }
    # highcontrast.style points at a flat black PNG that is not in this tree:
    # config/hooks/normal/0530-accessibility.hook.chroot base64-decodes it into
    # the chroot at build time. So this function failed on that one style on
    # every run, the style loop's "|| continue" swallowed it as a single "!"
    # line among thirteen successes, and the one style a low-vision owner needs
    # was the only tile in the gallery drawn as a blue letter instead of a
    # picture. Synthesising the flat colour here is exact rather than an
    # approximation: the shipped file is 256x256 solid black and Plasma scales
    # it, and scaling one colour gives back the same colour.
    if [ -z "$src" ] && [ "$1" = "/usr/share/dagric/accessibility/highcontrast-wallpaper.png" ]; then
        magick -size "${W}x${H}" xc:black "$2"
        return 0
    fi
    [ -n "$src" ] || { echo "  ! no wallpaper for '$1'"; return 1; }
    magick "$src" -resize "${W}x${H}^" -gravity center -extent "${W}x${H}" "$2"
}

# ------------------------------------------------------- shared window shadow
# The mock window sits at the same place in every style thumb, so its drop
# shadow is rendered once and reused.
WX0=100; WY0=48; WX1=400; WY1=218; WR=7
magick -size "${W}x${H}" xc:none \
    -fill "rgba(0,0,0,0.55)" \
    -draw "roundrectangle $((WX0+2)),$((WY0+5)) $((WX1+2)),$((WY1+7)) $WR,$WR" \
    -blur 0x7 "$WORK/shadow.png"

# =============================================================== STYLE THUMBS
echo "Styles:"
for f in "$STYLES"/*.style; do
    [ -f "$f" ] || continue
    id=$(basename "$f" .style)

    scheme=$(skey "$f" SCHEME)
    accent=$(skey "$f" ACCENT)
    wall=$(skey "$f" WALLPAPER)
    blur=$(skey "$f" BLUR)
    trans=$(skey "$f" TRANSLUCENCY)

    sfile="$SCHEMES/$scheme.colors"
    if [ ! -f "$sfile" ]; then
        echo "  ! $id: color scheme '$scheme' not found, skipping"
        continue
    fi

    WBG=$(ckey "$sfile" "Colors:Window" BackgroundNormal)
    WALT=$(ckey "$sfile" "Colors:Window" BackgroundAlternate)
    FG=$(ckey "$sfile" "Colors:Window" ForegroundNormal)
    VBG=$(ckey "$sfile" "Colors:View" BackgroundNormal)
    SEL=$(ckey "$sfile" "Colors:Selection" BackgroundNormal)

    # ACCENT=default means "whatever the scheme already highlights with".
    case "$accent" in ""|default) ACC="$SEL" ;; *) ACC="$accent" ;; esac
    [ -n "$ACC" ] || ACC="63,169,245"

    # Controls painted on the accent titlebar: dark on pale accents, else white.
    if [ "$(lum "$ACC")" -gt 165 ]; then CTL="0,0,0"; else CTL="255,255,255"; fi

    # Glass: translucency is the loud version, blur alone is the subtle one.
    if [ "$trans" = "true" ]; then A=0.74; PA=0.72
    elif [ "$blur" = "true" ]; then A=0.90; PA=0.86
    else A=1.0; PA=0.94; fi

    desktop_base "$wall" "$WORK/base.png" || continue

    # A blurred patch of wallpaper behind the window is what "blur" actually
    # looks like; without it a translucent window just looks washed out.
    if [ "$blur" = "true" ]; then
        magick "$WORK/base.png" \
            \( +clone -blur 0x8 \) \
            \( -size "${W}x${H}" xc:black -fill white \
               -draw "roundrectangle $WX0,$WY0 $WX1,$WY1 $WR,$WR" -alpha off \) \
            -composite "$WORK/base.png"
    fi

    magick "$WORK/base.png" "$WORK/shadow.png" -composite \
        -draw "fill rgba($WBG,$A) roundrectangle $WX0,$WY0 $WX1,$WY1 $WR,$WR" \
        \
        `# sidebar (square off its top and right edges)` \
        -draw "fill rgba($WALT,$A) roundrectangle 100,74 176,218 $WR,$WR" \
        -draw "fill rgba($WALT,$A) rectangle 100,74 176,92" \
        -draw "fill rgba($WALT,$A) rectangle 166,74 176,218" \
        \
        `# titlebar in the accent, square at the bottom` \
        -draw "fill rgba($ACC,$A) roundrectangle $WX0,$WY0 $WX1,74 $WR,$WR" \
        -draw "fill rgba($ACC,$A) rectangle $WX0,64 $WX1,74" \
        -draw "fill rgba($CTL,0.80) roundrectangle 113,56 197,63 3,3" \
        -draw "fill rgba($CTL,0.72) circle 347,60 347,63.5" \
        -draw "fill rgba($CTL,0.72) circle 363,60 363,63.5" \
        -draw "fill rgba($CTL,0.72) circle 379,60 379,63.5" \
        \
        `# selected sidebar row uses the accent as the highlight color` \
        -draw "fill rgba($ACC,0.95) roundrectangle 105,84 170,99 4,4" \
        -draw "fill rgba($CTL,0.90) rectangle 110,88 118,96" \
        -draw "fill rgba($CTL,0.80) roundrectangle 123,89 157,94 2,2" \
        -draw "fill rgba($FG,0.42) rectangle 110,108 118,116" \
        -draw "fill rgba($FG,0.30) roundrectangle 123,109 156,114 2,2" \
        -draw "fill rgba($FG,0.42) rectangle 110,128 118,136" \
        -draw "fill rgba($FG,0.30) roundrectangle 123,129 150,134 2,2" \
        -draw "fill rgba($FG,0.42) rectangle 110,148 118,156" \
        -draw "fill rgba($FG,0.30) roundrectangle 123,149 160,154 2,2" \
        \
        `# content pane` \
        -draw "fill rgba($VBG,$A) roundrectangle 186,88 386,206 5,5" \
        -draw "fill rgba($FG,0.70) roundrectangle 198,100 292,109 3,3" \
        -draw "fill rgba($FG,0.26) roundrectangle 198,122 372,127 2,2" \
        -draw "fill rgba($FG,0.26) roundrectangle 198,134 356,139 2,2" \
        -draw "fill rgba($FG,0.26) roundrectangle 198,146 374,151 2,2" \
        -draw "fill rgba($FG,0.26) roundrectangle 198,158 318,163 2,2" \
        -draw "fill rgba($ACC,0.95) roundrectangle 314,178 374,194 4,4" \
        \
        `# panel, so it reads as a desktop and not a floating dialog` \
        -draw "fill rgba($WBG,$PA) rectangle 0,244 480,270" \
        -draw "fill rgba($FG,0.13) rectangle 0,244 480,245" \
        -draw "fill rgba($ACC,1.0) roundrectangle 9,250 24,264 3,3" \
        -draw "fill rgba($FG,0.30) roundrectangle 32,251 78,263 2,2" \
        -draw "fill rgba($FG,0.20) roundrectangle 83,251 129,263 2,2" \
        -draw "fill rgba($FG,0.20) roundrectangle 134,251 180,263 2,2" \
        -draw "fill rgba($FG,0.45) circle 401,257 401,259.5" \
        -draw "fill rgba($FG,0.45) circle 412,257 412,259.5" \
        -draw "fill rgba($FG,0.45) circle 423,257 423,259.5" \
        -draw "fill rgba($FG,0.55) roundrectangle 436,252 470,262 3,3" \
        \
        `# hairline window outline — without it a light window on a light` \
        `# wallpaper (Dawn) loses its edges entirely` \
        -draw "fill none stroke rgba($FG,0.22) stroke-width 1 roundrectangle $WX0,$WY0 $WX1,$WY1 $WR,$WR" \
        $PNGOPTS "$OUT/$id.png"

    echo "  $id  ($(stat -c %s "$OUT/$id.png" | awk '{printf "%.1f", $1/1024}') KB)  scheme=$scheme accent=$ACC wall=$wall"
done

# ============================================================== LAYOUT THUMBS
# One dimmed desktop shared by every layout thumb: layouts differ by where the
# panels sit, so anything else that changes between them is a distraction.
# Squashing the wallpaper to 24x14 and smoothly blowing it back up leaves a
# pure color field — it keeps the wallpaper's palette but drops the logo and
# strapline, which at this size are an unreadable smudge competing with the
# panels the thumbnail exists to show.
desktop_base Dagric "$WORK/lbase.png"
magick "$WORK/lbase.png" -resize 24x14! \
    -filter Gaussian -define filter:sigma=1.1 -resize "${W}x${H}!" \
    -modulate 106,66 -fill "#0d1826" -colorize 24% -brightness-contrast 6x-12 \
    "$WORK/lbase.png"

PANEL="rgba(9,15,25,0.95)"
# A Dagric-blue edge on every panel: the single strongest cue that a bar IS a
# bar, and what makes the layouts scannable side by side in a grid.
EDGE="rgba(63,169,245,0.45)"
ACC="rgb(63,169,245)"
ICON="rgba(226,236,247,0.82)"
DIM="rgba(226,236,247,0.48)"
TRAY="rgba(226,236,247,0.62)"

layout_mvg() {
    case "$1" in
    # bottom taskbar: launcher, pager, wide task buttons, tray, clock, peek
    classic)
        cat <<EOF
fill $PANEL rectangle 0,243 480,270
fill $EDGE rectangle 0,243 480,244
fill $ACC roundrectangle 9,249 31,265 4,4
fill $DIM roundrectangle 39,251 52,263 2,2
fill rgba(226,236,247,0.24) roundrectangle 55,251 68,263 2,2
fill $ICON roundrectangle 78,249 154,264 3,3
fill rgba(226,236,247,0.50) roundrectangle 158,249 234,264 3,3
fill rgba(226,236,247,0.50) roundrectangle 238,249 314,264 3,3
fill $TRAY circle 389,257 389,259.8
fill $TRAY circle 400,257 400,259.8
fill $TRAY circle 411,257 411,259.8
fill $ICON roundrectangle 423,251 461,263 3,3
fill rgba(226,236,247,0.30) rectangle 469,247 475,266
EOF
        ;;
    # one tidy bottom bar: launcher, icon-only tasks, tray, clock
    focus)
        cat <<EOF
fill $PANEL rectangle 0,246 480,270
fill $EDGE rectangle 0,246 480,247
fill $ACC roundrectangle 9,251 27,267 3,3
fill $ICON roundrectangle 36,251 52,267 3,3
fill rgba(226,236,247,0.55) roundrectangle 58,251 74,267 3,3
fill rgba(226,236,247,0.55) roundrectangle 80,251 96,267 3,3
fill rgba(226,236,247,0.55) roundrectangle 102,251 118,267 3,3
fill $TRAY circle 393,259 393,261.8
fill $TRAY circle 404,259 404,261.8
fill $TRAY circle 415,259 415,261.8
fill $ICON roundrectangle 427,253 465,265 3,3
EOF
        ;;
    # centered task icons, launcher still pinned left
    eleven)
        cat <<EOF
fill $PANEL rectangle 0,241 480,270
fill $EDGE rectangle 0,241 480,242
fill $ACC roundrectangle 9,247 29,265 4,4
fill $ICON roundrectangle 179,246 197,264 4,4
fill rgba(226,236,247,0.55) roundrectangle 205,246 223,264 4,4
fill rgba(226,236,247,0.55) roundrectangle 231,246 249,264 4,4
fill rgba(226,236,247,0.55) roundrectangle 257,246 275,264 4,4
fill rgba(226,236,247,0.55) roundrectangle 283,246 301,264 4,4
fill $TRAY circle 387,256 387,258.8
fill $TRAY circle 398,256 398,258.8
fill $TRAY circle 409,256 409,258.8
fill $ICON roundrectangle 421,249 461,262 3,3
EOF
        ;;
    # menu bar on top, big icon dock along the bottom
    horizon)
        cat <<EOF
fill $PANEL rectangle 0,0 480,19
fill $EDGE rectangle 0,18 480,19
fill $ACC roundrectangle 6,3 21,16 3,3
fill $ICON roundrectangle 29,8 43,12 1,1
fill rgba(226,236,247,0.60) roundrectangle 48,8 60,12 1,1
fill rgba(226,236,247,0.60) roundrectangle 65,8 81,12 1,1
fill $TRAY circle 405,9 405,11.6
fill $TRAY circle 415,9 415,11.6
fill $TRAY circle 425,9 425,11.6
fill $ICON roundrectangle 436,4 470,15 2,2
fill $PANEL rectangle 0,236 480,270
fill $EDGE rectangle 0,236 480,237
fill $ICON roundrectangle 12,242 36,266 5,5
fill rgba(226,236,247,0.58) roundrectangle 46,242 70,266 5,5
fill rgba(226,236,247,0.58) roundrectangle 80,242 104,266 5,5
fill rgba(226,236,247,0.58) roundrectangle 114,242 138,266 5,5
fill rgba(226,236,247,0.58) roundrectangle 148,242 172,266 5,5
EOF
        ;;
    # side dock for apps, slim status strip on top (no global menu)
    command)
        cat <<EOF
fill $PANEL rectangle 0,0 480,18
fill $EDGE rectangle 0,17 480,18
fill $TRAY circle 405,9 405,11.6
fill $TRAY circle 415,9 415,11.6
fill $TRAY circle 425,9 425,11.6
fill $ICON roundrectangle 436,4 470,14 2,2
fill $PANEL rectangle 0,18 37,270
fill $EDGE rectangle 36,18 37,270
fill $ACC roundrectangle 8,25 29,46 4,4
fill $ICON roundrectangle 8,56 29,77 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,84 29,105 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,112 29,133 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,140 29,161 4,4
EOF
        ;;
    # side dock plus a global menu bar on top
    unity)
        cat <<EOF
fill $PANEL rectangle 0,0 480,18
fill $EDGE rectangle 0,17 480,18
fill rgba(226,236,247,0.95) roundrectangle 8,6 26,11 1,1
fill rgba(226,236,247,0.78) roundrectangle 32,6 46,11 1,1
fill rgba(226,236,247,0.78) roundrectangle 52,6 72,11 1,1
fill rgba(226,236,247,0.78) roundrectangle 78,6 92,11 1,1
fill $TRAY circle 405,9 405,11.6
fill $TRAY circle 415,9 415,11.6
fill $TRAY circle 425,9 425,11.6
fill $ICON roundrectangle 436,4 470,14 2,2
fill $PANEL rectangle 0,18 37,270
fill $EDGE rectangle 36,18 37,270
fill $ACC roundrectangle 8,25 29,46 4,4
fill $ICON roundrectangle 8,56 29,77 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,84 29,105 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,112 29,133 4,4
fill rgba(226,236,247,0.55) roundrectangle 8,140 29,161 4,4
EOF
        ;;
    # two panels: menu + status on top, pager + tasks on the bottom
    duo)
        cat <<EOF
fill $PANEL rectangle 0,0 480,20
fill $EDGE rectangle 0,19 480,20
fill $ACC roundrectangle 6,3 22,17 3,3
fill $ICON roundrectangle 30,8 44,12 1,1
fill rgba(226,236,247,0.60) roundrectangle 49,8 61,12 1,1
fill rgba(226,236,247,0.60) roundrectangle 66,8 82,12 1,1
fill $TRAY circle 405,10 405,12.6
fill $TRAY circle 415,10 415,12.6
fill $TRAY circle 425,10 425,12.6
fill $ICON roundrectangle 436,5 470,16 2,2
fill $PANEL rectangle 0,243 480,270
fill $EDGE rectangle 0,243 480,244
fill $DIM roundrectangle 9,251 22,263 2,2
fill rgba(226,236,247,0.24) roundrectangle 25,251 38,263 2,2
fill $ICON roundrectangle 48,249 124,264 3,3
fill rgba(226,236,247,0.50) roundrectangle 128,249 204,264 3,3
fill rgba(226,236,247,0.50) roundrectangle 208,249 284,264 3,3
fill rgba(226,236,247,0.30) rectangle 469,247 475,266
EOF
        ;;
    *) return 1 ;;
    esac
}

echo "Layouts:"
for f in "$LOOKS"/*.look; do
    [ -f "$f" ] || continue
    id=$(basename "$f" .look)
    if ! layout_mvg "$id" > "$WORK/$id.mvg" 2>/dev/null; then
        echo "  ! $id: no panel recipe for this layout, skipping"
        continue
    fi
    # The primitives go in as one inline string: ImageMagick's stock policy.xml
    # refuses to read a @file for -draw.
    magick "$WORK/lbase.png" -draw "$(cat "$WORK/$id.mvg")" \
        $PNGOPTS "$OUT/$id.png"
    echo "  $id  ($(stat -c %s "$OUT/$id.png" | awk '{printf "%.1f", $1/1024}') KB)"
done

echo
echo "Wrote $(ls -1 "$OUT"/*.png 2>/dev/null | wc -l) thumbnails to $OUT"
