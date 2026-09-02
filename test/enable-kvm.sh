#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — turn on hardware acceleration for the QEMU test harness.
#
#     .\test\enable-kvm.ps1       # Windows/PowerShell (called automatically)
#     sh test/enable-kvm.sh        # Linux shell fallback
#
# The PowerShell harnesses call their helper automatically. Run this shell
# version only when invoking QEMU/container tests outside those entry points.
#
# WHY THIS EXISTS
# ---------------
# The harness has been printing "No KVM — falling back to software emulation"
# and taking 5-7 minutes to reach a desktop, and every note about it — in the
# skill, in comments — treated that as a fact of life on WSL2. It is not, and
# nothing had to be installed or bought:
#
#   * the WSL2 kernel is built with CONFIG_KVM=m and CONFIG_KVM_AMD=m
#     (verified by reading /proc/config.gz from a privileged container)
#   * the host CPU already exposes virtualisation to the VM — /proc/cpuinfo
#     inside a container shows `svm` on this Ryzen, so WSL2's nested
#     virtualisation is already on
#   * the module files are already present in the Docker Desktop VM at
#     /lib/modules/6.18.33.2-microsoft-standard-WSL2/kernel/arch/x86/kvm/
#
# The modules simply were not loaded. Loading them creates /dev/kvm in the
# Docker VM, which a container can then be handed with --device.
#
# MEASURED: live desktop in ~30s with KVM against ~160s without, on the same
# ISO and the same machine. An install goes from "not worth attempting" to
# routine.
#
# IT DOES NOT PERSIST. The modules live in the Docker Desktop WSL VM, which is
# recreated on restart, so this is a per-boot step rather than a setting. That
# is also why it is a script and not a line in a document nobody re-reads.
set -e

# AMD (svm) and Intel (vmx) need different modules, so pick from what the CPU
# actually reports rather than assuming the machine this was written on.
VENDOR=$(docker run --rm --privileged alpine sh -c \
    'grep -oE "\bvmx\b|\bsvm\b" /proc/cpuinfo 2>/dev/null | head -1' 2>/dev/null || true)

case "$VENDOR" in
    svm) MOD=kvm_amd ;;
    vmx) MOD=kvm_intel ;;
    *)
        echo "ERROR: the Docker VM reports no virtualisation flag (no vmx, no svm)." >&2
        echo "       Either the CPU has virtualisation disabled in firmware, or" >&2
        echo "       WSL2 nested virtualisation is off. Check the BIOS/UEFI" >&2
        echo "       setting first — it is usually called SVM Mode or Intel VT-x." >&2
        exit 1
        ;;
esac

echo "CPU reports $VENDOR — loading $MOD"

# -v /lib/modules mounts the Docker VM's own modules, which is where the .ko
# files are; the container image has none of its own.
docker run --rm --privileged -v /lib/modules:/lib/modules alpine sh -c \
    "apk add -q kmod 2>/dev/null; modprobe $MOD" || {
        echo "ERROR: modprobe $MOD failed." >&2
        exit 1
    }

if docker run --rm --privileged -v /dev:/hostdev alpine test -e /hostdev/kvm; then
    echo "/dev/kvm is present — pass --device /dev/kvm to the test container."
    echo "Expect the harness to print 'KVM available — hardware-accelerated boot'."
else
    echo "ERROR: $MOD loaded but /dev/kvm was not created." >&2
    exit 1
fi
