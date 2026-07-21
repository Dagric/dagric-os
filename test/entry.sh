#!/bin/sh
# Boots /iso/dagric.iso in QEMU with the display on VNC :0,
# then bridges it to noVNC on port 6080.
# If /disk/disk.qcow2 exists it is attached as a virtio disk (install target).
set -e

if [ -e /dev/kvm ]; then
    ACCEL="-enable-kvm -cpu host"
    echo "KVM available — hardware-accelerated boot"
else
    ACCEL="-accel tcg,thread=multi -cpu max"
    echo "No KVM — falling back to software emulation (boot will be SLOW; be patient)"
fi

DISKARG=""
if [ -f /disk/disk.qcow2 ]; then
    DISKARG="-drive file=/disk/disk.qcow2,if=virtio,format=qcow2"
    echo "Install target disk attached"
fi

# Boot from CD when the ISO is mounted; from disk when it isn't
# (post-install boot test uses the disk alone).
CDARG=""
BOOTARG="-boot c"
if [ -f /iso/dagric.iso ]; then
    CDARG="-cdrom /iso/dagric.iso"
    BOOTARG="-boot d"
fi

# UEFI=1 boots with OVMF firmware instead of SeaBIOS, with persistent
# EFI variables so the installed system's boot entry survives reboots.
FIRMWARE=""
if [ "$UEFI" = "1" ]; then
    mkdir -p /disk
    [ -f /disk/OVMF_VARS.fd ] || cp /usr/share/OVMF/OVMF_VARS_4M.fd /disk/OVMF_VARS.fd
    FIRMWARE="-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
              -drive if=pflash,format=raw,file=/disk/OVMF_VARS.fd"
    echo "UEFI firmware (OVMF) enabled"
fi

qemu-system-x86_64 \
    $ACCEL \
    -m 4096 -smp 4 \
    $FIRMWARE \
    $CDARG $BOOTARG \
    $DISKARG \
    -vga virtio \
    -device usb-ehci -device usb-tablet \
    -display none -vnc :0 \
    -monitor unix:/tmp/monitor.sock,server,nowait &

exec websockify --web /usr/share/novnc 6080 localhost:5900
