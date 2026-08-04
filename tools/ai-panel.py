#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ask the same question of several different models and report where they disagree.

WHY THIS EXISTS. This project's expensive failures have all been the same shape:
a confident claim that nobody checked against a second source. The NVIDIA
sources, the Horizon dock drawn as a floating pill, the disk floor that promised
Pro would fit, the comment asserting a property the code did not have — every
one survived a self-review and died the moment something else looked at it.

A second pass by the SAME model is a weak check: it shares the first pass's
blind spots and its training. A different model family does not. The Qwen Cloud
Token Plan on this account serves several unrelated families through one
endpoint — Qwen, GLM and DeepSeek — so a three-way panel costs one subscription
and buys genuinely independent readings.

INDEPENDENT IN TRAINING IS NOT INDEPENDENT IN AVAILABILITY, and that distinction
cost a run. One endpoint means one rolling 5-hour quota, so when it emptied all
three panel members returned the same 429 from the same host within a second of
each other. The standing advice — fall back to --models deepseek-v4-pro, which
is on a separate account — was false while this tool read one credential pair:
the fallback resolved to the same exhausted plan. tools/qwen.py now routes
deepseek-* to .secrets/deepseek.{key,base}, so that fallback is real. The panel
still shares a quota by default; only the DeepSeek member escapes it.

The output that matters is DISAGREEMENT. Unanimity is weak evidence (models
share plenty of priors); a split is a reliable signal that the question is
actually hard and a human should look. So this prints the split first and does
not try to average anything away.

THE PANEL IS ONLY AS GOOD AS THE BRIEF, AND THE FIRST REAL RUN PROVED IT. A
finding that had already been measured in a browser — a 19rem grid track
overflowing a 280px container at a 320px viewport — was put to the panel with
the CSS pasted but WITHOUT the rendered measurement. deepseek-v4-pro did the
arithmetic and said STANDS. qwen3.8-max said REFUTED on the grounds that no
overflow measurement was supplied, which is not a stupid answer: it is correct
epistemic caution, and the verdict contract below explicitly tells it to refuse
when the material is insufficient. glm-5.2 ran out of tokens mid-reasoning and
returned nothing at all.

Two rules follow, and ignoring either makes this tool worse than useless because
it manufactures confident-looking disagreement out of a bad prompt:
  1. PASTE THE EVIDENCE, not just the artifact. These models cannot see the
     repository, run a browser, or check a file. A claim sent without its
     measurement will be refuted for lacking one.
  2. GIVE THEM ROOM. See the note on --max-tokens.

Usage:
  python tools/ai-panel.py --prompt-file brief.md
  python tools/ai-panel.py --prompt-file brief.md --models qwen3.8-max,glm-5.2,deepseek-v4-pro
  python tools/ai-panel.py --prompt-file claim.md --verdict   # ask for YES/NO first token
  echo "question" | python tools/ai-panel.py --out-dir answers/

Paths: pass ABSOLUTE Windows-style paths (C:/Users/...). A /tmp/... path is
mangled by MSYS translation between Git Bash and Windows Python and will not be
found — that cost a debugging round the first time.
"""
import argparse
import concurrent.futures as cf
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qwen  # noqa: E402  — the single-call client and the credential handling

# Three unrelated families, which is the entire point. Adding a fourth Qwen
# variant here would cost tokens and buy almost nothing: near-identical training
# produces near-identical mistakes, and this file exists to catch the mistakes
# one lineage cannot see in itself.
DEFAULT_PANEL = ["qwen3.8-max", "glm-5.2", "deepseek-v4-pro"]

VERDICT_SUFFIX = """

Answer in this exact shape and nothing else:

VERDICT: <STANDS or REFUTED>
CONFIDENCE: <HIGH, MEDIUM or LOW>
WHY: <at most three sentences, citing the specific evidence that decided it>

If the material given to you is not sufficient to decide, say REFUTED and
explain in WHY what is missing. Do not guess, and do not assume facts that were
not pasted in — you cannot see the repository."""


def _verdict_of(text):
    m = re.search(r'VERDICT:\s*(STANDS|REFUTED)', text or "", re.I)
    return m.group(1).upper() if m else "UNCLEAR"


def run(prompt, models, max_tokens, temperature, system=None):
    """Query every model concurrently. One failure must not lose the others."""
    def one(m):
        try:
            text, usage = qwen.ask(prompt, system=system, model=m,
                                   max_tokens=max_tokens, temperature=temperature)
            return m, text, usage, None
        except SystemExit as e:
            # qwen.ask calls sys.exit on an HTTP error; catching it keeps one
            # dead model from taking the whole panel down with it.
            return m, None, {}, str(e)
        except Exception as e:
            return m, None, {}, repr(e)

    with cf.ThreadPoolExecutor(max_workers=len(models)) as ex:
        return list(ex.map(one, models))


def main():
    # FIRST, before anything can reach a stream. A panel answer is the most
    # expensive text this repo produces — three concurrent reasoning calls,
    # minutes of wall clock, real tokens — and printing it is the last step.
    # A U+2011 non-breaking hyphen in one model's prose raised
    # UnicodeEncodeError on Windows' cp1252 stdout and discarded a run that had
    # already completed and been parsed. See qwen.use_utf8_stdout.
    qwen.use_utf8_stdout()

    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--system-file")
    ap.add_argument("--models", default=",".join(DEFAULT_PANEL))
    ap.add_argument("--verdict", action="store_true",
                    help="append the STANDS/REFUTED contract and tally the split")
    ap.add_argument("--out-dir", help="write each model's full answer to its own file")
    # 12000, not 4000. These are REASONING models and the budget covers the
    # scratchpad as well as the answer. Measured on a single short question:
    # qwen3.8-max spent 10,379 completion tokens to emit a sixty-word verdict,
    # and glm-5.2 hit a 900-token ceiling mid-thought and returned an EMPTY
    # string — which the parser then scored as UNCLEAR. That is the worst
    # possible failure mode for a panel: a truncated model looks like an
    # abstaining model, so a budget that is merely too low silently turns into a
    # third opinion that was never actually given.
    #
    # RAISED FROM 12000 TO 24000 after glm-5.2 truncated at exactly 12001
    # completion tokens on two separate real questions — once on the reflow
    # claim and again on the NVIDIA blacklist claim — returning an empty
    # string both times and scoring UNCLEAR. Twice is a pattern, not bad luck:
    # this model spends far more of its budget reasoning than the other two
    # (deepseek answered the same question in 1,442 tokens, qwen in 17,517),
    # so a ceiling that is comfortable for two of the panel silently removes
    # the third. A panel that reports 2-1 when it was really 2-0-and-a-timeout
    # is worse than one that reports nothing.
    ap.add_argument("--max-tokens", type=int, default=24000)
    ap.add_argument("--temperature", type=float, default=0.2)
    a = ap.parse_args()

    prompt = a.prompt
    if a.prompt_file:
        with open(a.prompt_file, encoding="utf-8") as fh:
            prompt = fh.read()
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read()
    if not prompt:
        sys.exit("Nothing to ask. Use --prompt, --prompt-file, or pipe stdin.")
    if a.verdict:
        prompt += VERDICT_SUFFIX

    system = None
    if a.system_file:
        with open(a.system_file, encoding="utf-8") as fh:
            system = fh.read()

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    results = run(prompt, models, a.max_tokens, a.temperature, system)

    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)

    verdicts = {}
    for m, text, usage, err in results:
        print("=" * 72)
        if err:
            print("%s  — FAILED: %s" % (m, err.strip()[:200]))
            continue
        v = _verdict_of(text)
        verdicts[m] = v
        print("%s%s  (%s completion tokens)"
              % (m, ("  [" + v + "]") if a.verdict else "",
                 usage.get("completion_tokens", "?")))
        print("-" * 72)
        print(text.strip())
        if a.out_dir:
            p = os.path.join(a.out_dir, m.replace("/", "_") + ".txt")
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)

    if a.verdict and verdicts:
        print("=" * 72)
        tally = {}
        for v in verdicts.values():
            tally[v] = tally.get(v, 0) + 1
        split = len(set(verdicts.values())) > 1
        print("PANEL: " + "  ".join("%s=%s" % (m, v) for m, v in verdicts.items()))
        print("TALLY: " + "  ".join("%s x%d" % (k, n) for k, n in sorted(tally.items())))
        # The split is the product. A unanimous panel is weak evidence — these
        # models share plenty of priors — but a disagreement reliably marks a
        # question that deserves a person.
        print("RESULT: " + ("SPLIT — a human should decide this one"
                            if split else "unanimous " + next(iter(tally))))
        sys.exit(2 if split else 0)


if __name__ == "__main__":
    main()
