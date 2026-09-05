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
case "$MODE" in
    bios|uefi|secureboot) ;;
    *) echo "mode must be bios|uefi|secureboot" >&2; exit 1 ;;
esac
case "$SECS" in
    ''|*[!0-9]*) echo "SECS must be a whole number of seconds" >&2; exit 1 ;;
esac
if [ "$SECS" -lt 1 ] || [ "$SECS" -gt 1800 ]; then
    echo "SECS must be between 1 and 1800" >&2
    exit 1
fi
# DAGRIC_REPO override: this script is normally run from a copy under /srv
# (the repo lives on a 9p mount where CRLF has to be stripped first), and in
# that case $0's parent is not the repo and screenshots land in /out.
REPO=${DAGRIC_REPO:-$(unset CDPATH; cd -- "$(dirname -- "$0")/.." && pwd)}
# Keyed by ISO as well as mode. Keying on mode alone meant testing the Pro
# image silently overwrote the free image's screenshots in out/boot-test/uefi,
# so the two editions could never be compared — which is exactly how the
# Firefox/Chromium difference nearly went unnoticed.
OUT=$REPO/out/boot-test/$(basename "$ISO" .iso)-$MODE

[ -f "$ISO" ] || { echo "no such ISO: $ISO" >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo "qemu-system-x86_64 missing" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"
MON_DIR=$(mktemp -d "${TMPDIR:-/tmp}/dagric-boot-monitor.XXXXXX") || exit 1
MON="$MON_DIR/monitor.sock"
QPID=""
cleanup() {
    if [ -n "$QPID" ]; then
        kill "$QPID" 2>/dev/null || true
        wait "$QPID" 2>/dev/null || true
    fi
    rm -rf "$MON_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP

OVMF=/usr/share/OVMF
set -- -m 4096 -smp 2 -cdrom "$ISO" -boot d \
       -display none -vga std \
       -monitor "unix:$MON,server,nowait" \
       -rtc base=localtime

# KVM if the kernel exposes it. Without it a Plasma boot takes long enough that
# the timer would expire before the desktop appears, and the run would look
# like a failure that is really just slowness.
#
# EXCEPT for secureboot on a nested host, where KVM cannot be used at all.
# OVMF_CODE_4M.ms.fd is built SMM_REQUIRE, and QEMU's q35 switches SMM on by
# itself — `smm` defaults to auto, which resolves to on for this firmware — so
# leaving `-machine smm=on` off the command line, which this script did and
# documented as the whole mitigation, changed nothing. Nested KVM does not carry
# SMM through, and the guest dies the instant GRUB hands off to the kernel:
#   KVM: entry failed, hardware error 0xffffffff ... SMM=1
# after which the run sits on the GRUB load screen for the rest of the timer.
# That reads exactly like an ISO that will not boot, and it is the mode whose
# whole job is to answer "will this boot on a retail Windows laptop" — so the
# one question most worth getting right was the one being answered wrongly.
#
# Measured on WSL2, same ISO, same firmware: under KVM every frame from t=30s to
# t=180s was the GRUB background and qemu.log carried the SMM entry failure;
# under TCG the run reached the first-run wizard at t=300s. Forcing smm=off is
# not an escape — the firmware then never initialises at all and every frame
# reads "Guest has not initialized the display (yet)".
#
# So a nested host runs this mode on TCG. It is slow, and it is the only way the
# mode tells the truth. Bare metal is unaffected and keeps KVM.
if [ "$MODE" = secureboot ] && grep -q '^flags.* hypervisor' /proc/cpuinfo 2>/dev/null; then
    echo "nested host detected: secureboot runs WITHOUT KVM, because SMM does not nest."
    # TCG is roughly 2-3x slower to a desktop here, and a timer that expires
    # before the desktop appears is the same false failure by another route.
    if [ "$SECS" -lt 300 ]; then
        echo "  raising SECS from $SECS to 300 so the desktop has time to appear"
        SECS=300
    fi
elif [ -w /dev/kvm ]; then
    set -- "$@" -enable-kvm -cpu host
fi

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
        # SMM=1 adds the variable-store lockdown on top. It is NOT what decides
        # whether this mode runs with SMM at all — the firmware settles that.
        #
        # This block used to say SMM was "deliberately NOT enabled, and it costs
        # this test nothing", on the theory that omitting `-machine smm=on` left
        # it off. It does not. `smm` defaults to auto on q35, and auto resolves
        # to ON for a SMM_REQUIRE firmware build like OVMF_CODE_4M.ms.fd, so the
        # line above has always run with SMM whatever this flag said. That is
        # why the nested-KVM crash the old comment described as avoided was
        # still happening on every WSL2 run; the KVM decision above is where it
        # is actually handled now.
        #
        # What SMM=1 still buys: `secure=on` on the pflash device makes the
        # variable store writable only from SMM, which is the guarantee that a
        # hostile guest cannot enrol its own keys. It plays no part in deciding
        # whether an image is allowed to load — OVMF verifies shim against the
        # enrolled Microsoft keys and shim verifies GRUB against Debian's either
        # way, and that chain is the question a boot test exists to answer.
        # Worth setting on bare metal for the complete picture.
        [ "${SMM:-0}" = 1 ] && set -- "$@" \
            -global driver=cfi.pflash01,property=secure,value=on \
            -machine smm=on
        ;;
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
        # HMP tokenises an unquoted path at spaces. The repository commonly
        # lives under a Windows folder such as "Dagric Os", so every command
        # used to be accepted but every frame silently went missing. Quote and
        # escape the monitor argument just as a shell path would be quoted.
        qp = p.replace("\\", "\\\\").replace('"', '\\"')
        s.send(('screendump "%s"\n' % qp).encode())
        time.sleep(1.2)
        try:
            reply = s.recv(65536).decode(errors="replace")
            if "Error:" in reply:
                print("  monitor rejected t=%ds: %s" % (t, reply.strip()))
        except Exception: pass
        print("  shot t=%ds %s" % (t, "ok" if os.path.exists(p) else "MISSING"))
    except Exception as e:
        print("  shot t=%ds failed: %s" % (t, e)); break
PY

kill $QPID 2>/dev/null || true
wait $QPID 2>/dev/null || true
QPID=""

# PPM is what the monitor emits; convert so the images can actually be looked at.
#
# DELETE ONLY WHAT WAS CONVERTED. This was `magick ... || true` followed by an
# unconditional `rm -f "$OUT"/*.ppm`, so a conversion that failed — a magick
# that is broken, or one killed by the OOM killer on a low-memory host — took
# the only evidence the run produced with it. The resize is the one step here
# with nothing riding on it; the frames ARE the product of this script, so a
# failed resize must cost the resize, not the screenshot.
if command -v magick >/dev/null 2>&1; then
    for f in "$OUT"/*.ppm; do
        [ -f "$f" ] || continue
        if magick "$f" -resize 1024x "${f%.ppm}.png" 2>/dev/null; then
            rm -f "$f"
        else
            echo "  WARNING: could not convert ${f##*/} — keeping the .ppm" >&2
        fi
    done
fi

echo "--- $MODE result ---"
ls -la "$OUT"

# COUNT THE FRAMES. `ls -la "$OUT" | grep -E '\.png|\.log'` could never report
# failure: qemu.log is written by every single run and matches '\.log', so grep
# always succeeded, the `|| echo "  NOTHING CAPTURED"` branch was unreachable
# dead code, and a run that photographed nothing still ended with a result
# banner and a tidy listing under it — indistinguishable from a clean run.
# Whether any frame exists is the only thing that says this test answered its
# question.
#
# Counted with a glob rather than by parsing ls: the glob IS the question, and
# an unmatched one expands to the literal pattern, which `[ -f ]` discards.
# .ppm counts too — magick may be absent, or a convert may have been kept above.
_frames=0
for f in "$OUT"/*.png "$OUT"/*.ppm; do
    if [ -f "$f" ]; then _frames=$((_frames + 1)); fi
done
if [ "$_frames" -eq 0 ]; then
    echo "  NOTHING CAPTURED — this run proves nothing about whether the ISO" >&2
    echo "  boots in $MODE mode. See $OUT/qemu.log." >&2
    exit 1
fi
echo "  $_frames frame(s) captured"
