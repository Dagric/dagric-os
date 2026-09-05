#!/usr/bin/env python3
"""Complete release-blocking PO entries with guarded machine translation.

This is not a native-speaker approval.  It replaces only fuzzy or untranslated
entries, preserves the catalogue's established register, validates variables,
URLs and product names, and leaves the existing no-native-review disclosure in
each PO header.  Responses are cached by prompt hash so an interrupted run can
resume without paying for the same public strings twice.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from babel.messages.pofile import read_po, write_po


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen  # noqa: E402

REVIEW_SPEC = importlib.util.spec_from_file_location(
    "dagric_i18n_review", ROOT / "tools/i18n-review.py"
)
assert REVIEW_SPEC and REVIEW_SPEC.loader
REVIEW = importlib.util.module_from_spec(REVIEW_SPEC)
REVIEW_SPEC.loader.exec_module(REVIEW)

LANGUAGES = {
    "de": ("German", "formal Sie throughout"),
    "es": ("Spanish (Spain)", "informal tú throughout"),
    "fr": ("French", "formal vous throughout"),
    "it": ("Italian", "informal tu throughout"),
    "pt_BR": ("Brazilian Portuguese", "informal você throughout"),
}

SYSTEM = """You are completing release-blocking operating-system UI translations.

Target: {language}. Established register: {register}.

Translate accurately, naturally, and completely. Preserve every variable,
format token, command, filesystem path, URL, keyboard shortcut, unit, line
break, bullet, and bracketed prompt such as [y/N]. Never translate product,
provider, application, or command names including Dagric, Debian, KDE, Plasma,
Steam, Valve, GOG, Epic Games Store, Amazon Games, Heroic, Wine, Proton,
GE-Proton, Ollama, Flatpak, Flathub, GitHub, NVIDIA, Windows, Firefox, Chromium,
Thunderbird, VS Code, OBS, Blender, Krita, LibreOffice, Audacity, Secure Boot,
BitLocker, AppArmor, OpenSnitch, and KVM.

Safety wording is literal: keep negation, direction, consent, privacy scope,
provider terms, and "nothing was changed/installed" claims exact. Do not add
marketing claims or imply affiliation. UI labels stay short; paragraphs remain
complete. For plural entries return every requested target form.

Input is a JSON array. Return one JSON object only, mapping each key to an array
of translated forms. Do not use Markdown or add commentary. Every input key
must appear exactly once and no extra key is allowed."""


class TranslationError(RuntimeError):
    pass


def needs_completion(message) -> bool:
    if not message.id:
        return False
    if "fuzzy" in message.flags:
        return True
    if isinstance(message.string, tuple):
        return any(not part for part in message.string)
    return not message.string


def target_item(number: int, message, forms: int) -> dict[str, object]:
    ids = list(message.id) if isinstance(message.id, tuple) else [message.id]
    return {
        "key": f"T{number:03d}",
        "source_forms": ids,
        "target_form_count": forms if len(ids) > 1 else 1,
        "context": message.context,
        "locations": [f"{filename}:{line}" for filename, line in message.locations],
    }


def make_batches(items: list[dict[str, object]], max_chars: int) -> list[list[dict[str, object]]]:
    batches: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    size = 0
    for item in items:
        item_size = len(json.dumps(item, ensure_ascii=False))
        if current and size + item_size > max_chars:
            batches.append(current)
            current, size = [], 0
        current.append(item)
        size += item_size
    if current:
        batches.append(current)
    return batches


def parse_response(raw: str) -> dict[str, object]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise TranslationError("model response did not contain a JSON object")
    try:
        value = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise TranslationError(f"model response was not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TranslationError("model response was not a JSON object")
    return value


def translate_batch(
    language: str,
    register: str,
    batch: list[dict[str, object]],
    cache: Path,
    model: str,
    max_tokens: int,
) -> dict[str, list[str]]:
    prompt = json.dumps(batch, ensure_ascii=False, indent=2)
    prompt_hash = hashlib.sha256(
        (
            language
            + "\0"
            + register
            + "\0"
            + model
            + "\0thinking-disabled-json\0"
            + prompt
        ).encode("utf-8")
    ).hexdigest()
    cache_path = cache / language / f"{prompt_hash}.json"
    if cache_path.is_file():
        result = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        answer, usage = qwen.ask(
            prompt,
            system=SYSTEM.format(language=language, register=register),
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            timeout=2400,
            thinking="disabled",
            response_format={"type": "json_object"},
        )
        result = parse_response(answer)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(cache_path)
        print(
            f"i18n-release: {language} model response "
            f"({usage.get('prompt_tokens', '?')} prompt + "
            f"{usage.get('completion_tokens', '?')} completion tokens)",
            flush=True,
        )
    expected = {str(item["key"]): int(item["target_form_count"]) for item in batch}
    if set(result) != set(expected):
        missing = sorted(set(expected) - set(result))
        extra = sorted(set(result) - set(expected))
        raise TranslationError(f"response key mismatch; missing={missing}, extra={extra}")
    checked: dict[str, list[str]] = {}
    for key, count in expected.items():
        forms = result[key]
        if not isinstance(forms, list) or len(forms) != count:
            raise TranslationError(f"{key}: expected {count} translated forms")
        if not all(isinstance(form, str) and form.strip() for form in forms):
            raise TranslationError(f"{key}: translation contains an empty/non-string form")
        checked[key] = forms
    return checked


def guard_translation(message, forms: list[str]) -> None:
    sources = list(message.id) if isinstance(message.id, tuple) else [message.id]
    for index, translated in enumerate(forms):
        source = sources[min(index, len(sources) - 1)]
        problems = REVIEW.guard(source, translated)
        if problems:
            raise TranslationError(
                f"{message.id!r} form {index}: " + "; ".join(problems)
            )


def complete_language(
    language: str, cache: Path, model: str, max_chars: int, max_tokens: int
) -> int:
    path = ROOT / "po" / f"{language}.po"
    with path.open(encoding="utf-8") as handle:
        catalog = read_po(handle, locale=language)
    targets = [message for message in catalog if needs_completion(message)]
    if not targets:
        print(f"i18n-release: {language}: already complete")
        return 0
    items = [target_item(number, message, catalog.num_plurals) for number, message in enumerate(targets, 1)]
    batches = make_batches(items, max_chars)
    translated: dict[str, list[str]] = {}
    language_name, register = LANGUAGES[language]
    for index, batch in enumerate(batches, 1):
        print(
            f"i18n-release: {language}: batch {index}/{len(batches)} "
            f"({len(batch)} entries)",
            flush=True,
        )
        translated.update(
            translate_batch(language_name, register, batch, cache, model, max_tokens)
        )
    for number, message in enumerate(targets, 1):
        key = f"T{number:03d}"
        forms = translated[key]
        guard_translation(message, forms)
        message.string = tuple(forms) if isinstance(message.id, tuple) else forms[0]
        message.flags.discard("fuzzy")
    catalog.revision_date = datetime.now(timezone.utc)
    temporary = path.with_suffix(".po.tmp")
    with temporary.open("wb") as handle:
        write_po(
            handle,
            catalog,
            width=79,
            sort_output=False,
            include_previous=True,
        )
    temporary.replace(path)
    print(f"i18n-release: {language}: completed {len(targets)} entries", flush=True)
    return len(targets)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=sorted(LANGUAGES), action="append")
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--max-chars", type=int, default=9000)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "out/i18n-release-completion",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    languages = args.lang or list(LANGUAGES)
    total = 0
    for language in languages:
        total += complete_language(
            language, args.cache, args.model, args.max_chars, args.max_tokens
        )
    print(
        f"i18n-release: completed {total} release-blocking entries; "
        "native-speaker approval is still separate",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TranslationError as exc:
        print(f"i18n-release: BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
