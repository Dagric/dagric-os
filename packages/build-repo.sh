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

# dists IS CLEARED TOO, not just the pool.
#
# This line used to remove only $POOL, so dists/<suite>/ was overwritten in
# place and any suite that ever existed here stayed on disk — and stayed
# PUBLISHED, because `firebase deploy` serves whatever is under site/. Rename
# SUITE below and the old suite's index keeps a perfectly valid signature over
# Filename: fields pointing into pool/main, which this same line has just wiped
# and repopulated with different bytes under the same names. Every machine in
# the field still asking for the old suite then fails `apt update` on a hash-sum
# mismatch, permanently, with nothing looking wrong on the publishing side.
# Removing it makes that a plain 404, which is noticed immediately instead.
# Everything under dists is regenerated below; dagric-repo.gpg.asc sits beside
# dists rather than under it and is re-exported after signing.
rm -rf "$STAGE" "$POOL" "$OUT/dists"
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
#
# DO NOT BUMP THIS AT THE NEXT DEBIAN REBASE. It reads like a mirror of the base
# distribution and it is not: it is the suite name burned into
# /etc/apt/sources.list.d/dagric.list on every machine ever sold, and
# dagric-upgrade deliberately refuses to rewrite that file
# (`case "$f" in *dagric*) continue ;;`) precisely so the channel keeps working
# across a release upgrade. Rename this and the whole installed base asks for a
# suite that no longer exists — on the one channel that could have fixed it.
# The Dagric channel tracks Dagric, not Debian; "trixie" is now just its name.
SUITE=trixie
COMP=main
DIST=$OUT/dists/$SUITE
mkdir -p "$DIST/$COMP/binary-amd64" "$POOL/$COMP"
mv "$POOL"/*.deb "$POOL/$COMP/" 2>/dev/null || true

cd "$OUT"
# Run from the repo root so the Filename: fields come out relative to it.
dpkg-scanpackages --multiversion "pool/$COMP" /dev/null \
    > "$DIST/$COMP/binary-amd64/Packages" 2>/dev/null
# COUNT THE ENTRIES, because this step cannot fail loudly on its own.
#
# dpkg-scanpackages exits 0 over an EMPTY pool. If the `mv` above moved nothing
# — a glob matching no .deb, a half-finished stage — this wrote a Packages file
# with zero stanzas, and everything below carried on and SIGNED it. That is the
# worst shape this repository can take: a correctly signed index that offers
# nothing. Every owner's `apt update` succeeds, Discover shows no updates, and
# no error appears anywhere on either side.
#
# The 2>/dev/null above is kept and is not the problem: a hard dpkg-scanpackages
# failure is a non-zero exit that `set -e` already catches. Silent success is
# the case only a count can catch, and the count also catches a partial mv.
ENTRIES=$(grep -c '^Package: ' "$DIST/$COMP/binary-amd64/Packages" || true)
DEBS=$(find "$POOL/$COMP" -maxdepth 1 -name '*.deb' | wc -l)
if [ "$ENTRIES" -eq 0 ] || [ "$ENTRIES" -ne "$DEBS" ]; then
    echo "ERROR: the index lists $ENTRIES package(s) but pool/$COMP holds $DEBS .deb(s)." >&2
    echo "Refusing to sign an index that does not match the pool." >&2
    exit 1
fi
echo "index: $ENTRIES package(s) from $DEBS .deb(s)"
gzip -kf "$DIST/$COMP/binary-amd64/Packages"

# The packages are Architecture: all, but apt only looks in binary-<arch> for
# the architectures a Release declares — so amd64 is what must be advertised.
#
# NO Valid-Until, AND THAT IS A DECISION RATHER THAN AN OVERSIGHT.
#
# A Release with no Valid-Until can be replayed forever: anyone able to serve an
# old, still-validly-signed Release freezes a machine's view of this repository,
# and the freeze is silent because every signature checks out. Adding the field
# is the textbook answer, so here is why it is not the answer here.
#
# What it would cost. The field is a hard deadline enforced on the CUSTOMER'S
# machine. The day it passes, every Dagric installation in the field starts
# failing `apt update` with "Release file has expired" — including Discover,
# which is where a non-technical owner meets it as a broken update system. This
# repository is regenerated by hand, at release time, by a one-person operation.
# A deadline that must be beaten by a human with no automation behind it is a
# deadline that will eventually be missed, and missing it breaks working machines
# that no attacker ever touched.
#
# What it would buy, honestly measured. The channel is HTTPS to a host the
# project controls, so replaying an old Release means compromising that host or
# its CDN, not merely sitting on the network — the usual precondition for this
# attack is already off the table. The packages served here are excluded from
# unattended-upgrades on purpose (see dagric.list), so a frozen view delays an
# update the owner clicks, rather than suppressing a silent security patch. And
# an attacker who can replay can equally just refuse to serve the repo at all,
# which produces the same denial and which Valid-Until does not prevent.
#
# A window long enough to be safely maintainable — a year or two — is also long
# enough to be nearly worthless as a bound on the attack. The field only helps
# when it is short, and short is exactly what cannot be promised here.
#
# Revisit when repository generation is automated on a schedule. At that point a
# one-week window costs nothing and this reasoning inverts. Until then, do not
# add it because a checklist said to: the failure lands on customers.
cd "$DIST"
# WRITTEN OUTSIDE THE SCANNED DIRECTORY, THEN MOVED IN.
#
# This was `apt-ftparchive release . > Release`, and the shell creates the empty
# Release in "." BEFORE apt-ftparchive starts reading it — so the partially
# written file got hashed into its own index. The published Release listed
# itself at 177 bytes while the file actually served was 1487, and the four
# digests for it matched nothing on the server.
#
# apt never verifies that self-entry, so no customer was affected. Any strict
# mirroring tool that fetches every listed file — debmirror, aptly, apt-mirror —
# reports a hash-sum mismatch on a perfectly good repository, which is a bad
# first impression to give somebody who mirrors us.
rm -f Release Release.new
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=Dagric \
    -o APT::FTPArchive::Release::Label="Dagric OS" \
    -o APT::FTPArchive::Release::Suite="$SUITE" \
    -o APT::FTPArchive::Release::Codename="$SUITE" \
    -o APT::FTPArchive::Release::Architectures=amd64 \
    -o APT::FTPArchive::Release::Components="$COMP" \
    -o APT::FTPArchive::Release::Description="Dagric OS update channel" \
    release . > "$OUT/Release.new"
mv "$OUT/Release.new" Release
# And prove it: a Release that still describes itself would mean the redirect
# has crept back.
if grep -qE '^ [0-9a-f]+ +[0-9]+ Release$' Release; then
    echo "build-repo: Release contains an entry for itself — the index was" >&2
    echo "  generated into the directory being scanned. Mirroring tools will" >&2
    echo "  report a hash mismatch on a good repository." >&2
    exit 1
fi

echo "=== signing with the release key ==="
KEY=6CE37402BA0A0EF8
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || {
    echo "signing key $KEY not in the keyring — import it first" >&2; exit 1; }
rm -f Release.gpg InRelease
gpg --batch --yes --default-key "$KEY" -abs -o Release.gpg Release
gpg --batch --yes --default-key "$KEY" --clearsign -o InRelease Release
# export-clean, export-minimal: strip revoked user IDs and third-party
# signatures from the PUBLISHED key. A plain `--armor --export` carries the
# key's whole history, and this key's history includes a revoked placeholder uid
# reading "Dagric OS Repository <repo@example.org>" — visible to anyone who runs
# `gpg --show-keys` on the trust anchor of a product sold on verifiability. It
# is cryptographically harmless (the binary keyring shipped in the image has
# only the clean uid) and it is exactly the artefact a security-conscious buyer
# inspects first.
gpg --armor --export-options export-clean,export-minimal \
    --export "$KEY" > "$OUT/dagric-repo.gpg.asc"
if gpg --show-keys "$OUT/dagric-repo.gpg.asc" 2>/dev/null | grep -qi 'example\.org'; then
    echo "build-repo: the exported key still carries the example.org placeholder uid." >&2
    exit 1
fi

# Verify our own signature before it is served to anybody — as a PLAIN command
# whose exit status is checked, not as
#     gpg --verify Release.gpg Release 2>&1 | grep -E 'Good signature|BAD' | head -1
# A pipeline's status is the LAST command's, and `head -1` succeeds whatever it
# reads. So gpg failing outright and grep matching the word "BAD" both left $?
# at 0 under `set -e`: the one check standing between a broken signature and
# every installed machine's apt could print "BAD signature" and still let the
# script exit successfully two lines later. It reported success by construction.
#
# AND IT MUST BE THE FLEET'S KEYRING, NOT THIS HOST'S. `gpg --verify` reads
# ~/.gnupg — which, a few lines above, was proved to hold the SECRET key. So it
# can only ever answer "did the signer sign this", never "will a sold machine
# accept it". The file every machine checks against is
# config/includes.chroot/usr/share/keyrings/dagric.gpg, a binary keyring
# committed to the tree that nothing here regenerates: the export above
# refreshes the PUBLISHED .asc and leaves that one alone. Add a signing subkey,
# renew, or replace the key and `gpg --verify` still says "Good signature" while
# every installed machine starts failing `apt update` with NO_PUBKEY.
#
# BOTH ARTEFACTS, because apt only fetches one of them and it was not the one
# being checked. apt asks for InRelease and uses it when it is there
# (out/pro-release-build.log: "Get:5 https://dagric-os.web.app/repo trixie
# InRelease"; Release.gpg is never requested), and Release + Release.gpg is only
# the fallback for repositories that have no InRelease. A malformed InRelease is
# a hard apt error with no fallback, and it is written by a second, unchecked
# gpg run.
command -v gpgv >/dev/null 2>&1 || {
    echo "ERROR: gpgv is not installed, so the signature cannot be checked" >&2
    echo "against the keyring installed machines trust. NOT publishing." >&2
    exit 1
}
KEYRING=$REPO/config/includes.chroot/usr/share/keyrings/dagric.gpg
[ -f "$KEYRING" ] || {
    echo "ERROR: $KEYRING is missing — cannot check the signature against the" >&2
    echo "keyring installed machines actually trust. NOT publishing." >&2
    exit 1
}
gpgv --keyring "$KEYRING" Release.gpg Release || {
    echo "ERROR: Release.gpg does not verify against the keyring shipped to" >&2
    echo "installed machines. NOT publishing." >&2
    exit 1
}
gpgv --keyring "$KEYRING" InRelease || {
    echo "ERROR: InRelease does not verify against the keyring shipped to" >&2
    echo "installed machines — and InRelease is the file apt actually fetches." >&2
    echo "NOT publishing." >&2
    exit 1
}

echo
echo "=== repository layout ==="
cd "$OUT"
find . -type f | sed 's|^\./|  |' | sort
du -sh "$OUT"
