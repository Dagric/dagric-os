#!/bin/sh
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — upload a release artifact to R2 and PROVE the bytes arrived.
#
#   sh tools/upload-to-r2.sh D:/Dagric-Backup/Dagric-OS-1.0-Free.ova
#   sh tools/upload-to-r2.sh out/dagric-os-1.0-amd64.iso dagric-downloads
#
# WHY THIS EXISTS. tools/release.sh says, in as many words, "The upload to R2
# happens BETWEEN sign and publish, by hand" — and there was no tool for that
# hand step. The CI workflow can upload, but only what CI itself built; an
# artefact produced locally (the test appliance, a rebuilt ISO) had no path to
# the bucket except an ad-hoc aws command typed from memory, with the
# credential on the command line where the shell history keeps it.
#
# CREDENTIALS COME FROM THE ENVIRONMENT AND ARE NEVER WRITTEN ANYWHERE.
# There is no credential in this repo and there must not be one. Export the
# same three the CI workflow uses, ideally in a subshell so they leave with it:
#
#   export R2_ACCOUNT_ID=...
#   export R2_ACCESS_KEY_ID=...
#   export R2_SECRET_ACCESS_KEY=...
#
# THE UPLOAD IS NOT THE POINT — THE VERIFICATION IS. This project has already
# published a checksum that did not match the file R2 was serving, twice, and
# the download page tells buyers that a mismatch means a tampered download. So
# this refuses to report success until it has re-read the object FROM THE PUBLIC
# URL and hashed it. A copy that "completed" is not evidence.
set -eu

FILE=${1:-}
BUCKET=${2:-dagric-downloads}
PUBHOST=${R2_PUBLIC_HOST:-pub-23bebbd32e3b44c4af6e53c06194e77f.r2.dev}

if [ -z "$FILE" ]; then
    echo "usage: sh tools/upload-to-r2.sh <file> [bucket]" >&2
    exit 1
fi
[ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }

for v in R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY; do
    eval "_val=\${$v:-}"
    if [ -z "$_val" ]; then
        echo "ERROR: $v is not set." >&2
        echo "       Export R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and" >&2
        echo "       R2_SECRET_ACCESS_KEY first. They are the same three the" >&2
        echo "       release workflow uses as repo secrets." >&2
        exit 1
    fi
done
unset _val

command -v rclone >/dev/null 2>&1 || {
    echo "ERROR: rclone is not installed (apt install rclone)." >&2; exit 1; }

NAME=$(basename "$FILE")
SIZE=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE")
echo "=== hashing the local copy before anything leaves this machine ==="
LOCAL=$(sha256sum "$FILE" | cut -d' ' -f1)
printf "  %s\n  %s bytes\n  sha256 %s\n" "$NAME" "$SIZE" "$LOCAL"

# rclone is configured entirely through the environment, so nothing is written
# to ~/.config/rclone and there is no config file to leak.
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
# R2 has no ACLs; sending one makes it reject the request.
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true

echo
echo "=== uploading to r2:$BUCKET/$NAME ==="
rclone copyto "$FILE" "R2:$BUCKET/$NAME" --progress --s3-chunk-size 64M

echo
echo "=== what the bucket now holds ==="
rclone lsl "R2:$BUCKET/$NAME" | sed 's/^/  /'

URL="https://${PUBHOST}/${NAME}"
echo
echo "=== re-reading it from the PUBLIC url and hashing what a customer gets ==="
echo "  $URL"
REMOTE=$(curl -fsSL --retry 3 "$URL" | sha256sum | cut -d' ' -f1) || {
    echo "ERROR: could not fetch $URL" >&2
    echo "       The object may be in a bucket that is not publicly readable," >&2
    echo "       or the public host differs — set R2_PUBLIC_HOST to override." >&2
    exit 1
}

echo "  local  $LOCAL"
echo "  served $REMOTE"
if [ "$LOCAL" = "$REMOTE" ]; then
    echo
    echo "MATCH — the bytes R2 serves are the bytes built here."
    echo
    echo "Send this link:"
    echo "  $URL"
    echo
    echo "sha256 for anyone who wants to verify:"
    echo "  $LOCAL"
else
    echo >&2
    echo "MISMATCH — do NOT publish this link." >&2
    echo "R2 is serving different bytes from the file uploaded. Re-run the" >&2
    echo "upload; if it persists, the object is being cached or was truncated." >&2
    exit 1
fi
