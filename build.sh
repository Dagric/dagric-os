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

chmod +x auto/* config/hooks/normal/*.hook.chroot 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* \
         config/includes.chroot/usr/lib/live/config/* 2>/dev/null || true

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

# Refuse to ship 16-bit wallpapers. Six of the packs predate
# branding/wallpaper/make-wallpapers.sh and have no generator in the tree, so
# the only thing standing between us and a repeat of the 43 MB regression --
# where six packs were written as 16-bit RGBA and nobody noticed until the ISO
# was measured -- is somebody remembering. Check it instead of remembering.
#
# Read the depth out of the PNG header directly (byte 24, right after IHDR's
# width and height) rather than shelling out to ImageMagick: the build host is
# a live-build chroot toolchain and is not required to have `identify`, and a
# check that silently no-ops when its dependency is missing is worse than none.
deep=
for png in config/includes.chroot/usr/share/wallpapers/*/contents/images/*.png; do
    [ -f "$png" ] || continue
    [ "$(od -An -tu1 -j24 -N1 "$png" | tr -d ' ')" = 8 ] || deep="$deep $png"
done
if [ -n "$deep" ]; then
    echo "ERROR: wallpapers are not 8-bit — this doubles their size for no" >&2
    echo "visible gain. Re-encode with: mogrify -depth 8 <file>" >&2
    for d in $deep; do echo "  $d" >&2; done
    exit 1
fi

lb clean
lb config
lb build

mkdir -p "$SRC/out"
case "$EDITION" in
    pro) NAME=dagric-os-pro-1.0-amd64.iso ;;
    *)   NAME=dagric-os-1.0-amd64.iso ;;
esac
cp -v ./*.iso "$SRC/out/$NAME"
echo "Done ($EDITION edition) — ISO is at out/$NAME"
