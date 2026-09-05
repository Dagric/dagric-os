#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Explicitly promote one fully gated, offline-signed Dagric candidate from its
# isolated R2 prefix to the exact live Free/Pro keys. This is the only release
# helper allowed to write those keys. It is intentionally separate from stage.
set -eu

cd "$(dirname "$0")/.."

if [ "${DAGRIC_PROMOTE_TO_LIVE:-}" != YES ]; then
    echo "r2-promote: refusing live writes." >&2
    echo "Set DAGRIC_PROMOTE_TO_LIVE=YES for this exact reviewed invocation." >&2
    exit 2
fi
[ -n "${DAGRIC_RELEASE_TAG:-}" ] || {
    echo "r2-promote: DAGRIC_RELEASE_TAG is required." >&2
    exit 1
}
[ -n "${COMMERCIAL_RELEASE_APPROVAL_JSON:-}" ] || {
    echo "r2-promote: COMMERCIAL_RELEASE_APPROVAL_JSON is required." >&2
    exit 1
}
[ -n "${PHYSICAL_RELEASE_EVIDENCE_JSON:-}" ] || {
    echo "r2-promote: PHYSICAL_RELEASE_EVIDENCE_JSON is required." >&2
    exit 1
}
[ -n "${DAGRIC_STAGING_BUCKET:-}" ] || {
    echo "r2-promote: DAGRIC_STAGING_BUCKET is required." >&2
    exit 1
}
case "$DAGRIC_STAGING_BUCKET" in
    dagric-downloads|dagric-pro)
        echo "r2-promote: staging bucket must differ from both live buckets." >&2
        exit 1
        ;;
esac
STAGING_BUCKET=$DAGRIC_STAGING_BUCKET

# Fail before touching R2 unless tag/commit identity, source map, both ISO
# hashes, every resolved package, restricted-package review, artwork/trademark
# approval and release localization all still reproduce the authorization.
sh tools/release.sh gate
sh tools/release.sh physical

VERSION=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["version"])')
SOURCE_COMMIT=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["source"]["commit"])')
PREFIX="staging/$DAGRIC_RELEASE_TAG/$SOURCE_COMMIT"
FREE_ISO="dagric-os-$VERSION-amd64.iso"
PRO_ISO="dagric-os-pro-$VERSION-amd64.iso"
AUTHORIZATION=out/release-gate/COMMERCIAL-RELEASE-AUTHORIZATION.json
KEY_FINGERPRINT=3A079F85DE74375DD65557096CE37402BA0A0EF8

for FILE in out/SHA256SUMS out/SHA256SUMS.sig "$AUTHORIZATION"; do
    [ -f "$FILE" ] || {
        echo "r2-promote: missing $FILE; sign and stage the candidate first." >&2
        exit 1
    }
done
( cd out && sha256sum -c SHA256SUMS >/dev/null ) || {
    echo "r2-promote: local ISO bytes no longer match SHA256SUMS." >&2
    exit 1
}

# `gpg --verify` alone accepts any trusted key. Bind the signature to the
# fingerprint suffix published on Dagric's download page.
STATUS=$(mktemp) || exit 1
trap 'rm -f "$STATUS"' EXIT HUP INT TERM
if ! gpg --batch --status-fd 3 --verify out/SHA256SUMS.sig \
        out/SHA256SUMS 3>"$STATUS" >/dev/null 2>&1; then
    echo "r2-promote: SHA256SUMS.sig does not verify." >&2
    exit 1
fi
FINGERPRINT=$(awk '$2=="VALIDSIG"{print $3}' "$STATUS")
case "$FINGERPRINT" in
    "$KEY_FINGERPRINT") ;;
    "")
        echo "r2-promote: gpg returned no valid signing fingerprint." >&2
        exit 1
        ;;
    *)
        echo "r2-promote: signature was made by the wrong key." >&2
        exit 1
        ;;
esac

for VALUE in "${R2_ACCOUNT_ID:-}" "${R2_ACCESS_KEY_ID:-}" \
             "${R2_SECRET_ACCESS_KEY:-}"; do
    [ -n "$VALUE" ] || {
        echo "r2-promote: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and" >&2
        echo "            R2_SECRET_ACCESS_KEY are all required." >&2
        exit 1
    }
done
unset VALUE
python3 tools/check-private-r2-staging.py \
    --account "$R2_ACCOUNT_ID" --bucket "$STAGING_BUCKET"
command -v rclone >/dev/null 2>&1 || {
    echo "r2-promote: rclone is not installed (apt install rclone)." >&2
    exit 1
}

export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true

FREE_HASH=$(awk -v name="$FREE_ISO" '$2==name{print $1}' out/SHA256SUMS)
PRO_HASH=$(awk -v name="$PRO_ISO" '$2==name{print $1}' out/SHA256SUMS)
SUMS_HASH=$(sha256sum out/SHA256SUMS | cut -d' ' -f1)
SIG_HASH=$(sha256sum out/SHA256SUMS.sig | cut -d' ' -f1)
AUTH_HASH=$(sha256sum "$AUTHORIZATION" | cut -d' ' -f1)
[ -n "$FREE_HASH" ] && [ -n "$PRO_HASH" ] || {
    echo "r2-promote: signed manifest does not contain both exact ISO names." >&2
    exit 1
}

r2_digest() {
    rclone cat "$1" | sha256sum | cut -d' ' -f1
}

require_remote_hash() {
    _object=$1
    _expected=$2
    _actual=$(r2_digest "$_object") || return 1
    if [ "$_actual" != "$_expected" ]; then
        echo "r2-promote: staged object mismatch: $_object" >&2
        echo "            expected $_expected" >&2
        echo "            got      $_actual" >&2
        return 1
    fi
}

# Verify every staged input before the first customer-facing write. The helper
# refuses to fall back to a live-root source when a staged object is missing.
require_remote_hash "R2:$STAGING_BUCKET/$PREFIX/$FREE_ISO" "$FREE_HASH"
require_remote_hash "R2:$STAGING_BUCKET/$PREFIX/$PRO_ISO" "$PRO_HASH"
require_remote_hash "R2:$STAGING_BUCKET/$PREFIX/SHA256SUMS" "$SUMS_HASH"
require_remote_hash "R2:$STAGING_BUCKET/$PREFIX/SHA256SUMS.sig" "$SIG_HASH"
require_remote_hash \
    "R2:$STAGING_BUCKET/$PREFIX/manifest/COMMERCIAL-RELEASE-AUTHORIZATION.json" \
    "$AUTH_HASH"

# Fixed live keys may change only while every known Free origin, the Pro worker
# and the public download page are mechanically held. This must remain true
# until matching site records are deployed and distribution is explicitly
# re-enabled as a separate operation.
sh tools/check-release-hold.sh

echo "r2-promote: all candidate objects and the offline signature are verified."
echo "r2-promote: promoting exact $DAGRIC_RELEASE_TAG ($SOURCE_COMMIT)."

# These are the only live writes in the script. ISO bytes move first, then the
# signed checksum pair, with the detached signature LAST. Never move a manifest
# or signature before both edition objects have passed the same gate.
rclone copyto "R2:$STAGING_BUCKET/$PREFIX/$FREE_ISO" \
    "R2:dagric-downloads/$FREE_ISO"
rclone copyto "R2:$STAGING_BUCKET/$PREFIX/$PRO_ISO" \
    "R2:dagric-pro/$PRO_ISO"
rclone copyto "R2:$STAGING_BUCKET/$PREFIX/SHA256SUMS" \
    R2:dagric-downloads/SHA256SUMS
rclone copyto "R2:$STAGING_BUCKET/$PREFIX/SHA256SUMS.sig" \
    R2:dagric-downloads/SHA256SUMS.sig

# Read back every customer-facing object. A successful copy operation is not
# evidence that the exact intended bytes are now served.
require_remote_hash "R2:dagric-downloads/$FREE_ISO" "$FREE_HASH"
require_remote_hash "R2:dagric-pro/$PRO_ISO" "$PRO_HASH"
require_remote_hash R2:dagric-downloads/SHA256SUMS "$SUMS_HASH"
require_remote_hash R2:dagric-downloads/SHA256SUMS.sig "$SIG_HASH"
sh tools/check-release-hold.sh

RECEIPT=out/release-gate/R2-LIVE-PROMOTION.json
PHYSICAL_DIGEST=$(awk 'NF{print $1; exit}' out/release-gate/PHYSICAL-RELEASE-EVIDENCE.sha256)
RECEIPT="$RECEIPT" RELEASE_TAG="$DAGRIC_RELEASE_TAG" \
    SOURCE_COMMIT="$SOURCE_COMMIT" AUTH_HASH="$AUTH_HASH" \
    PHYSICAL_DIGEST="$PHYSICAL_DIGEST" \
    FREE_ISO="$FREE_ISO" FREE_HASH="$FREE_HASH" \
    PRO_ISO="$PRO_ISO" PRO_HASH="$PRO_HASH" \
    SUMS_HASH="$SUMS_HASH" SIG_HASH="$SIG_HASH" python3 - <<'PY'
import json
import os
from pathlib import Path

receipt = {
    "schema": "dagric-r2-live-promotion-v1",
    "release_tag": os.environ["RELEASE_TAG"],
    "candidate_commit": os.environ["SOURCE_COMMIT"],
    "authorization_sha256": os.environ["AUTH_HASH"],
    "physical_evidence_sha256": os.environ["PHYSICAL_DIGEST"],
    "artifacts": {
        "free": {
            "filename": os.environ["FREE_ISO"],
            "sha256": os.environ["FREE_HASH"],
        },
        "pro": {
            "filename": os.environ["PRO_ISO"],
            "sha256": os.environ["PRO_HASH"],
        },
    },
    "checksums_sha256": os.environ["SUMS_HASH"],
    "signature_sha256": os.environ["SIG_HASH"],
}
path = Path(os.environ["RECEIPT"])
temporary = path.with_name(path.name + ".tmp")
temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
temporary.replace(path)
PY

echo "r2-promote: live Free/Pro bytes and signature verified."
echo "r2-promote: wrote verified promotion receipt: $RECEIPT"
echo "r2-promote: now run: sh tools/release.sh publish"
