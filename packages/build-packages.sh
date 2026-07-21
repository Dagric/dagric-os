#!/bin/sh
# Freehold OS — build the freehold-* config packages from the SAME files the
# ISO ships (config/includes.chroot is the single source of truth).
# Runs inside the freehold-builder container with the repo at /src (ro)
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

# ---- freehold-branding -----------------------------------------------------
P=$STAGE/freehold-branding
mkdir -p "$P/usr/share/wallpapers" "$P/usr/share/freehold" "$P/usr/share/sddm/themes/breeze"
cp -r "$SRC/packages/freehold-branding/DEBIAN" "$P/"
cp -r "$INC/usr/share/wallpapers/Freehold"     "$P/usr/share/wallpapers/"
cp -r "$INC/usr/share/freehold/logo"           "$P/usr/share/freehold/"
cp    "$INC/usr/share/sddm/themes/breeze/theme.conf.user" "$P/usr/share/sddm/themes/breeze/"
build_pkg freehold-branding

# ---- freehold-desktop-defaults --------------------------------------------
P=$STAGE/freehold-desktop-defaults
mkdir -p "$P/etc/skel/.config" "$P/usr/lib/firefox-esr/distribution"
cp -r "$SRC/packages/freehold-desktop-defaults/DEBIAN" "$P/"
cp    "$INC/etc/skel/.config/kdeglobals" "$P/etc/skel/.config/"
cp    "$INC/etc/skel/.config/kwinrc"     "$P/etc/skel/.config/"
cp    "$INC/usr/lib/firefox-esr/distribution/policies.json" "$P/usr/lib/firefox-esr/distribution/"
build_pkg freehold-desktop-defaults

# ---- freehold-security-policy ---------------------------------------------
P=$STAGE/freehold-security-policy
mkdir -p "$P/etc/apt/apt.conf.d" "$P/etc/sysctl.d"
cp -r "$SRC/packages/freehold-security-policy/DEBIAN" "$P/"
cp    "$INC/etc/apt/apt.conf.d/01freehold-norecommends" "$P/etc/apt/apt.conf.d/"
cp    "$INC/etc/sysctl.d/99-freehold-hardening.conf"    "$P/etc/sysctl.d/"
build_pkg freehold-security-policy

echo "Built packages:"
ls -la "$OUT"
