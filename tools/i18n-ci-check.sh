#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — is po/ actually in sync with the source?  (needs gettext)
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
# Local runs are transactional: generated files are compared with the starting
# files and restored on exit. CI explicitly sets
# DAGRIC_I18N_KEEP_REGENERATED=1 so a failing job can attach the proposed fix.
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
BEFORE="$SAVE/before.list"
AFTER="$SAVE/after.list"
ALL="$SAVE/all.list"
mkdir -p "$SAVE/artifacts"

artifact_paths() {
    for f in po/dagric-data-strings.sh "$POT" po/*.po \
        config/includes.chroot/usr/share/locale/*/LC_MESSAGES/dagric.mo; do
        [ -f "$f" ] && printf '%s\n' "$f"
    done | sort -u
}

artifact_paths > "$BEFORE"
while IFS= read -r f; do
    mkdir -p "$SAVE/artifacts/$(dirname "$f")"
    cp "$f" "$SAVE/artifacts/$f"
done < "$BEFORE"

restore_artifacts() {
    [ "${DAGRIC_I18N_KEEP_REGENERATED:-0}" = "1" ] && return
    artifact_paths > "$AFTER"
    while IFS= read -r f; do
        grep -Fqx "$f" "$BEFORE" || rm -f "$f"
    done < "$AFTER"
    while IFS= read -r f; do
        mkdir -p "$(dirname "$f")"
        cp "$SAVE/artifacts/$f" "$f"
    done < "$BEFORE"
}

cleanup() {
    status=$?
    trap - EXIT INT TERM HUP
    restore_artifacts
    rm -rf "$SAVE" "$A" "$B"
    exit "$status"
}
trap cleanup EXIT INT TERM HUP

sh tools/i18n-extract.sh

# Restore every file whose only change is the timestamp. Note this runs BEFORE
# i18n-build.sh: the .mo files embed the .po header, so compiling first would
# bake a stamp that is about to be reverted and every catalogue would then
# disagree with its own source.
for f in "$POT" po/*.po; do
    [ -f "$f" ] || continue
    orig="$SAVE/artifacts/$f"
    [ -f "$orig" ] || continue
    grep -v '^"POT-Creation-Date:' "$f"    > "$A" || true
    grep -v '^"POT-Creation-Date:' "$orig" > "$B" || true
    if cmp -s "$A" "$B"; then
        cp "$orig" "$f"
    fi
done

sh tools/i18n-build.sh

artifact_paths > "$AFTER"
cat "$BEFORE" "$AFTER" | sort -u > "$ALL"
CHANGED=""
while IFS= read -r f; do
    if ! grep -Fqx "$f" "$BEFORE" || [ ! -f "$f" ] \
        || ! cmp -s "$SAVE/artifacts/$f" "$f"; then
        CHANGED="${CHANGED}${CHANGED:+
}$f"
    fi
done < "$ALL"

# Compare against the byte-for-byte starting snapshot, not against Git HEAD.
# That keeps the result correct in an intentionally dirty developer worktree and
# still detects a newly generated catalogue that was absent at the start.
if [ -z "$CHANGED" ]; then
    echo "i18n: po/ and the catalogues match the source"
    exit 0
fi

# SAY WHICH KIND OF DRIFT THIS IS. Two very different things fail this check
# and they deserve different amounts of the reader's attention:
#
#   * a NEW msgid — a user-facing string that currently ships as English in
#     every language, because there is nothing to translate it to. This is the
#     defect the job exists for.
#   * only the "#:" source references moved, because someone added a comment
#     above a gettext call and every line number after it shifted. Regenerating
#     is still the right response, but nothing is broken for any owner.
#
# Reporting both as the same wall of red is how a gate gets ignored, which is
# the failure mode this project keeps writing comments about.
NEW=$(diff -U0 "$SAVE/artifacts/$POT" "$POT" | grep '^+msgid "' | grep -v '^+msgid ""$' || true)
GONE=$(diff -U0 "$SAVE/artifacts/$POT" "$POT" | grep '^-msgid "' | grep -v '^-msgid ""$' || true)

echo "" >&2
if [ -n "$NEW" ]; then
    echo "ERROR: po/ is out of date — there are NEW UNTRANSLATED STRINGS." >&2
    echo "" >&2
    echo "Each msgid below ships as ENGLISH in all five languages today," >&2
    echo "because a string with no msgid has nothing to translate to:" >&2
    echo "" >&2
    printf '%s\n' "$NEW" | sed 's/^+/    /' >&2
else
    echo "ERROR: po/ is out of date, but no msgid was added or removed —" >&2
    echo "       only the '#:' source references moved, which happens when a" >&2
    echo "       line is added above a gettext call. Nothing is broken for an" >&2
    echo "       owner; the template just needs regenerating." >&2
fi
if [ -n "$GONE" ]; then
    echo "" >&2
    echo "These msgids are GONE from the source. If that was not intended, a" >&2
    echo "string was deleted or edited and its translations are being retired:" >&2
    echo "" >&2
    printf '%s\n' "$GONE" | sed 's/^-/    /' >&2
fi
echo "" >&2
echo "Files that changed when the extraction was re-run:" >&2
printf '%s\n' "$CHANGED" | sed 's/^/    /' >&2
echo "" >&2
if [ "${DAGRIC_I18N_KEEP_REGENERATED:-0}" = "1" ]; then
    echo "The regenerated po/ and catalogues are retained for the CI" >&2
    echo "'i18n-regenerated' artifact. Download, unpack over the repo, commit." >&2
else
    echo "This local check restores the starting files on exit. Run" >&2
    echo "tools/i18n-extract.sh and tools/i18n-build.sh to apply the update." >&2
fi
exit 1
