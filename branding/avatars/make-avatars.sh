#!/bin/sh
# Dagric user avatars.
#
#   sh branding/avatars/make-avatars.sh [REPO_ROOT]
#
# Writes twelve 256px avatars to usr/share/plasma/avatars, which is where the
# Plasma 6 Users settings page reads its picker from, plus a copy as SDDM's
# default.face.icon so a freshly installed account shows a Dagric mark at the
# login screen instead of the generic grey bust. Needs ImageMagick 7.
#
# There were no avatars in the tree at all. On Windows, picking your picture
# is part of setting the machine up, and the people this distro is for expect
# to find that; landing on a stock grey silhouette is a small thing that makes
# a new machine feel unfinished.
#
# The set is deliberately abstract -- rings, chevrons, facets, a dot grid --
# rather than faces or animals. An avatar has to survive being drawn at 32px
# in a corner of the login screen, so each one is a single high-contrast
# figure on a two-stop ground, with nothing thinner than about 6% of the
# frame. Colours are drawn from the wallpaper palette, so the login screen,
# the desktop and the user's own picture agree with each other.
#
# Full bleed, no transparency: Plasma masks these into a circle and SDDM does
# not, so the art has to work as both a square tile and a disc. Every figure
# therefore stays inside the inscribed circle.
set -e

REPO=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}
SHARE=$REPO/config/includes.chroot/usr/share
DST=$SHARE/plasma/avatars
FACES=$SHARE/sddm/faces
M=magick
S=256

mkdir -p "$DST" "$FACES"

WK=$(mktemp -d "${TMPDIR:-/tmp}/avatarXXXXXX")
trap 'rm -rf "$WK"' EXIT

# A diagonal two-stop ground, interpolated between opposite corners.
#
# The obvious way -- render a vertical gradient oversized, -rotate it and crop
# back -- put a white wedge in the corner of all twelve avatars, because what
# rotate leaves outside the source square is background, and the crop could
# not miss it. barycentric interpolates across the real canvas instead, so
# there is nothing outside the image to leak in.
ground() {                                # TOP BOT OUT
    E=$((S-1))
    $M -size "${S}x${S}" xc: \
       -sparse-color barycentric "0,0 #$1 $E,$E #$2" "$3"
}

# figure() draws one motif in INK over the ground. Every geometry is a
# fraction of S, so bumping the avatar size up later re-renders identically.
avatar() {                                # NAME TOP BOT INK MOTIF
    ground "$2" "$3" "$WK/g.png"
    Q=$((S/2))
    case $5 in
    rings)
        $M "$WK/g.png" -stroke "#$4" -fill none -strokewidth $((S*7/100)) \
           -draw "circle $Q,$Q $Q,$((Q - S*13/100))" \
           -strokewidth $((S*5/100)) \
           -draw "arc $((S*20/100)),$((S*20/100)) $((S*80/100)),$((S*80/100)) 200,340" \
           "$WK/a.png" ;;
    chevron)
        $M "$WK/g.png" -stroke "#$4" -fill none -strokewidth $((S*8/100)) \
           -draw "polyline $((S*28/100)),$((S*42/100)) $Q,$((S*24/100)) $((S*72/100)),$((S*42/100))" \
           -draw "polyline $((S*28/100)),$((S*62/100)) $Q,$((S*44/100)) $((S*72/100)),$((S*62/100))" \
           -draw "polyline $((S*28/100)),$((S*82/100)) $Q,$((S*64/100)) $((S*72/100)),$((S*82/100))" \
           "$WK/a.png" ;;
    facet)
        # A peak with its left face knocked back, so it still reads as one
        # solid figure at 32px. Drawn as two separate triangles it came out
        # looking like a broken arrow.
        # The two faces are drawn as separate, NON-overlapping polygons. The
        # first cut painted the whole triangle solid and then laid a 45%
        # version of the SAME ink over its left half -- blending a colour
        # with itself returns that colour, so the facet came out flat. The
        # dim face has to meet the ground, not the ink, to shade at all.
        $M "$WK/g.png" -stroke none -fill "#$4" \
           -draw "polygon $Q,$((S*22/100)) $((S*82/100)),$((S*76/100)) $Q,$((S*76/100))" \
           -draw "fill-opacity 0.45 polygon $Q,$((S*22/100)) $Q,$((S*76/100)) $((S*18/100)),$((S*76/100))" \
           "$WK/a.png" ;;
    dots)
        CMD="$M '$WK/g.png' -stroke none -fill '#$4'"
        r=0
        while [ $r -lt 4 ]; do
            c=0
            while [ $c -lt 4 ]; do
                CX=$((S*26/100 + c*S*16/100)); CY=$((S*26/100 + r*S*16/100))
                RR=$((S*5/100 - (r+c)*S/400))
                if [ $RR -lt $((S*2/100)) ]; then RR=$((S*2/100)); fi
                CMD="$CMD -draw 'circle $CX,$CY $((CX+RR)),$CY'"
                c=$((c+1))
            done
            r=$((r+1))
        done
        eval "$CMD '$WK/a.png'" ;;
    bars)
        # Three parallel strokes on the same diagonal, stepping shorter. The
        # first cut gave them different lengths AND different centres, which
        # read as an accident rather than as a mark.
        $M "$WK/g.png" -stroke "#$4" -strokewidth $((S*9/100)) \
           -draw "stroke-linecap round line $((S*26/100)),$((S*74/100)) $((S*62/100)),$((S*26/100))" \
           -draw "stroke-linecap round line $((S*46/100)),$((S*74/100)) $((S*74/100)),$((S*37/100))" \
           -draw "stroke-linecap round line $((S*66/100)),$((S*74/100)) $((S*82/100)),$((S*53/100))" \
           "$WK/a.png" ;;
    hex)
        $M "$WK/g.png" -stroke "#$4" -fill none -strokewidth $((S*8/100)) \
           -draw "polygon $Q,$((S*20/100)) $((S*78/100)),$((S*35/100)) $((S*78/100)),$((S*65/100)) $Q,$((S*80/100)) $((S*22/100)),$((S*65/100)) $((S*22/100)),$((S*35/100))" \
           "$WK/a.png" ;;
    esac
    # -alpha off: these are opaque tiles, and the alpha plane is dead weight.
    # Date chunks excluded so a rebuild is byte-identical and does not churn
    # the signed release checksums over art that did not change.
    $M "$WK/a.png" -alpha off -depth 8 \
       +set date:create +set date:modify +set date:timestamp \
       -define png:exclude-chunk=date,time -quality 95 "$DST/$1.png"
}

#         name       top     bot     ink     motif
avatar dagric-blue    2b6fb5  10243c  eaf4ff  rings
avatar dagric-cyan    16889a  05323c  e6feff  chevron
avatar dagric-teal    1d9c7a  06342a  e8fff6  facet
avatar dagric-violet  6b4fc6  241546  f1ebff  dots
avatar dagric-amber   d08a1e  4a2a05  fff4dd  bars
avatar dagric-rose    c2436f  40122a  ffe9f0  hex
avatar dagric-slate   5a6b7d  1a2029  eef2f6  facet
avatar dagric-forest  2f8f4e  0c2e1a  e9ffee  rings
avatar dagric-ember   d1541f  40120a  ffe8dd  chevron
avatar dagric-ink     2a3f66  080d1a  dce6ff  dots
avatar dagric-sand    bf9257  3d2a14  fff3e0  hex
avatar dagric-void    23262b  000000  cfd6de  bars

# SDDM shows default.face.icon for any account without a picture of its own.
cp "$DST/dagric-blue.png" "$FACES/default.face.icon"

echo "wrote $(ls "$DST" | wc -l) avatars to $DST ($(du -sh "$DST" | cut -f1))"
echo "wrote $FACES/default.face.icon"
