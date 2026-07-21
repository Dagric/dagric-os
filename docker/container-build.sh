#!/bin/sh
# Runs INSIDE the build container. Do not run on the host.
#
# The source tree is mounted read-only at /src (Windows filesystems can't
# hold device nodes and hardlinks that live-build creates), so we copy the
# config to the container's own filesystem, build there, and drop the
# finished ISO into /out which maps back to the Windows folder.
set -e

rsync -a --exclude 'out/' --exclude '.git/' /src/ /build/
cd /build
chmod +x auto/* config/hooks/normal/*.hook.chroot 2>/dev/null || true

lb clean
lb config
lb build

cp -v ./*.iso /out/ 2>/dev/null || { echo "BUILD FAILED — no ISO produced. See output above."; exit 1; }
cp -v build.log /out/ 2>/dev/null || true
echo ""
echo "=========================================="
echo "  Freehold OS ISO is in the out/ folder"
echo "=========================================="
