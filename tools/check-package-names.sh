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

# THE UPGRADE TOOL CARRIES ITS OWN COPY OF THE PRO PACKAGE LIST, AND A SECOND
# COPY OF ANYTHING DRIFTS.
#
# dagric-upgrade-to-pro turns a free machine into a Pro one, and it has to know
# what Pro contains. It embeds the list rather than fetching it, deliberately: a
# machine that cannot reach a list server is exactly the machine that should
# still be able to finish an upgrade somebody has paid for. The cost of that
# choice is this check.
#
# The failure it prevents is quiet and expensive. Add a package to
# pro-apps.list.chroot, ship it on the Pro ISO, and every customer who UPGRADES
# instead of reinstalling silently does not get it — with nothing anywhere
# saying the two paths now disagree about what Pro is.
UPG=config/includes.chroot/usr/bin/dagric-upgrade-to-pro
if [ -r "$UPG" ]; then
    _pro_real=$(cat "$LISTS"/pro-*.list.chroot 2>/dev/null \
                | sed -e 's/#.*//' -e 's/[[:space:]]*$//' | grep -v '^$' | sort -u)
    # The embedded list is one shell string spanning several lines; splitting on
    # whitespace is exactly how the tool itself expands it.
    _pro_tool=$(sed -n '/^PRO_PACKAGES="/,/"$/p' "$UPG" \
                | sed -e 's/^PRO_PACKAGES="//' -e 's/"$//' \
                | tr ' \t' '\n\n' | grep -v '^$' | sort -u)
    # Temp files, not process substitution. <(...) is bash-only and this file is
    # /bin/sh — dash rejects it outright with "Syntax error: "(" unexpected",
    # which would have turned the whole check into a build failure on every run.
    _tl=$(mktemp) || exit 1
    _tt=$(mktemp) || { rm -f "$_tl"; exit 1; }
    printf '%s\n' "$_pro_real" > "$_tl"
    printf '%s\n' "$_pro_tool" > "$_tt"
    _only_list=$(comm -23 "$_tl" "$_tt")
    _only_tool=$(comm -13 "$_tl" "$_tt")
    rm -f "$_tl" "$_tt"
    if [ -n "$_only_list$_only_tool" ]; then
        echo "" >&2
        echo "pkgcheck: the Pro package list and dagric-upgrade-to-pro disagree." >&2
        [ -n "$_only_list" ] && { echo "  on the Pro ISO but NOT installed by an upgrade:" >&2
                                  printf '%s\n' "$_only_list" | sed 's/^/    /' >&2; }
        [ -n "$_only_tool" ] && { echo "  installed by an upgrade but NOT on the Pro ISO:" >&2
                                  printf '%s\n' "$_only_tool" | sed 's/^/    /' >&2; }
        echo "  A customer who upgrades and a customer who reinstalls must end up" >&2
        echo "  with the same machine. Update PRO_PACKAGES in $UPG." >&2
        echo "" >&2
        exit 1
    fi
fi

# THE CHECK BELOW USED TO BE  [ -n "$(apt-cache policy "$p")" ]  AND IT HAD A
# HOLE THE EXACT SHAPE OF THE BUG IT EXISTS TO CATCH.
#
# Its comment claimed policy "prints nothing at all for a name apt cannot
# locate". That is true for a TYPO and false for the case that actually costs a
# build. apt knows every name mentioned anywhere in the archive's dependency
# fields, including names that no longer resolve to a package. For those it
# prints a full record with Candidate: (none) — 67 bytes for signon-ui, which
# the old test read as "not empty, therefore fine".
#
#     $ apt-cache policy signon-ui          $ apt-cache policy no-such-pkg
#     signon-ui:                            (nothing)
#       Installed: (none)
#       Candidate: (none)
#       Version table:
#
# So the check passed signon-ui — the name that aborted the Pro chroot an hour
# in on 2026-08-04 — while correctly catching a name apt had simply never heard
# of. It caught typos and waved through the dangerous case: a package that was
# removed from the archive between releases, which is the one that LOOKS
# plausible and is why nobody checks it by hand.
#
# `apt-get install -s` is used instead because it is not an approximation of
# what live-build does, it is the same operation. It also resolves a virtual
# package with exactly one provider, which a Candidate: (none) test would
# wrongly reject — the reason the original avoided this shape.
#
# One simulated install for the whole set is the fast path, because that is one
# apt invocation rather than ~200. It is only used to decide whether anything is
# wrong at all; when it fails, the per-name loop below finds out which, since a
# combined run can also fail for a reason that is not a bad name (two packages
# that conflict) and that must not be reported as a missing name.
pkg_ok() { apt-get install -s "$1" >/dev/null 2>&1; }

# PROVE THE METHOD BEFORE TRUSTING IT. Today's lesson, written down: three of
# this session's verification attempts produced a confident wrong answer from a
# broken method, and each was caught by a control whose result was known in
# advance. A check that cannot detect its own failure is worse than no check,
# because the build proceeds on its word. If any of these three disagree, the
# environment is not what this script assumes and it must not fail a build.
#   network-manager  real, installable        -> must pass
#   signon-ui        known name, no candidate -> must fail  (the regression)
#   the nonsense one never heard of           -> must fail
if pkg_ok network-manager && ! pkg_ok signon-ui \
   && ! pkg_ok dagric-nonexistent-selftest-name; then
    :
else
    echo "pkgcheck: self-test failed — apt is not behaving as this check" >&2
    echo "  assumes, so its answers cannot be trusted. Skipping rather than" >&2
    echo "  failing the build on a method that is provably broken." >&2
    rm -f /etc/apt/sources.list.d/dagric-pkgcheck.list 2>/dev/null || true
    exit 0
fi

MISSING=""
COUNT=$(printf '%s\n' $NAMES | wc -l)
if ! apt-get install -s $NAMES >/dev/null 2>&1; then
    for p in $NAMES; do
        pkg_ok "$p" || MISSING="$MISSING $p"
    done
    # The set fails but every name resolves on its own: the problem is between
    # two packages, not in this file. Say so precisely instead of printing an
    # empty list of bad names under a heading that says they do not exist.
    if [ -z "$MISSING" ]; then
        echo "" >&2
        echo "pkgcheck: every package name exists, but they cannot be installed" >&2
        echo "  together — apt reports a conflict. Rerun to see it:" >&2
        echo "    apt-get install -s \$(cat $LISTS/*.list.chroot | sed 's/#.*//')" >&2
        echo "" >&2
        rm -f /etc/apt/sources.list.d/dagric-pkgcheck.list 2>/dev/null || true
        exit 1
    fi
fi

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

# A PERCENT SIGN ANYWHERE IN THESE FILES SILENTLY TRUNCATES THE PACKAGE LIST.
#
# live-build's chroot_package-lists feeds each file through printf, so a "%" —
# even inside a comment, even in the middle of a sentence — is read as a format
# specifier. The parser prints "printf: %" to its own log and then DROPS EVERY
# PACKAGE BELOW THAT LINE. Nothing reports a missing package, because as far as
# apt is concerned it was never asked for.
#
# THIS COST A BUILD AND WAS EXPENSIVE TO FIND. A comment block quoting font
# coverage as "0.0%" and "99.6%" swallowed fonts-nanum and
# plasma-browser-integration out of apps.list.chroot, and gawk out of
# system.list.chroot fifty lines further down. The visible symptom was none of
# those: it was 0340-offline-docs.hook.chroot exiting non-zero with no message
# at all, because the hook calls gawk and there was no longer any awk on the
# image. Two hours, and the log line that named the real cause was eleven words
# long and eight thousand lines above the failure.
#
# Checked here rather than in the hook because this is the same family as the
# inline-comment rule above and belongs beside it: both are cases where a file
# that reads perfectly well to a human is parsed as something else.
PCT=$(grep -n '%' config/package-lists/*.list.chroot 2>/dev/null || true)
if [ -n "$PCT" ]; then
    echo "" >&2
    echo "pkgcheck: a percent sign appears in a package list. live-build runs" >&2
    echo "          these through printf, so everything BELOW each of these" >&2
    echo "          lines is silently dropped from the build:" >&2
    echo "$PCT" | sed 's/^/    /' >&2
    echo "" >&2
    echo "  Write the number in words, or drop the sign. Comments count." >&2
    echo "" >&2
    exit 1
fi

echo "pkgcheck: all $COUNT package names resolve, and no list contains a percent sign"
