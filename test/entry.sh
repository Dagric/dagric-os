#!/bin/sh
# Boots /iso/dagric.iso in QEMU with the display on VNC :0,
# then bridges it to noVNC on port 6080.
# If /disk/disk.qcow2 exists it is attached as a virtio disk (install target).
set -e

ISO_DIR=${ISO_DIR:-/iso}
DISK_DIR=${DISK_DIR:-/disk}
VNC_DISPLAY=${VNC_DISPLAY:-0}
NOVNC_PORT=${NOVNC_PORT:-6080}
MONITOR_SOCKET=${MONITOR_SOCKET:-/tmp/monitor.sock}

if [ -e /dev/kvm ]; then
    ACCEL="-enable-kvm -cpu host"
    echo "KVM available — hardware-accelerated boot"
else
    ACCEL="-accel tcg,thread=multi -cpu max"
    echo "No KVM — falling back to software emulation (boot will be SLOW; be patient)"
fi

DISKARG=""
if [ -f "$DISK_DIR/disk.qcow2" ]; then
    DISKARG="-drive file=$DISK_DIR/disk.qcow2,if=virtio,format=qcow2"
    echo "Install target disk attached"
fi

# Boot from CD when the ISO is mounted; from disk when it isn't
# (post-install boot test uses the disk alone).
CDARG=""
BOOTARG="-boot c"
if [ -f "$ISO_DIR/dagric.iso" ]; then
    CDARG="-cdrom $ISO_DIR/dagric.iso"
    BOOTARG="-boot d"
fi

# UEFI=1 boots with OVMF firmware instead of SeaBIOS, with persistent
# EFI variables so the installed system's boot entry survives reboots.
FIRMWARE=""
if [ "$UEFI" = "1" ]; then
    mkdir -p "$DISK_DIR"
    [ -f "$DISK_DIR/OVMF_VARS.fd" ] || cp /usr/share/OVMF/OVMF_VARS_4M.fd "$DISK_DIR/OVMF_VARS.fd"
    FIRMWARE="-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
              -drive if=pflash,format=raw,file=$DISK_DIR/OVMF_VARS.fd"
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
    -display none -vnc ":$VNC_DISPLAY" \
    -monitor "unix:$MONITOR_SOCKET,server,nowait" &

exec websockify --web /usr/share/novnc "$NOVNC_PORT" "localhost:$((5900 + VNC_DISPLAY))"
