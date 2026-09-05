#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — the full translation QA pass: blind back-translation, then an
# independent judge, for every catalogue.
#
#     sh tools/i18n-qa-run.sh            all languages
#     sh tools/i18n-qa-run.sh fr it      only these
#
# WHAT IT DOES, AND WHY IN THIS ORDER. Three model families, each checking work
# it did not produce:
#
#   1. deepseek-v4-pro back-translates every msgstr into English, BLIND — it is
#      told the target language and nothing else. No product name, no source
#      file, no description of what the program does. A model that cannot see
#      the English cannot agree with it, which is the entire mechanism.
#   2. glm-5.2 compares each back-translation against the real English source
#      and marks it SAME, DRIFT or INVERSION.
#   3. A person reads the INVERSIONs.
#
# It is not theoretical. Run against the pre-fix French, this pipeline recovered
# "Dagric can copy your Documents … there" from a string whose English says
# "copy … over" — the inversion of the product's "Windows is only ever READ"
# guarantee, which a full review pass had already looked at and let through
# because catching it there required noticing a French preposition.
#
# ON QUOTA. The Qwen Token Plan enforces a rolling 5-hour quota and a 429 kills
# a run mid-pass. The back-translation stage therefore runs on the DIRECT
# DeepSeek account (metered, separate balance) and only the judge stage touches
# the Token Plan — so an exhausted subscription costs you the cheaper half of
# the work, not both. If the judge 429s, the renders are already on disk and
# `judge` can be re-run alone.
#
# Output, per language, under out/i18n-qa/:
#   bt-<lang>.json     every string with its blind back-translation
#   drift-<lang>.json  the judge's verdicts, flagged entries only
set -e

cd "$(dirname "$0")/.."
OUT=out/i18n-qa
mkdir -p "$OUT"

LANGS="$*"
[ -n "$LANGS" ] || LANGS="de es fr it pt_BR"

for L in $LANGS; do
    echo "=== $L ==============================================================="
    if [ ! -f "$OUT/bt-$L.json" ]; then
        python tools/i18n-backtranslate.py render --lang "$L" --out "$OUT/bt-$L.json"
    else
        echo "  render already on disk, skipping"
    fi
    python tools/i18n-backtranslate.py judge --in "$OUT/bt-$L.json" \
        --out "$OUT/drift-$L.json" || {
        echo "  judge failed for $L (quota?) — the render is kept; re-run:"
        echo "    python tools/i18n-backtranslate.py judge --in $OUT/bt-$L.json --out $OUT/drift-$L.json"
    }
done

echo
echo "=== INVERSIONS — read every one of these ==============================="
python - "$OUT" <<'PY'
import glob, json, io, os, sys
out = sys.argv[1]
total = 0
for p in sorted(glob.glob(os.path.join(out, "drift-*.json"))):
    d = json.load(io.open(p, encoding="utf-8"))
    inv = [r for r in d["flagged"] if r["verdict"] == "INVERSION"]
    dri = [r for r in d["flagged"] if r["verdict"] == "DRIFT"]
    total += len(inv)
    print("%-6s %3d/%d flagged  (%d INVERSION, %d DRIFT)"
          % (d["lang"], len(d["flagged"]), d["total"], len(inv), len(dri)))
    for r in inv:
        print("   [%s] %s" % (r["source"], r["note"]))
        print("      EN  : %s" % r["msgid"][:120].replace("\n", " | "))
        print("      BACK: %s" % r["back"][:120])
print("\n%d inversion(s) across all catalogues." % total)
PY
