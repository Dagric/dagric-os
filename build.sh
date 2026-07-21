#!/bin/sh
# Freehold OS — build natively on a Debian machine (needs root).
#   sudo apt install live-build
#   sudo ./build.sh
set -e
cd "$(dirname "$0")"
chmod +x auto/* config/hooks/normal/*.hook.chroot 2>/dev/null || true
lb clean
lb config
lb build
echo "Done — ISO is in the current directory."
