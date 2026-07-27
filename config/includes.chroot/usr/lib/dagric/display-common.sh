# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Dagric OS — everything both display tools need to know about screens.
# SOURCED, never executed: /usr/bin/dagric-display (the settings window) and
# /usr/lib/dagric/display-autoscale (the first-login default) share it.
#
# WHICH PATH THIS SUPPORTS: WAYLAND, and only Wayland.
# That is not a shortcut, it is a property of X11. On Wayland KWin owns the
# per-screen scale, kscreen-doctor changes it live with no sign-out, and that
# live change is what makes an undo timer possible in the first place. Plasma 6
# on X11 has no live per-output scale at all — only the global kdeglobals
# [KScreen] ScaleFactor, which needs a full sign-out to take effect and
# therefore cannot be tried and taken back. Rather than ship a half-working X11
# path, both tools say plainly that they need a Wayland session and point at
# System Settings.
#
# UPDATED: this used to add "and anyway there is no X11 session on a Dagric
# image", which was true when it was written and is no longer. kwin-x11 is now
# an explicit line in desktop.list.chroot, because plasma-workspace had always
# shipped /usr/share/xsessions/plasmax11.desktop with no window manager behind
# it and SDDM offered that trap at every login. So an X11 session CAN start
# here now, Wayland is still the default and the tested path, and the fallback
# below is a real code path rather than dead defensive code.
#
# WHERE THE NUMBERS COME FROM. Nothing here is invented. dg_auto_scale100 is a
# transcription of KWin 6.3.6's OutputConfigurationStore::chooseScale(), and
# dg_snap100 is the pair of corrections KWin added in 6.4 that 6.3.6 lacks.
# The EDID reading matches KWin's own (src/utils/edid.cpp) so that our number
# and KWin's are computed from the same millimetres — see dg_edid_mm.

# kscreen-doctor writes its ANSI colour codes unconditionally: the escapes are
# plain constants in doctor.cpp, there is no isatty() check, so the output is
# coloured even down a pipe and every field has to be de-coloured before it can
# be read. LC_ALL=C on top, because the scale is parsed as a decimal number and
# a locale with a comma decimal separator would read "1.25" as 1.
DG_ESC=$(printf '\033')
DG_SED_DECOLOUR="s/${DG_ESC}\[[0-9;]*m//g"

# --- what kind of session are we in ------------------------------------------
dg_session() {
    if [ -n "$WAYLAND_DISPLAY" ] || [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        printf 'wayland'
    elif [ -n "$DISPLAY" ] || [ "$XDG_SESSION_TYPE" = "x11" ]; then
        printf 'x11'
    else
        printf 'unknown'
    fi
}

# True only when we can both read and change screen scale. kscreen-doctor comes
# from libkscreen-bin, which is a hard Depends of the kscreen package in the
# desktop list — but check anyway rather than fail with a "command not found"
# in front of somebody who just left Windows.
dg_can_scale() {
    [ "$(dg_session)" = "wayland" ] || return 1
    command -v kscreen-doctor >/dev/null 2>&1 || return 1
    return 0
}

# --- reading the screens -----------------------------------------------------
# One line per enabled, connected screen:
#
#     name <TAB> width_px <TAB> height_px <TAB> scale_hundredths <TAB> scale_text
#
# width/height are the CURRENT mode in real pixels (the mode kscreen-doctor
# marks with a '*'), not the Geometry line — Geometry is already divided by the
# scale, so using it would make the answer depend on the thing we are trying to
# compute. scale_text is kept verbatim alongside the rounded hundredths so that
# putting a scale back restores the exact value that was there, even if some
# other tool set something that is not a clean 0.05 step.
dg_outputs() {
    command -v kscreen-doctor >/dev/null 2>&1 || return 0
    kscreen-doctor -o 2>/dev/null | sed "$DG_SED_DECOLOUR" | LC_ALL=C awk '
        function flush_out() {
            if (name != "" && en && conn && w > 0 && h > 0 && stxt != "")
                printf "%s\t%d\t%d\t%d\t%s\n", name, w, h, int(s * 100 + 0.5), stxt
        }
        $1 == "Output:"  { flush_out(); name = $3; en = 0; conn = 0
                           w = 0; h = 0; s = 0; stxt = ""; next }
        $1 == "enabled"   { en = 1;   next }
        $1 == "connected" { conn = 1; next }
        $1 == "Scale:"    { s = $2 + 0; stxt = $2; next }
        $1 == "Modes:"    { for (i = 2; i <= NF; i++) {
                                if ($i ~ /^[0-9]+:[0-9]+x[0-9]+@[0-9]+\*/) {
                                    split($i, m, /[:x@]/); w = m[2] + 0; h = m[3] + 0
                                }
                            }
                            next }
        END { flush_out() }
    '
}

# A screen KWin treats as built-in. KWin decides from the DRM connector type
# (LVDS, eDP or DSI — DrmConnector::isInternal), and the kernel names those
# connectors after the same types, so the name is the same answer without
# needing to open anything.
dg_is_internal() {
    case "$1" in
        eDP-*|eDP|LVDS-*|LVDS|DSI-*|DSI) return 0 ;;
        *) return 1 ;;
    esac
}

# --- the panel's own account of itself ---------------------------------------
# /sys/class/drm/<card>-<connector>/edid, e.g. card0-eDP-1 for the output
# kscreen calls eDP-1. Two graphics cards can each have a "DP-1", and picking
# the wrong one would measure the wrong screen, so an ambiguous match is
# treated as no answer at all.
# A variable rather than a literal only so the build's test harness can point
# it at a directory of captured EDIDs; nothing on the image ever sets it.
DG_DRM=${DG_DRM:-/sys/class/drm}

dg_edid_file() {
    _hit=
    for _d in "$DG_DRM"/*-"$1"; do
        [ -r "$_d/edid" ] || continue
        if [ -n "$_hit" ]; then return 1; fi
        _hit=$_d/edid
    done
    [ -n "$_hit" ] || return 1
    printf '%s' "$_hit"
}

# Physical size in millimetres, or nothing when the panel does not say.
#
# This deliberately mirrors KWin's determineScreenPhysicalSizeMm() rather than
# doing the obvious thing (bytes 21/22, the centimetre fields). KWin prefers
# the millimetre figures inside a detailed timing descriptor and only falls
# back to centimetres, so reading only the centimetres would give a number a
# centimetre out on many panels — and this whole design turns on our figure and
# KWin's agreeing. A disagreement means we misread the screen and must not
# touch it.
#
# The aspect-ratio test is KWin's too: a descriptor whose physical shape does
# not match its own pixel shape is a mis-typed EDID, not a measurement.
dg_edid_mm() {
    _f=$(dg_edid_file "$1") || return 1
    dg_edid_mm_file "$_f"
}

dg_edid_mm_file() {
    od -An -v -tu1 -N 128 "$1" 2>/dev/null | LC_ALL=C awk '
        { for (i = 1; i <= NF; i++) b[n++] = $i }
        END {
            if (n < 128) exit
            # 00 FF FF FF FF FF FF 00 — anything else is not an EDID block.
            if (b[0] != 0 || b[7] != 0) exit
            for (i = 1; i <= 6; i++) if (b[i] != 255) exit
            for (d = 54; d <= 108; d += 18) {
                if (b[d] == 0 && b[d+1] == 0) continue   # a descriptor, not a timing
                hpx = b[d+2]  + int(b[d+4] / 16) * 256
                vpx = b[d+5]  + int(b[d+7] / 16) * 256
                hmm = b[d+12] + int(b[d+14] / 16) * 256
                vmm = b[d+13] + (b[d+14] % 16) * 256
                if (hmm <= 0 || vmm <= 0 || hpx <= 0 || vpx <= 0) continue
                diff = hmm * vpx - vmm * hpx
                if (diff < 0) diff = -diff
                if (10 * diff <= vmm * vpx) { print hmm, vmm; exit }
            }
            if (b[21] > 0 && b[22] > 0) print b[21] * 10, b[22] * 10
        }'
    return 0
}

# Does the panel report a size a real screen could have? A depressing number of
# cheap panels, docks and virtual machines put an aspect ratio, a zero or plain
# rubbish in the size fields, and a DPI computed from rubbish is rubbish. The
# bounds are a 5-inch and a 90-inch diagonal, compared squared so no square
# root is needed. Fail this and both tools leave the scale exactly as it is.
dg_mm_sane() {
    _w=$1; _h=$2
    case "$_w$_h" in ''|*[!0-9]*) return 1 ;; esac
    [ "$_w" -ge 30 ] && [ "$_h" -ge 30 ] || return 1
    _d=$(( _w * _w + _h * _h ))
    [ "$_d" -ge 16129 ] && [ "$_d" -le 5225796 ]
}

# --- the scale maths ---------------------------------------------------------
# dg_auto_scale100 <px_w> <px_h> <mm_w> <mm_h> <1 if internal>
#
# KWin 6.3.6's OutputConfigurationStore::chooseScale(), transcribed. The
# comments below are upstream's reasoning, not ours. awk is used rather than
# shell arithmetic because awk works in doubles, exactly like the C++ does, so
# the two land on the same 0.05 step instead of drifting apart on rounding.
#
# One knowing difference: KWin uses targetDpi 150 for an internal screen with
# no laptop lid switch, on the grounds that it is a phone. Dagric is not sold
# for phones, and if KWin ever did take that branch our number would disagree
# with its number and we would — correctly — change nothing.
dg_auto_scale100() {
    LC_ALL=C awk -v pw="$1" -v ph="$2" -v mmw="$3" -v mmh="$4" -v internal="$5" '
        function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v) }
        BEGIN {
            if (mmw < 3 || mmh < 3) { print 100; exit }
            # Eyes resolve less detail further away, so each kind of screen has
            # its own ideal physical item size. minSize is the fewest logical
            # pixels that must survive the scale.
            if (internal == 1) { td = 125 } else { td = 96 }
            ms = 800
            dpix = pw / (mmw / 25.4)
            dpiy = ph / (mmh / 25.4)
            sx = clamp(dpix / td, 1.0, clamp(pw / ms, 1.0, 3.0))
            sy = clamp(dpiy / td, 1.0, clamp(ph / ms, 1.0, 3.0))
            s = (sx < sy) ? sx : sy
            print int(100.0 * s / 5 + 0.5) * 5      # 0.05 steps, as hundredths
        }'
}

# The two corrections KWin 6.4 added and 6.3.6 does not have. Both are pure
# improvements to a number KWin already chose, and both only ever move it a
# little:
#
#   under 1.20  ->  1.0    A scale of 1.05 or 1.15 is too small to make
#                          anything easier to read and large enough to make
#                          every XWayland app soft. 1x is the better screen.
#                          This is the 15.6" 1080p laptop and the 27" 1440p
#                          monitor — the two most common panels in the market
#                          Dagric sells into, and 6.3.6 puts both on 1.15.
#
#   within 0.06 of a whole number -> that whole number
#                          Whole-number scaling is pixel-exact. 1.95 on a 14"
#                          OLED is fractional for no gain when 2.0 was right
#                          there, and fractional is exactly what makes older
#                          apps blurry.
dg_snap100() {
    _s=$1
    [ "$_s" -lt 120 ] && { printf '100'; return 0; }
    _i=$(( (_s + 50) / 100 * 100 ))
    _d=$(( _s - _i )); [ "$_d" -lt 0 ] && _d=$(( -_d ))
    [ "$_d" -lt 6 ] && { printf '%s' "$_i"; return 0; }
    printf '%s' "$_s"
}

# 125 -> "1.25". kscreen-doctor splits its argument on dots and reassembles the
# number itself, so a plain decimal is what it wants.
dg_scale_text() {
    printf '%d.%02d' $(( $1 / 100 )) $(( $1 % 100 ))
}

# The largest scale that still leaves a usable desktop on this screen, in
# hundredths. 800x600 logical pixels is the floor KWin uses when it picks a
# scale itself, and it is the reason a 1366x768 laptop never gets scaled into
# uselessness. The settings window applies the same floor to what it OFFERS,
# which is the difference between "that size is not available on this screen"
# and a desktop where the button that undoes the mistake is off the edge.
dg_max_scale100() {
    _w=$(( $1 * 100 / 800 ))
    _h=$(( $2 * 100 / 600 ))
    _m=$_w
    [ "$_h" -lt "$_m" ] && _m=$_h
    [ "$_m" -gt 200 ] && _m=200
    [ "$_m" -lt 100 ] && _m=100
    printf '%s' "$_m"
}

# --- changing a screen -------------------------------------------------------
# kscreen-doctor's exit status is not a reliable account of whether the change
# landed, so read the scale back and compare instead of believing it. Every
# caller here treats "changed" and "did not change" differently — an undo that
# silently did nothing is worse than one that admits it.
dg_apply_scale() {
    _out=$1
    _want=$2
    kscreen-doctor "output.$_out.scale.$(dg_scale_text "$_want")" >/dev/null 2>&1
    _now=$(dg_outputs | LC_ALL=C awk -F'\t' -v n="$_out" '$1 == n { print $4; exit }')
    [ "$_now" = "$_want" ]
}

# --- saying which screen is which --------------------------------------------
# "DP-2" means nothing to somebody who has only ever used Windows. Connector
# names are only added when two screens would otherwise read the same.
#
# These six went out UNTRANSLATED for one release. They are the only user-facing
# strings in this file, and this file is a LIBRARY under /usr/lib — while
# tools/i18n-extract.sh only listed the tools in /usr/bin. So a French owner got
# a screen picker offering "Built-in screen (1920 x 1080)", and worse, the
# sentence around it is built with eval_gettext: "Taille du texte et des icônes
# sur Built-in screen (1920 x 1080) :". Half-translated reads as broken, not as
# untranslated. display-common.sh is in the extract list now; anything else that
# lands under /usr/lib/dagric and speaks to the owner has to go in too.
#
# gettext is safe to call here even though this file does not source
# dagric-i18n.sh itself: dg_friendly_name has exactly one caller, dagric-display,
# which sources dagric-i18n.sh on the next line — and a function body is not
# resolved until it is called. display-autoscale sources this file at login and
# never calls this function, so nothing there gains a dependency.
dg_friendly_name() {
    # TRANSLATORS: how Dagric names a screen for somebody who has only ever
    # used Windows — the connector name ("eDP-1", "HDMI-A-1") is meaningless to
    # them. Shown as the rows of a "Which screen?" list and inside the sentence
    # "Text and icon size on $_fr:", so it has to read naturally mid-sentence.
    case "$1" in
        eDP-*|eDP|LVDS-*|LVDS|DSI-*|DSI) _k=$(gettext "Built-in screen") ;;
        HDMI-*|HDMI)                     _k=$(gettext "Screen on HDMI") ;;
        DP-*|DP|DisplayPort-*)           _k=$(gettext "Screen on DisplayPort") ;;
        VGA-*|VGA)                       _k=$(gettext "Screen on VGA") ;;
        DVI*)                            _k=$(gettext "Screen on DVI") ;;
        *)                               _k=$(gettext "Screen") ;;
    esac
    # The format stays a literal. $_k is an ARGUMENT, so a msgstr with a % in it
    # can never become a conversion specifier — the rule from dagric-i18n.sh.
    printf '%s (%s x %s)' "$_k" "$2" "$3"
}
