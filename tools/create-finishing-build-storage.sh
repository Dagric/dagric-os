#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# One-purpose build filesystem, not a VM disk. Preserve it after use.
# Run only on this owner's Debian WSL host. No existing path is formatted.
set -eu
test "$(id -u)" = 0
BASE=/mnt/c/Users/1248n/Downloads
test -d "$BASE"
for command in qemu-img mkfs.ext4 mount mktemp realpath; do command -v "$command" >/dev/null; done
DIR=$(mktemp -d "$BASE/Dagric-finishing-build-storage.XXXXXXXX")
IMAGE="$DIR/build-filesystem.ext4"
RESOLVED=$(realpath -m "$IMAGE")
case "$RESOLVED" in "$BASE"/Dagric-finishing-build-storage.*/build-filesystem.ext4) ;; *) exit 1 ;; esac
test ! -e "$IMAGE"
test ! -L "$IMAGE"
qemu-img create -f raw "$IMAGE" 96G
mkfs.ext4 -q -F -m 0 -E lazy_itable_init=1,lazy_journal_init=1 "$IMAGE"
MOUNT=$(mktemp -d /var/tmp/dagric-finishing-build-mount.XXXXXXXX)
mount -o loop,nodev,nosuid "$IMAGE" "$MOUNT"
# live-build chroots need device nodes and setuid semantics inside this private
# build filesystem. Remount only the exact mount just created.
mount -o remount,dev,suid "$MOUNT"
chmod 0700 "$MOUNT"
printf 'Build image: %s\nBuild mount: %s\n' "$IMAGE" "$MOUNT"
df -h "$MOUNT"
