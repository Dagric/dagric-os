#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — compile po/*.po into the .mo catalogues the image ships.
#
#     sh tools/i18n-build.sh            compile
#     sh tools/i18n-build.sh --check    verify only, change nothing
#
# Output:  config/includes.chroot/usr/share/locale/<lang>/LC_MESSAGES/dagric.mo
#
# WHY THE .mo FILES ARE COMMITTED, RATHER THAN BUILT BY A HOOK
# ------------------------------------------------------------
# msgfmt is in the `gettext` package, which is a BUILD-HOST tool and is not on
# the image (only gettext-base is, and correctly so — 2 MB of .po tooling has
# no business on a desktop ISO). A chroot hook would therefore have to
# apt-install gettext, compile, and uninstall it again inside every build:
# slower, and it puts a network dependency in the middle of the image build for
# a file that is 20 KB of static data.
#
# So this runs on the developer's machine and its output is committed under
# config/includes.chroot, exactly like the wallpapers and the manual. A build
# with no gettext installed anywhere still ships working translations, because
# live-build copies includes.chroot verbatim. The cost is that whoever changes
# an English string has to re-run this — which is what --check, wired into
# 0150-locales.hook.chroot, is there to catch.
#
# A .po that msgfmt rejects fails the build. That is deliberate: `msgfmt -c`
# catches a msgstr whose format specifiers or plural count do not match the
# msgid, and shipping a catalogue that crashes a tool is worse than shipping
# English.
set -e
cd "$(dirname "$0")/.."

LOCALEDIR=config/includes.chroot/usr/share/locale
DOMAIN=dagric
MODE=${1:-build}

case "$MODE" in
    --check|build) ;;
    *) echo "usage: $0 [--check]" >&2; exit 2 ;;
esac

command -v msgfmt >/dev/null 2>&1 || {
    echo "msgfmt is required: apt install gettext" >&2; exit 1; }

fail=0
count=0
TMP=$(mktemp) || exit 1
trap 'rm -f "$TMP"' EXIT INT TERM

for po in po/*.po; do
    [ -f "$po" ] || continue
    lang=${po##*/}
    lang=${lang%.po}
    mo=$LOCALEDIR/$lang/LC_MESSAGES/$DOMAIN.mo

    if [ "$MODE" = --check ]; then
        # Compare CONTENT, not timestamps. An mtime test is the obvious way to
        # write this and it is wrong here: the working tree is routinely a
        # Windows drvfs mount whose timestamps round to the second, so a .po and
        # the .mo built from it seconds apart compare as "source is newer" and
        # the check cries wolf on a tree that is perfectly in sync.
        # msgfmt output is deterministic — a .mo carries no build timestamp —
        # so recompiling and comparing bytes is both exact and portable.
        if [ ! -s "$mo" ]; then
            echo "ERROR: $mo is missing or empty — run: sh tools/i18n-build.sh" >&2
            fail=1
        elif ! msgfmt -c -o "$TMP" "$po" 2>/dev/null || ! cmp -s "$TMP" "$mo"; then
            echo "ERROR: $mo does not match $po — run: sh tools/i18n-build.sh" >&2
            fail=1
        else
            count=$((count + 1))
        fi
        continue
    fi

    mkdir -p "$LOCALEDIR/$lang/LC_MESSAGES"
    # -c is the gate. Without it a msgstr with a broken plural rule or a
    # mismatched format specifier compiles happily and misbehaves at runtime,
    # in a language nobody here reads.
    #
    # NOT --use-fuzzy, ever: a message marked "#, fuzzy" is a machine or
    # half-finished translation that has not been checked, and msgfmt's default
    # of dropping it means the owner sees the English source instead. That
    # fallback is the whole safety net.
    if msgfmt -c -o "$mo" "$po"; then
        printf '  %-8s ' "$lang"
        msgfmt --statistics -o /dev/null "$po" 2>&1 | tr -d '\n'
        printf '  -> %s\n' "$mo"
        count=$((count + 1))
    else
        echo "ERROR: $po did not compile." >&2
        fail=1
    fi
done

if [ "$count" = 0 ]; then
    echo "ERROR: no .po files found in po/ — nothing to compile." >&2
    exit 1
fi

[ "$fail" = 0 ] || exit 1

if [ "$MODE" = --check ]; then
    echo "i18n: $count catalogue(s) present and up to date"
else
    echo "i18n: $count catalogue(s) written under $LOCALEDIR"
fi
