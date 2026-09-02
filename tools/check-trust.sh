#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

python3 test/test-trust.py
python3 config/includes.chroot/usr/lib/dagric/trust.py audit

echo "trust-check: Support Mode, privacy boundary, hardware passport, protection status and history summary passed"
