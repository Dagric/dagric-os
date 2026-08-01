#!/bin/sh
# Dagric OS — build the four dagric-* config packages from config/includes.chroot.
#
#   sh packages/stage-packages.sh <REPO_ROOT> <OUTPUT_DIR>
#
# Nothing here signs anything and nothing here needs the network, because this
# script has TWO callers with very different privileges:
#
#   * packages/build-repo.sh, which publishes the update channel and holds the
#     release key;
#   * build.sh, which drops the .debs into config/packages.chroot so live-build
#     INSTALLS them into the image it is building.
#
# The second caller is the reason this file exists. The four packages used to be
# assembled only by build-repo.sh and only into site/repo, while the files they
# contain reached the ISO through config/includes.chroot — so dpkg on a sold
# machine had no record of dagric-tools, dagric-branding, dagric-desktop-defaults
# or dagric-security-policy at all, and `apt upgrade` could never deliver a fix
# to any of them. The channel was live, signed and reachable, and no machine was
# subscribed to a single package in it. Building the same .debs during the image
# build and letting live-build install them is what registers them with dpkg.
#
# ORDERING, WHICH IS WHAT MAKES THIS SAFE. live-build runs, in this order:
#     chroot_archives          (a local file: repo made from config/packages.chroot)
#     chroot_install-packages  (apt installs everything, ours included)
#     chroot_includes_after_packages   (config/includes.chroot copied over the top)
#     chroot_hooks             (0100..0995)
# So config/includes.chroot is still the single source of truth for the image's
# contents — a package file can never mask a newer file from the tree, because
# the tree is copied in afterwards. The packages exist to be RECORDED, and the
# .debs are built from that same tree microseconds earlier, so the two agree by
# construction rather than by anyone remembering to re-publish.
#
# THE VERSION IN DEBIAN/control MUST ALWAYS LEAD WHAT THE CHANNEL PUBLISHES,
# AND THE BUILD BREAKS IF IT DOES NOT. This is not a release-hygiene nicety.
#
# The image ships /etc/apt/sources.list.d/dagric.list through includes.chroot, so
# the live update channel is a visible apt source INSIDE the build chroot. After
# the hooks run, live-build's binary pass (chroot_archives binary install) does
# one more `apt-get upgrade -y`, and at that moment apt can see two packages
# called dagric-tools: the one just installed from config/packages.chroot, and
# the one on https://dagric-os.web.app/repo. live-build pins its local file:
# repo at 1001, and a pin above 1000 is precisely the setting that authorises a
# DOWNGRADE — so when the two carry the SAME version string but different bytes,
# apt resolves the tie by swapping one for the other and calls it a downgrade:
#
#     The following packages will be DOWNGRADED:
#       dagric-branding dagric-desktop-defaults dagric-security-policy dagric-tools
#     E: Packages were downgraded and -y was used without --allow-downgrades.
#     E: An unexpected failure occurred, exiting...
#
# live-build then unwinds and the run ends with "no ISO produced" — a build that
# got as far as a fully populated chroot and produced nothing.
#
# Same-version-different-bytes is the normal state here, not an accident: a free
# build stages a dagric-tools assembled after the edition gating, so it can never
# be byte-identical to a published package built from the whole tree. The version
# is therefore the only thing that can break the tie, and it has to break it in
# our favour. Bump these four whenever the tree changes what they contain; the
# 1.1.0 -> 1.1.1 bump was made because the packages had already diverged from the
# published 1.1.0 (all 34 wallpaper packs instead of one, a conffiles entry, and
# corrected file modes) while still claiming to be it.
set -e

REPO=${1:?usage: stage-packages.sh REPO_ROOT OUTPUT_DIR}
OUT=${2:?usage: stage-packages.sh REPO_ROOT OUTPUT_DIR}
INC=$REPO/config/includes.chroot
STAGE=${DAGRIC_PKG_STAGE:-/srv/pkgstage}

command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb required" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE" "$OUT"

# Normalise permissions before packing.
#
# The published .debs carried 0755 on theme.conf, metadata.json, Main.qml,
# mimeapps.list and the three /etc/skel Plasma configs — so an update made an
# owner's kdeglobals executable. That is the Windows checkout leaking through:
# this tree is routinely a drvfs mount where every file reads back as 0755, and
# the old build chmodded only usr/bin. 0995-file-modes fixes modes INSIDE the
# image and never saw this staging tree at all. Data is 0644, directories are
# 0755, and the executables are put back by name afterwards.
normalise_modes() {
    find "$1" -type d -exec chmod 0755 {} +
    find "$1" -type f -exec chmod 0644 {} +
}

build_pkg() {
    name=$1
    root="$STAGE/$name"
    version=$(sed -n 's/^Version: //p' "$root/DEBIAN/control")
    [ -n "$version" ] || { echo "$name: no Version in DEBIAN/control" >&2; exit 1; }

    # DEBIAN/ itself must not be 0644'd into unreadability, and maintainer
    # scripts must stay executable. There are none today; the loop is here so
    # that adding one does not silently ship a package that cannot configure.
    chmod 0755 "$root/DEBIAN"
    for s in preinst postinst prerm postrm; do
        [ -f "$root/DEBIAN/$s" ] && chmod 0755 "$root/DEBIAN/$s"
    done

    # Every path in conffiles must actually be in the package. dpkg fails the
    # INSTALL, not the build, when it is not — i.e. on the owner's machine.
    if [ -f "$root/DEBIAN/conffiles" ]; then
        while IFS= read -r c; do
            [ -n "$c" ] || continue
            [ -f "$root$c" ] || {
                echo "$name: conffiles lists $c, which is not in the package" >&2
                exit 1
            }
        done < "$root/DEBIAN/conffiles"
    fi

    dpkg-deb --build --root-owner-group "$root" "$OUT/${name}_${version}_all.deb" >/dev/null
    printf '  %-26s %s\n' "$name" "$version"
}

# ---- dagric-branding: what the machine LOOKS like -------------------------
P=$STAGE/dagric-branding
mkdir -p "$P/usr/share/wallpapers" "$P/usr/share/dagric" "$P/usr/share/sddm/themes"
cp -r "$REPO/packages/dagric-branding/DEBIAN" "$P/"
# EVERY wallpaper pack, not just the one called "Dagric".
#
# This was `cp -r "$INC/usr/share/wallpapers/Dagric"` — an exact directory name
# — so of the 34 packs the tree ships, dagric-branding contained exactly one.
# The package's own description promises that "updating this package updates the
# look of every installed machine", and the first-run wizard builds its wallpaper
# grid from all 34, so a corrected or added pack could never reach a sold
# machine. The glob is the fix; the count assertion below is what stops it
# silently going back to one.
for d in "$INC"/usr/share/wallpapers/Dagric*; do
    [ -d "$d" ] || continue
    cp -r "$d" "$P/usr/share/wallpapers/"
done
have=$(ls -1d "$P"/usr/share/wallpapers/*/ 2>/dev/null | wc -l)
want=$(ls -1d "$INC"/usr/share/wallpapers/Dagric*/ 2>/dev/null | wc -l)
[ "$have" = "$want" ] || {
    echo "dagric-branding: packed $have wallpaper packs, the tree has $want" >&2
    exit 1
}
cp -r "$INC/usr/share/dagric/logo"        "$P/usr/share/dagric/"
[ -d "$INC/usr/share/dagric/sddm" ]   && cp -r "$INC/usr/share/dagric/sddm"   "$P/usr/share/dagric/"
[ -d "$INC/usr/share/dagric/splash" ] && cp -r "$INC/usr/share/dagric/splash" "$P/usr/share/dagric/"
[ -d "$INC/usr/share/sddm/themes" ]   && cp -r "$INC/usr/share/sddm/themes/." "$P/usr/share/sddm/themes/"
# The Plasma startup screen (ksplash look-and-feel package). Branding, so it
# travels with the wallpapers and the SDDM theme: a splash fix must be able to
# reach sold machines the same way a wallpaper fix can.
if [ -d "$INC/usr/share/plasma/look-and-feel" ]; then
    mkdir -p "$P/usr/share/plasma"
    cp -r "$INC/usr/share/plasma/look-and-feel" "$P/usr/share/plasma/"
fi
normalise_modes "$P"
build_pkg dagric-branding

# ---- dagric-desktop-defaults ---------------------------------------------
P=$STAGE/dagric-desktop-defaults
mkdir -p "$P/etc/skel/.config" "$P/usr/lib/firefox-esr/distribution" "$P/etc/xdg"
cp -r "$REPO/packages/dagric-desktop-defaults/DEBIAN" "$P/"
# kglobalshortcutsrc and kaccessrc were missing from this list, which meant
# the Ctrl+Shift+Esc Task Manager key and the Meta+Alt+S screen-reader key
# could never be fixed on a sold machine — the update channel carried the
# other skel files around them. (skel only reaches users created after the
# update; that is a known limit of skel-borne defaults, not a reason to leave
# the files out.)
for f in kdeglobals kwinrc kcminputrc kglobalshortcutsrc kaccessrc; do
    [ -f "$INC/etc/skel/.config/$f" ] && cp "$INC/etc/skel/.config/$f" "$P/etc/skel/.config/"
done
cp "$INC/usr/lib/firefox-esr/distribution/policies.json" "$P/usr/lib/firefox-esr/distribution/"
# The default-browser declaration. Pro shipped Chromium as the default for
# every link because nothing declared one; that fix has to reach sold machines.
# klipperrc (clipboard-history defaults) and ksplashrc (the Dagric startup
# screen selection) ride beside it: /etc/xdg is system-level, so unlike skel
# these reach EXISTING users on upgrade — any owner who has not overridden
# them in their own ~/.config gets the fix at next login.
for f in mimeapps.list klipperrc ksplashrc; do
    [ -f "$INC/etc/xdg/$f" ] && cp "$INC/etc/xdg/$f" "$P/etc/xdg/"
done
normalise_modes "$P"
build_pkg dagric-desktop-defaults

# ---- dagric-security-policy ----------------------------------------------
P=$STAGE/dagric-security-policy
mkdir -p "$P/etc/apt/apt.conf.d" "$P/etc/sysctl.d"
cp -r "$REPO/packages/dagric-security-policy/DEBIAN" "$P/"
cp "$INC/etc/apt/apt.conf.d/01dagric-norecommends" "$P/etc/apt/apt.conf.d/"
cp "$INC/etc/sysctl.d/99-dagric-hardening.conf"    "$P/etc/sysctl.d/"
normalise_modes "$P"
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
[ -d "$INC/usr/lib/dagric" ] && cp -r "$INC/usr/lib/dagric/." "$P/usr/lib/dagric/"
for d in firstrun appearance manual guide welcome styles looks hwcheck boot; do
    [ -e "$INC/usr/share/dagric/$d" ] && cp -r "$INC/usr/share/dagric/$d" "$P/usr/share/dagric/"
done
for f in "$INC/usr/share/dagric/"*.py "$INC/usr/share/dagric/README"; do
    [ -f "$f" ] && cp "$f" "$P/usr/share/dagric/"
done
# The Pro-only launcher entries travel WITH the package, deliberately. One file
# list serves both editions, and dropping them here would make a Pro machine
# lose its Pro launchers on the first upgrade (dpkg removes what a new version
# no longer owns). The gate is applied on the machine instead: dagric-app-names
# deletes X-Dagric-Edition=pro entries whenever /etc/dagric-edition is not "pro",
# and /etc/apt/apt.conf.d/99dagric-app-names runs it after every dpkg operation
# — so a free owner never sees them, including immediately after an update.
for f in "$INC/usr/share/applications/"dagric-*.desktop; do
    [ -f "$f" ] && cp "$f" "$P/usr/share/applications/"
done
[ -d "$INC/usr/share/icons/hicolor" ] && cp -r "$INC/usr/share/icons/hicolor/." "$P/usr/share/icons/hicolor/"
# The translations, so an update can also fix a bad string.
[ -d "$INC/usr/share/locale" ] && mkdir -p "$P/usr/share/locale" && \
    cp -r "$INC/usr/share/locale/." "$P/usr/share/locale/"
normalise_modes "$P"
# The tools are the one thing in these four packages that has to be runnable.
chmod 0755 "$P/usr/bin/"* 2>/dev/null || true
find "$P/usr/lib/dagric" -name '*.sh' -exec chmod 0755 {} + 2>/dev/null || true
build_pkg dagric-tools
