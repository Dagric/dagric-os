#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Dagric OS — prove every package name in config/package-lists actually exists,
# before spending twenty minutes finding out that one of them does not.
#
# WHY THIS EXISTS. "kimageformats" was added to desktop.list.chroot. It is the
# upstream KDE project name; the Debian binary package is kimageformat6-plugins.
# live-build got as far as chroot_install-packages, printed
#
#     E: Unable to locate package kimageformats
#
# and destroyed the build — four times, across four commits, because apt stops
# at the FIRST name it cannot find and says nothing about the rest. Every one of
# those runs cost a full bootstrap first. One typo, four dead builds, and no way
# to tell from the failure whether there were five more behind it.
#
# This resolves every name against the real archive in a few seconds and reports
# ALL the bad ones at once, so a list of typos costs one fix instead of one
# build each.
#
# Run from the repository root. Shared by build.sh and docker/container-build.sh
# deliberately: those two scripts have drifted apart before — container-build.sh
# carries a comment about shipping ISOs that build.sh's path did not — and a
# check that lives in only one of them is a check that silently does not apply
# to half the builds.
set -e

LISTS=config/package-lists
[ -d "$LISTS" ] || { echo "pkgcheck: no $LISTS — run me from the repo root" >&2; exit 1; }

if ! command -v apt-cache >/dev/null 2>&1; then
    echo "pkgcheck: apt-cache not installed — skipping the package-name check"
    exit 0
fi

# The archive areas MUST match auto/config's --archive-areas. The builder image
# is debian:trixie, whose stock sources carry main only, so a contrib or
# non-free package would look missing and this check would fail good builds —
# which is worse than the bug it exists to catch.
if [ -w /etc/apt/sources.list.d ]; then
    cat > /etc/apt/sources.list.d/dagric-pkgcheck.list <<'EOF'
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
EOF
else
    echo "pkgcheck: cannot add archive areas (not root?) — contrib/non-free may look missing"
fi

# A stale or empty cache would report every package as missing. If the update
# fails — no network, mirror hiccup — say so and pass, rather than blocking a
# build over something that is not the tree's fault. This check may only ever
# fail the build on evidence it actually has.
if ! apt-get update -qq >/dev/null 2>&1; then
    echo "pkgcheck: apt-get update failed — skipping rather than guessing" >&2
    exit 0
fi

# Full-line comments only: an inline "# foo" would make the whole line a bogus
# package name, which is the rule the list files are written to and the reason
# they carry their comments ABOVE each entry.
NAMES=$(cat "$LISTS"/*.list.chroot | sed -e 's/#.*//' -e 's/[[:space:]]*$//' \
        | grep -v '^$' | sort -u)

MISSING=""
COUNT=0
for p in $NAMES; do
    COUNT=$((COUNT + 1))
    # apt-cache policy prints nothing at all for a name apt cannot locate, and
    # prints a record for a virtual package that something provides — which is
    # exactly the line live-build's `apt-get install` draws.
    [ -n "$(apt-cache policy "$p" 2>/dev/null)" ] || MISSING="$MISSING $p"
done

rm -f /etc/apt/sources.list.d/dagric-pkgcheck.list 2>/dev/null || true

if [ -n "$MISSING" ]; then
    echo "" >&2
    echo "pkgcheck: these package names do not exist in trixie:" >&2
    for p in $MISSING; do echo "    $p" >&2; done
    echo "" >&2
    echo "  Check the DEBIAN BINARY package name, which is often not the" >&2
    echo "  upstream project name — kimageformats is kimageformat6-plugins." >&2
    echo "    https://packages.debian.org/search?suite=trixie&searchon=names" >&2
    echo "" >&2
    exit 1
fi

echo "pkgcheck: all $COUNT package names resolve"
