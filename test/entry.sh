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

case "$VNC_DISPLAY" in
    ''|*[!0-9]*) echo "VNC_DISPLAY must be a number from 0 to 99" >&2; exit 2 ;;
esac
[ "$VNC_DISPLAY" -le 99 ] || {
    echo "VNC_DISPLAY must be a number from 0 to 99" >&2
    exit 2
}
case "$NOVNC_PORT" in
    ''|*[!0-9]*) echo "NOVNC_PORT must be a number from 1 to 65535" >&2; exit 2 ;;
esac
if [ "$NOVNC_PORT" -lt 1 ] || [ "$NOVNC_PORT" -gt 65535 ]; then
    echo "NOVNC_PORT must be a number from 1 to 65535" >&2
    exit 2
fi

# Build the QEMU command as positional arguments.  These values include paths
# and multi-option groups, so storing them in strings and expanding them
# unquoted lets spaces or option-looking path segments change the command.
set -- qemu-system-x86_64

if [ "${SECURE_BOOT:-0}" = 1 ]; then
    # Nested KVM on the Windows/WSL host cannot expose SMM reliably. Secure
    # Boot requires SMM-protected variable storage, so use deterministic TCG
    # for this one matrix row instead of producing a false firmware failure.
    set -- "$@" -accel tcg,thread=multi -cpu max
    set -- "$@" -machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on
    echo "Secure Boot requested — using Microsoft-keyed OVMF under TCG"
elif [ -e /dev/kvm ]; then
    set -- "$@" -enable-kvm -cpu host
    echo "KVM available — hardware-accelerated boot"
else
    set -- "$@" -accel tcg,thread=multi -cpu max
    echo "No KVM — falling back to software emulation (boot will be SLOW; be patient)"
fi

if [ -f "$DISK_DIR/disk.qcow2" ]; then
    set -- "$@" -drive "file=$DISK_DIR/disk.qcow2,if=virtio,format=qcow2"
    echo "Install target disk attached"
fi

# Optional read-only host payload for installed-system update tests. The guest
# mounts this explicitly as dagric_payload; ordinary boot tests do not bind a
# /payload directory and therefore get no extra device.
if [ -d /payload ]; then
    set -- "$@" -virtfs local,path=/payload,mount_tag=dagric_payload,security_model=none,readonly=on
    echo "Read-only test payload attached as 9p tag dagric_payload"
fi

# Writable evidence exchange for installed-system audit scripts. A small FAT
# image works on the stock Debian kernel without the optional 9p transport
# module, and can be read back from the host after the VM stops.
if [ -f /evidence/evidence.img ]; then
    set -- "$@" -drive file=/evidence/evidence.img,format=raw,if=virtio
    echo "Writable audit evidence attached as a FAT virtio disk"
fi

# Boot from CD when the ISO is mounted; from disk when it isn't
# (post-install boot test uses the disk alone).
if [ -f "$ISO_DIR/dagric.iso" ]; then
    set -- "$@" -cdrom "$ISO_DIR/dagric.iso" -boot d
else
    set -- "$@" -boot c
fi

# UEFI=1 boots with OVMF firmware instead of SeaBIOS, with persistent
# EFI variables so the installed system's boot entry survives reboots.
if [ "${SECURE_BOOT:-0}" = 1 ]; then
    mkdir -p "$DISK_DIR"
    [ -f "$DISK_DIR/OVMF_VARS.fd" ] || cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$DISK_DIR/OVMF_VARS.fd"
    set -- "$@" \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.ms.fd \
        -drive "if=pflash,format=raw,file=$DISK_DIR/OVMF_VARS.fd"
    echo "Microsoft Secure Boot keys enrolled"
elif [ "$UEFI" = "1" ]; then
    mkdir -p "$DISK_DIR"
    [ -f "$DISK_DIR/OVMF_VARS.fd" ] || cp /usr/share/OVMF/OVMF_VARS_4M.fd "$DISK_DIR/OVMF_VARS.fd"
    set -- "$@" \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
        -drive "if=pflash,format=raw,file=$DISK_DIR/OVMF_VARS.fd"
    echo "UEFI firmware (OVMF) enabled"
fi

set -- "$@" \
    -m 4096 -smp 4 \
    -vga virtio \
    -device usb-ehci -device usb-tablet \
    -display none -vnc ":$VNC_DISPLAY" \
    -monitor "unix:$MONITOR_SOCKET,server,nowait"

"$@" &

exec websockify --web /usr/share/novnc "$NOVNC_PORT" "127.0.0.1:$((5900 + VNC_DISPLAY))"
