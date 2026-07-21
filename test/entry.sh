#!/bin/sh
# Boots /iso/freehold.iso in QEMU with the display on VNC :0,
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
if [ -f /iso/freehold.iso ]; then
    CDARG="-cdrom /iso/freehold.iso"
    BOOTARG="-boot d"
fi

qemu-system-x86_64 \
    $ACCEL \
    -m 4096 -smp 4 \
    $CDARG $BOOTARG \
    $DISKARG \
    -vga virtio \
    -device usb-ehci -device usb-tablet \
    -display none -vnc :0 \
    -monitor unix:/tmp/monitor.sock,server,nowait &

exec websockify --web /usr/share/novnc 6080 localhost:5900
