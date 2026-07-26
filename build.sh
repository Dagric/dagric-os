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
    # the Pro layouts and styles by deleting one line of text.
    grep -rlx 'EDITION=pro' config/includes.chroot/usr/share/dagric/looks \
        config/includes.chroot/usr/share/dagric/styles 2>/dev/null | xargs -r rm -f
fi
mkdir -p config/includes.chroot/etc
printf '%s\n' "$EDITION" > config/includes.chroot/etc/dagric-edition
export DAGRIC_EDITION="$EDITION"

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
