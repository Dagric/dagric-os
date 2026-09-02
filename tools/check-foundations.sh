#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

python3 -m py_compile config/includes.chroot/usr/lib/dagric/foundations.py
python3 test/test-foundations.py
python3 tools/check-foundations.py

tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT HUP INT TERM
python3 config/includes.chroot/usr/lib/dagric/foundations.py blueprint export "$tmp/blueprint.json"
python3 config/includes.chroot/usr/lib/dagric/foundations.py blueprint audit "$tmp/blueprint.json"
python3 config/includes.chroot/usr/lib/dagric/foundations.py blueprint plan "$tmp/blueprint.json" > "$tmp/plan.json"
python3 config/includes.chroot/usr/lib/dagric/foundations.py blackbox --state-dir "$tmp/blackbox" sample
python3 config/includes.chroot/usr/lib/dagric/foundations.py blackbox --state-dir "$tmp/blackbox" status > "$tmp/status.json"

echo "foundations-check: live export/audit/plan and private Black Box sample passed"
