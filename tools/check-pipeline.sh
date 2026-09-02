#!/bin/sh
# Dagric Adaptive Pipeline source and safety gate.
set -eu
cd "$(dirname "$0")/.."

python3 test/test-pipeline.py
python3 test/test-twin.py

WORK=$(mktemp -d "${TMPDIR:-/tmp}/dagric-pipeline.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
DAGRIC_PIPELINE_STATE_DIR="$WORK/state" \
    python3 config/includes.chroot/usr/lib/dagric/pipeline.py scan --quiet
DAGRIC_PIPELINE_STATE_DIR="$WORK/state" \
    python3 config/includes.chroot/usr/lib/dagric/pipeline.py audit

for forbidden in 'sched_ext.*True' 'binary_rewriting.*True' 'background_warming.*True'; do
    if grep -E -q "$forbidden" "$WORK/state/profile.json"; then
        echo "pipeline-check: unsafe policy escaped its guard: $forbidden" >&2
        exit 1
    fi
done

echo "pipeline-check: machine-specific policy, privacy boundary and pressure guard passed"
