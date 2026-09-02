#!/bin/sh
# Create a fresh FAT exchange disk containing the installed-system audit.
# Refuses to overwrite an existing image so evidence from an earlier run cannot
# be mistaken for the current result.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:-}
[ -n "$DEST" ] || { echo "usage: $0 OUTPUT-DIRECTORY" >&2; exit 2; }
case "$DEST" in /*) ;; *) DEST="$ROOT/$DEST" ;; esac
mkdir -p "$DEST"
IMAGE="$DEST/evidence.img"
[ ! -e "$IMAGE" ] || { echo "prepare-evidence: refusing to overwrite $IMAGE" >&2; exit 1; }

for command in truncate mkfs.vfat mcopy; do
    command -v "$command" >/dev/null 2>&1 || { echo "prepare-evidence: missing $command" >&2; exit 1; }
done

truncate -s 64M "$IMAGE"
mkfs.vfat -n DGR_AUDIT "$IMAGE" >/dev/null
mcopy -i "$IMAGE" "$ROOT/test/installed-audit.sh" ::/installed-audit.sh
echo "prepare-evidence: created $IMAGE"
