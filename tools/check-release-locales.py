#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail a commercial release unless every advertised locale is complete.

Normal development builds may keep fuzzy or untranslated entries so language
work can proceed incrementally. A commercial release may not: fuzzy entries are
omitted by msgfmt and empty translations fall back to English, contradicting a
fully localized product claim. This check is intentionally release-only.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REQUIRED_LOCALES = ("de", "es", "fr", "it", "pt_BR")
FIELD_RE = re.compile(
    r'^(msgctxt|msgid|msgid_plural|msgstr(?:\[\d+\])?)\s+("(?:[^"\\]|\\.)*")\s*$'
)


class LocaleError(ValueError):
    """A PO file is absent, malformed, out of sync, or incomplete."""


@dataclass(frozen=True)
class Entry:
    identity: tuple[str, str, str]
    fuzzy: bool
    translations: tuple[str, ...]


def quoted(value: str, path: Path, line_number: int) -> str:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise LocaleError(f"{path}:{line_number}: malformed PO string") from exc
    if not isinstance(parsed, str):
        raise LocaleError(f"{path}:{line_number}: PO value is not a string")
    return parsed


def parse_po(path: Path) -> list[Entry]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise LocaleError(f"cannot read required catalog {path}: {exc}") from exc

    entries: list[Entry] = []
    for raw_block in re.split(r"\n\s*\n", "\n".join(lines)):
        block = raw_block.splitlines()
        if not block or all(not line.strip() for line in block):
            continue
        if any(line.startswith("#~") for line in block):
            continue
        flags: set[str] = set()
        fields: dict[str, str] = {}
        index = 0
        while index < len(block):
            line = block[index]
            if line.startswith("#,"):
                flags.update(part.strip() for part in line[2:].split(","))
                index += 1
                continue
            match = FIELD_RE.match(line)
            if match is None:
                index += 1
                continue
            key = match.group(1)
            value = quoted(match.group(2), path, index + 1)
            index += 1
            while index < len(block) and re.fullmatch(
                r'"(?:[^"\\]|\\.)*"\s*', block[index]
            ):
                value += quoted(block[index].strip(), path, index + 1)
                index += 1
            if key in fields:
                raise LocaleError(f"{path}: duplicate {key} in one entry")
            fields[key] = value

        msgid = fields.get("msgid")
        if msgid is None:
            continue
        if msgid == "":
            continue  # catalog header
        translations = tuple(
            value
            for key, value in sorted(fields.items())
            if key == "msgstr" or key.startswith("msgstr[")
        )
        entries.append(
            Entry(
                identity=(
                    fields.get("msgctxt", ""),
                    msgid,
                    fields.get("msgid_plural", ""),
                ),
                fuzzy="fuzzy" in flags,
                translations=translations,
            )
        )
    return entries


def identities(entries: list[Entry], label: str) -> set[tuple[str, str, str]]:
    counts = Counter(entry.identity for entry in entries)
    duplicates = [identity for identity, count in counts.items() if count != 1]
    if duplicates:
        raise LocaleError(f"{label} has duplicate active message identities")
    return set(counts)


def check(root: Path) -> None:
    template_path = root / "po/dagric.pot"
    template = parse_po(template_path)
    expected = identities(template, str(template_path))
    if not expected:
        raise LocaleError(f"{template_path} has no active messages")

    failed = False
    for locale in REQUIRED_LOCALES:
        path = root / f"po/{locale}.po"
        entries = parse_po(path)
        actual = identities(entries, str(path))
        missing = len(expected - actual)
        extra = len(actual - expected)
        fuzzy = sum(entry.fuzzy for entry in entries)
        untranslated = sum(
            not entry.translations or any(not value.strip() for value in entry.translations)
            for entry in entries
        )
        print(
            f"release-locale: {locale}: {len(entries)} entries, "
            f"{fuzzy} fuzzy, {untranslated} untranslated, "
            f"{missing} missing, {extra} extra"
        )
        if fuzzy or untranslated or missing or extra:
            failed = True

    if failed:
        raise LocaleError(
            "commercial release requires de, es, fr, it and pt_BR to match "
            "dagric.pot with zero fuzzy and zero untranslated entries"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        check(args.root.resolve())
    except LocaleError as exc:
        print(f"release-locale: BLOCKED: {exc}", file=sys.stderr)
        return 1
    print("release-locale: all five required catalogs are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
