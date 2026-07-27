#!/bin/sh
# Runs INSIDE the build container. Do not run on the host.
#
# The source tree is mounted read-only at /src (Windows filesystems can't
# hold device nodes and hardlinks that live-build creates), so we copy the
# config to the container's own filesystem, build there, and drop the
# finished ISO into /out which maps back to the Windows folder.
#
# EDITION=free (default) or EDITION=pro selects the flavor:
# pro keeps the pro-*.list.chroot package lists; free removes them.
set -e

EDITION="${EDITION:-free}"

rsync -a --exclude 'out/' --exclude '.git/' /src/ /build/
cd /build
chmod +x auto/* config/hooks/normal/*.hook.chroot 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* config/includes.chroot/usr/lib/live/config/* \
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

# Same 8-bit art guard as build.sh — see the comment there for why this reads
# the PNG header directly instead of asking ImageMagick (`identify` reports the
# *effective* depth and calls a 16-bit-header file "8-bit" when its samples
# happen to fit in 8 bits, which is precisely the case that doubles the file
# size and the case we are trying to catch), why it covers every shipped PNG
# rather than only the wallpapers, and why it tests "> 8" rather than "= 8".
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

lb clean
lb config
lb build

cp -v ./*.iso /out/ 2>/dev/null || { echo "BUILD FAILED — no ISO produced. See output above."; exit 1; }
cp -v build.log /out/ 2>/dev/null || true
echo ""
echo "=========================================="
echo "  Dagric OS ($EDITION) ISO is in out/"
echo "=========================================="
