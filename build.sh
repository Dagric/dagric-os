#!/bin/sh
# Dagric OS — build natively on a Debian machine (needs root).
#   sudo apt install live-build rsync
#   sudo ./build.sh            # free edition
#   sudo ./build.sh pro        # Pro edition
#
# This mirrors docker/container-build.sh: without the edition gating below,
# a native build would include ALL pro-*.list.chroot packages under free
# branding, and leave the includes.chroot helper scripts non-executable.
#
# The build happens in a COPY of the tree, never in place. Building free
# edition used to `rm -f config/package-lists/pro-*.list.chroot` in the source
# directory itself — permanently deleting the Pro lists from the working tree,
# so the next `./build.sh pro` would silently produce a "Pro" ISO with none of
# the Pro packages in it. Copy first; the source tree is now read-only to us.
set -e
cd "$(dirname "$0")"
SRC=$(pwd)

EDITION="${1:-free}"
BUILD="${DAGRIC_BUILD_DIR:-$SRC/../dagric-build-$EDITION}"

command -v rsync >/dev/null 2>&1 || { echo "rsync is required: apt install rsync"; exit 1; }

echo "Building $EDITION edition in: $BUILD"
rm -rf "$BUILD"
mkdir -p "$BUILD"
rsync -a --exclude 'out/' --exclude '.git/' "$SRC/" "$BUILD/"
cd "$BUILD"

# *.hook.* and not *.hook.chroot: the boot-menu branding is a .hook.BINARY and
# was outside this line, so it depended entirely on the executable bit
# surviving the checkout. On a Windows clone that bit is synthesised by the
# drvfs mount rather than stored, and a binary hook live-build declines to run
# fails silently — the ISO simply comes out with Debian's generic boot menu and
# no accessible entry.
chmod +x auto/* config/hooks/normal/*.hook.* 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* \
         config/includes.chroot/usr/lib/live/config/* \
         config/includes.chroot/usr/lib/dagric/* 2>/dev/null || true

if [ "$EDITION" != "pro" ]; then
    rm -f config/package-lists/pro-*.list.chroot
    # Pro-only appearance drop-ins are REMOVED from the free image, not just
    # hidden by their EDITION=pro flag — otherwise a free user could unlock
    # the Pro layouts and styles by deleting one line of text. Each one's
    # gallery preview thumbnail goes with it: an orphan thumb is dead weight
    # in a lean free image, and a gallery that lists thumbs would advertise a
    # style the free edition can no longer apply.
    for drop in $(grep -rlx 'EDITION=pro' config/includes.chroot/usr/share/dagric/looks \
        config/includes.chroot/usr/share/dagric/styles 2>/dev/null); do
        base=${drop##*/}
        rm -f "$drop" \
            "config/includes.chroot/usr/share/dagric/appearance/thumbs/${base%.*}.png"
    done
fi
mkdir -p config/includes.chroot/etc
printf '%s\n' "$EDITION" > config/includes.chroot/etc/dagric-edition
export DAGRIC_EDITION="$EDITION"

# Refuse to ship 16-bit wallpapers. Every pack now comes out of
# branding/wallpaper/make-wallpapers.sh, which writes -depth 8 -- the six wave-1
# packs that used to have no generator were fitted and folded into it. So the
# generator is no longer the risk; a hand-edited or re-exported PNG is. This
# gate is what proves one never sneaks back in, and it is the only thing
# standing between us and a repeat of the 43 MB regression, where six packs were
# written as 16-bit RGBA and nobody noticed until the ISO was measured.
#
# Read the depth out of the PNG header directly (byte 24, right after IHDR's
# width and height) rather than shelling out to ImageMagick: the build host is
# a live-build chroot toolchain and is not required to have `identify`, and a
# check that silently no-ops when its dependency is missing is worse than none.
#
# Every shipped PNG is checked, not just the wallpapers. The wallpapers were
# where the regression happened, but they are not the only 4K art in the image:
# usr/share/dagric/sddm/background.png is 3840x2160 and comes out of its own
# generator (branding/sddm/make-login-art.sh), so it can regress exactly the
# same way and used to sit outside this gate entirely.
#
# The test is "greater than 8", not "equal to 8". 16-bit is the thing that
# doubles the file for no visible gain; a palette PNG with a depth of 1, 2 or 4
# is SMALLER, and several of the icons and avatars here are one pngquant pass
# away from being exactly that. An equality test would reject a file for being
# too cheap, which is the opposite of what this gate is for.
deep=
for png in $(find config/includes.chroot -name '*.png' | sort); do
    [ -f "$png" ] || continue
    if [ "$(od -An -tu1 -j24 -N1 "$png" | tr -d ' ')" -gt 8 ]; then
        deep="$deep $png"
    fi
done
if [ -n "$deep" ]; then
    echo "ERROR: wallpapers are not 8-bit — this doubles their size for no" >&2
    echo "visible gain. Re-encode with: mogrify -depth 8 <file>" >&2
    for d in $deep; do echo "  $d" >&2; done
    exit 1
fi

# Translation drift. The .mo catalogues and the localised .desktop keys are
# COMMITTED build products (see tools/i18n-build.sh for why), so the failure
# this catches is somebody editing an English string and forgetting to
# recompile: the catalogue still loads, still says the old thing, and the only
# symptom is a language that quietly goes stale. Both checks are read-only and
# exit non-zero on drift.
#
# SKIPPED rather than fatal when the tooling is absent. gettext and python3 are
# build-HOST packages that the image does not need and the live-build container
# is not required to carry; the catalogues are committed, so a host without
# them still produces a fully translated ISO. Making this a hard requirement
# would break the build for a check, which is the wrong trade — but it is
# announced, because a gate that skips in silence is a gate nobody trusts.
if command -v msgfmt >/dev/null 2>&1; then
    sh tools/i18n-build.sh --check
else
    echo "i18n: msgfmt not installed — skipping the catalogue drift check"
fi
if command -v python3 >/dev/null 2>&1; then
    python3 tools/i18n-desktop.py --check
    # The setup wizard's English sentences live in one file and are asked for by
    # name in another, and nothing compared the two — so 18 shipped strings were
    # never displayed while about fifty displayed strings were never shipped, and
    # the build log reported a fully translated wizard the whole time. See the
    # header of tools/i18n-wizard.py.
    python3 tools/i18n-wizard.py --check
else
    echo "i18n: python3 not installed — skipping the .desktop drift check"
fi

lb clean
lb config

# SUBSCRIBE THE IMAGE TO ITS OWN UPDATE CHANNEL.
#
# config/includes.chroot/etc/apt/sources.list.d/dagric.list points every
# installed machine at the signed repository, and the keyring beside it is
# shipped — but none of that delivers anything, because the four dagric-*
# packages only ever existed in site/repo. Their CONTENTS reached the ISO
# through includes.chroot, so dpkg had no record of dagric-tools at all and
# `apt upgrade` on a sold machine could never offer a fix to the wizard, the
# manual, the wallpapers or the security baseline. The channel was live, signed,
# reachable — and nothing was subscribed to a single package in it.
#
# Building the .debs here, from the tree that is about to become the image, and
# handing them to live-build as local packages is what registers them. They are
# installed before config/includes.chroot is copied in (see the ordering note in
# stage-packages.sh), so the tree remains the source of truth for what ships and
# the packages exist to be RECORDED, at a version the channel can supersede.
#
# Free and Pro each build their own, after the edition gating above — so the
# free image never records a package built from the Pro tree.
#
# Skipped, loudly, when dpkg-deb is missing: a build host without it can still
# produce a correct ISO, it just produces one that cannot be updated in place.
if command -v dpkg-deb >/dev/null 2>&1; then
    rm -rf config/packages.chroot
    mkdir -p config/packages.chroot
    DAGRIC_PKG_STAGE="$BUILD/.pkgstage" \
        sh packages/stage-packages.sh "$BUILD" "$BUILD/config/packages.chroot"
    rm -rf "$BUILD/.pkgstage"
    echo "update channel: $(ls -1 config/packages.chroot/*.deb | wc -l) config packages staged for install"
else
    echo "WARNING: dpkg-deb not installed — the ISO will not be subscribed to" >&2
    echo "         the Dagric update channel (apt upgrade will deliver nothing)." >&2
fi

lb build

mkdir -p "$SRC/out"
case "$EDITION" in
    pro) NAME=dagric-os-pro-1.0-amd64.iso ;;
    *)   NAME=dagric-os-1.0-amd64.iso ;;
esac
# dd, not cp, and then check the size — because the destination is usually a
# Windows drive seen through WSL's 9p bridge, and cp fails there on a file this
# large:
#     cp: error writing '.../dagric-os-pro-1.0-amd64.iso': Cannot allocate memory
# It failed at 1.1 GB of a 3.8 GB image and still exited before the verify, so
# out/ was left holding a TRUNCATED ISO with a plausible name and a fresh
# timestamp. That is the worst possible failure mode for a build: the artefact
# looks finished, and the only way to find out otherwise is for somebody to
# flash it and watch it not boot.
#
# dd with an explicit block size writes in bounded chunks instead of letting cp
# choose a mapping strategy 9p cannot satisfy. The size comparison afterwards is
# the part that actually matters — any copy method can be interrupted, and a
# build must not report success over a short file.
SRCISO=$(ls -1 ./*.iso 2>/dev/null | head -1)
[ -n "$SRCISO" ] || { echo "no ISO produced" >&2; exit 1; }
mkdir -p "$SRC/out"
dd if="$SRCISO" of="$SRC/out/$NAME" bs=4M status=none

WANT=$(stat -c%s "$SRCISO")
GOT=$(stat -c%s "$SRC/out/$NAME" 2>/dev/null || echo 0)
if [ "$WANT" != "$GOT" ]; then
    echo "ERROR: copy is short — $GOT of $WANT bytes." >&2
    echo "The ISO itself is fine at $SRCISO; only the copy failed." >&2
    rm -f "$SRC/out/$NAME"
    exit 1
fi
echo "copied $NAME ($GOT bytes, verified)"
echo "Done ($EDITION edition) — ISO is at out/$NAME"
