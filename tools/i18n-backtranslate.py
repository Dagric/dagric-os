#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blind back-translation: catch meaning drift without asking a model's opinion.

WHY THIS IS DIFFERENT FROM A REVIEW, AND STRONGER. A reviewer is shown the
English and the translation together and asked "is this right?" — and a model
shown both will pattern-match them into agreement more often than it should.
That is how the French catalogue kept a defect through a full careful review
pass: dagric-migrate rendered "copy your files FROM the Windows drive" as
"y copier", which reads as copying TO it, inverting the one guarantee the whole
migration tool rests on. The reviewer that eventually found it had to notice a
preposition. Nothing forced the issue.

Back-translation forces it. A model that has NEVER SEEN the English source is
given only the translated string and asked to render it in English. Then the
round trip is compared to the original. A meaning inversion cannot survive that:
if the French says "copy to Windows", the back-translation says "copy to
Windows", and it no longer matches a source that says "copy from". No judgement
call, no opinion, no chance to agree with something it can see.

BLINDNESS IS THE WHOLE MECHANISM AND IT IS EASY TO DESTROY. The back-translator
must not be told the product name, the source file, what the program does, or
anything else that would let it reconstruct the English it is supposed to be
recovering independently. Every one of those is context a REVIEW would want and
this must not have. If you find yourself adding context here to improve the
output, you are converting the test back into the weaker thing.

THREE MODELS, THREE JOBS, NO MARKING OF OWN HOMEWORK:
  qwen3.8-max      reviewed and proposed the translations (tools/i18n-qwen-review.py)
  deepseek-v4-pro  back-translates, blind — a different family from the reviewer
  glm-5.2          judges whether the round trip preserved the meaning
Each stage is a family that did not produce the thing it is checking.

Usage:
  python tools/i18n-backtranslate.py render --lang fr --out bt-fr.json
  python tools/i18n-backtranslate.py judge  --in  bt-fr.json --out drift-fr.json
  python tools/i18n-backtranslate.py render --lang fr --po /path/to/old.po --out bt-old.json
"""
import argparse
import concurrent.futures as cf
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import qwen  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "i18nreview", os.path.join(ROOT, "tools", "i18n-review.py"))
_rev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rev)

LANGNAME = {"de": "German", "es": "Spanish", "fr": "French",
            "it": "Italian", "pt_BR": "Brazilian Portuguese"}

# The back-translator's entire world. No product name, no domain, no purpose.
BT_SYSTEM = """You translate {lang} into English.

Render each numbered line literally and completely. Preserve the direction of
every action (from/to, into/out of), every negation, every modal (must, may,
can, will), and every conditional exactly as the {lang} states them — even
where the result is awkward English. Do not improve, shorten, explain or guess
at intent.

Leave untouched, exactly as they appear: anything beginning with $ or %,
anything inside [ ], and any URL or capitalised product name.

Output format, and nothing else — no preamble, no commentary, no fences:
<number>|<English>

One line per input. Keep the numbering. If an input is empty, output the number
and an empty field."""

JUDGE_SYSTEM = """You are comparing an original English UI string against an English
back-translation of its {lang} rendering. The back-translator never saw the
original.

Your only question: could a reader act differently on these two?

Answer for each pair, one per line, nothing else:
<number>|<SAME or DRIFT or INVERSION>|<at most 12 words>

INVERSION  — direction, negation, permission or obligation is reversed. Copying
             FROM became copying TO. "Never" became "not always". "You must"
             became "you may". This is the category that hurts people.
DRIFT      — a fact changed: a quantity, a condition, a scope, a named thing,
             or something the original said that is now absent.
SAME       — the two would lead a reader to do the same thing. Different
             wording, different register, clumsier phrasing and lost idiom are
             all SAME. The back-translation is deliberately literal; do not
             mark it DRIFT for being ugly.

When genuinely unsure, answer DRIFT. A false DRIFT costs someone a minute of
reading; a missed INVERSION ships."""


def _client(model):
    """Route to whichever account serves this model.

    deepseek-* runs against the direct DeepSeek account when a key exists, so
    the back-translation does not share an endpoint, a quota or an account with
    the review it is checking. It falls back to the Qwen Token Plan, which also
    carries deepseek-v4-pro, if there is no direct key.
    """
    dk = os.path.join(ROOT, ".secrets", "deepseek.key")
    if model.startswith("deepseek") and os.path.exists(dk):
        return {"QWEN_API_KEY": open(dk, encoding="utf-8").read().strip(),
                "QWEN_BASE_URL": "https://api.deepseek.com"}
    return {}


def _ask(model, system, prompt, max_tokens):
    saved = {k: os.environ.get(k) for k in ("QWEN_API_KEY", "QWEN_BASE_URL")}
    try:
        for k, v in _client(model).items():
            os.environ[k] = v
        return qwen.ask(prompt, system=system, model=model,
                        max_tokens=max_tokens, temperature=0, timeout=2400)[0]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _numbered(rows):
    return "\n".join("%d|%s" % (i, t.replace("\n", " ⏎ ")) for i, t in rows)


def _parse_numbered(text, want):
    out = {}
    for line in (text or "").split("\n"):
        m = re.match(r'\s*(\d+)\s*\|(.*)$', line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def cmd_render(a):
    po = a.po or os.path.join(ROOT, "po", a.lang + ".po")
    ents = [e for e in _rev.parse(po) if e["msgstr"].strip()]
    lang = LANGNAME[a.lang]
    system = BT_SYSTEM.format(lang=lang)
    chunks = [ents[i:i + a.per_call] for i in range(0, len(ents), a.per_call)]
    print("%s: %d strings, %d call(s), model %s (BLIND — no English source sent)"
          % (a.lang, len(ents), len(chunks), a.model), file=sys.stderr)

    def one(ix):
        i, chunk = ix
        rows = [(n, e["msgstr"]) for n, e in enumerate(chunk)]
        txt = _ask(a.model, system, _numbered(rows), a.max_tokens)
        got = _parse_numbered(txt, len(chunk))
        print("  chunk %-2d %3d strings -> %3d back-translated"
              % (i, len(chunk), len(got)), file=sys.stderr)
        return [{"msgid": e["msgid"], "msgstr": e["msgstr"],
                 "back": got.get(n, ""), "source": e["source"]}
                for n, e in enumerate(chunk)]

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        rows = [r for part in ex.map(one, enumerate(chunks)) for r in part]
    json.dump({"lang": a.lang, "model": a.model, "rows": rows},
              open(a.out, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    done = sum(1 for r in rows if r["back"])
    print("%s: %d/%d back-translated -> %s" % (a.lang, done, len(rows), a.out),
          file=sys.stderr)


def cmd_judge(a):
    d = json.load(open(a.infile, encoding="utf-8"))
    rows = [r for r in d["rows"] if r["back"]]
    system = JUDGE_SYSTEM.format(lang=LANGNAME[d["lang"]])
    chunks = [rows[i:i + a.per_call] for i in range(0, len(rows), a.per_call)]
    print("%s: judging %d pair(s), %d call(s), model %s"
          % (d["lang"], len(rows), len(chunks), a.model), file=sys.stderr)

    def one(ix):
        i, chunk = ix
        body = "\n".join(
            "%d|ORIGINAL: %s\n%d|BACK:     %s" % (n, r["msgid"].replace("\n", " ⏎ "),
                                                  n, r["back"])
            for n, r in enumerate(chunk))
        txt = _ask(a.model, system, body, a.max_tokens)
        got = _parse_numbered(txt, len(chunk))
        res = []
        for n, r in enumerate(chunk):
            raw = got.get(n, "")
            parts = raw.split("|", 1)
            verdict = (parts[0] or "").strip().upper() or "UNKNOWN"
            res.append(dict(r, verdict=verdict,
                            note=(parts[1].strip() if len(parts) > 1 else "")))
        flagged = sum(1 for x in res if x["verdict"] in ("DRIFT", "INVERSION"))
        print("  chunk %-2d %3d pairs -> %2d flagged" % (i, len(chunk), flagged),
              file=sys.stderr)
        return res

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        out = [r for part in ex.map(one, enumerate(chunks)) for r in part]
    flagged = [r for r in out if r["verdict"] in ("DRIFT", "INVERSION")]
    json.dump({"lang": d["lang"], "backtranslator": d["model"],
               "judge": a.model, "total": len(out), "flagged": flagged},
              open(a.out, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    inv = sum(1 for r in flagged if r["verdict"] == "INVERSION")
    print("%s: %d/%d flagged (%d INVERSION, %d DRIFT) -> %s"
          % (d["lang"], len(flagged), len(out), inv, len(flagged) - inv, a.out),
          file=sys.stderr)


DIR_W = {"from", "to", "into", "onto", "out", "over", "there", "here", "off",
         "back", "across", "away"}
NEG_W = {"not", "never", "no", "none", "cannot", "without", "n't", "nothing",
         "neither"}
MOD_W = {"must", "may", "can", "will", "should", "might", "could", "would",
         "shall"}


def cmd_triage(a):
    """Rank pairs by mechanical divergence, for when no judge model is reachable.

    THIS IS A NET, NOT A DETECTOR, and the difference is worth stating because
    the numbers flatter it. Measured against the known French inversion — the
    one a full review pass nearly missed — it scored the real defect at rank 24
    of 438 and flagged 85 pairs overall. So reading the top 25 finds it: a 94%
    cut in what a person has to read, which is genuinely useful.

    But most of the top of that list is noise. "Could not" against "Cannot",
    "OFF" against "DISABLED", "work out" against "determine" all score highly
    and none of them mean anything — the back-translator is asked to be literal,
    so synonym churn is expected and this scoring cannot tell it apart from
    meaning. `judge` is what actually decides; use this when the Token Plan's
    5-hour quota is exhausted and you still want somewhere to start.
    """
    d = json.load(open(a.infile, encoding="utf-8"))
    def toks(s):
        return set(re.findall(r"[a-z']+", s.lower()))
    def nums(s):
        return set(re.findall(r"\d+", s))
    scored = []
    for r in d["rows"]:
        if not r.get("back"):
            continue
        x, y = toks(r["msgid"]), toks(r["back"])
        s = (len((x & DIR_W) ^ (y & DIR_W)) * 3
             + len((x & NEG_W) ^ (y & NEG_W)) * 4
             + len((x & MOD_W) ^ (y & MOD_W)) * 2
             + len(nums(r["msgid"]) ^ nums(r["back"])) * 3)
        if s:
            scored.append((s, r))
    scored.sort(key=lambda t: -t[0])
    print("%s: %d of %d pairs diverge mechanically; showing top %d"
          % (d["lang"], len(scored), len(d["rows"]), a.top), file=sys.stderr)
    for s, r in scored[:a.top]:
        print("\nscore %-3d [%s]" % (s, r["source"]))
        print("  EN  : %s" % r["msgid"][:150].replace("\n", " | "))
        print("  BACK: %s" % r["back"][:150])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("triage")
    t.add_argument("--in", dest="infile", required=True)
    t.add_argument("--top", type=int, default=25)
    r = sub.add_parser("render")
    r.add_argument("--lang", required=True, choices=sorted(LANGNAME))
    r.add_argument("--po")
    r.add_argument("--out", required=True)
    r.add_argument("--model", default="deepseek-v4-pro")
    r.add_argument("--per-call", type=int, default=45)
    r.add_argument("--workers", type=int, default=3)
    r.add_argument("--max-tokens", type=int, default=16000)
    j = sub.add_parser("judge")
    j.add_argument("--in", dest="infile", required=True)
    j.add_argument("--out", required=True)
    j.add_argument("--model", default="glm-5.2")
    j.add_argument("--per-call", type=int, default=35)
    j.add_argument("--workers", type=int, default=3)
    j.add_argument("--max-tokens", type=int, default=16000)
    a = ap.parse_args()
    {"render": cmd_render, "judge": cmd_judge, "triage": cmd_triage}[a.cmd](a)


if __name__ == "__main__":
    main()
