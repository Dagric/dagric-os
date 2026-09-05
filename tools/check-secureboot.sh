#!/bin/sh
# Dagric OS — inspect static EFI signature presence and signer identities.
#
#   sh tools/check-secureboot.sh out/dagric-os-1.0-amd64.iso
#
# This is not cryptographic chain validation or physical boot evidence.
# Firmware trust/revocation databases and an actual boot must be checked
# separately. These static checks diagnose several common packaging errors:
#   - no EFI boot image in the ISO at all (BIOS-only build)
#   - EFI/boot/bootx64.efi is GRUB rather than shim, so nothing Microsoft signed
#     is ever executed and the firmware refuses at the first hop
#   - shim is there but unsigned, or signed by a key the firmware does not carry
#   - shim is signed but grubx64.efi is not, so it fails at the second hop
# These errors can look identical from the outside: a black screen.
#
# Note the asymmetry that trips people up. bootx64.efi must carry MICROSOFT's
# signature, because Microsoft's cert is what retail firmware trusts. grubx64.efi
# must carry DEBIAN's, because shim carries Debian's cert internally and does the
# second verification itself. A build that signs everything with the same key is
# broken in a way that only shows up on real hardware.
set -e

ISO=$1
[ -f "$ISO" ] || { echo "usage: $0 <iso>" >&2; exit 1; }

command -v sbverify >/dev/null 2>&1 || {
    echo "installing sbsigntool..."
    apt-get install -y -qq sbsigntool >/dev/null 2>&1 || {
        echo "could not install sbsigntool" >&2; exit 1; }
}

# `strings` is the second half of the first-hop test below.  It comes from
# binutils, not sbsigntool.  A minimal Debian verifier therefore had sbverify,
# printed both signatures correctly, then treated `strings: not found` (whose
# stderr was deliberately hidden) as proof that Microsoft's signed first hop
# was not shim.  That is a false Secure Boot failure.  Make the diagnostic's
# own dependency explicit before it is allowed to issue a verdict.
command -v strings >/dev/null 2>&1 || {
    echo "installing binutils for shim identification..."
    apt-get install -y -qq binutils >/dev/null 2>&1 || {
        echo "could not install binutils" >&2; exit 1; }
}

MNT=$(mktemp -d)
mount -o loop,ro "$ISO" "$MNT" 2>/dev/null || {
    echo "could not mount $ISO (need root?)" >&2; exit 1; }

fail=0
echo "=== EFI payload in the ISO filesystem ==="
find "$MNT" -iname '*.efi' 2>/dev/null | sed "s|$MNT|  |" || true
find "$MNT" -iname 'efi*.img' 2>/dev/null | sed "s|$MNT|  |" || true

# The ISO9660 tree usually carries EFI/boot/*.efi directly; some builds only
# have it inside the El Torito FAT image, so look in both.
EFIDIR=""
for d in "$MNT/EFI/boot" "$MNT/EFI/BOOT" "$MNT/efi/boot"; do
    [ -d "$d" ] && EFIDIR=$d && break
done

IMG=$(find "$MNT" -iname 'efi*.img' 2>/dev/null | head -1)
IMGMNT=""
if [ -z "$EFIDIR" ] && [ -n "$IMG" ]; then
    IMGMNT=$(mktemp -d)
    mount -o loop,ro "$IMG" "$IMGMNT" 2>/dev/null && \
        for d in "$IMGMNT/EFI/boot" "$IMGMNT/EFI/BOOT"; do
            [ -d "$d" ] && EFIDIR=$d && break
        done
fi

if [ -z "$EFIDIR" ]; then
    echo "RESULT: No EFI boot directory found in the checked locations — static check failed." >&2
    fail=1
else
    echo
    echo "=== signatures ==="
    for f in "$EFIDIR"/*.efi "$EFIDIR"/*.EFI; do
        [ -f "$f" ] || continue
        n=$(basename "$f")
        echo "--- $n ---"
        if sbverify --list "$f" 2>&1 | grep -q 'signature certificates'; then
            sbverify --list "$f" 2>/dev/null \
                | grep -E 'subject|issuer' | sed 's/^/    /' | head -8
        else
            echo "    NO SIGNATURE"
            case "$n" in
                [bB][oO][oO][tT][xX]64.[eE][fF][iI]|[gG][rR][uU][bB][xX]64.[eE][fF][iI])
                    echo "    ^ this one MUST be signed for Secure Boot" >&2; fail=1 ;;
            esac
        fi
    done

    echo
    echo "=== is the first hop actually shim? ==="
    B=""
    for c in "$EFIDIR/bootx64.efi" "$EFIDIR/BOOTX64.EFI"; do
        [ -f "$c" ] && B=$c && break
    done
    if [ -z "$B" ]; then
        echo "  NO bootx64.efi — firmware has nothing to load" >&2; fail=1
    elif strings "$B" 2>/dev/null | grep -qiE 'mok manager|shim|MokManager'; then
        echo "  yes — bootx64.efi is shim (MOK strings present)"
        sbverify --list "$B" 2>/dev/null | grep -i 'subject' | head -2 \
            | grep -qi 'microsoft' \
            && echo "  Microsoft signer identity is present — firmware acceptance is not tested" \
            || { echo "  Microsoft signer identity was not found — static check failed" >&2; fail=1; }
    else
        echo "  Shim identification strings were not found in bootx64.efi — static check failed." >&2
        fail=1
    fi
fi

umount "$IMGMNT" 2>/dev/null || true
umount "$MNT" 2>/dev/null || true

echo
[ $fail -eq 0 ] && echo "VERDICT: Static EFI signature presence/identity checks passed (not a physical boot test)." \
                || echo "VERDICT: Static EFI signature presence/identity checks failed."
echo "PENDING: Cryptographic chain validation, firmware trust/revocation checks, and physical Secure Boot evidence."
exit $fail
