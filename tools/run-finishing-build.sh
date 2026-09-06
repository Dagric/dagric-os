#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Freeze one committed source and build both editions serially on an explicitly
# selected private build filesystem. No existing build directory is reused.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then echo 'usage: run-finishing-build.sh /existing/private/build-mount [free|pro|both]' >&2; exit 2; fi
ROOT=$(realpath -e -- "$1")
case "$ROOT" in /var/tmp/dagric-finishing-build-mount.*) ;; *) echo 'Expected the dedicated finishing-build mount.' >&2; exit 2 ;; esac
mountpoint -q -- "$ROOT" || { echo 'Build storage is not mounted.' >&2; exit 1; }
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REVISION=${DAGRIC_FINISHING_REVISION:-$(git -C "$REPO" rev-parse HEAD)}
[[ "$REVISION" =~ ^[a-f0-9]{40}$ ]] || { echo 'Expected an exact source revision.' >&2; exit 2; }
git -C "$REPO" cat-file -e "$REVISION^{commit}"
case "${2:-both}" in free) EDITIONS=(free) ;; pro) EDITIONS=(pro) ;; both) EDITIONS=(free pro) ;; *) exit 2 ;; esac
for EDITION in "${EDITIONS[@]}"; do
    python3 "$REPO/tools/build-guard.py" --check-space "$ROOT" "$EDITION"
    RUN=$(mktemp -d "$ROOT/$EDITION.XXXXXXXX")
    printf 'Build edition: %s\nBuild run: %s\nFrozen source: %s\n' "$EDITION" "$RUN" "$REVISION"
    git clone --quiet --no-hardlinks "$REPO" "$RUN/source"
    git -C "$RUN/source" checkout --quiet --detach "$REVISION"
    if [[ -n "${DAGRIC_FINISHING_CACHE:-}" ]]; then
        CACHE=$(realpath -e "$DAGRIC_FINISHING_CACHE")
        case "$CACHE" in "$ROOT"/free.*/build/cache|"$ROOT"/pro.*/build/cache) ;; *) echo 'Cache must belong to this private build mount.' >&2; exit 2 ;; esac
        mkdir "$RUN/source/cache"
        cp -a "$CACHE/." "$RUN/source/cache/"
    fi
    DAGRIC_BUILD_DIR="$RUN/build" bash "$RUN/source/build.sh" "$EDITION" 2>&1 | tee "$RUN/console.log"
    printf 'Build completed: %s\n' "$RUN"
done
