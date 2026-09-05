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

    # AND THE OTHER DIRECTION, which is the one that actually bit.
    #
    # The check above only proves conffiles doesn't name a file that is missing.
    # It says nothing about a file under /etc that is packed WITHOUT a conffiles
    # entry — and dpkg treats such a file as an ordinary package file, replacing
    # it unconditionally on every upgrade: no prompt, no .dpkg-old, no trace.
    # An owner who set Engine=none in /etc/xdg/ksplashrc to kill the splash, or
    # who edited a shortcut, would silently get their change reverted by an
    # update they did not connect to it.
    #
    # It happened because four files (kglobalshortcutsrc, kaccessrc, klipperrc,
    # ksplashrc) were added to the copy loops without extending conffiles. That
    # is a mistake a person makes every time; this makes the BUILD refuse it, so
    # the next file added to /etc cannot repeat it.
    if [ -d "$root/etc" ]; then
        find "$root/etc" -type f | while IFS= read -r f; do
            rel=${f#"$root"}
            if ! grep -qxF "$rel" "$root/DEBIAN/conffiles" 2>/dev/null; then
                echo "$name: $rel is packed under /etc but is not in DEBIAN/conffiles." >&2
                echo "  dpkg would overwrite the owner's edits to it on every upgrade." >&2
                echo "  Add it to packages/$name/DEBIAN/conffiles." >&2
                exit 1
            fi
        done || exit 1
    fi

    # Debian Policy 12.5: "Every package must be accompanied by a verbatim copy
    # of its copyright information and distribution license in the file
    # /usr/share/doc/<package>/copyright." None of these four had one, and they
    # are not incidental packages — they are installed on the ISO and pushed to
    # sold machines through the paid update channel, so site/licenses.html's
    # promise that every licence text is on disk under /usr/share/doc held for
    # every package on the machine EXCEPT the Dagric layer itself.
    #
    # Written here rather than as four checked-in files so it cannot drift out
    # of sync between the packages. normalise_modes has already run, so every
    # directory this creates is chmodded by hand afterwards rather than being
    # left on the build container's umask.
    mkdir -p "$root/usr/share/doc/$name"
    cat > "$root/usr/share/doc/$name/copyright" << 'COPYRIGHT'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Dagric OS
Source: https://dagric.com/licenses

Files: *
Copyright: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
License: GPL-3.0-or-later

Files: usr/share/wallpapers/*
       usr/share/dagric/logo/*
       usr/share/dagric/sddm/*
       usr/share/dagric/splash/*
Copyright: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
License: CC-BY-SA-4.0

License: GPL-3.0-or-later
 This program is free software: you can redistribute it and/or modify it under
 the terms of the GNU General Public License as published by the Free Software
 Foundation, either version 3 of the License, or (at your option) any later
 version.
 .
 This program is distributed in the hope that it will be useful, but WITHOUT ANY
 WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 PARTICULAR PURPOSE.  See the GNU General Public License for more details.
 .
 On Debian systems the complete text of the GNU General Public License version 3
 is in /usr/share/common-licenses/GPL-3.

License: CC-BY-SA-4.0
 Creative Commons Attribution-ShareAlike 4.0 International. The complete text is
 at https://creativecommons.org/licenses/by-sa/4.0/legalcode
 .
 Trade marks are not licensed by the above: the Dagric name, the D monogram and
 the Dagric logo are marks of IMPRESSIONSDIRECT360 LLC. See https://dagric.com/licenses.
COPYRIGHT
    chmod 0755 "$root/usr" "$root/usr/share" "$root/usr/share/doc" \
               "$root/usr/share/doc/$name"
    chmod 0644 "$root/usr/share/doc/$name/copyright"

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
# THE .ts SOURCES MUST NOT BE PACKED. 0995-file-modes deletes them from the
# image (they are Qt translation SOURCES; only the compiled .qm is read at
# runtime), so packing them makes dpkg own five paths that are not on disk and
# `dpkg -V dagric-branding` reports them modified on every machine. That is the
# same defect as the Windows __pycache__ junk removed from dagric-tools in this
# same release, arriving through the same wholesale directory copy.
find "$P/usr/share/sddm/themes" -name '*.ts' -delete 2>/dev/null || true
if find "$P/usr/share/sddm/themes" -name '*.ts' | grep -q .; then
    echo "dagric-branding: .ts translation sources survived the strip" >&2
    exit 1
fi
# ...and the .qm must NOT have been caught by that. They are the runtime
# catalogues; without them the login screen is English in five languages.
_qm=$(find "$P/usr/share/sddm/themes" -name '*.qm' | wc -l)
[ "$_qm" -ge 5 ] || {
    echo "dagric-branding: only $_qm compiled login-screen catalogues packed (want 5)" >&2
    exit 1
}
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
mkdir -p "$P/etc/skel/.config" "$P/etc/xdg" \
         "$P/usr/share/color-schemes"
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
# Firefox ESR is intentionally redistributed exactly as Debian packages it.
# Do not add a distribution/policies.json here: changing defaults, first-run
# content, or extensions changes the Mozilla trademark-distribution posture.
# The default-browser declaration. Pro shipped Chromium as the default for
# every link because nothing declared one; that fix has to reach sold machines.
# klipperrc (clipboard-history defaults) and ksplashrc (the Dagric startup
# screen selection) ride beside it: /etc/xdg is system-level, so unlike skel
# these reach EXISTING users on upgrade — any owner who has not overridden
# them in their own ~/.config gets the fix at next login.
for f in mimeapps.list klipperrc ksplashrc konsolerc kdeglobals kicker-extra-favoritesrc; do
    [ -f "$INC/etc/xdg/$f" ] && cp "$INC/etc/xdg/$f" "$P/etc/xdg/"
done
# The Konsole profile and colour scheme travel with the rc that selects them —
# shipping the pointer without its target would leave every sold machine
# pointing DefaultProfile at a file that is not there.
if [ -d "$INC/usr/share/konsole" ]; then
    mkdir -p "$P/usr/share/konsole"
    cp "$INC/usr/share/konsole/"* "$P/usr/share/konsole/"
fi
# The colour scheme named by kdeglobals has to travel with that pointer. These
# files previously reached a fresh ISO through includes.chroot but belonged to
# no Dagric package, so the update channel could not deliver a contrast fix to
# an installed machine. Keep all three together: Light/Dark are the defaults and
# High Contrast is the escape hatch exposed by Dagric Appearance.
cp "$INC/usr/share/color-schemes/"Dagric*.colors "$P/usr/share/color-schemes/"
_schemes=$(find "$P/usr/share/color-schemes" -maxdepth 1 -name 'Dagric*.colors' -type f | wc -l)
[ "$_schemes" -eq 3 ] || {
    echo "dagric-desktop-defaults: packed $_schemes Dagric colour schemes (want 3)" >&2
    exit 1
}
normalise_modes "$P"
build_pkg dagric-desktop-defaults

# ---- dagric-security-policy ----------------------------------------------
P=$STAGE/dagric-security-policy
mkdir -p "$P/etc/apt/apt.conf.d" "$P/etc/sysctl.d"
cp -r "$REPO/packages/dagric-security-policy/DEBIAN" "$P/"
cp "$INC/etc/apt/apt.conf.d/01dagric-norecommends" "$P/etc/apt/apt.conf.d/"
cp "$INC/etc/sysctl.d/99-dagric-hardening.conf"    "$P/etc/sysctl.d/"
# THE TWO APT POLICIES THAT WERE OWNED BY NOTHING.
#
# 52dagric-unattended decides whether the machine installs its own security
# updates, and 99dagric-app-names is the hook that re-applies the free/Pro gate
# after every dpkg operation — the only thing keeping Pro launcher entries off a
# free machine once the channel starts delivering. Both reached the image
# through includes.chroot alone, so neither could ever be corrected on a machine
# already sold: a mistake in the update policy was unfixable BY an update, and
# if the gate hook was ever lost the Pro entries would quietly return on the
# next dagric-tools upgrade.
#
# They belong in the security package rather than dagric-tools because they are
# policy, and because dagric-tools is deliberately NOT in the automatic-install
# origin — a fix to the enforcement of the edition gate should not wait for
# somebody to click Update.
cp "$INC/etc/apt/apt.conf.d/52dagric-unattended"   "$P/etc/apt/apt.conf.d/"
cp "$INC/etc/apt/apt.conf.d/99dagric-app-names"    "$P/etc/apt/apt.conf.d/"
normalise_modes "$P"
build_pkg dagric-security-policy

# ---- dagric-tools: the product itself -------------------------------------
# Nothing here overlaps dagric-branding. Two packages shipping the same path is
# a dpkg unpack error, not a warning, so logo/ sddm/ and splash/ belong to
# branding and are excluded from this list rather than being copied twice.
P=$STAGE/dagric-tools
mkdir -p "$P/usr/bin" "$P/usr/sbin" "$P/usr/lib/dagric" "$P/usr/share/dagric" \
         "$P/usr/share/applications" "$P/usr/share/icons/hicolor" \
         "$P/usr/share/polkit-1/actions" "$P/etc/xdg/autostart" \
         "$P/etc/systemd/system"
cp -r "$REPO/packages/dagric-tools/DEBIAN" "$P/"
# THE AUTOSTART ENTRY TRAVELS WITH THE PROGRAM IT STARTS.
#
# dagric-restart-check — the one quiet notice that a security update needs a
# restart — was packed as a program with nothing to invoke it: its .desktop went
# into no package at all, so the channel delivered a script that never ran. The
# feature then existed only on machines installed from a new ISO, which is the
# exact opposite of the installed base its own header says it exists for ("a
# Dagric machine could run a kernel with a known, already-patched hole for
# months"). Same rule as the Konsole profile and the family window: never ship
# the pointer without its target, or the target without its pointer.
cp "$INC/etc/xdg/autostart/dagric-restart-check.desktop" "$P/etc/xdg/autostart/"
for f in "$INC/usr/bin/"dagric-*; do
    [ -f "$f" ] && cp "$f" "$P/usr/bin/"
done
# Own only the boundary wrapper; preinst diverts the vendor UI and dpkg keeps
# delivering upstream updates to the diversion target. No vendor code is copied.
cp "$INC/usr/bin/opensnitch-ui" "$P/usr/bin/"
mkdir -p "$P/usr/lib/tmpfiles.d" "$P/etc/systemd/system/opensnitch.service.d"
cp "$INC/usr/lib/tmpfiles.d/dagric-opensnitch.conf" "$P/usr/lib/tmpfiles.d/"
cp "$INC/etc/systemd/system/opensnitch.service.d/"*.conf "$P/etc/systemd/system/opensnitch.service.d/"
mkdir -p "$P/usr/lib/systemd/system/opensnitch.service.d"
cp "$INC/usr/lib/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf" "$P/usr/lib/systemd/system/opensnitch.service.d/"
[ -f "$INC/usr/sbin/dagric-pipeline" ] && cp "$INC/usr/sbin/dagric-pipeline" "$P/usr/sbin/"
[ -f "$INC/etc/systemd/system/dagric-pipeline.service" ] && \
    cp "$INC/etc/systemd/system/dagric-pipeline.service" "$P/etc/systemd/system/"
[ -f "$INC/etc/systemd/system/dagric-pipeline.timer" ] && \
    cp "$INC/etc/systemd/system/dagric-pipeline.timer" "$P/etc/systemd/system/"
[ -f "$INC/etc/systemd/system/dagric-blackbox.service" ] && \
    cp "$INC/etc/systemd/system/dagric-blackbox.service" "$P/etc/systemd/system/"
[ -f "$INC/etc/systemd/system/dagric-blackbox.timer" ] && \
    cp "$INC/etc/systemd/system/dagric-blackbox.timer" "$P/etc/systemd/system/"
[ -d "$INC/usr/lib/dagric" ] && cp -r "$INC/usr/lib/dagric/." "$P/usr/lib/dagric/"
# Untracked checkout junk must not become dpkg-owned. The Windows checkout this
# tree is edited on compiles boot-find-splash-rule to __pycache__/*.pyc (for two
# CPython versions, with drvfs-mangled names), .gitignore hides them, and the
# wholesale copy above packed them: the shipped ISOs have dpkg owning two .pyc
# paths that nothing put on disk, so `dpkg -V dagric-tools` reports missing
# files on every sold machine, and the next upgrade would install Windows-built
# bytecode onto customers' machines. Bytecode is regenerated on demand anyway.
rm -rf "$P/usr/lib/dagric/__pycache__"
find "$P/usr/lib/dagric" -name '*.pyc' -delete 2>/dev/null || true
# 'family' was missing from this list, which is the whole reason Family Limits
# could not be delivered or repaired through the channel: /usr/bin/dagric-family
# and the Hub row that launches it were packed by the loops above, while
# /usr/share/dagric/family/main.qml — the window itself — was not. The rule this
# broke is the one stated for the Konsole profile above: never ship the pointer
# without its target.
for d in firstrun appearance manual guide welcome styles looks icon-styles hwcheck boot family rewind budgets; do
    [ -e "$INC/usr/share/dagric/$d" ] && cp -r "$INC/usr/share/dagric/$d" "$P/usr/share/dagric/"
done
# Fail rather than ship a dagric-family with no window, the same way the
# wallpaper count above refuses a one-pack branding package.
[ -f "$P/usr/bin/dagric-family" ] && [ ! -f "$P/usr/share/dagric/family/main.qml" ] && {
    echo "dagric-tools: packs /usr/bin/dagric-family but not its window" >&2
    echo "  (usr/share/dagric/family/main.qml). Every machine that took this" >&2
    echo "  update would get a menu entry that cannot open." >&2
    exit 1
}
[ -f "$P/usr/bin/dagric-rewind" ] && [ ! -f "$P/usr/share/dagric/rewind/main.qml" ] && {
    echo "dagric-tools: packs /usr/bin/dagric-rewind but not its window" >&2
    echo "  (usr/share/dagric/rewind/main.qml). Refusing a broken update." >&2
    exit 1
}

# THE PAID APPEARANCE DROP-INS DO NOT TRAVEL IN THIS PACKAGE.
#
# The loop above copies share/dagric/looks and share/dagric/styles wholesale,
# and four of those layouts and three of those styles carry EDITION=pro. That
# put them in the deb on the PUBLIC update channel, where anyone could fetch
# dagric-tools with plain curl and unpack the entire paid appearance set without
# buying anything — the exact payload infra/gate-worker.js exists to sell, given
# away by the channel. build.sh states the principle this violated: the Pro
# drop-ins are DELETED from a free image rather than flagged, "otherwise a free
# user could unlock the Pro layouts and styles by deleting one line of text".
# A package published to the world is a stronger version of that same hole.
#
# Selected by the same grep build.sh and tools/build-pro-assets.sh use, so this
# cannot drift from the edition split when a Pro layout is added.
#
# The thumbnails go too. They live under appearance/thumbs, which the loop packs
# as a whole, and a preview of a layout the package no longer carries is both a
# leak of the artwork and a gallery tile for something that cannot be applied.
#
# WHAT KEEPS A PAYING CUSTOMER'S LAYOUTS: dpkg deletes the files a new version
# no longer owns, so this change alone would strip the paid set from a Pro
# machine on its first upgrade. packages/dagric-tools/DEBIAN/preinst stashes
# them and postinst puts them back, using the machine's own copy — no network,
# no payload in the package. On free machines the stash is empty because the
# files are not there to begin with, so nothing is restored and the gate holds.
for _pro in $(grep -rlx 'EDITION=pro' "$P/usr/share/dagric/looks" \
    "$P/usr/share/dagric/styles" 2>/dev/null); do
    _base=${_pro##*/}
    rm -f "$_pro" "$P/usr/share/dagric/appearance/thumbs/${_base%.*}.png"
done
unset _pro _base
# The free edition's own drop-ins must survive this, or the package ships an
# empty gallery to everyone.
_free_looks=$(ls -1 "$P/usr/share/dagric/looks/"*.look 2>/dev/null | wc -l)
[ "$_free_looks" -ge 3 ] || {
    echo "dagric-tools: only $_free_looks layouts left after the Pro strip." >&2
    echo "  Expected the free set (classic, eleven, focus). Either the strip" >&2
    echo "  is matching too much or the tree was already stripped." >&2
    exit 1
}
unset _free_looks
grep -rlx 'EDITION=pro' "$P/usr/share/dagric" >/dev/null 2>&1 && {
    echo "dagric-tools: an EDITION=pro drop-in survived the strip." >&2
    exit 1
}
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
for f in "$INC/usr/share/polkit-1/actions/"*.policy; do
    [ -f "$f" ] && cp "$f" "$P/usr/share/polkit-1/actions/"
done
[ -d "$INC/usr/share/icons/hicolor" ] && cp -r "$INC/usr/share/icons/hicolor/." "$P/usr/share/icons/hicolor/"
# Selectable Dagric icon families. Each carries only Dagric-owned application
# icons and inherits Breeze/hicolor for third-party programs, so an update does
# not overwrite or redraw another project's official mark.
for _theme in "$INC/usr/share/icons/"Dagric*; do
    [ -d "$_theme" ] || continue
    cp -r "$_theme" "$P/usr/share/icons/"
done
_icon_themes=$(find "$P/usr/share/icons" -mindepth 1 -maxdepth 1 -type d -name 'Dagric*' | wc -l)
[ "$_icon_themes" -eq 3 ] || {
    echo "dagric-tools: packed $_icon_themes selectable icon themes (want 3)." >&2
    exit 1
}
unset _theme _icon_themes
# The translations, so an update can also fix a bad string.
[ -d "$INC/usr/share/locale" ] && mkdir -p "$P/usr/share/locale" && \
    cp -r "$INC/usr/share/locale/." "$P/usr/share/locale/"
normalise_modes "$P"
# The tools are the one thing in these four packages that has to be runnable.
chmod 0755 "$P/usr/bin/"* 2>/dev/null || true
chmod 0755 "$P/usr/sbin/dagric-pipeline" 2>/dev/null || true

# EXECUTABLE BY SHEBANG, NOT BY FILE EXTENSION — and the old rule was exactly
# inverted, which is why this is worth the paragraph.
#
# It was `find "$P/usr/lib/dagric" -name '*.sh' -exec chmod 0755`. There is
# precisely one *.sh file in that directory, display-common.sh, and it is a
# SOURCED library — the single file there that must NOT be executable. The three
# that are actually run — display-autoscale, desktop-shortcut-trust,
# boot-find-splash-rule — carry no extension, so the glob never matched any of
# them. normalise_modes has just set every file 0644, so they stayed 0644.
#
# The ISO never showed it. build.sh chmods includes.chroot/usr/lib/dagric/*, and
# hooks 0500 and 0520 chmod their targets inside the chroot, so a freshly
# installed machine is correct. It breaks on the first UPDATE: dpkg applies the
# archive's recorded modes, so the moment a sold machine takes a dagric-tools
# update through the paid channel, display-autoscale and desktop-shortcut-trust
# arrive 0644 and stop running. Silently — a .desktop whose Exec is not
# executable produces no error anywhere, the features just quietly cease. An
# update channel that disables features is worse than no update channel.
#
# Keyed on the shebang because that is the property that actually decides it,
# and because it stays right on its own: any new program dropped in here is
# covered the day it is added, and a new sourced library is correctly left
# alone. Today it gives 0755 to the three with #! and leaves display-common.sh
# at 0644, which is exactly the inverse of what shipped.
for _f in "$P/usr/lib/dagric/"*; do
    [ -f "$_f" ] || continue
    _first=""
    read -r _first < "$_f" 2>/dev/null || _first=""
    case "$_first" in
        '#!'*) chmod 0755 "$_f" ;;
    esac
done
unset _f _first
build_pkg dagric-tools
