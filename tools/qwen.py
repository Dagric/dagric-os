#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Call the Qwen Cloud Token Plan endpoint, or the direct DeepSeek one.

WHY THIS EXISTS AS A FILE. The credential belongs in exactly one place and that
place is not a shell command, a transcript, or an argument list. It is read from
.secrets/qwen.key, which .gitignore covers twice (`.secrets/` and `*.key`), and
it is never printed — --check reports only whether it authenticated.

TWO ACCOUNTS, ROUTED BY MODEL ID. .secrets holds a second, unrelated pair —
deepseek.key and deepseek.base — and a model id starting with "deepseek" is
served from it when that key exists. See _route() for why that matters: the two
accounts have separate quotas, and treating them as one turned a three-model
panel into a single point of failure. QWEN_API_KEY / QWEN_BASE_URL override
both.

The base URL is not the one the Qwen documentation shows first. A Token Plan
subscription is served from its own regional host:

    https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1

and the ordinary DashScope hosts reject a Token Plan key outright with
"Incorrect API key provided", which reads exactly like a bad key rather than a
wrong endpoint. That cost a round of debugging and is why the base URL lives in
.secrets/qwen.base rather than being remembered.

Models on this plan (GET /models): qwen3.8-max, qwen3.8-max-preview,
qwen3.7-max, qwen3.7-plus, qwen3.6-flash, glm-5.2, deepseek-v4-pro,
deepseek-v4-flash-0731, wan2.7-image, wan2.7-image-pro,
qwen-audio-3.0-tts-plus.

Note that qwen3.8-max returns a `reasoning_content` field alongside `content`.
Only `content` is the answer; printing both would paste the model's scratchpad
into whatever consumes this.

Usage:
  python tools/qwen.py --check
  python tools/qwen.py --models
  python tools/qwen.py --prompt-file brief.md --out out.md [--model qwen3.8-max]
  echo "question" | python tools/qwen.py
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(ROOT, ".secrets", "qwen.key")
BASE_FILE = os.path.join(ROOT, ".secrets", "qwen.base")
DEFAULT_BASE = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-max"


def use_utf8_stdout():
    """Let stdout carry characters the console codepage has no slot for.

    Windows hands Python a cp1252 stdout. A model that emits U+2011 — the
    non-breaking hyphen, which cp1252 cannot represent at all — turns a bare
    print() into UnicodeEncodeError. That is not a cosmetic failure: it strikes
    AFTER the request has been paid for and the answer parsed, so a completed
    result is destroyed on its way to the screen by one character of
    punctuation. errors="replace" makes the worst case a wrong-looking glyph.

    Called from main(), not at import, so importing this module never mutates
    a caller's streams behind its back.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # already detached, or not a TextIOWrapper — nothing to fix


def _read(path, fallback=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return fallback


def _key():
    k = os.environ.get("QWEN_API_KEY") or _read(KEY_FILE)
    if not k:
        sys.exit(
            "No API key. Put it in .secrets/qwen.key (gitignored) or set "
            "QWEN_API_KEY.\n"
            "  read -s -p 'key: ' k && printf '%s' \"$k\" > .secrets/qwen.key"
        )
    return k


DS_KEY_FILE = os.path.join(ROOT, ".secrets", "deepseek.key")
DS_BASE_FILE = os.path.join(ROOT, ".secrets", "deepseek.base")
DS_DEFAULT_BASE = "https://api.deepseek.com"


def _route(model):
    """Pick the account that should serve this model.

    DeepSeek models exist on BOTH accounts: the Qwen Cloud Token Plan carries
    deepseek-v4-pro, and there is a direct DeepSeek account with its own
    balance. They are not interchangeable in the way that matters — the Token
    Plan enforces a rolling 5-hour quota, and when it is exhausted every model
    on it returns 429 including the DeepSeek ones.

    That is not hypothetical: an audit run had all three panel members die at
    once mid-pass, and the separate DeepSeek balance sat unused because this
    client only ever read .secrets/qwen.key. A three-model panel whose members
    share one quota is one model wearing three hats.

    So deepseek-* prefers the direct account whenever its key is present, and
    falls back to the Token Plan when it is not. An explicit QWEN_API_KEY or
    QWEN_BASE_URL in the environment still wins over both, because callers that
    set them are doing so deliberately.

    The host comes from .secrets/deepseek.base, not from a constant here. Both
    halves of a credential move together — an account that changes region or
    path changes its key too — so the pair is read from the pair of files, the
    same way the Token Plan's is. A literal in this file would be a second
    place to remember, which is the mistake .secrets/qwen.base exists to avoid.
    """
    if os.environ.get("QWEN_API_KEY") or os.environ.get("QWEN_BASE_URL"):
        return None
    if model.startswith("deepseek"):
        k = _read(DS_KEY_FILE)
        if k:
            return k, (_read(DS_BASE_FILE) or DS_DEFAULT_BASE)
    return None


def _base():
    # `or`, not _read's fallback argument: a present-but-empty file reads as ""
    # and would otherwise be handed on as the base URL, producing a baffling
    # "could not reach" against the empty string rather than a working default.
    return os.environ.get("QWEN_BASE_URL") or _read(BASE_FILE) or DEFAULT_BASE


def _creds(model):
    r = _route(model)
    return r if r else (_key(), _base())


def _post(path, payload, timeout):
    key, base = _creds(payload.get("model", ""))
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        # `base`, not _base(). Reporting the Token Plan host for a request that
        # went to DeepSeek is how a quota problem gets diagnosed as a key
        # problem — the failure this whole routing path exists to make visible.
        # Still deliberately not echoing the key or the Authorization header.
        sys.exit("HTTP %s from %s\n%s" % (e.code, base + path, body[:1500]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach %s: %s" % (base + path, e.reason))


def _get(path, model="", timeout=60):
    key, base = _creds(model)
    req = urllib.request.Request(
        base + path, headers={"Authorization": "Bearer " + key}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s from %s\n%s"
                 % (e.code, base + path, e.read().decode("utf-8", "replace")[:800]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach %s: %s" % (base + path, e.reason))


def ask(prompt, system=None, model=DEFAULT_MODEL, max_tokens=8192,
        temperature=0.7, timeout=1800):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    d = _post("/chat/completions", {
        "model": model,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }, timeout)
    ch = d.get("choices") or []
    if not ch:
        sys.exit("No choices in response: " + json.dumps(d)[:800])
    # `content`, never `reasoning_content` — the latter is the model's
    # scratchpad and is not the answer.
    text = ch[0].get("message", {}).get("content") or ""
    return text, d.get("usage", {})


def main():
    use_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="authenticate and exit")
    ap.add_argument("--models", action="store_true", help="list available models")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system")
    ap.add_argument("--system-file")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--out")
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    if a.models:
        # Routed on --model so `--models --model deepseek-v4-pro` lists the
        # direct DeepSeek account. Without this, --models could only ever show
        # the Token Plan's catalogue while --check happily talked to the other
        # account, which reads as a model that exists and cannot be listed.
        for m in _get("/models", a.model).get("data", []):
            print(m["id"])
        return

    if a.check:
        # 512, not 16. These are REASONING models: they spend budget on a
        # scratchpad before emitting a token of answer. At 16 the direct
        # DeepSeek account returned finish_reason="length" with all 16 tokens
        # billed as reasoning_tokens and content "" — a call that authenticated
        # perfectly and printed as ''. That is the worst reading available,
        # because '' is what a broken credential would also look like, and the
        # command it misleads is the one used to confirm routing works.
        txt, usage = ask("Reply with exactly: ok", model=a.model, max_tokens=512,
                         temperature=0)
        # Reaching this line means authentication succeeded — _post exits on any
        # HTTP error — so say so, and name the host that answered. That is the
        # fact --check exists to establish, and with two accounts in play the
        # host is the half that tells you which one you actually reached.
        base = _creds(a.model)[1]
        print("%s -> AUTHENTICATED via %s  (%s tokens)  reply=%r"
              % (a.model, base, usage.get("total_tokens", "?"), txt.strip()))
        return

    prompt = a.prompt
    if a.prompt_file:
        prompt = _read(a.prompt_file)
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read()
    if not prompt:
        sys.exit("Nothing to ask. Use --prompt, --prompt-file, or pipe stdin.")

    system = a.system
    if a.system_file:
        system = _read(a.system_file)

    text, usage = ask(prompt, system=system, model=a.model,
                      max_tokens=a.max_tokens, temperature=a.temperature,
                      timeout=a.timeout)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("%s -> %s  (%s prompt + %s completion tokens)"
              % (a.model, a.out, usage.get("prompt_tokens", "?"),
                 usage.get("completion_tokens", "?")), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
