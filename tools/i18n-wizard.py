#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DGR Operations <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS -- the setup wizard's words, checked against the wizard.
#
#     python3 tools/i18n-wizard.py            report
#     python3 tools/i18n-wizard.py --check    same, and fail the build on drift
#
# WHY THIS EXISTS
# ---------------
# The first-run wizard is split across two files on purpose: dagric-firstrun
# holds an English sentence list that gettext translates and hands to the window
# as data, and main.qml asks for each sentence by its English text. Neither file
# can see the other, and nothing in the build compared them -- so both halves of
# the obvious failure happened at once and neither was noticed:
#
#   * 18 of the 39 sentences the shell shipped were never asked for. Translators
#     translated them into five languages; nobody ever read one.
#   * roughly fifty sentences the window DID display were never in the list at
#     all -- every heading on the display, files and finish pages, the welcome
#     headline, the size cards, and every word Orca speaks. A German owner met a
#     German desktop through a wizard whose Next button said "Next".
#
# The build log said "39 strings, 5 languages" the whole time, because counting
# what you shipped is not the same as checking that anything wanted it.
#
# WHAT COUNTS AS "ASKED FOR"
# --------------------------
# app.t("...") and app.tf("...") are the direct lookups. Three QML models hold
# English text that is put through app.t() at the point of display -- the three
# text-size cards and the four cards on the finish page -- so those are read out
# of the models too. A string that reaches the screen any other way is invisible
# here, which is the one limitation worth knowing: this proves the two lists
# agree, not that every literal in the QML has been extracted. Adding a bare
# literal to a Text element still needs a human to notice.
import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
QML = os.path.join(ROOT, 'config/includes.chroot/usr/share/dagric/firstrun/main.qml')
SH = os.path.join(ROOT, 'config/includes.chroot/usr/bin/dagric-firstrun')


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


def emitted():
    """The sentences dagric-firstrun ships in the catalogue, in file order."""
    s = read(SH)
    try:
        a = s.index("<<'STRINGS'\n") + len("<<'STRINGS'\n")
        b = s.index('\nSTRINGS\n', a)
    except ValueError:
        print('ERROR: no STRINGS here-doc in dagric-firstrun', file=sys.stderr)
        sys.exit(2)
    return [ln for ln in s[a:b].split('\n') if ln.strip()]


def asked():
    """Every string main.qml looks up in that catalogue."""
    s = read(QML)
    out = [m.group(1).replace('\\"', '"').replace('\\\\', '\\')
           for m in re.finditer(r'app\.(?:t|tf)\(\s*"((?:[^"\\]|\\.)*)"', s)]
    # The text-size cards: { v: 100, name: "Normal", note: "Standard size" }
    for m in re.finditer(r'\{ v: \d+, name: "([^"]*)",\s*note: "([^"]*)" \}', s):
        out += [m.group(1), m.group(2)]
    # The finish cards: { act: "hub", title: "...", body: "..." }
    for m in re.finditer(r'\{ act: "\w+",\s*title: "([^"]*)",\s*\n\s*body: "([^"]*)" \}', s):
        out += [m.group(1), m.group(2)]
    return out


def main():
    check = '--check' in sys.argv
    em = emitted()
    want = asked()
    em_set, want_set = set(em), set(want)

    bad = 0
    for s in [x for x in dict.fromkeys(want) if x not in em_set]:
        print('ERROR: main.qml asks for a string dagric-firstrun does not ship: %r'
              % s, file=sys.stderr)
        bad = 1
    for s in [x for x in em if x not in want_set]:
        print('ERROR: dagric-firstrun ships a string main.qml never asks for: %r'
              % s, file=sys.stderr)
        bad = 1
    if len(em) != len(em_set):
        for s in sorted(x for x in em_set if em.count(x) > 1):
            print('ERROR: duplicate line in the STRINGS here-doc: %r' % s,
                  file=sys.stderr)
        bad = 1

    if bad:
        print('Fix by editing the STRINGS here-doc in '
              'config/includes.chroot/usr/bin/dagric-firstrun, then re-running '
              'tools/i18n-extract.sh and tools/i18n-build.sh.', file=sys.stderr)
        return 1 if check else 0

    print('i18n-wizard: %d strings, all shipped and all used' % len(em))
    return 0


if __name__ == '__main__':
    sys.exit(main())
