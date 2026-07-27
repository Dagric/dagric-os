#!/bin/sh
# Dagric wallpaper generator -- second wave (DagricSlate .. DagricSand).
#
# Renders the eight second-wave wallpaper packs, plus the two no-branding
# "Clean" variants, straight into config/includes.chroot/usr/share/wallpapers.
# Needs ImageMagick 7 (`magick`) and the DejaVu Sans font.
#
#   sh branding/wallpaper/make-wallpapers.sh [REPO_ROOT]
#
# Env knobs, for iterating on the art:
#   RESLIST="1920x1080"                  # skip the slow 4K pass
#   ONLY="DagricSlate DagricEmber"       # rebuild just these
#   OUTROOT=/tmp/wpstage                 # render somewhere other than the tree
#
# House look, inherited from the first six packs: a deep vertical ground, a
# wide soft radial bloom screened on, and the monogram + wordmark + tagline
# centred in the upper third. What is new here is that each entry gets its own
# COMPOSITION -- corner light, low horizon glow, contour rings, plain gradient,
# light shafts, top-edge band, aurora curtains, dune strata -- so a grid of
# thumbnails reads as eight pictures rather than one picture in eight colours.
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

    *) echo "unknown design $1" >&2; exit 1 ;;
    esac
}

# --------------------------------------------------------------- driver -----
# NAME|TITLE|CLEAN(0/1)  -- CLEAN also emits a <Name>Clean pack from the same
# base, written before brand() runs, for owners who want no logo on the desktop
#
# CLEAN is 1 for every pack on purpose. The branded art carries the logo and
# the words "OWN IT OUTRIGHT", which is right for a screenshot or a store page
# and wrong for the desktop somebody just paid for -- a slogan burned into the
# wallpaper reads as an advertisement in your own house. Only Slate and Aurora
# used to offer a logo-free twin, so fourteen of sixteen packs were unusable by
# anyone who simply wanted the art. Both versions now ship for all eight; the
# owner picks in the Appearance gallery, and the extra packs cost about 11 MB.
SPECS="DagricSlate|Dagric Slate|1
DagricEmber|Dagric Ember|1
DagricViolet|Dagric Violet|1
DagricArctic|Dagric Arctic|1
DagricCopper|Dagric Copper|1
DagricInk|Dagric Ink|1
DagricAurora|Dagric Aurora|1
DagricSand|Dagric Sand|1"

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
