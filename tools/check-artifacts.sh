#!/bin/sh
# Audit the already-built Free and Pro ISOs without modifying either image.
# Run as root on Linux/WSL because reading one file from each squashfs requires
# a loop mount. Usage: sudo sh tools/check-artifacts.sh [out/week-audit]
#
# `--pipeline-only` is a deliberately narrower developer-candidate inspection:
# it validates both immutable images, their checksums, package split, signed
# EFI, Adaptive Pipeline and Foundations payloads, but does not claim boot
# evidence exists.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pipeline_only=0
if [ "${1:-}" = --pipeline-only ]; then
    pipeline_only=1
    shift
fi
BASE=${1:-"$ROOT/out/week-audit"}
case "$BASE" in /*) ;; *) BASE="$ROOT/$BASE" ;; esac

FREE="$BASE/free/dagric-os-1.0-amd64.iso"
PRO="$BASE/pro/dagric-os-pro-1.0-amd64.iso"
[ "$(id -u)" -eq 0 ] || { echo "artifact-check: run as root" >&2; exit 1; }
for file in "$FREE" "$PRO"; do
    [ -f "$file" ] || { echo "artifact-check: missing $file" >&2; exit 1; }
done
for command in sha256sum xorriso unsquashfs mount umount python3; do
    command -v "$command" >/dev/null 2>&1 || { echo "artifact-check: missing $command" >&2; exit 1; }
done

tmp=$(mktemp -d)
free_mnt="$tmp/free"
pro_mnt="$tmp/pro"
mkdir "$free_mnt" "$pro_mnt"
mounted_free=0
mounted_pro=0
cleanup() {
    [ "$mounted_pro" -eq 0 ] || umount "$pro_mnt" 2>/dev/null || true
    [ "$mounted_free" -eq 0 ] || umount "$free_mnt" 2>/dev/null || true
    rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

if [ -f "$BASE/SHA256SUMS" ]; then
    (cd "$BASE" && sha256sum -c SHA256SUMS)
elif [ "$pipeline_only" -eq 1 ] && [ -f "$BASE/free/SHA256SUMS" ] && [ -f "$BASE/pro/SHA256SUMS" ]; then
    (cd "$BASE/free" && sha256sum -c SHA256SUMS)
    (cd "$BASE/pro" && sha256sum -c SHA256SUMS)
else
    echo "artifact-check: missing combined $BASE/SHA256SUMS" >&2
    exit 1
fi
mount -o loop,ro "$FREE" "$free_mnt"
mounted_free=1
mount -o loop,ro "$PRO" "$pro_mnt"
mounted_pro=1

require_package() {
    manifest=$1
    package=$2
    grep -Eq "^${package}(:[^[:space:]]+)?[[:space:]]" "$manifest" || {
        echo "artifact-check: $manifest lacks $package" >&2
        exit 1
    }
}

reject_package() {
    manifest=$1
    package=$2
    if grep -Eq "^${package}(:[^[:space:]]+)?[[:space:]]" "$manifest"; then
        echo "artifact-check: Free artifact unexpectedly contains Pro package $package" >&2
        exit 1
    fi
}

free_manifest="$free_mnt/live/filesystem.packages"
pro_manifest="$pro_mnt/live/filesystem.packages"
for package in calamares grub-pc-bin grub-efi-amd64-signed shim-signed mokutil \
               orca speech-dispatcher-espeak-ng firewalld apparmor snapper \
               btrfs-assistant kup-backup ntfs-3g exfatprogs; do
    require_package "$free_manifest" "$package"
    require_package "$pro_manifest" "$package"
done

for package in wine wine32 winetricks dxvk-wine32 gamemode mangohud lutris \
               opensnitch usbguard virt-manager qemu-system-x86 ovmf swtpm \
               borgbackup vorta; do
    require_package "$pro_manifest" "$package"
    reject_package "$free_manifest" "$package"
done

free_edition=$(unsquashfs -cat "$free_mnt/live/filesystem.squashfs" etc/dagric-edition 2>/dev/null)
pro_edition=$(unsquashfs -cat "$pro_mnt/live/filesystem.squashfs" etc/dagric-edition 2>/dev/null)
[ "$free_edition" = free ] || { echo "artifact-check: Free marker is '$free_edition'" >&2; exit 1; }
[ "$pro_edition" = pro ] || { echo "artifact-check: Pro marker is '$pro_edition'" >&2; exit 1; }

# The adaptive profile compiler is deliberately service-only: there must be no
# desktop entry, but both editions must contain its audited command, launch
# wrapper and refresh timer.  Inspect the immutable squashfs rather than
# trusting source files or a package staging directory.
require_pipeline() {
    image=$1
    listing=$(unsquashfs -ll "$image" 2>/dev/null)
    for path in \
        squashfs-root/usr/sbin/dagric-pipeline \
        squashfs-root/usr/bin/dagric-pipeline-launch \
        squashfs-root/usr/lib/dagric/pipeline.py \
        squashfs-root/etc/systemd/system/dagric-pipeline.service \
        squashfs-root/etc/systemd/system/dagric-pipeline.timer \
        squashfs-root/etc/systemd/system/timers.target.wants/dagric-pipeline.timer; do
        printf '%s\\n' "$listing" | grep -Fq " $path" || {
            echo "artifact-check: adaptive pipeline missing $path" >&2
            exit 1
        }
    done
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.service 2>/dev/null \
        | grep -Fq 'ProtectSystem=strict' || {
            echo "artifact-check: adaptive pipeline service is not hardened" >&2
            exit 1
        }
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.timer 2>/dev/null \
        | grep -Fq 'OnUnitActiveSec=6h' || {
            echo "artifact-check: adaptive pipeline refresh interval is absent" >&2
            exit 1
        }
    if printf '%s\\n' "$listing" | grep -Fq 'squashfs-root/usr/share/applications/dagric-pipeline.desktop'; then
        echo "artifact-check: adaptive pipeline unexpectedly has a desktop entry" >&2
        exit 1
    fi
}
require_pipeline "$free_mnt/live/filesystem.squashfs"
require_pipeline "$pro_mnt/live/filesystem.squashfs"

# Blueprint, Black Box and Life Support are the privacy/safety foundations for
# a hardware-specific Dagric pipeline.  Verify the actual compressed payload,
# enablement links and resource limits in both immutable images.  Source-only
# checks would miss a hook that forgot to copy or enable one of these pieces.
require_foundations() {
    image=$1
    listing=$(unsquashfs -ll "$image" 2>/dev/null)
    for path in \
        squashfs-root/usr/bin/dagric-blueprint \
        squashfs-root/usr/bin/dagric-blackbox \
        squashfs-root/usr/bin/dagric-life-support \
        squashfs-root/usr/bin/dagric-support \
        squashfs-root/usr/bin/dagric-update \
        squashfs-root/usr/lib/dagric/foundations.py \
        squashfs-root/usr/lib/dagric/update_core.py \
        squashfs-root/etc/systemd/system/dagric-blackbox.service \
        squashfs-root/etc/systemd/system/dagric-blackbox.timer \
        squashfs-root/etc/systemd/system/timers.target.wants/dagric-blackbox.timer \
        squashfs-root/usr/share/dagric/budgets/services.json \
        squashfs-root/usr/share/applications/dagric-blueprint.desktop \
        squashfs-root/usr/share/applications/dagric-update.desktop \
        squashfs-root/usr/share/polkit-1/actions/org.dagric.rewind.policy \
        squashfs-root/usr/share/applications/dagric-life-support.desktop; do
        printf '%s\n' "$listing" | grep -Fq " $path" || {
            echo "artifact-check: Dagric Foundations missing $path" >&2
            exit 1
        }
    done
    service=$(unsquashfs -cat "$image" etc/systemd/system/dagric-blackbox.service 2>/dev/null)
    for setting in ProtectSystem=strict ProtectHome=yes NoNewPrivileges=yes \
                   ReadWritePaths=/var/lib/dagric/blackbox MemoryMax=64M \
                   CPUQuota=5% IOSchedulingClass=idle UMask=0077; do
        printf '%s\n' "$service" | grep -Fqx "$setting" || {
            echo "artifact-check: Black Box service lacks $setting" >&2
            exit 1
        }
    done
    timer=$(unsquashfs -cat "$image" etc/systemd/system/dagric-blackbox.timer 2>/dev/null)
    for setting in OnBootSec=5m OnUnitActiveSec=5m Persistent=false; do
        printf '%s\n' "$timer" | grep -Fqx "$setting" || {
            echo "artifact-check: Black Box timer lacks $setting" >&2
            exit 1
        }
    done
    unsquashfs -cat "$image" usr/share/dagric/budgets/services.json 2>/dev/null \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); required={"dagric-blackbox.service","dagric-pipeline.service","dagric-efi-fallback.service","dagric-pdf-queue.service","dagric-snapshot-setup.service"}; assert d.get("schema")==1; assert set(d.get("services",{}))==required; assert all(v.get("network")=="none" and v.get("decision") in {"provisional","measured"} for v in d["services"].values())' || {
            echo "artifact-check: service budget contract is invalid" >&2
            exit 1
        }
}
require_foundations "$free_mnt/live/filesystem.squashfs"
require_foundations "$pro_mnt/live/filesystem.squashfs"

sh "$ROOT/tools/check-secureboot.sh" "$FREE"
sh "$ROOT/tools/check-secureboot.sh" "$PRO"

if [ "$pipeline_only" -eq 0 ]; then
    evidence="$BASE/boot-evidence"
    for run in \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-bios" \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-uefi" \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-secureboot" \
        "$evidence/pro/boot-test/dagric-os-pro-1.0-amd64-uefi"; do
        [ -s "$run/qemu.log" ] || { echo "artifact-check: missing boot log $run/qemu.log" >&2; exit 1; }
        frames=$(find "$run" -name 't*.png' -type f -size +10k | wc -l)
        [ "$frames" -ge 3 ] || { echo "artifact-check: insufficient non-empty frames in $run" >&2; exit 1; }
    done
fi

free_size=$(stat -c %s "$FREE")
pro_size=$(stat -c %s "$PRO")
[ "$free_size" -gt 1500000000 ] || { echo "artifact-check: Free ISO is implausibly small" >&2; exit 1; }
[ "$pro_size" -gt "$free_size" ] || { echo "artifact-check: Pro ISO is not larger than Free" >&2; exit 1; }

if [ "$pipeline_only" -eq 1 ]; then
    echo "artifact-check: candidate passed (checksums, edition split, package manifests, signed EFI, adaptive pipeline and Foundations payloads)"
else
    echo "artifact-check: passed (checksums, edition split, package manifests, signed EFI, adaptive pipeline, Foundations and four boot evidence sets)"
fi
