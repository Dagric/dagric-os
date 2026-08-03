#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — does the ISO a customer downloads match the signature we publish?
#
#     sh tools/verify-published.sh            check the free ISO (~2.1 GB)
#     sh tools/verify-published.sh --quick    check signature + sizes only
#
# WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL
# -------------------------------------------
# On 2026-08-03 the published checksums did not describe the published ISO:
#
#     site/SHA256SUMS says   533126a5baff2fd7ae2f17f400da0bc8891bf04089a64f8dd8df78c8f1a7e270
#     the live ISO hashes to dabdc0b395fcfaade4c4705ce2be343f366b709572e1f8d1bbdbccd93c220261
#
# The signature was fine — "Good signature from Dagric OS Repository", made Tue
# Jul 28 03:04:31 2026. The ISO behind it had been replaced on Sun Aug 2
# 23:08:36 GMT, five days later, and the checksums were never re-signed.
#
# So every customer who followed the download page's own verification
# instructions got a MISMATCH. Not a missing signature, not a warning — the
# specific result that means "this file has been tampered with". On a product
# whose security pitch is "verified releases, GPG-signed", the integrity
# guarantee did not merely fail, it accused us.
#
# .github/workflows/release.yml already TELLS you not to do this. Its summary
# says "Order matters: an ISO live against an older signature reads as a
# tampered download, which is worse than an older release." The instructions
# were right and were followed halfway: the image got promoted, the checksums
# and signature did not. Nothing checked the end state, so nothing noticed.
#
# That is the gap this closes. Promotion is a manual copy-paste of four aws
# commands; the one thing that can catch a partial run is asking, afterwards,
# what a customer would actually see.
#
# RUN IT AFTER EVERY PROMOTE. It downloads what the download page links to, not
# what is in out/ — a local build is not evidence about the live object, and
# conflating the two is how this went unnoticed for five days.
set -e
cd "$(dirname "$0")/.."

ISO_URL=$(grep -oE 'https://[^"]*dagric-os-1\.0-amd64\.iso' site/download.html | head -1)
SUMS_URL="https://dagric.com/SHA256SUMS"
SIG_URL="https://dagric.com/SHA256SUMS.sig"
KEY=site/dagric-signing-key.asc
QUICK=${1:-}

[ -n "$ISO_URL" ] || { echo "ERROR: no ISO URL in site/download.html" >&2; exit 1; }
[ -f "$KEY" ]     || { echo "ERROR: $KEY missing" >&2; exit 1; }

TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT INT TERM

echo "Checking what a customer actually downloads."
echo "  ISO:  $ISO_URL"

curl -fsS -o "$TMP/SHA256SUMS"     "$SUMS_URL" || { echo "ERROR: cannot fetch $SUMS_URL" >&2; exit 1; }
curl -fsS -o "$TMP/SHA256SUMS.sig" "$SIG_URL"  || { echo "ERROR: cannot fetch $SIG_URL" >&2; exit 1; }

# Verify against the key WE PUBLISH, in a throwaway keyring, so a key trusted in
# the developer's own keyring cannot make a bad signature look fine.
GNUPGHOME="$TMP/gnupg"; export GNUPGHOME
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"
gpg --batch --quiet --import "$KEY" 2>/dev/null || {
    echo "ERROR: could not import $KEY" >&2; exit 1; }

if gpg --batch --verify "$TMP/SHA256SUMS.sig" "$TMP/SHA256SUMS" 2>"$TMP/gpgout"; then
    echo "  signature: GOOD  ($(sed -n 's/.*Signature made //p' "$TMP/gpgout" | head -1))"
else
    echo "ERROR: the published signature does not verify against the published key." >&2
    sed 's/^/       /' "$TMP/gpgout" >&2
    exit 1
fi

EXPECT=$(awk '/dagric-os-1\.0-amd64\.iso$/ {print $1}' "$TMP/SHA256SUMS" | head -1)
[ -n "$EXPECT" ] || { echo "ERROR: SHA256SUMS has no line for the free ISO" >&2; exit 1; }
echo "  signed hash: $EXPECT"

if [ "$QUICK" = "--quick" ]; then
    echo "  --quick: skipping the download. Signature is valid; the hash is NOT checked."
    echo "  This does NOT tell you whether the live ISO matches. Run without --quick"
    echo "  before announcing a release."
    exit 0
fi

echo "  downloading (~2.1 GB, this is the point of the check)..."
curl -fsS -o "$TMP/iso" "$ISO_URL" || { echo "ERROR: download failed" >&2; exit 1; }
ACTUAL=$(sha256sum "$TMP/iso" | awk '{print $1}')
echo "  actual hash: $ACTUAL"

if [ "$ACTUAL" = "$EXPECT" ]; then
    echo ""
    echo "MATCH — a customer following the download page's instructions gets 'OK'."
    exit 0
fi

echo "" >&2
echo "MISMATCH. THE PUBLISHED SIGNATURE DOES NOT DESCRIBE THE PUBLISHED ISO." >&2
echo "" >&2
echo "  signed:  $EXPECT" >&2
echo "  actual:  $ACTUAL" >&2
echo "" >&2
echo "Every customer verifying their download is being told it was tampered" >&2
echo "with. This is almost always a half-finished promote: the image was" >&2
echo "copied to the bucket and SHA256SUMS + .sig were not." >&2
echo "" >&2
echo "Fix by re-signing the CURRENT objects and promoting all three together," >&2
echo "signature last, exactly as release.yml's job summary sets out. Then run" >&2
echo "this again — it is the only thing that proves the end state." >&2
exit 1
