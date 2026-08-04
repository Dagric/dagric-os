#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native-level review of po/*.po by a second model, in context, in batches.

WHY. Every catalogue in po/ is 100% translated and 0% reviewed. Each header says
so and names the strings that cost money when they are wrong. Those languages
are already advertised — the user guide is published in five of them — so the
review the headers ask for is overdue.

WHAT THIS IS NOT. It is not a re-translation. The existing machine output is
mechanically sound (tools/i18n-review.py check reports zero problems across all
five) and in places genuinely good: Spanish renders the accepted-answer list
"y yes" as "s si sí y yes", keeping the English letters a shell script still
tests for. A rewrite would risk that. So the reviewer is asked to CHANGE ONLY
WHAT IS WRONG and to justify every change, and anything it proposes still has to
pass the mechanical guards in i18n-review.py before it lands.

REGISTER IS FIXED PER LANGUAGE AND IS NOT THE REVIEWER'S TO CHOOSE. Measured
across the existing catalogues, each is already internally consistent with zero
mixing: de 261 formal / 0 informal, fr 117 / 0, es 0 formal / 64 informal,
it 0 / 44, pt_BR 0 / 54. That matches convention — German and French consumer
software addresses you formally, Spanish, Italian and Brazilian Portuguese do
not — and a reviewer "fixing" it would make the wizard and the guide disagree
with each other mid-sentence.

Batching is by SOURCE FILE, not by size, because the same English sentence means
different things in an installer, a migration tool and a games launcher, and a
reviewer shown a bare list has no way to tell which it is looking at.

Usage:
  python tools/i18n-qwen-review.py --lang es --in review-es.json --out changes-es.json
  python tools/i18n-qwen-review.py --lang es --in ... --out ... --model glm-5.2
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qwen  # noqa: E402

LANGS = {
    "de":    ("German",              "Sie (formal). 261 formal forms and zero informal ones in the current catalogue."),
    "es":    ("Spanish (Spain)",     "tú (informal). 64 informal forms and zero 'usted' in the current catalogue."),
    "fr":    ("French",              "vous (formal). 117 formal forms and zero 'tu' in the current catalogue."),
    "it":    ("Italian",             "tu (informal). 44 informal forms and zero 'Lei' in the current catalogue."),
    "pt_BR": ("Brazilian Portuguese", "você (informal). 54 informal forms and zero 'o senhor' in the current catalogue."),
}

# What each program is, so a string is reviewed for the job it actually does.
CONTEXT = {
    "dagric-migrate": "Copies the owner's files off the Windows partition still on the machine. The product's promise is that Windows is ONLY EVER READ, never modified. Negation and modality carry the liability here.",
    "dagric-usb-protect": "Blocks unknown USB devices. If a warning to plug in your keyboard and mouse BEFORE enabling it is softened or lost, the owner ends up with a machine they cannot type on.",
    "dagric-drivers": "Installs graphics drivers. The Secure Boot notice matters most: get it wrong and the next boot is a black screen.",
    "dagric-vm": "Runs Windows in a virtual machine. Contains consent wording; this product is sold in the EU.",
    "dagric-get-steam": "Offers to install Steam. Contains licence wording the owner is agreeing to.",
    "dagric-get-resolve": "Offers to install DaVinci Resolve. Contains licence wording.",
    "dagric-firstrun": "The first-run wizard. The very first sentences a new owner reads.",
    "dagric-hub": "The Dagric Hub — one window listing every owner tool. Mostly short menu rows; they must read as labels, not sentences.",
    "dagric-security-checkup": "Reports on firewall, updates, encryption and drive health. Alarming when it should be, calm when it should not.",
    "dagric-display": "Screen resolution, text size and night light.",
    "dagric-setup": "Post-install setup.",
    "dagric-gaming": "Steam, Proton and the gaming runtime.",
    "dagric-style": "Colour themes.",
    "dagric-looks": "Desktop layouts.",
    "dagric-data-strings.sh": "Menu entries and .desktop names. These are LABELS — short, title-style, no trailing full stop.",
}

BRIEF = """You are reviewing an existing machine translation of the user interface of
Dagric OS — a commercial Linux desktop sold to people leaving Windows 10. The
buyers are often not technical, often over sixty, and nervous about breaking the
only computer they own. The product's whole market position is that it does not
lie to them.

TARGET LANGUAGE: {lang_name}
REGISTER, ALREADY ESTABLISHED AND NOT YOURS TO CHANGE: {register}

You are a native speaker of {lang_name} reviewing this for release. The existing
translation is machine-produced and has never been read by a native speaker.
Some of it is good. Your job is to find what is WRONG, not to restyle what is
merely different from your preference.

CHANGE A STRING ONLY IF ONE OF THESE IS TRUE:
  1. It is wrong — mistranslated, or it says something the English does not.
  2. It inverts or weakens a negation, a permission, or a safety warning.
     ("Windows is only ever read" must not become "Windows is not changed much".)
  3. It is not what a native speaker would ever say — machine-shaped word order,
     a false friend, a literal idiom.
  4. It uses the wrong register, breaking the consistency stated above.
  5. It is a UI LABEL written as a sentence, or a sentence written as a label.
  6. Its terminology contradicts the rest of the catalogue — the same English
     term must get the same translation everywhere.

DO NOT CHANGE:
  - Anything merely stylistic. If it is correct and natural, leave it.
  - Product, application and command names: Dagric, Steam, Bottles, Proton,
    Wine, Ollama, Flatpak, Flathub, GitHub, NVIDIA, BitLocker, Firefox,
    LibreOffice, Windows, and every dagric-* command. These are names.
  - Shell and printf substitutions: $NAME, ${{NAME}}, %s, %d. They must appear in
    your translation exactly as in the English, same spelling, none added, none
    lost. A lost one prints a literal "$WINUSER" at the owner.
  - URLs.
  - ACCEPTED-ANSWER LISTS. A msgid like "y yes" is the set of replies a [y/N]
    prompt accepts. The translation must keep the English letters AND add the
    target language's. Spanish already does this correctly as "s si sí y yes".
    Dropping "y" means the owner types the letter the prompt showed them and
    nothing happens.
  - Keyboard key names as they are printed on a keyboard in that language.

OUTPUT: strict JSON, nothing else. No markdown fence, no commentary.

{{"changes":[
  {{"msgid":"<the English source, copied EXACTLY, byte for byte>",
    "new":"<your corrected translation>",
    "reason":"<one short sentence: what was wrong>",
    "severity":"<safety|meaning|fluency|terminology|label>"}}
]}}

An empty list is a perfectly good answer for a batch that is already correct —
and a better answer than inventing work. Return ONLY the entries you changed.
"""


def batches(groups, per_call):
    """Group by source file, then pack groups into calls without splitting one."""
    out, cur, n = [], [], 0
    for src, items in groups.items():
        if cur and n + len(items) > per_call:
            out.append(cur); cur, n = [], 0
        cur.append((src, items)); n += len(items)
    if cur:
        out.append(cur)
    return out


def render(batch):
    lines = []
    for src, items in batch:
        ctx = CONTEXT.get(src, "")
        lines.append("\n--- from %s%s" % (src, ("  [" + ctx + "]") if ctx else ""))
        for it in items:
            lines.append("EN: " + json.dumps(it["msgid"], ensure_ascii=False))
            lines.append("CURRENT: " + json.dumps(it["current"], ensure_ascii=False))
    return "\n".join(lines)


def extract_json(text):
    """Models wrap JSON in prose or fences more often than not."""
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t, flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    depth = start = None
    for i, ch in enumerate(t):
        if ch == '{':
            if depth is None:
                depth, start = 0, i
            depth += 1
        elif ch == '}' and depth is not None:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except Exception:
                    depth = start = None
    return {"changes": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=sorted(LANGS))
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="qwen3.8-max")
    ap.add_argument("--per-call", type=int, default=70)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=24000)
    a = ap.parse_args()

    data = json.load(open(a.infile, encoding="utf-8"))
    name, register = LANGS[a.lang]
    system = BRIEF.format(lang_name=name, register=register)
    packs = batches(data["groups"], a.per_call)
    print("%s: %d entries, %d call(s) of <=%d, model %s"
          % (a.lang, data["total"], len(packs), a.per_call, a.model), file=sys.stderr)

    def one(idx_batch):
        idx, batch = idx_batch
        body = render(batch)
        prompt = ("Review these strings. Return ONLY the JSON object described "
                  "in your instructions.\n" + body)
        try:
            text, usage = qwen.ask(prompt, system=system, model=a.model,
                                   max_tokens=a.max_tokens, temperature=0.2,
                                   timeout=2400)
        except SystemExit as e:
            print("  batch %d FAILED: %s" % (idx, str(e)[:160]), file=sys.stderr)
            return []
        got = extract_json(text).get("changes", []) or []
        print("  batch %-2d %3d strings -> %2d change(s)  (%s tok)"
              % (idx, sum(len(i) for _, i in batch), len(got),
                 usage.get("completion_tokens", "?")), file=sys.stderr)
        return got

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(one, enumerate(packs)))

    changes, seen = [], set()
    for r in results:
        for c in r:
            k = c.get("msgid")
            if k and k not in seen and c.get("new"):
                seen.add(k); changes.append(c)

    known = {it["msgid"] for g in data["groups"].values() for it in g}
    # A change whose msgid was not in the batch is a hallucinated or reworded
    # source string; applying it would silently do nothing, so drop it loudly.
    unknown = [c for c in changes if c["msgid"] not in known]
    changes = [c for c in changes if c["msgid"] in known]
    if unknown:
        print("  dropped %d change(s) whose msgid does not exist in the catalogue"
              % len(unknown), file=sys.stderr)

    json.dump({"lang": a.lang, "model": a.model, "changes": changes},
              open(a.out, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    by = {}
    for c in changes:
        by[c.get("severity", "?")] = by.get(c.get("severity", "?"), 0) + 1
    print("%s: %d proposed change(s) -> %s   %s"
          % (a.lang, len(changes), a.out,
             " ".join("%s=%d" % kv for kv in sorted(by.items()))), file=sys.stderr)


if __name__ == "__main__":
    main()
