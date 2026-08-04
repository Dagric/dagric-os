#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Call the Qwen Cloud Token Plan endpoint.

WHY THIS EXISTS AS A FILE. The credential belongs in exactly one place and that
place is not a shell command, a transcript, or an argument list. It is read from
.secrets/qwen.key, which .gitignore covers twice (`.secrets/` and `*.key`), and
it is never printed — --check reports only whether it authenticated.

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


def _base():
    return os.environ.get("QWEN_BASE_URL") or _read(BASE_FILE, DEFAULT_BASE)


def _post(path, payload, timeout):
    req = urllib.request.Request(
        _base() + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + _key(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        # Deliberately not echoing the key or the Authorization header here.
        sys.exit("HTTP %s from %s\n%s" % (e.code, _base() + path, body[:1500]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach %s: %s" % (_base(), e.reason))


def _get(path, timeout=60):
    req = urllib.request.Request(
        _base() + path, headers={"Authorization": "Bearer " + _key()}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s\n%s" % (e.code, e.read().decode("utf-8", "replace")[:800]))


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
        for m in _get("/models").get("data", []):
            print(m["id"])
        return

    if a.check:
        txt, usage = ask("Reply with exactly: ok", model=a.model, max_tokens=16,
                         temperature=0)
        print("%s -> %r  (%s tokens)"
              % (a.model, txt.strip(), usage.get("total_tokens", "?")))
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
