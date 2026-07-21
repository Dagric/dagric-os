#!/bin/sh
# Boots /iso/freehold.iso in QEMU with the display on VNC :0,
# then bridges it to noVNC on port 6080.
set -e

if [ -e /dev/kvm ]; then
    ACCEL="-enable-kvm -cpu host"
    echo "KVM available — hardware-accelerated boot"
else
    ACCEL="-accel tcg,thread=multi -cpu max"
    echo "No KVM — falling back to software emulation (boot will be SLOW; be patient)"
fi

qemu-system-x86_64 \
    $ACCEL \
    -m 4096 -smp 4 \
    -cdrom /iso/freehold.iso -boot d \
    -vga virtio \
    -display none -vnc :0 \
    -monitor unix:/tmp/monitor.sock,server,nowait &

exec websockify --web /usr/share/novnc 6080 localhost:5900
