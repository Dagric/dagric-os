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

if [ "${SECURE_BOOT:-0}" = 1 ]; then
    # Nested KVM on the Windows/WSL host cannot expose SMM reliably. Secure
    # Boot requires SMM-protected variable storage, so use deterministic TCG
    # for this one matrix row instead of producing a false firmware failure.
    ACCEL="-accel tcg,thread=multi -cpu max"
    MACHINE="-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on"
    echo "Secure Boot requested — using Microsoft-keyed OVMF under TCG"
elif [ -e /dev/kvm ]; then
    ACCEL="-enable-kvm -cpu host"
    MACHINE=""
    echo "KVM available — hardware-accelerated boot"
else
    ACCEL="-accel tcg,thread=multi -cpu max"
    MACHINE=""
    echo "No KVM — falling back to software emulation (boot will be SLOW; be patient)"
fi

DISKARG=""
if [ -f "$DISK_DIR/disk.qcow2" ]; then
    DISKARG="-drive file=$DISK_DIR/disk.qcow2,if=virtio,format=qcow2"
    echo "Install target disk attached"
fi

# Optional read-only host payload for installed-system update tests. The guest
# mounts this explicitly as dagric_payload; ordinary boot tests do not bind a
# /payload directory and therefore get no extra device.
SHAREARG=""
if [ -d /payload ]; then
    SHAREARG="-virtfs local,path=/payload,mount_tag=dagric_payload,security_model=none,readonly=on"
    echo "Read-only test payload attached as 9p tag dagric_payload"
fi

# Writable evidence exchange for installed-system audit scripts. A small FAT
# image works on the stock Debian kernel without the optional 9p transport
# module, and can be read back from the host after the VM stops.
EVIDENCEARG=""
if [ -f /evidence/evidence.img ]; then
    EVIDENCEARG="-drive file=/evidence/evidence.img,format=raw,if=virtio"
    echo "Writable audit evidence attached as a FAT virtio disk"
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
if [ "${SECURE_BOOT:-0}" = 1 ]; then
    mkdir -p "$DISK_DIR"
    [ -f "$DISK_DIR/OVMF_VARS.fd" ] || cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$DISK_DIR/OVMF_VARS.fd"
    FIRMWARE="-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.ms.fd \
              -drive if=pflash,format=raw,file=$DISK_DIR/OVMF_VARS.fd"
    echo "Microsoft Secure Boot keys enrolled"
elif [ "$UEFI" = "1" ]; then
    mkdir -p "$DISK_DIR"
    [ -f "$DISK_DIR/OVMF_VARS.fd" ] || cp /usr/share/OVMF/OVMF_VARS_4M.fd "$DISK_DIR/OVMF_VARS.fd"
    FIRMWARE="-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
              -drive if=pflash,format=raw,file=$DISK_DIR/OVMF_VARS.fd"
    echo "UEFI firmware (OVMF) enabled"
fi

qemu-system-x86_64 \
    $ACCEL \
    $MACHINE \
    -m 4096 -smp 4 \
    $FIRMWARE \
    $CDARG $BOOTARG \
    $DISKARG \
    $SHAREARG \
    $EVIDENCEARG \
    -vga virtio \
    -device usb-ehci -device usb-tablet \
    -display none -vnc ":$VNC_DISPLAY" \
    -monitor "unix:$MONITOR_SOCKET,server,nowait" &

exec websockify --web /usr/share/novnc "$NOVNC_PORT" "localhost:$((5900 + VNC_DISPLAY))"
