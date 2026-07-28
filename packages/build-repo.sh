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
INC=$REPO/config/includes.chroot
OUT=$REPO/site/repo
POOL=$OUT/pool
STAGE=/srv/pkgstage

command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb required" >&2; exit 1; }
command -v apt-ftparchive >/dev/null 2>&1 || { echo "apt-utils required" >&2; exit 1; }

rm -rf "$STAGE" "$POOL"
mkdir -p "$POOL"

build_pkg() {
    name=$1
    root="$STAGE/$name"
    version=$(sed -n 's/^Version: //p' "$root/DEBIAN/control")
    dpkg-deb --build --root-owner-group "$root" "$POOL/${name}_${version}_all.deb" >/dev/null
    printf '  %-26s %s\n' "$name" "$version"
}

echo "=== building packages from config/includes.chroot ==="

# ---- dagric-branding: what the machine LOOKS like -------------------------
P=$STAGE/dagric-branding
mkdir -p "$P/usr/share/wallpapers" "$P/usr/share/dagric" "$P/usr/share/sddm/themes"
cp -r "$REPO/packages/dagric-branding/DEBIAN" "$P/"
cp -r "$INC/usr/share/wallpapers/Dagric"  "$P/usr/share/wallpapers/"
cp -r "$INC/usr/share/dagric/logo"        "$P/usr/share/dagric/"
[ -d "$INC/usr/share/dagric/sddm" ]   && cp -r "$INC/usr/share/dagric/sddm"   "$P/usr/share/dagric/"
[ -d "$INC/usr/share/dagric/splash" ] && cp -r "$INC/usr/share/dagric/splash" "$P/usr/share/dagric/"
[ -d "$INC/usr/share/sddm/themes" ]   && cp -r "$INC/usr/share/sddm/themes/." "$P/usr/share/sddm/themes/"
build_pkg dagric-branding

# ---- dagric-desktop-defaults ---------------------------------------------
P=$STAGE/dagric-desktop-defaults
mkdir -p "$P/etc/skel/.config" "$P/usr/lib/firefox-esr/distribution" "$P/etc/xdg"
cp -r "$REPO/packages/dagric-desktop-defaults/DEBIAN" "$P/"
for f in kdeglobals kwinrc kcminputrc; do
    [ -f "$INC/etc/skel/.config/$f" ] && cp "$INC/etc/skel/.config/$f" "$P/etc/skel/.config/"
done
cp "$INC/usr/lib/firefox-esr/distribution/policies.json" "$P/usr/lib/firefox-esr/distribution/"
# The default-browser declaration. Pro shipped Chromium as the default for
# every link because nothing declared one; that fix has to reach sold machines.
[ -f "$INC/etc/xdg/mimeapps.list" ] && cp "$INC/etc/xdg/mimeapps.list" "$P/etc/xdg/"
build_pkg dagric-desktop-defaults

# ---- dagric-security-policy ----------------------------------------------
P=$STAGE/dagric-security-policy
mkdir -p "$P/etc/apt/apt.conf.d" "$P/etc/sysctl.d"
cp -r "$REPO/packages/dagric-security-policy/DEBIAN" "$P/"
cp "$INC/etc/apt/apt.conf.d/01dagric-norecommends" "$P/etc/apt/apt.conf.d/"
cp "$INC/etc/sysctl.d/99-dagric-hardening.conf"    "$P/etc/sysctl.d/"
build_pkg dagric-security-policy

# ---- dagric-tools: the product itself -------------------------------------
# Nothing here overlaps dagric-branding. Two packages shipping the same path is
# a dpkg unpack error, not a warning, so logo/ sddm/ and splash/ belong to
# branding and are excluded from this list rather than being copied twice.
P=$STAGE/dagric-tools
mkdir -p "$P/usr/bin" "$P/usr/lib/dagric" "$P/usr/share/dagric" \
         "$P/usr/share/applications" "$P/usr/share/icons/hicolor"
cp -r "$REPO/packages/dagric-tools/DEBIAN" "$P/"
for f in "$INC/usr/bin/"dagric-*; do
    [ -f "$f" ] && cp "$f" "$P/usr/bin/"
done
chmod 0755 "$P/usr/bin/"* 2>/dev/null || true
[ -d "$INC/usr/lib/dagric" ] && cp -r "$INC/usr/lib/dagric/." "$P/usr/lib/dagric/"
for d in firstrun appearance manual guide welcome styles looks hwcheck boot; do
    [ -e "$INC/usr/share/dagric/$d" ] && cp -r "$INC/usr/share/dagric/$d" "$P/usr/share/dagric/"
done
for f in "$INC/usr/share/dagric/"*.py "$INC/usr/share/dagric/README"; do
    [ -f "$f" ] && cp "$f" "$P/usr/share/dagric/"
done
for f in "$INC/usr/share/applications/"dagric-*.desktop; do
    [ -f "$f" ] && cp "$f" "$P/usr/share/applications/"
done
[ -d "$INC/usr/share/icons/hicolor" ] && cp -r "$INC/usr/share/icons/hicolor/." "$P/usr/share/icons/hicolor/"
# The translations, so an update can also fix a bad string.
[ -d "$INC/usr/share/locale" ] && mkdir -p "$P/usr/share/locale" && \
    cp -r "$INC/usr/share/locale/." "$P/usr/share/locale/"
build_pkg dagric-tools

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
