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
chmod +x config/includes.chroot/usr/bin/* config/includes.chroot/usr/lib/live/config/* 2>/dev/null || true

if [ "$EDITION" != "pro" ]; then
    rm -f config/package-lists/pro-*.list.chroot
fi
mkdir -p config/includes.chroot/etc
printf '%s\n' "$EDITION" > config/includes.chroot/etc/dagric-edition
export DAGRIC_EDITION="$EDITION"

lb clean
lb config
lb build

cp -v ./*.iso /out/ 2>/dev/null || { echo "BUILD FAILED — no ISO produced. See output above."; exit 1; }
cp -v build.log /out/ 2>/dev/null || true
echo ""
echo "=========================================="
echo "  Dagric OS ($EDITION) ISO is in out/"
echo "=========================================="
