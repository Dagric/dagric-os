#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
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
PKGS_URL="https://dagric.com/repo/dists/trixie/main/binary-amd64/Packages"
KEY=site/dagric-signing-key.asc
QUICK=${1:-}

# THE UPDATE CHANNEL, WHICH NOTHING HAS EVER CHECKED.
#
# Everything above this line is about the ISO a new customer downloads. The
# channel is the half that serves the customers who ALREADY bought — and it was
# the one release artefact with no end-state check of any kind: not here, not in
# release.sh, not in build.sh (whose version gate only refuses a COLLISION, so a
# channel arbitrarily far behind passes it).
#
# It bit exactly as you would expect. On 2026-08-29 the live channel was still
# publishing 1.1.1, dated 29 Jul, while the shipped ISOs installed 1.1.3/1.1.4:
# a month of fixes — the Dagric startup screen, the Kickoff favourites fix, the
# corrected wizard, Family Limits — had reached no sold machine, and the
# release that built them had run the ISO half and skipped the channel half.
# docs/REPOSITORY.md's checklist said to do both. A checklist is a reminder;
# this is a mechanism, which is the same lesson release.sh's own header records
# about SHA256SUMS.
#
# Compares the live channel against packages/*/DEBIAN/control, which is the
# version the tree would publish, so "did this release include a channel
# publish" is answerable rather than assumed.
check_channel() {
    echo ""
    echo "update channel:"
    _p=$(curl -fsS "$PKGS_URL" 2>/dev/null) || {
        echo "  ERROR: could not fetch $PKGS_URL" >&2
        echo "  The channel is how a fix reaches a machine that is already sold." >&2
        return 1
    }
    _bad=0
    for _c in packages/*/DEBIAN/control; do
        _name=$(sed -n 's/^Package: //p' "$_c" | head -1)
        _want=$(sed -n 's/^Version: //p' "$_c" | head -1)
        [ -n "$_name" ] && [ -n "$_want" ] || continue
        _live=$(printf '%s\n' "$_p" \
                | awk -v n="$_name" '$1=="Package:" && $2==n {f=1;next} f && $1=="Version:" {print $2; exit}')
        if [ -z "$_live" ]; then
            echo "  $_name: NOT PUBLISHED (tree has $_want)" >&2
            _bad=1
        elif [ "$_live" != "$_want" ]; then
            echo "  $_name: live $_live, tree $_want  <-- BEHIND" >&2
            _bad=1
        else
            echo "  $_name: $_live"
        fi
    done
    if [ "$_bad" = 1 ]; then
        echo "" >&2
        echo "THE UPDATE CHANNEL IS BEHIND THE TREE." >&2
        echo "" >&2
        echo "Machines already sold are not receiving these fixes, and Discover" >&2
        echo "on those machines correctly reports that there is nothing to" >&2
        echo "install. Publishing the ISO without publishing the channel is" >&2
        echo "half a release." >&2
        echo "" >&2
        echo "Fix:  sh packages/build-repo.sh" >&2
        echo "      firebase deploy --only hosting" >&2
        echo "      sh tools/verify-published.sh --quick" >&2
        return 1
    fi
    echo "  channel matches the tree."
    return 0
}

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
    # The channel check still runs: it is four small HTTP fetches, and the
    # failure it catches (a release that shipped an ISO and forgot the channel)
    # is exactly the one somebody in a hurry with --quick is likeliest to have.
    check_channel
    exit $?
fi

echo "  downloading (~2.1 GB, this is the point of the check)..."
curl -fsS -o "$TMP/iso" "$ISO_URL" || { echo "ERROR: download failed" >&2; exit 1; }
ACTUAL=$(sha256sum "$TMP/iso" | awk '{print $1}')
echo "  actual hash: $ACTUAL"

if [ "$ACTUAL" = "$EXPECT" ]; then
    echo ""
    echo "MATCH — a customer following the download page's instructions gets 'OK'."
    check_channel
    exit $?
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
