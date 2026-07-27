#!/bin/sh
# Dagric login-screen backdrop.
#
#   sh branding/sddm/make-login-art.sh [REPO_ROOT]
#
# Writes config/includes.chroot/usr/share/dagric/sddm/background.png, which
# usr/share/sddm/themes/breeze/theme.conf.user points at. Needs ImageMagick 7.
#
# This is the first thing anyone sees on every single boot, and it had been a
# flat navy rectangle -- correct in that it stayed out of the way, but it read
# as an unfinished screen rather than a designed one.
#
# The rule that shapes it: the login form sits dead centre, so the CENTRE has
# to stay quiet and every bit of interest belongs out at the edges. A corner
# light top left, a low horizon glow along the bottom, contour work confined
# to the bottom band, and a strong vignette that darkens the frame inward.
# Nothing here is bright enough to fight a password field.
#
# The desktop wallpaper cannot be reused for this: it carries the wordmark and
# the tagline baked in, and the theme already draws the logo above the form,
# so the two would collide.
set -e

REPO=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}
OUT=$REPO/config/includes.chroot/usr/share/dagric/sddm/background.png
M=magick

W=${W:-3840}
H=${H:-2160}

WK=$(mktemp -d "${TMPDIR:-/tmp}/loginXXXXXX")
trap 'rm -rf "$WK"' EXIT
C="$WK/c.miff"

geo() {
    case $1 in -*) sx=$1 ;; *) sx="+$1" ;; esac
    case $2 in -*) sy=$2 ;; *) sy="+$2" ;; esac
    printf '%s%s' "$sx" "$sy"
}

# Intermediates stay 16-bit MIFF so the strength multiply does not quantise
# before the final 8-bit write.
bloom() {                                 # TW TH CX CY COLOR STRENGTH
    $M -size 1600x1600 radial-gradient:"#$5-#000000" \
       -resize "${1}x${2}!" -evaluate multiply "$6" "$WK/_b.miff"
    $M -size "${W}x${H}" xc:black "$WK/_z.miff"
    $M "$WK/_z.miff" "$WK/_b.miff" \
       -geometry "$(geo $(( $3 - $1 / 2 )) $(( $4 - $2 / 2 )))" \
       -compose plus -composite "$WK/_bl.miff"
    $M "$C" "$WK/_bl.miff" -compose screen -composite "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

# ---------------------------------------------------------------- ground ---
$M -size "${W}x${H}" gradient:'#0e1a2c-#04070d' -colorspace sRGB "$C"

# corner light, top left, its centre well off the canvas so only the outer
# skirt of the falloff lands in frame -- brought any closer it reads as a grey
# wash rather than as light coming from somewhere
bloom $((W*150/100)) $((H*190/100)) $((-W*4/100)) $((-H*12/100)) cfe3f5 0.52

# low horizon glow in the brand blue, centre pushed below the bottom edge
bloom $((W*210/100)) $((H*95/100)) $((W*50/100)) $((H*112/100)) 2f7fc4 0.72

# ------------------------------------------------------------- contours ---
# The same iso-line trick as the DagricContour wallpaper, so the login screen
# and the desktop plainly come from the same hand. Held to the bottom third
# and screened on weakly: at this strength it is texture, not pattern.
$M -size 14x8 -seed 21 xc:gray50 +noise Random -colorspace gray \
   -resize "${W}x${H}!" -blur "0x$((W*20/1000))" -auto-level "$WK/_hf.miff"
$M "$WK/_hf.miff" -function Sinusoid 7,0,0.5,0.5 -level 93%,100% \
   -blur "0x$((W/960))" "$WK/_ln.miff"
$M \( -size "${W}x$((H*62/100))"                   xc:'#040404' \) \
   \( -size "${W}x$((H*22/100))" gradient:'#040404-#ffffff' \) \
   \( -size "${W}x$((H - H*62/100 - H*22/100))"    xc:'#ffffff' \) \
   -append "$WK/_lm.miff"
$M "$WK/_ln.miff" "$WK/_lm.miff" -compose multiply -composite \
   \( -size "${W}x${H}" xc:'#6fc6d8' \) -compose multiply -composite \
   "$WK/_ln2.miff"
$M "$C" \( "$WK/_ln2.miff" -evaluate multiply 0.30 \) \
   -compose screen -composite "$WK/c2.miff"
mv "$WK/c2.miff" "$C"

# ------------------------------------------------------------- vignette ---
# Heavier than the wallpapers use. The form is centred and light, so pulling
# the corners down is what stops the eye wandering off to them.
$M -size 1600x1600 radial-gradient:'#ffffff-#000000' -resize "${W}x${H}!" \
   -negate -evaluate multiply 0.40 -negate "$WK/_v.miff"
$M "$C" "$WK/_v.miff" -compose multiply -composite "$WK/c2.miff"
mv "$WK/c2.miff" "$C"

# ---------------------------------------------------------------- write ---
# Same ordered-dither and reproducibility rules as the wallpapers: a 4x4 Bayer
# matrix just under one 8-bit LSB kills the banding a 4K ramp would otherwise
# show, and excluding the date chunks keeps rebuilds byte-identical so signed
# release checksums do not churn over art that did not change.
$M -size 4x4 xc:black -depth 16 \
  -fill '#000000000000' -draw 'point 0,0' -fill '#008000800080' -draw 'point 1,0' \
  -fill '#002000200020' -draw 'point 2,0' -fill '#00a000a000a0' -draw 'point 3,0' \
  -fill '#00c000c000c0' -draw 'point 0,1' -fill '#004000400040' -draw 'point 1,1' \
  -fill '#00e000e000e0' -draw 'point 2,1' -fill '#006000600060' -draw 'point 3,1' \
  -fill '#003000300030' -draw 'point 0,2' -fill '#00b000b000b0' -draw 'point 1,2' \
  -fill '#001000100010' -draw 'point 2,2' -fill '#009000900090' -draw 'point 3,2' \
  -fill '#00f000f000f0' -draw 'point 0,3' -fill '#007000700070' -draw 'point 1,3' \
  -fill '#00d000d000d0' -draw 'point 2,3' -fill '#005000500050' -draw 'point 3,3' \
  "$WK/bayer.png"
$M -size "${W}x${H}" tile:"$WK/bayer.png" -depth 16 "$WK/tile.miff"

mkdir -p "$(dirname "$OUT")"
$M "$C" "$WK/tile.miff" -compose plus -composite \
   -alpha off -depth 8 \
   +set date:create +set date:modify +set date:timestamp \
   -define png:exclude-chunk=date,time \
   -quality 95 "$OUT"

echo "wrote $OUT ($(wc -c < "$OUT") bytes, ${W}x${H})"
