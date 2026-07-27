#!/bin/sh
# Dagric wallpaper generator -- every shipped pack, all twenty designs.
#
# Renders each design as a branded pack and a no-branding "Clean" twin,
# straight into config/includes.chroot/usr/share/wallpapers. Needs
# ImageMagick 7 (`magick`) and the DejaVu Sans font.
#
#   sh branding/wallpaper/make-wallpapers.sh [REPO_ROOT]
#
# Env knobs, for iterating on the art:
#   RESLIST="1920x1080"                  # skip the slow 4K pass
#   ONLY="DagricSlate DagricEmber"       # rebuild just these
#   OUTROOT=/tmp/wpstage                 # render somewhere other than the tree
#
# House look: a deep vertical ground, a wide soft radial bloom screened on,
# and the monogram + wordmark + tagline centred in the upper third. Each
# design then gets its own COMPOSITION -- corner light, horizon glow, contour
# rings, light shafts, aurora curtains, dune strata, iso-lines, mesh blobs,
# facets, halftone -- so a grid of thumbnails reads as twenty pictures rather
# than one picture in twenty colours.
#
# Three waves, in the order they were drawn:
#
#   1. Dagric, Dawn, Dusk, Forest, Midnight, Neon. These six shipped for
#      months with NO generator -- they were drawn by hand and so could not be
#      re-rendered, corrected or restyled, and five of them are named by a
#      .style file. They are back under the generator now: `classic()` below
#      is the composition recovered by fitting the shipped PNGs pixel by
#      pixel (full-width bloom, 88% of H tall, centred at 45% of H, RMSE
#      under one part in 255), so the art in the tree is what this script
#      makes, not something nobody could reproduce.
#   2. Slate, Ember, Violet, Arctic, Copper, Ink, Aurora, Sand.
#   3. Contour, Mesh, Prism, Linen, Void, Halftone -- added for variety that
#      is structural rather than chromatic: line work, blobs, flat facets, a
#      paper grain, a true-black panel and a dot matrix.
#
# Every geometry below is a percentage of W or H, so 1080p and 4K come out as
# the same picture rather than the same picture with differently-sized details.
set -e

REPO=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}
SHARE=$REPO/config/includes.chroot/usr/share
DST=$SHARE/wallpapers
LOGO=$SHARE/dagric/logo/dagric-logo.png
M=magick

[ -f "$LOGO" ] || { echo "no logo at $LOGO -- is $REPO the repo root?" >&2; exit 1; }

WK=$(mktemp -d "${TMPDIR:-/tmp}/wpgenXXXXXX")
trap 'rm -rf "$WK"' EXIT

RESLIST=${RESLIST:-"1920x1080 3840x2160"}
ONLY=${ONLY:-""}
OUTROOT=${OUTROOT:-"$DST"}

C="$WK/c.miff"

# ---------------------------------------------------------------- helpers ---
geo() {                                   # x y -> +x+y / -x-y
    case $1 in -*) sx=$1 ;; *) sx="+$1" ;; esac
    case $2 in -*) sy=$2 ;; *) sy="+$2" ;; esac
    printf '%s%s' "$sx" "$sy"
}

ground() {                                # TOP BOT
    $M -size "${W}x${H}" gradient:"#$1-#$2" -colorspace sRGB "$C"
}

# A real radial gradient, squashed to shape, centred anywhere on -- or off --
# the canvas and screened on at a controlled strength, so it reads as
# atmosphere rather than a spotlight. CX/CY are the CENTRE, in pixels; putting
# the centre outside the frame is how the corner lights and horizon glows are
# built. Intermediates stay 16-bit MIFF so the strength multiply does not
# quantise before the final 8-bit write.
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

vig() {                                   # amount 0..1
    $M -size 1600x1600 radial-gradient:"#ffffff-#000000" -resize "${W}x${H}!" \
       -negate -evaluate multiply "$1" -negate "$WK/_v.miff"
    $M "$C" "$WK/_v.miff" -compose multiply -composite "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

screen_on() {                             # layerfile strength
    $M "$C" \( "$1" -evaluate multiply "$2" \) -compose screen -composite "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

# the three faint sweeps low in frame, straight from the house look
sweeps() {                                # COLOR
    $M "$C" -stroke "#$1" -fill none -strokewidth "$SWD" \
      -draw "stroke-opacity 0.30 bezier 0,$((H*76/100)) $((W*32/100)),$((H*70/100)) $((W*68/100)),$((H*83/100)) $W,$((H*74/100))" \
      -draw "stroke-opacity 0.20 bezier 0,$((H*83/100)) $((W*36/100)),$((H*77/100)) $((W*72/100)),$((H*90/100)) $W,$((H*81/100))" \
      -draw "stroke-opacity 0.12 bezier 0,$((H*90/100)) $((W*40/100)),$((H*85/100)) $((W*76/100)),$((H*96/100)) $W,$((H*88/100))" \
      "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

# The whole first-wave composition in one line. Recovered from the shipped
# PNGs rather than guessed: the ground is a plain vertical gradient, the bloom
# is an ellipse exactly as wide as the frame and 88% of H tall centred at 45%
# of H, and the sweeps are drawn in the bloom's own colour. There is no
# vignette -- the corners of the originals match their row exactly.
classic() {                               # GTOP GBOT BLOOMCOL STRENGTH
    ground "$1" "$2"
    bloom "$W" $((H*88/100)) $((W/2)) $((H*45/100)) "$3" "$4"
    sweeps "$3"
}

# A smooth grayscale height field: a handful of random cells blown up to the
# full canvas and blurred until the noise becomes rolling terrain. The blur
# is proportional to W so 4K gets the same landforms as 1080p rather than the
# same landforms at half the size. -seed makes it reproducible; without it
# every rebuild would churn the signed release checksums.
field() {                                 # SEED COLS ROWS BLURPERMILL OUT
    $M -size "${2}x${3}" -seed "$1" xc:gray50 +noise Random -colorspace gray \
       -resize "${W}x${H}!" -blur "0x$((W*$4/1000))" -auto-level "$5"
}

# Fine grain, built once as a 256px tile and then tiled over the canvas. The
# obvious way -- +noise straight onto a 4K canvas -- is 20x the bytes, because
# PNG cannot predict random pixels. A repeating tile is periodic, so LZ77
# matches it after the first row of tiles and the texture is nearly free.
# At this amplitude the repeat is invisible; it reads as paper, not as tiling.
# A woven texture: two thread directions alternating over a 2N pixel cell,
# tiled across the frame and overlaid so it darkens and lightens the ground
# without changing its colour.
#
# This started out as random grain, and random grain is a trap. Gaussian
# noise fine enough to read as paper is invisible past arm's length, and it
# costs 4.9 MB a frame because PNG's row filters cannot predict a random
# pixel from its neighbours. The weave is PERIODIC, so LZ77 matches it after
# the first band of tiles: the same picture, plainly visible, for 30 KB.
#
# -virtual-pixel tile makes the softening blur wrap around the tile's own
# edges, so it still butts up against itself invisibly; blurring without it
# leaves a faint lattice across the whole desktop. The tile is built at the
# 4K cell size and scaled down, so 1080p gets the same weave at half the
# pixels rather than a weave twice as fine per inch.
weave() {                                 # HI LO
    TS=$((W/320))                         # 6 px cell at 1080p, 12 at 4K
    [ -f "$WK/weave_${TS}.png" ] || \
        $M -size 12x12 xc:"#808080" \
           -fill "#$1" -draw "rectangle 0,0 5,5"  -draw "rectangle 6,6 11,11" \
           -fill "#$2" -draw "rectangle 6,0 11,5" -draw "rectangle 0,6 5,11" \
           -virtual-pixel tile -blur 0x1.4 -resize "${TS}x${TS}!" \
           "$WK/weave_${TS}.png"
    $M -size "${W}x${H}" tile:"$WK/weave_${TS}.png" "$WK/_wv.miff"
    $M "$C" "$WK/_wv.miff" -compose overlay -composite "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

# mark + wordmark + tagline, centred in the upper third
brand() {                                 # INK SUB
    LGW=$((W*6/100))
    $M "$LOGO" -resize "${LGW}x${LGW}" "$WK/_m.png"
    PT=$((W*20/1000)); SPT=$((W*8/1000))
    Y0=$((H*24/100))
    $M "$C" "$WK/_m.png" -gravity north -geometry "+0+$Y0" -compose over -composite \
       -gravity north -font DejaVu-Sans -kerning $((W*4/1000)) \
       -pointsize "$PT" -fill "#$1" \
       -annotate "+0+$((Y0 + LGW + H*4/100))" "DAGRIC" \
       -font DejaVu-Sans -kerning $((W*2/1000)) \
       -pointsize "$SPT" -fill "#$2" \
       -annotate "+0+$((Y0 + LGW + H*4/100 + PT + H*2/100))" "OWN IT OUTRIGHT" \
       "$WK/c2.miff"
    mv "$WK/c2.miff" "$C"
}

# 4x4 Bayer matrix scaled so the whole matrix spans just under one 8-bit LSB
# (1 LSB = 257 in Q16). Added just before the depth-8 write this is textbook
# ordered dithering: a quantisation contour becomes a 4px stipple nobody can
# see. It matters most at 4K, where the same colour ramp is spread over twice
# as many rows and the bands are twice as wide. Because the pattern is strictly
# periodic PNG's LZ77 pass swallows it for about 25% more bytes -- the obvious
# alternative, random Gaussian dither, costs 20x and is not worth it.
mk_bayer() {
    $M -size 4x4 xc:black -depth 16 \
      -fill "#000000000000" -draw "point 0,0" -fill "#008000800080" -draw "point 1,0" \
      -fill "#002000200020" -draw "point 2,0" -fill "#00a000a000a0" -draw "point 3,0" \
      -fill "#00c000c000c0" -draw "point 0,1" -fill "#004000400040" -draw "point 1,1" \
      -fill "#00e000e000e0" -draw "point 2,1" -fill "#006000600060" -draw "point 3,1" \
      -fill "#003000300030" -draw "point 0,2" -fill "#00b000b000b0" -draw "point 1,2" \
      -fill "#001000100010" -draw "point 2,2" -fill "#009000900090" -draw "point 3,2" \
      -fill "#00f000f000f0" -draw "point 0,3" -fill "#007000700070" -draw "point 1,3" \
      -fill "#00d000d000d0" -draw "point 2,3" -fill "#005000500050" -draw "point 3,3" \
      "$WK/bayer.png"
}

emit() {                                  # PKGNAME
    O="$OUTROOT/$1/contents/images"
    mkdir -p "$O"
    [ -f "$WK/tile_${W}x${H}.miff" ] || \
        $M -size "${W}x${H}" tile:"$WK/bayer.png" -depth 16 "$WK/tile_${W}x${H}.miff"
    # -alpha off: every pixel is opaque, so the alpha plane is 6% of dead weight.
    # The date/time chunks are excluded so re-running this script produces
    # byte-identical PNGs -- otherwise every rebuild churns the signed release
    # checksums for artwork that did not actually change.
    $M "$C" "$WK/tile_${W}x${H}.miff" -compose plus -composite \
       -alpha off -depth 8 \
       +set date:create +set date:modify +set date:timestamp \
       -define png:exclude-chunk=date,time \
       -quality 95 "$O/${W}x${H}.png"
}

meta() {                                  # PKGNAME TITLE
    mkdir -p "$OUTROOT/$1"
    cat > "$OUTROOT/$1/metadata.json" << EOF
{
    "KPlugin": {
        "Id": "$1",
        "Name": "$2",
        "License": "CC-BY-SA-4.0",
        "Authors": [ { "Name": "DGR Operations" } ]
    }
}
EOF
}

# ------------------------------------------------------------ compositions ---
compose() {
    SWD=$((W/960))                        # 2 px at 1080p, 4 px at 4K
    QW=$((W/4)); QH=$((H/4))              # quarter-res scratch for soft glows

    case $1 in

    # =================================================== wave 1: classic ===
    # Six colourways of one composition. They were built that way by hand and
    # the .style files lean on the colour, not the shape, so the shape stays.

    # --- the default: brand blue, near full strength -----------------------
    Dagric)
        classic 0d1728 060b14 40b0ff 0.962
        INK=ffffff; SUB=cfe0f2 ;;

    # --- the one light pack of the wave: pale sky, dark ink ----------------
    DagricDawn)
        classic e8eef6 c9d8ea 5ebfff 0.760
        INK=16283c; SUB=3d5a78 ;;

    # --- amber, the warm evening one ---------------------------------------
    DagricDusk)
        classic 1c1018 0a0509 ffab31 0.852
        INK=ffffff; SUB=cfe0f2 ;;

    # --- mint over a green-black ground ------------------------------------
    DagricForest)
        classic 0c1a15 050d0a 6fffc3 0.702
        INK=ffffff; SUB=cfe0f2 ;;

    # --- the same blue as Dagric, turned down two thirds -------------------
    DagricMidnight)
        classic 0a1018 03060b 42b3ff 0.618
        INK=ffffff; SUB=cfe0f2 ;;

    # --- hard cyan, the loudest of the six ---------------------------------
    DagricNeon)
        classic 081420 03080f 00ecff 0.848
        INK=ffffff; SUB=cfe0f2 ;;

    # ==================================================== wave 2: shapes ===

    # --- corner light: one hard-falloff source top-left, deep graphite ------
    DagricSlate)
        ground 232830 070a0e
        bloom $((W*144/100)) $((H*190/100)) $((W*8/100))  $((H*2/100))  eef4fa 0.92
        bloom $((W*46/100))  $((H*46/100))  $((W*2/100))  0             ffffff 0.45
        $M "$C" -stroke "#ffffff" -fill none -strokewidth "$SWD" \
          -draw "stroke-opacity 0.12 line 0,$((H*34/100)) $W,$((H*88/100))" \
          -draw "stroke-opacity 0.06 line 0,$((H*47/100)) $W,$((H*101/100))" \
          "$WK/c2.miff"; mv "$WK/c2.miff" "$C"
        vig 0.34
        INK=ffffff; SUB=c3ced9 ;;

    # --- low horizon glow: coals burning off the bottom edge ---------------
    DagricEmber)
        ground 0d0604 2a1208
        bloom $((W*200/100)) $((H*110/100)) $((W*42/100)) $((H*102/100)) ff6a1e 1.0
        bloom $((W*90/100))  $((H*40/100))  $((W*46/100)) $((H*105/100)) ffd08a 0.70
        sweeps ff9a4d
        vig 0.20
        INK=ffffff; SUB=f5cba6 ;;

    # --- concentric contour rings radiating out of the mark ----------------
    DagricViolet)
        ground 1d1338 06040e
        bloom $((W*160/100)) $((H*130/100)) $((W*50/100)) $((H*30/100)) 7b5cf0 0.74
        CX=$((W/2)); CY=$((H*32/100))
        # built as one command line: 16 separate magick runs over a 4K canvas
        # would cost 16 decode/encode round trips for no reason
        CMD="$M '$C' -stroke '#c0aaff' -fill none -strokewidth $SWD"
        i=1
        while [ $i -le 16 ]; do
            RY=$((H*i*7/100)); RX=$((RY*17/10))
            OP=$(awk "BEGIN{printf \"%.3f\", 0.30*exp(-$i/7.0)+0.03}")
            CMD="$CMD -draw 'stroke-opacity $OP ellipse $CX,$CY $RX,$RY 0,360'"
            i=$((i+1))
        done
        CMD="$CMD '$WK/c2.miff'"
        eval "$CMD"; mv "$WK/c2.miff" "$C"
        vig 0.28
        INK=ffffff; SUB=d5c9ff ;;

    # --- plain gradient, no line work at all: the calm one -----------------
    DagricArctic)
        ground f7fbfe a9c9e2
        bloom $((W*180/100)) $((H*130/100)) $((W*50/100)) $((H*4/100)) ffffff 0.70
        vig 0.16
        INK=15293e; SUB=4d6c88 ;;

    # --- angled light shafts off the top-right corner ----------------------
    DagricCopper)
        # shafts are drawn and blurred at quarter res: a 4K gaussian with this
        # sigma is minutes of work and the result is identical once upscaled
        ground 20150a 070403
        CMD="$M -size ${QW}x${QH} xc:black -fill none"
        set -- "0.60 94 16 10" "0.34 103 34 6" "0.22 86 2 13" "0.15 114 50 7" "0.10 78 -14 5"
        for r in "$@"; do
            OP=$(echo "$r" | cut -d' ' -f1)
            X1=$(echo "$r" | cut -d' ' -f2)
            X2=$(echo "$r" | cut -d' ' -f3)
            SW=$(echo "$r" | cut -d' ' -f4)
            CMD="$CMD -stroke '#ffbe7c' -strokewidth $((QW*SW/1000))"
            CMD="$CMD -draw 'stroke-opacity $OP line $((QW*X1/100)),$((-QH*15/100)) $((QW*X2/100)),$((QH*130/100))'"
        done
        CMD="$CMD -blur 0x$((QW*9/1000)) '$WK/_r.miff'"
        eval "$CMD"
        $M "$WK/_r.miff" -resize "${W}x${H}!" "$WK/_r2.miff"
        screen_on "$WK/_r2.miff" 0.75
        bloom $((W*100/100)) $((H*115/100)) $((W*94/100)) $((-H*4/100)) e09550 0.85
        vig 0.34
        INK=ffffff; SUB=e8c3a0 ;;

    # --- near-black, single soft band of light along the top edge ----------
    DagricInk)
        ground 0e1728 010305
        bloom $((W*240/100)) $((H*80/100)) $((W*50/100)) $((H*2/100)) 3288c8 0.85
        vig 0.28
        INK=ffffff; SUB=9fc4e0 ;;

    # --- soft vertical aurora curtains, left and right of centre -----------
    DagricAurora)
        ground 05161f 01070b
        # Each curtain is a tapered quad that runs off both the top and the
        # bottom of the frame, so the blur never leaves a visible rounded cap.
        # They sit in the outer thirds; the centre stays clear for the mark.
        CMD="$M -size ${QW}x${QH} xc:black -stroke none"
        set -- "3ff0b4 5 6 12 2 0.90" "2fc8e8 16 4 11 2 0.66" "6f5ce0 26 3 32 1 0.44" \
               "3ff0b4 74 4 68 2 0.56" "2fc8e8 86 5 91 2 0.80" "6f5ce0 96 3 89 1 0.40"
        for r in "$@"; do
            CO=$(echo "$r" | cut -d' ' -f1)
            XT=$(echo "$r" | cut -d' ' -f2)
            WT=$(echo "$r" | cut -d' ' -f3)
            XB=$(echo "$r" | cut -d' ' -f4)
            WB=$(echo "$r" | cut -d' ' -f5)
            OP=$(echo "$r" | cut -d' ' -f6)
            CMD="$CMD -fill '#$CO' -draw \"fill-opacity $OP path 'M $((QW*(XT-WT)/100)),$((-QH*12/100)) L $((QW*(XT+WT)/100)),$((-QH*12/100)) L $((QW*(XB+WB)/100)),$((QH*114/100)) L $((QW*(XB-WB)/100)),$((QH*114/100)) Z'\""
        done
        CMD="$CMD -blur 0x$((QW*11/1000)) '$WK/_a.miff'"
        eval "$CMD"
        # dark -> bright over the top third, then a long fade to the floor, so
        # the curtains rise into frame instead of being clipped off at y=0
        $M \( -size "${QW}x$((QH*32/100))"        gradient:"#0f0f0f-#ffffff" \) \
           \( -size "${QW}x$((QH - QH*32/100))"   gradient:"#ffffff-#0e0e0e" \) \
           -append "$WK/_fm.miff"
        $M "$WK/_a.miff" "$WK/_fm.miff" \
           -compose multiply -composite -resize "${W}x${H}!" "$WK/_a2.miff"
        screen_on "$WK/_a2.miff" 1.0
        bloom $((W*170/100)) $((H*80/100)) $((W*50/100)) $((H*96/100)) 12707e 0.55
        vig 0.22
        INK=ffffff; SUB=bfe8dd ;;

    # --- layered dune strata, warm and light -------------------------------
    DagricSand)
        ground fbf0dc e0b581
        bloom $((W*90/100)) $((H*80/100)) $((W*24/100)) $((H*36/100)) fff3d6 0.75
        CMD="$M '$C' -stroke none"
        set -- "c9a072 0.45 58 46 66" "b98d5e 0.45 69 78 61" "a87a4b 0.50 79 66 88" "8b6136 0.55 89 96 82"
        for r in "$@"; do
            CO=$(echo "$r" | cut -d' ' -f1)
            OP=$(echo "$r" | cut -d' ' -f2)
            Y0=$(echo "$r" | cut -d' ' -f3)
            YA=$(echo "$r" | cut -d' ' -f4)
            YB=$(echo "$r" | cut -d' ' -f5)
            CMD="$CMD -fill '#$CO' -draw \"fill-opacity $OP path 'M 0,$((H*Y0/100)) C $((W*30/100)),$((H*YA/100)) $((W*66/100)),$((H*YB/100)) $W,$((H*(Y0+3)/100)) L $W,$H L 0,$H Z'\""
        done
        CMD="$CMD '$WK/c2.miff'"
        eval "$CMD"; mv "$WK/c2.miff" "$C"
        $M "$C" -blur 0x"$SWD" "$WK/c2.miff"; mv "$WK/c2.miff" "$C"
        vig 0.16
        INK=3b2b1b; SUB=7f6247 ;;

    # ===================================================== wave 3: texture ===
    # The first fourteen are all soft light on a gradient. These six are the
    # other half of the gallery: line work, blobs, flat colour, grain, true
    # black and a dot grid -- so somebody scrolling the Appearance page sees
    # different KINDS of picture, not more colours of the same one.

    # --- iso-lines off a smooth random terrain -----------------------------
    DagricContour)
        ground 08202a 03090d
        bloom $((W*170/100)) $((H*120/100)) $((W*50/100)) $((H*64/100)) 1d7f8c 0.78
        field 21 14 8 20 "$WK/_hf.miff"
        # A sinusoid through the height field gives evenly spaced bands; the
        # hard level keeps only each band's crest, which is exactly a contour
        # line. The threshold sets line WEIGHT, and it has to be this high:
        # a line here is as wide as the band's crest is flat, so at 86% the
        # gentle ground swelled into fat blobs instead of hairlines.
        $M "$WK/_hf.miff" -function Sinusoid 7,0,0.5,0.5 -level 93%,100% \
           -blur 0x"$SWD" "$WK/_ln.miff"
        # Hold the line work out of the top of the frame entirely, then ramp
        # it in. The first cut faded it and that was not enough -- contours
        # still crossed the wordmark, and hairlines behind small white text
        # read as a dirty screen, not as art. Now the top is open sky and the
        # terrain rises into the lower half, which is also how a map looks.
        $M \( -size "${W}x$((H*38/100))"                   xc:"#050505" \) \
           \( -size "${W}x$((H*28/100))" gradient:"#050505-#ffffff" \) \
           \( -size "${W}x$((H - H*38/100 - H*28/100))"    xc:"#ffffff" \) \
           -append "$WK/_lm.miff"
        $M "$WK/_ln.miff" "$WK/_lm.miff" -compose multiply -composite \
           \( -size "${W}x${H}" xc:"#7fe8d2" \) -compose multiply -composite \
           "$WK/_ln2.miff"
        screen_on "$WK/_ln2.miff" 0.62
        vig 0.26
        INK=ffffff; SUB=a6d6cd ;;

    # --- five big soft blobs bleeding into each other ----------------------
    DagricMesh)
        ground 15122b 08061a
        bloom $((W*95/100))  $((H*150/100)) $((W*16/100)) $((H*20/100)) c23f8a 0.85
        bloom $((W*105/100)) $((H*140/100)) $((W*84/100)) $((H*26/100)) 3f5ce0 0.80
        bloom $((W*120/100)) $((H*130/100)) $((W*38/100)) $((H*94/100)) 1f9e86 0.60
        bloom $((W*70/100))  $((H*90/100))  $((W*96/100)) $((H*88/100)) d98a2b 0.42
        bloom $((W*80/100))  $((H*80/100))  $((W*56/100)) $((H*54/100)) 5a7cf0 0.34
        vig 0.22
        INK=ffffff; SUB=d6cdec ;;

    # --- flat low-poly facets, no gradient inside any one triangle ---------
    DagricPrism)
        ground 1a2433 070b12
        CO=16; RO=9
        CMD="$M '$C' -stroke none"
        j=0
        while [ $j -lt $RO ]; do
            i=0
            while [ $i -lt $CO ]; do
                X0=$((W*i/CO));     Y0=$((H*j/RO))
                X1=$((W*(i+1)/CO)); Y1=$((H*(j+1)/RO))
                # Light falls from the top-left, so the base shade is a
                # diagonal ramp. The hash is what stops it looking like a
                # gradient with lines on it: each facet steps off the ramp by
                # a fixed, repeatable amount, which is what makes it read as
                # a folded surface. Nothing here is random at build time.
                k=0
                while [ $k -le 1 ]; do
                    T=$(( (i*100/CO + (RO-1-j)*100/RO) / 2 ))
                    T=$(( T + ((i*73 + j*151 + k*97) % 17) - 8 ))
                    if [ $T -lt 0 ]; then T=0; fi
                    if [ $T -gt 100 ]; then T=100; fi
                    FR=$(( 24 + (108-24)*T/100 ))
                    FG=$(( 34 + (150-34)*T/100 ))
                    FB=$(( 50 + (205-50)*T/100 ))
                    # alternate the split diagonal by cell parity so the
                    # facets do not all lean the same way
                    if [ $(( (i+j) % 2 )) -eq 0 ]; then
                        if [ $k -eq 0 ]; then
                            P="$X0,$Y0 $X1,$Y0 $X0,$Y1"
                        else
                            P="$X1,$Y0 $X1,$Y1 $X0,$Y1"
                        fi
                    else
                        if [ $k -eq 0 ]; then
                            P="$X0,$Y0 $X1,$Y0 $X1,$Y1"
                        else
                            P="$X0,$Y0 $X1,$Y1 $X0,$Y1"
                        fi
                    fi
                    CMD="$CMD -fill 'rgb($FR,$FG,$FB)' -draw 'polygon $P'"
                    k=$((k+1))
                done
                i=$((i+1))
            done
            j=$((j+1))
        done
        CMD="$CMD '$WK/c2.miff'"
        eval "$CMD"; mv "$WK/c2.miff" "$C"
        bloom $((W*130/100)) $((H*130/100)) $((W*10/100)) $((H*4/100)) dbe8ff 0.34
        vig 0.30
        INK=ffffff; SUB=c4d2e6 ;;

    # --- warm cloth: a light ground carrying a woven texture ---------------
    DagricLinen)
        ground f4efe6 dbd0be
        bloom $((W*160/100)) $((H*120/100)) $((W*50/100)) $((H*6/100)) ffffff 0.50
        weave a8a8a8 585858
        vig 0.14
        INK=2c2620; SUB=6e6357 ;;

    # --- true black for OLED panels, lit only along the bottom edge --------
    # Every pixel outside the glow is #000000, so on an OLED those pixels are
    # switched off: less power, and no grey haze in a dark room. The glow is
    # what keeps it from looking like the monitor is broken.
    DagricVoid)
        ground 000000 000000
        bloom $((W*185/100)) $((H*74/100)) $((W*50/100)) $((H*108/100)) 1e5f8f 0.72
        INK=e8eef6; SUB=5f7186 ;;

    # --- dot matrix, dots shrinking away from the light --------------------
    DagricHalftone)
        ground 101a33 04070e
        CO=48; RO=27
        RMAX=$((W*6/1000))
        # The light sits low and left, so the dots gather in that corner and
        # die out before they reach the wordmark. The first cut lit it from
        # the top left with a falloff so slow that every cell still drew a
        # near-full-size dot: 1296 identical dots across the whole frame read
        # as a screen door over the text, and cost 800 KB to say nothing.
        LX=$((W*20/100)); LY=$((H*82/100))
        CMD="$M -size ${W}x${H} xc:black -stroke none -fill white"
        j=0
        while [ $j -lt $RO ]; do
            i=0
            while [ $i -lt $CO ]; do
                CXP=$((W*(2*i+1)/(2*CO))); CYP=$((H*(2*j+1)/(2*RO)))
                # distance from the light, in permille of W and H
                DX=$(( (CXP - LX) * 1000 / W ))
                DY=$(( (CYP - LY) * 1000 / H ))
                D=$(( (DX*DX + DY*DY) / 1000 ))
                R=$(( RMAX - RMAX*D/340 ))
                # Past the cutoff no dot is drawn at all. That is what keeps
                # two thirds of the frame flat, and flat is what compresses.
                if [ $R -ge 1 ]; then
                    CMD="$CMD -draw 'circle $CXP,$CYP $((CXP+R)),$CYP'"
                fi
                i=$((i+1))
            done
            j=$((j+1))
        done
        CMD="$CMD '$WK/_dot.miff'"
        eval "$CMD"
        # tint the dots and let a radial mask do the brightness falloff --
        # cheaper and smoother than a fill-opacity on every single dot
        $M -size 1600x1600 radial-gradient:"#ffffff-#0a0a0a" \
           -resize "$((W*126/100))x$((H*126/100))!" "$WK/_dm.miff"
        $M -size "${W}x${H}" xc:black "$WK/_dz.miff"
        $M "$WK/_dz.miff" "$WK/_dm.miff" \
           -geometry "$(geo $(( LX - W*63/100 )) $(( LY - H*63/100 )))" \
           -compose plus -composite "$WK/_dmask.miff"
        $M "$WK/_dot.miff" "$WK/_dmask.miff" -compose multiply -composite \
           \( -size "${W}x${H}" xc:"#a8c8ff" \) -compose multiply -composite \
           "$WK/_dot2.miff"
        screen_on "$WK/_dot2.miff" 0.85
        bloom $((W*150/100)) $((H*150/100)) "$LX" "$LY" 2f5ad0 0.46
        vig 0.30
        INK=ffffff; SUB=b9c8e8 ;;

    *) echo "unknown design $1" >&2; exit 1 ;;
    esac
}

# --------------------------------------------------------------- driver -----
# NAME|TITLE|CLEAN(0/1)  -- CLEAN also emits a <Name>Clean pack from the same
# base, written before brand() runs, for owners who want no logo on the desktop
#
# CLEAN emits a second, logo-free pack from the same base. The branded art
# carries the logo and the words "OWN IT OUTRIGHT", which is right for a
# screenshot or a store page and wrong for the desktop somebody just paid for
# -- a slogan burned into the wallpaper reads as an advertisement in your own
# house. Only Slate and Aurora used to offer a logo-free twin, so fourteen of
# sixteen packs were unusable by anyone who simply wanted the art.
#
# Wave 1 is the exception, and it is a BUDGET decision, not a design one. In
# this house style a design costs about 3-6 MB once you count a branded cut, a
# clean cut, 1080p and 4K -- most of it the ordered dither, which is half the
# bytes of a smooth frame and is not negotiable because without it 4K gradients
# band. Twenty designs with a twin each is 78 MB against a 70 MB ceiling, so
# something had to give: either six designs or six duplicates. Six more
# PICTURES beat six more copies of pictures already in the gallery, and the
# fourteen clean cuts that do ship cover every mood in it.
#
# If the ceiling ever moves, this is a one-character change: flip these six to
# 1 and the wave-1 clean twins cost 9.7 MB.
#
# The wave-1 names are load-bearing: classy.style, dawn.style, forest.style,
# midnight.style and neon.style each name one of them, so these Ids cannot be
# renamed without breaking a style.
SPECS="Dagric|Dagric|0
DagricDawn|Dagric Dawn|0
DagricDusk|Dagric Dusk|0
DagricForest|Dagric Forest|0
DagricMidnight|Dagric Midnight|0
DagricNeon|Dagric Neon|0
DagricSlate|Dagric Slate|1
DagricEmber|Dagric Ember|1
DagricViolet|Dagric Violet|1
DagricArctic|Dagric Arctic|1
DagricCopper|Dagric Copper|1
DagricInk|Dagric Ink|1
DagricAurora|Dagric Aurora|1
DagricSand|Dagric Sand|1
DagricContour|Dagric Contour|1
DagricMesh|Dagric Mesh|1
DagricPrism|Dagric Prism|1
DagricLinen|Dagric Linen|1
DagricVoid|Dagric Void|1
DagricHalftone|Dagric Halftone|1"

mk_bayer

echo "$SPECS" | while IFS='|' read -r NAME TITLE CLEAN; do
    [ -n "$NAME" ] || continue
    if [ -n "$ONLY" ]; then
        case " $ONLY " in *" $NAME "*) : ;; *) continue ;; esac
    fi
    for RES in $RESLIST; do
        W=${RES%x*}; H=${RES#*x}
        compose "$NAME"
        if [ "$CLEAN" = 1 ]; then emit "${NAME}Clean"; fi
        brand "$INK" "$SUB"
        emit "$NAME"
    done
    meta "$NAME" "$TITLE"
    if [ "$CLEAN" = 1 ]; then meta "${NAME}Clean" "$TITLE Clean"; fi
    echo "  built $NAME"
done

echo "--- sizes ---"
du -sh "$OUTROOT"/Dagric* 2>/dev/null | sort -k2
