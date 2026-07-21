#!/bin/sh
# Dagric OS — build the dagric-* config packages from the SAME files the
# ISO ships (config/includes.chroot is the single source of truth).
# Runs inside the dagric-builder container with the repo at /src (ro)
# and an output dir at /out.
set -e

SRC=/src
INC=$SRC/config/includes.chroot
OUT=/out/repo/pool
STAGE=/tmp/pkgstage
rm -rf "$STAGE"
mkdir -p "$OUT"

build_pkg() {
    name=$1
    root="$STAGE/$name"
    version=$(sed -n 's/^Version: //p' "$root/DEBIAN/control")
    dpkg-deb --build --root-owner-group "$root" "$OUT/${name}_${version}_all.deb"
}

# ---- dagric-branding -----------------------------------------------------
P=$STAGE/dagric-branding
mkdir -p "$P/usr/share/wallpapers" "$P/usr/share/dagric" "$P/usr/share/sddm/themes/breeze"
cp -r "$SRC/packages/dagric-branding/DEBIAN" "$P/"
cp -r "$INC/usr/share/wallpapers/Dagric"     "$P/usr/share/wallpapers/"
cp -r "$INC/usr/share/dagric/logo"           "$P/usr/share/dagric/"
cp    "$INC/usr/share/sddm/themes/breeze/theme.conf.user" "$P/usr/share/sddm/themes/breeze/"
build_pkg dagric-branding

# ---- dagric-desktop-defaults --------------------------------------------
P=$STAGE/dagric-desktop-defaults
mkdir -p "$P/etc/skel/.config" "$P/usr/lib/firefox-esr/distribution"
cp -r "$SRC/packages/dagric-desktop-defaults/DEBIAN" "$P/"
cp    "$INC/etc/skel/.config/kdeglobals" "$P/etc/skel/.config/"
cp    "$INC/etc/skel/.config/kwinrc"     "$P/etc/skel/.config/"
cp    "$INC/usr/lib/firefox-esr/distribution/policies.json" "$P/usr/lib/firefox-esr/distribution/"
build_pkg dagric-desktop-defaults

# ---- dagric-security-policy ---------------------------------------------
P=$STAGE/dagric-security-policy
mkdir -p "$P/etc/apt/apt.conf.d" "$P/etc/sysctl.d"
cp -r "$SRC/packages/dagric-security-policy/DEBIAN" "$P/"
cp    "$INC/etc/apt/apt.conf.d/01dagric-norecommends" "$P/etc/apt/apt.conf.d/"
cp    "$INC/etc/sysctl.d/99-dagric-hardening.conf"    "$P/etc/sysctl.d/"
build_pkg dagric-security-policy

echo "Built packages:"
ls -la "$OUT"
