#!/bin/sh
# Verify the Adaptive Pipeline payload inside immutable ISO artifacts.
# This deliberately does not substitute for check-artifacts.sh: it contains no
# boot-evidence claim and is intended for the fast post-build payload check.
set -eu

[ "$#" -ge 1 ] || {
    echo "usage: $0 ISO [ISO ...]" >&2
    exit 2
}
[ "$(id -u)" -eq 0 ] || {
    echo "pipeline-artifact-check: run as root" >&2
    exit 1
}
for command in mount umount unsquashfs; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "pipeline-artifact-check: missing $command" >&2
        exit 1
    }
done

tmp=$(mktemp -d)
cleanup() {
    for mountpoint in "$tmp"/*; do
        [ -d "$mountpoint" ] && umount "$mountpoint" 2>/dev/null || true
    done
    rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

check_file() {
    image=$1
    path=$2
    unsquashfs -cat "$image" "$path" >/dev/null 2>&1 || {
        echo "pipeline-artifact-check: missing $path" >&2
        exit 1
    }
}

index=0
for iso in "$@"; do
    [ -f "$iso" ] || { echo "pipeline-artifact-check: missing $iso" >&2; exit 1; }
    index=$((index + 1))
    mountpoint="$tmp/$index"
    mkdir "$mountpoint"
    mount -o loop,ro "$iso" "$mountpoint"
    image="$mountpoint/live/filesystem.squashfs"
    [ -f "$image" ] || { echo "pipeline-artifact-check: missing live squashfs" >&2; exit 1; }

    check_file "$image" usr/sbin/dagric-pipeline
    check_file "$image" usr/bin/dagric-pipeline-launch
    check_file "$image" usr/lib/dagric/pipeline.py
    check_file "$image" usr/lib/dagric/private_files.py
    check_file "$image" etc/systemd/system/dagric-pipeline.service
    check_file "$image" etc/systemd/system/dagric-pipeline.timer
    # unsquashfs -cat intentionally does not follow this systemd symlink, so
    # verify the entry itself from the image listing instead.
    unsquashfs -ll "$image" etc/systemd/system/timers.target.wants/dagric-pipeline.timer 2>/dev/null \
        | grep -Fq 'dagric-pipeline.timer' || {
            echo "pipeline-artifact-check: timer is not enabled" >&2
            exit 1
        }
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.service 2>/dev/null \
        | grep -Fq 'ProtectSystem=strict' || {
            echo "pipeline-artifact-check: service is not hardened" >&2
            exit 1
        }
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.timer 2>/dev/null \
        | grep -Fq 'OnUnitActiveSec=6h' || {
            echo "pipeline-artifact-check: timer interval is absent" >&2
            exit 1
        }
    if unsquashfs -cat "$image" usr/share/applications/dagric-pipeline.desktop >/dev/null 2>&1; then
        echo "pipeline-artifact-check: unexpected desktop entry" >&2
        exit 1
    fi
    umount "$mountpoint"
done

echo "pipeline-artifact-check: passed ($# immutable ISO payloads)"
