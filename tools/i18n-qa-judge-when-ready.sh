#!/bin/sh
# Wait for the Qwen Token Plan's 5-hour quota window to reopen, then run the
# judge stage over the back-translations already on disk.
#
# WHY A WAITER AND NOT A RETRY LOOP. The judge is glm-5.2 deliberately: the
# back-translation was done by deepseek-v4-pro, and a judge from the same family
# as the translator is marking its own homework. DeepSeek is reachable right now
# and glm is not, so the correct move is to wait rather than to substitute — the
# independence IS the check.
#
# The renders are the expensive half and they are already complete, so nothing
# is lost by waiting.
set -e
cd "$(dirname "$0")/.."
TARGET=$(date -u -d '2026-08-04 10:06:00' +%s)
while [ "$(date -u +%s)" -lt "$TARGET" ]; do sleep 300; done
for L in de es fr it pt_BR; do
    [ -f "out/i18n-qa/bt-$L.json" ] || continue
    python tools/i18n-backtranslate.py judge \
        --in "out/i18n-qa/bt-$L.json" --out "out/i18n-qa/drift-$L.json" || true
done
