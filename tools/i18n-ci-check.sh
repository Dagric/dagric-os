#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — is po/ actually in sync with the source?  (CI only; needs gettext)
#
#     sh tools/i18n-ci-check.sh
#
# WHAT THIS CATCHES, AND WHY NOTHING ELSE DID
# -------------------------------------------
# tools/i18n-build.sh --check verifies that each .mo matches its .po. Nothing
# verified that the .po files match THE SOURCE. So a new user-facing string
# could be added to a shipped tool, never extracted, and every check in the
# project would pass while that sentence stayed English in all five languages.
#
# That is not hypothetical: when this was written, 29 strings shipped with no
# msgid anywhere in po/dagric.pot, and they were concentrated in exactly the
# worst place — the error paths of dagric-ai, dagric-drivers and dagric-gaming.
# The German owner whose driver install fails is the one person guaranteed to
# get an English wall of text.
#
# It went unnoticed because the extraction cannot run on the machine this
# project is developed on: no gettext, no working WSL, no Docker daemon. CI is
# the only Linux host in the loop, so the check belongs here.
#
# AND IT HANDS BACK THE FIX. A red X saying "run i18n-extract.sh" is useless to
# someone who has nowhere to run it. On failure the workflow uploads the
# regenerated po/ and the recompiled catalogues as an artifact, so the fix is a
# download and a commit rather than a machine nobody has.
#
# THE DATE STAMP IS WHY THIS IS NOT A ONE-LINE `git diff`
# ------------------------------------------------------
# xgettext writes POT-Creation-Date with the current time on every run, and
# msgmerge copies it into every .po header. A naive regenerate-and-diff
# therefore reports drift on a tree that is perfectly in sync — it would fail
# 100% of the time, be recognised as noise within a day, and be ignored or
# deleted.
#
# The obvious fix is to rewrite the stamp back with sed, and that was tried and
# abandoned: GNU sed reads "\\n" in a regex as a newline escape rather than a
# literal backslash-n, so the pattern silently matched NOTHING, and on the
# replacement side "\\\\n" produced a real newline that corrupted the header.
# A check that quietly does nothing is worse than no check.
#
# So there is no rewriting. A pristine copy is kept, and any file whose ONLY
# difference is the stamp line is restored from it — a comparison of two files
# with that one line filtered out, which needs no escaping at all and cannot
# half-work.
set -e
cd "$(dirname "$0")/.."

command -v xgettext >/dev/null 2>&1 || {
    echo "xgettext is required: apt install gettext" >&2; exit 1; }

POT=po/dagric.pot
[ -f "$POT" ] || { echo "ERROR: $POT missing" >&2; exit 1; }

SAVE=$(mktemp -d) || exit 1
A=$(mktemp) || exit 1
B=$(mktemp) || exit 1
trap 'rm -rf "$SAVE" "$A" "$B"' EXIT INT TERM

for f in "$POT" po/*.po; do
    [ -f "$f" ] || continue
    cp "$f" "$SAVE/$(basename "$f")"
done

sh tools/i18n-extract.sh

# Restore every file whose only change is the timestamp. Note this runs BEFORE
# i18n-build.sh: the .mo files embed the .po header, so compiling first would
# bake a stamp that is about to be reverted and every catalogue would then
# disagree with its own source.
for f in "$POT" po/*.po; do
    [ -f "$f" ] || continue
    orig="$SAVE/$(basename "$f")"
    [ -f "$orig" ] || continue
    grep -v '^"POT-Creation-Date:' "$f"    > "$A" || true
    grep -v '^"POT-Creation-Date:' "$orig" > "$B" || true
    if cmp -s "$A" "$B"; then
        cp "$orig" "$f"
    fi
done

sh tools/i18n-build.sh

# --porcelain rather than `git diff --quiet`, because diff only sees TRACKED
# files: a brand-new catalogue or a new generated file in po/ is untracked, and
# a new language appearing out of nowhere is exactly the change worth catching.
if [ -z "$(git status --porcelain -- po config/includes.chroot/usr/share/locale)" ]; then
    echo "i18n: po/ and the catalogues match the source"
    exit 0
fi

echo "" >&2
echo "ERROR: po/ is out of date with respect to the source." >&2
echo "" >&2
echo "Files that changed when the extraction was re-run:" >&2
git diff --stat -- po config/includes.chroot/usr/share/locale >&2
echo "" >&2
echo "Any msgid listed below currently ships as ENGLISH in all five" >&2
echo "languages, because a string with no msgid has nothing to translate to:" >&2
echo "" >&2
git diff -U0 -- "$POT" | grep '^+msgid "' | grep -v '^+msgid ""$' \
    | sed 's/^+/    /' >&2 || true
echo "" >&2
echo "The regenerated po/ and catalogues are attached to this run as the" >&2
echo "'i18n-regenerated' artifact. Download, unpack over the repo, commit." >&2
exit 1
