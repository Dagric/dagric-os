#!/bin/sh
# Dagric OS — boot an ISO in QEMU and photograph what actually happens.
#
#   sh tools/boot-test.sh out/dagric-os-1.0-amd64.iso bios
#   sh tools/boot-test.sh out/dagric-os-1.0-amd64.iso uefi
#   sh tools/boot-test.sh out/dagric-os-1.0-amd64.iso secureboot
#
# WHY THIS EXISTS. Dagric shipped a first-run wizard, a 95-page manual, 34
# wallpaper packs and an EDID-driven scaling detector without anyone ever
# watching the thing boot. Every one of those features is worth nothing if the
# ISO stops at a firmware error, and the most likely place to stop is Secure
# Boot: most machines being rescued from Windows 10 have it switched on, and
# "go into your BIOS and disable a security feature" is where a non-technical
# switcher gives up and puts Windows back.
#
# The three modes are the three firmware paths real hardware presents:
#
#   bios        SeaBIOS. Pre-2012 machines, and anything set to Legacy/CSM.
#   uefi        OVMF with Secure Boot support absent. UEFI machines with SB off.
#   secureboot  OVMF_CODE_4M.ms.fd + OVMF_VARS_4M.ms.fd — the firmware built
#               with Microsoft's keys ALREADY ENROLLED, which is what ships on
#               a retail Windows laptop. This is the honest test. Booting under
#               plain OVMF proves nothing about Secure Boot.
#
# There is no serial console to scrape: the live ISO does not append
# console=ttyS0, and adding it would mean driving the boot menu blind. So this
# drives QEMU's monitor over a unix socket and takes SCREENSHOTS on a timer,
# which is both more honest (it sees what a user would see) and immune to
# whether the guest ever configures a serial port.
set -e

ISO=$1
MODE=${2:-uefi}
SECS=${SECS:-240}
# DAGRIC_REPO override: this script is normally run from a copy under /srv
# (the repo lives on a 9p mount where CRLF has to be stripped first), and in
# that case $0's parent is not the repo and screenshots land in /out.
REPO=${DAGRIC_REPO:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
# Keyed by ISO as well as mode. Keying on mode alone meant testing the Pro
# image silently overwrote the free image's screenshots in out/boot-test/uefi,
# so the two editions could never be compared — which is exactly how the
# Firefox/Chromium difference nearly went unnoticed.
OUT=$REPO/out/boot-test/$(basename "$ISO" .iso)-$MODE

[ -f "$ISO" ] || { echo "no such ISO: $ISO" >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo "qemu-system-x86_64 missing" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"
MON=$(mktemp -u /tmp/dgmonXXXXXX)

OVMF=/usr/share/OVMF
set -- -m 4096 -smp 2 -cdrom "$ISO" -boot d \
       -display none -vga std \
       -monitor "unix:$MON,server,nowait" \
       -rtc base=localtime

# KVM if the kernel exposes it. Without it a Plasma boot takes long enough that
# the timer would expire before the desktop appears, and the run would look
# like a failure that is really just slowness.
[ -w /dev/kvm ] && set -- "$@" -enable-kvm -cpu host

case "$MODE" in
    bios)
        ;;
    uefi)
        [ -f "$OVMF/OVMF_CODE_4M.fd" ] || { echo "install ovmf" >&2; exit 1; }
        cp "$OVMF/OVMF_VARS_4M.fd" "$OUT/vars.fd"
        set -- "$@" \
            -drive "if=pflash,format=raw,unit=0,readonly=on,file=$OVMF/OVMF_CODE_4M.fd" \
            -drive "if=pflash,format=raw,unit=1,file=$OUT/vars.fd"
        ;;
    secureboot)
        # The vars file MUST be a writable copy: the firmware writes to it, and
        # pointing pflash at the packaged read-only original either fails to
        # start or silently discards state.
        [ -f "$OVMF/OVMF_CODE_4M.ms.fd" ] || { echo "no OVMF_CODE_4M.ms.fd — install ovmf" >&2; exit 1; }
        cp "$OVMF/OVMF_VARS_4M.ms.fd" "$OUT/vars.fd"
        # q35 always, SMM separately. Dropping smm=on by removing the whole
        # `-machine q35,smm=on` argument also dropped q35, and QEMU fell back to
        # the default i440fx chipset, which the 4M OVMF build does not drive:
        # every frame came out uniform black and looked precisely like an ISO
        # that will not boot.
        set -- "$@" -machine q35 \
            -drive "if=pflash,format=raw,unit=0,readonly=on,file=$OVMF/OVMF_CODE_4M.ms.fd" \
            -drive "if=pflash,format=raw,unit=1,file=$OUT/vars.fd"
        # SMM is deliberately NOT enabled, and it costs this test nothing.
        #
        # The textbook invocation adds `-machine q35,smm=on` plus
        # `-global driver=cfi.pflash01,property=secure,value=on`. Under WSL2 —
        # which is itself a guest on Hyper-V — that combination dies the moment
        # the kernel is handed control:
        #   KVM: entry failed, hardware error 0xffffffff ... SMM=1
        # Nested KVM does not carry SMM through. The run reached the GRUB menu
        # and then froze on one frame for 285 seconds, which reads exactly like
        # an OS that fails to boot and is nothing of the kind.
        #
        # SMM only protects the variable store from being rewritten at runtime.
        # It plays no part in deciding whether an image is allowed to load —
        # OVMF still verifies shim against the enrolled Microsoft keys, and shim
        # still verifies GRUB against Debian's, which is the entire question a
        # boot test is here to answer. What is lost is the guarantee that a
        # hostile guest cannot forge its own keys, which no honest ISO is trying
        # to do. Enable it with SMM=1 on a bare-metal host if you want the
        # complete picture.
        [ "${SMM:-0}" = 1 ] && set -- "$@" \
            -global driver=cfi.pflash01,property=secure,value=on \
            -machine smm=on
        ;;
    *) echo "mode must be bios|uefi|secureboot" >&2; exit 1 ;;
esac

echo "booting $MODE for ${SECS}s -> $OUT"
qemu-system-x86_64 "$@" >"$OUT/qemu.log" 2>&1 &
QPID=$!

# Screenshot on a schedule. Early frames catch the boot menu and any firmware
# refusal (which is the whole point in secureboot mode); later frames catch the
# desktop and the first-run wizard.
python3 - "$MON" "$OUT" "$SECS" <<'PY'
import socket, sys, time, os
mon, out, secs = sys.argv[1], sys.argv[2], int(sys.argv[3])
for _ in range(50):
    if os.path.exists(mon): break
    time.sleep(0.2)
s = socket.socket(socket.AF_UNIX)
for _ in range(50):
    try:
        s.connect(mon); break
    except OSError:
        time.sleep(0.2)
else:
    print("could not reach qemu monitor"); sys.exit(1)
s.settimeout(5)
time.sleep(1)
try: s.recv(65536)
except Exception: pass

shots = [t for t in (5, 15, 30, 45, 60, 90, 120, 150, 180, 210, 240, 300) if t <= secs]
start = time.time()
for t in shots:
    d = t - (time.time() - start)
    if d > 0: time.sleep(d)
    p = os.path.join(out, "t%03d.ppm" % t)
    try:
        s.send(("screendump %s\n" % p).encode())
        time.sleep(1.2)
        try: s.recv(65536)
        except Exception: pass
        print("  shot t=%ds %s" % (t, "ok" if os.path.exists(p) else "MISSING"))
    except Exception as e:
        print("  shot t=%ds failed: %s" % (t, e)); break
PY

kill $QPID 2>/dev/null || true
wait $QPID 2>/dev/null || true
rm -f "$MON"

# PPM is what the monitor emits; convert so the images can actually be looked at.
if command -v magick >/dev/null 2>&1; then
    for f in "$OUT"/*.ppm; do
        [ -f "$f" ] || continue
        magick "$f" -resize 1024x "${f%.ppm}.png" 2>/dev/null || true
    done
    rm -f "$OUT"/*.ppm
fi

echo "--- $MODE result ---"
ls -la "$OUT" | grep -E '\.png|\.log' || echo "  NOTHING CAPTURED"
