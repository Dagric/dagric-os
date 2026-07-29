#!/bin/sh
# Dagric OS — build the config packages and the signed APT repository, natively.
#
#   sh packages/build-repo.sh [REPO_ROOT]
#
# This replaces the container path in repo.ps1 and docs/REPOSITORY.md. Docker on
# this machine is permanently broken (Windows AF_UNIX bind returns EACCES even
# elevated), and the repo signing key that document describes lives in a Docker
# volume that can no longer be reached. Everything here runs in WSL instead.
#
# TWO DELIBERATE DEPARTURES FROM THE ORIGINAL DESIGN
#
# 1. ONE KEY, NOT TWO. make-repo.sh generated a fresh key whose identity is
#    "Dagric OS Repository <repo@dagric.com>" — which is exactly the identity of
#    the release key that already signs the ISO checksums. A second key would
#    mean a second irreplaceable no-passphrase secret to protect, for a threat
#    model that does not separate: whoever holds either can already publish a
#    forged image or push a package to every machine. So the existing key signs
#    both, and users who imported it to check their download are already set up
#    to trust their updates.
#
# 2. THE OUTPUT GOES IN site/repo. docs/REPOSITORY.md waits on repo.dagric.com,
#    which does not exist. dagric-os.web.app does, is already on HTTPS, and is
#    deployed by the same `firebase deploy` that publishes the download page —
#    so the update channel needs no new infrastructure and no new domain, and
#    the URL is one the owner controls rather than a bucket hostname.
set -e

REPO=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
OUT=$REPO/site/repo
POOL=$OUT/pool
STAGE=/srv/pkgstage

command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb required" >&2; exit 1; }
command -v apt-ftparchive >/dev/null 2>&1 || { echo "apt-utils required" >&2; exit 1; }

rm -rf "$STAGE" "$POOL"
mkdir -p "$POOL"

# The packages themselves are built by packages/stage-packages.sh, which is
# shared with build.sh so that the ISO installs exactly the .debs this repo
# publishes. Splitting it out is what let the image subscribe to its own update
# channel: this script holds the release key and cannot run inside an image
# build, and the half that just assembles the four packages has no business
# needing a key at all.
sh "$REPO/packages/stage-packages.sh" "$REPO" "$POOL"

echo
echo "=== generating the repository index ==="
#
# A SUITE LAYOUT, NOT A FLAT ONE, AND THE REASON IS THE HOST.
#
# docs/REPOSITORY.md describes a flat repo ("deb URL ./"), which is the simplest
# thing that works on most static hosts. It does not work on this one. For a
# flat repo apt requests the index as URL/./Release — with the dot-segment
# literally in the path — and Firebase Hosting's cleanUrls does not normalise
# it away. Measured against the deployed site:
#     /repo/Release     -> 200
#     /repo/./Release   -> 302
# apt followed the redirect, did not find an index, and reported
# "does not have a Release file" — which reads exactly like a repo that was
# never published, on a repo that was published perfectly.
#
# The dists/SUITE/COMPONENT layout never emits a dot segment, so it is immune,
# and it is what every real Debian mirror uses anyway.
SUITE=trixie
COMP=main
DIST=$OUT/dists/$SUITE
mkdir -p "$DIST/$COMP/binary-amd64" "$POOL/$COMP"
mv "$POOL"/*.deb "$POOL/$COMP/" 2>/dev/null || true

cd "$OUT"
# Run from the repo root so the Filename: fields come out relative to it.
dpkg-scanpackages --multiversion "pool/$COMP" /dev/null \
    > "$DIST/$COMP/binary-amd64/Packages" 2>/dev/null
gzip -kf "$DIST/$COMP/binary-amd64/Packages"

# The packages are Architecture: all, but apt only looks in binary-<arch> for
# the architectures a Release declares — so amd64 is what must be advertised.
cd "$DIST"
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=Dagric \
    -o APT::FTPArchive::Release::Label="Dagric OS" \
    -o APT::FTPArchive::Release::Suite="$SUITE" \
    -o APT::FTPArchive::Release::Codename="$SUITE" \
    -o APT::FTPArchive::Release::Architectures=amd64 \
    -o APT::FTPArchive::Release::Components="$COMP" \
    -o APT::FTPArchive::Release::Description="Dagric OS update channel" \
    release . > Release

echo "=== signing with the release key ==="
KEY=6CE37402BA0A0EF8
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || {
    echo "signing key $KEY not in the keyring — import it first" >&2; exit 1; }
rm -f Release.gpg InRelease
gpg --batch --yes --default-key "$KEY" -abs -o Release.gpg Release
gpg --batch --yes --default-key "$KEY" --clearsign -o InRelease Release
gpg --armor --export "$KEY" > "$OUT/dagric-repo.gpg.asc"

# Verify our own signature before it is served to anybody.
gpg --verify Release.gpg Release 2>&1 | grep -E 'Good signature|BAD' | head -1

echo
echo "=== repository layout ==="
cd "$OUT"
find . -type f | sed 's|^\./|  |' | sort
du -sh "$OUT"
