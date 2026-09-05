#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Stage one already-gated commercial release file under an immutable,
# candidate-specific R2 prefix. This script deliberately has no live-key mode.
# Live promotion is a separate, post-signature operation implemented by
# tools/promote-r2-release.sh.
set -eu

cd "$(dirname "$0")/.."

FILE=${1:-}
if [ "$#" -ne 1 ] || [ -z "$FILE" ]; then
    echo "usage: sh tools/upload-to-r2.sh <approved-release-file>" >&2
    echo "       destination bucket/key are derived; live keys are never accepted" >&2
    exit 2
fi
[ -f "$FILE" ] || { echo "r2-stage: no such file: $FILE" >&2; exit 1; }
[ -n "${DAGRIC_RELEASE_TAG:-}" ] || {
    echo "r2-stage: DAGRIC_RELEASE_TAG is required." >&2
    exit 1
}
[ -n "${COMMERCIAL_RELEASE_APPROVAL_JSON:-}" ] || {
    echo "r2-stage: COMMERCIAL_RELEASE_APPROVAL_JSON is required." >&2
    exit 1
}
[ -n "${DAGRIC_STAGING_BUCKET:-}" ] || {
    echo "r2-stage: DAGRIC_STAGING_BUCKET is required." >&2
    exit 1
}
case "$DAGRIC_STAGING_BUCKET" in
    dagric-downloads|dagric-pro)
        echo "r2-stage: staging must use a dedicated bucket, never a live bucket." >&2
        exit 1
        ;;
esac
BUCKET=$DAGRIC_STAGING_BUCKET

VERSION=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["version"])')
SOURCE_COMMIT=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["source"]["commit"])')
SOURCE_INDEX=$(python3 -c \
    'import json,urllib.parse; print(urllib.parse.urlsplit(json.load(open("site/manifest/release.json"))["source_index"]["url"]).path.rsplit("/",1)[-1])')
PREFIX="staging/$DAGRIC_RELEASE_TAG/$SOURCE_COMMIT"
GATE_DIR=out/release-gate
AUTHORIZATION="$GATE_DIR/COMMERCIAL-RELEASE-AUTHORIZATION.json"
FREE_ISO="dagric-os-$VERSION-amd64.iso"
PRO_ISO="dagric-os-pro-$VERSION-amd64.iso"
FREE_MANIFEST="dagric-os-$VERSION.packages"
PRO_MANIFEST="dagric-os-pro-$VERSION.packages"
NAME=$(basename "$FILE")

# This exact allowlist prevents the old `[file] [bucket]` interface from being
# repurposed to overwrite a live object. The caller cannot supply either a
# bucket or a key. Every destination begins with the validated staging prefix.
case "$NAME" in
    "$FREE_ISO")
        EXPECTED="out/$FREE_ISO"
        KEY="$PREFIX/$FREE_ISO"
        ;;
    "$PRO_ISO")
        EXPECTED="out/$PRO_ISO"
        KEY="$PREFIX/$PRO_ISO"
        ;;
    SHA256SUMS|SHA256SUMS.sig)
        EXPECTED="out/$NAME"
        KEY="$PREFIX/$NAME"
        ;;
    "$FREE_MANIFEST"|"$PRO_MANIFEST")
        EXPECTED="$GATE_DIR/$NAME"
        KEY="$PREFIX/manifest/$NAME"
        ;;
    PACKAGE_SECTIONS-free.tsv|PACKAGE_SECTIONS-pro.tsv)
        EXPECTED="out/$NAME"
        KEY="$PREFIX/manifest/$NAME"
        ;;
    COMMERCIAL-RELEASE-AUTHORIZATION.json)
        EXPECTED="$AUTHORIZATION"
        KEY="$PREFIX/manifest/$NAME"
        ;;
    release.json)
        EXPECTED=site/manifest/release.json
        KEY="$PREFIX/manifest/$NAME"
        ;;
    "$SOURCE_INDEX")
        EXPECTED="site/manifest/$SOURCE_INDEX"
        KEY="$PREFIX/manifest/$NAME"
        ;;
    *)
        echo "r2-stage: $NAME is not an approved commercial-release artifact." >&2
        echo "          This helper cannot upload arbitrary files or live keys." >&2
        exit 1
        ;;
esac

[ -f "$EXPECTED" ] || {
    echo "r2-stage: expected gated file is missing: $EXPECTED" >&2
    exit 1
}
cmp -s "$FILE" "$EXPECTED" || {
    echo "r2-stage: $FILE is not byte-identical to the gated $EXPECTED" >&2
    exit 1
}

# This also binds the tag to the clean release-record checkout, verifies that
# only metadata changed after the recorded build-source commit, checks all five
# release locales, re-extracts both ISO package manifests and refreshes the
# deterministic authorization file.
sh tools/release.sh gate
[ -f "$AUTHORIZATION" ] || {
    echo "r2-stage: commercial gate did not produce an authorization." >&2
    exit 1
}
# The gate can regenerate extracted manifests and authorization records. Never
# upload the pre-gate bytes merely because they matched before that refresh.
cmp -s "$FILE" "$EXPECTED" || {
    echo "r2-stage: $FILE changed or became stale while the gate refreshed." >&2
    exit 1
}

FREE_PROVENANCE=out/SOURCE_COMMIT-free
[ -f "$FREE_PROVENANCE" ] || FREE_PROVENANCE=out/SOURCE_COMMIT
PRO_PROVENANCE=out/SOURCE_COMMIT-pro
[ -f "$PRO_PROVENANCE" ] || PRO_PROVENANCE=out/SOURCE_COMMIT

# A stamp is evidence only when it can be reproduced. Re-run the complete
# candidate gate over the current ISO bytes, manifests, source records and
# protected human approval, then require an exact match with the stored stamp.
RECHECK=$(mktemp) || exit 1
trap 'rm -f "$RECHECK"' EXIT HUP INT TERM
python3 tools/check-commercial-release.py promotion \
    --checksums out/SHA256SUMS \
    --free-manifest "$GATE_DIR/$FREE_MANIFEST" \
    --pro-manifest "$GATE_DIR/$PRO_MANIFEST" \
    --free-package-sections out/PACKAGE_SECTIONS-free.tsv \
    --pro-package-sections out/PACKAGE_SECTIONS-pro.tsv \
    --free-iso "out/$FREE_ISO" \
    --pro-iso "out/$PRO_ISO" \
    --free-provenance "$FREE_PROVENANCE" \
    --pro-provenance "$PRO_PROVENANCE" \
    --candidate-commit "$SOURCE_COMMIT" \
    --release-tag "$DAGRIC_RELEASE_TAG" \
    --authorization-output "$RECHECK"
cmp -s "$RECHECK" "$AUTHORIZATION" || {
    echo "r2-stage: authorization stamp is stale or belongs to other bytes." >&2
    exit 1
}

for VALUE in "${R2_ACCOUNT_ID:-}" "${R2_ACCESS_KEY_ID:-}" \
             "${R2_SECRET_ACCESS_KEY:-}"; do
    [ -n "$VALUE" ] || {
        echo "r2-stage: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and" >&2
        echo "          R2_SECRET_ACCESS_KEY are all required." >&2
        exit 1
    }
done
unset VALUE
python3 tools/check-private-r2-staging.py \
    --account "$R2_ACCOUNT_ID" --bucket "$BUCKET"
command -v rclone >/dev/null 2>&1 || {
    echo "r2-stage: rclone is not installed (apt install rclone)." >&2
    exit 1
}

# Environment-only rclone configuration: no credential file or shell-history
# argument is created.
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true

LOCAL=$(sha256sum "$FILE" | cut -d' ' -f1)
SIZE=$(wc -c < "$FILE" | tr -d ' ')
echo "r2-stage: $NAME ($SIZE bytes; sha256 $LOCAL)"
echo "r2-stage: uploading only to R2:$BUCKET/$KEY"
rclone copyto "$FILE" "R2:$BUCKET/$KEY" --immutable --s3-chunk-size 64M

# Candidate staging is normally private, so verify through authenticated R2
# instead of pretending the public/live URL changed.
REMOTE=$(rclone cat "R2:$BUCKET/$KEY" | sha256sum | cut -d' ' -f1)
if [ "$REMOTE" != "$LOCAL" ]; then
    echo "r2-stage: remote bytes do not match; no live key was touched." >&2
    exit 1
fi

echo "r2-stage: verified candidate object; live downloads are unchanged."
echo "r2-stage: promotion requires tools/promote-r2-release.sh after signing."
