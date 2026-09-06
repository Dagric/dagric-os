#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Freeze one committed source and build both editions serially on an explicitly
# selected private build filesystem. No existing build directory is reused.
set -euo pipefail
if [[ $# != 1 ]]; then echo 'usage: run-finishing-build.sh /existing/private/build-mount' >&2; exit 2; fi
ROOT=$(realpath -e -- "$1")
case "$ROOT" in /var/tmp/dagric-finishing-build-mount.*) ;; *) echo 'Expected the dedicated finishing-build mount.' >&2; exit 2 ;; esac
mountpoint -q -- "$ROOT" || { echo 'Build storage is not mounted.' >&2; exit 1; }
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REVISION=$(git -C "$REPO" rev-parse HEAD)
for EDITION in free pro; do
    python3 "$REPO/tools/build-guard.py" --check-space "$ROOT" "$EDITION"
    RUN=$(mktemp -d "$ROOT/$EDITION.XXXXXXXX")
    printf 'Build edition: %s\nBuild run: %s\nFrozen source: %s\n' "$EDITION" "$RUN" "$REVISION"
    git clone --quiet --no-hardlinks "$REPO" "$RUN/source"
    git -C "$RUN/source" checkout --quiet --detach "$REVISION"
    DAGRIC_BUILD_DIR="$RUN/build" bash "$RUN/source/build.sh" "$EDITION" 2>&1 | tee "$RUN/console.log"
    printf 'Build completed: %s\n' "$RUN"
done
