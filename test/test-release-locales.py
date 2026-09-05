#!/usr/bin/env python3
"""Focused tests for the commercial-release localization completeness gate."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check-release-locales.py"
LOCALES = ("de", "es", "fr", "it", "pt_BR")
POT = '''msgid ""
msgstr ""

#: one
msgid "Hello"
msgstr ""

#: two
msgid "One file"
msgid_plural "Many files"
msgstr[0] ""
msgstr[1] ""
'''
COMPLETE = '''msgid ""
msgstr ""

#: one
msgid "Hello"
msgstr "Translated hello"

#: two
msgid "One file"
msgid_plural "Many files"
msgstr[0] "Translated one"
msgstr[1] "Translated many"
'''


def run(folder: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(folder)],
        text=True,
        capture_output=True,
        check=False,
    )


def fixture(folder: Path) -> Path:
    po = folder / "po"
    po.mkdir()
    (po / "dagric.pot").write_text(POT, encoding="utf-8")
    for locale in LOCALES:
        (po / f"{locale}.po").write_text(COMPLETE, encoding="utf-8")
    return po


def main() -> int:
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        fixture(root)
        result = run(root)
        assert result.returncode == 0, result.stderr

    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        po = fixture(root)
        (po / "de.po").write_text(
            COMPLETE.replace("#: one", "#, fuzzy\n#: one"), encoding="utf-8"
        )
        result = run(root)
        assert result.returncode != 0 and "1 fuzzy" in result.stdout, result.stderr

    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        po = fixture(root)
        (po / "es.po").write_text(
            COMPLETE.replace('msgstr "Translated hello"', 'msgstr ""'),
            encoding="utf-8",
        )
        result = run(root)
        assert result.returncode != 0 and "1 untranslated" in result.stdout, result.stderr

    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        po = fixture(root)
        (po / "fr.po").write_text(
            COMPLETE.split("\n#: two", 1)[0] + "\n", encoding="utf-8"
        )
        result = run(root)
        assert result.returncode != 0 and "1 missing" in result.stdout, result.stderr

    print("release-locales tests: complete, fuzzy, untranslated and missing cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
