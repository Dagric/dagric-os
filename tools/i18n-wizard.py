#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS -- every QML window's words, checked against the window.
#
#     python3 tools/i18n-wizard.py            report
#     python3 tools/i18n-wizard.py --check    same, and fail the build on drift
#
# COVERS EVERY SHELL+QML PAIR, NOT JUST THE WIZARD. It was wizard-only, and the
# Family Limits window then shipped with the exact defect this file exists to
# catch -- 26 sentences in qsTr() with no .qm anywhere in the image, so five of
# the six languages got an English window in the one feature whose own header
# says it exists BECAUSE timekpr is not translated into them. A check that
# covers one window silently does not apply to the next one somebody writes, so
# the pairs are a list now and a new window is one line.
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

# Every window that gets its words as catalogue data. Adding one here is what
# puts it under this check; a window not listed is not checked at all, which is
# how the Family Limits window shipped untranslated.
INC = 'config/includes.chroot'
WINDOWS = [
    ('wizard', INC + '/usr/bin/dagric-firstrun',
     INC + '/usr/share/dagric/firstrun/main.qml'),
    ('family', INC + '/usr/bin/dagric-family',
     INC + '/usr/share/dagric/family/main.qml'),
]


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


def emitted(sh_path):
    """The sentences the shell script ships in the catalogue, in file order."""
    s = read(sh_path)
    try:
        a = s.index("<<'STRINGS'\n") + len("<<'STRINGS'\n")
        b = s.index('\nSTRINGS\n', a)
    except ValueError:
        print('ERROR: no STRINGS here-doc in %s' % sh_path, file=sys.stderr)
        sys.exit(2)
    return [ln for ln in s[a:b].split('\n') if ln.strip()]


def asked(qml_path):
    """Every string the window looks up in that catalogue."""
    s = read(qml_path)
    out = [m.group(1).replace('\\"', '"').replace('\\\\', '\\')
           for m in re.finditer(r'app\.(?:t|tf)\(\s*"((?:[^"\\]|\\.)*)"', s)]
    # The wizard's text-size cards: { v: 100, name: "Normal", note: "Standard" }
    for m in re.finditer(r'\{ v: \d+, name: "([^"]*)",\s*note: "([^"]*)" \}', s):
        out += [m.group(1), m.group(2)]
    # The wizard's finish cards: { act: "hub", title: "...", body: "..." }
    for m in re.finditer(r'\{ act: "\w+",\s*title: "([^"]*)",\s*\n\s*body: "([^"]*)" \}', s):
        out += [m.group(1), m.group(2)]
    return out


# A window that reaches this file having gone back to qsTr() is the original
# defect returning, and the pairing check above cannot see it: qsTr strings are
# in neither list, so both sides agree and the window is still English.
#
# Comments are stripped first, because the files that were converted away from
# qsTr explain in a comment what they were converted away FROM -- and failing
# the build over the word in a comment would teach the next person to delete
# the explanation.
def stray_qstr(qml_path):
    s = read(qml_path)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = '\n'.join(ln for ln in s.split('\n') if not ln.lstrip().startswith('//'))
    return len(re.findall(r'\bqsTr\s*\(', s))


def check_window(name, sh_rel, qml_rel):
    sh, qml = os.path.join(ROOT, sh_rel), os.path.join(ROOT, qml_rel)
    em, want = emitted(sh), asked(qml)
    em_set, want_set = set(em), set(want)

    bad = 0
    for s in [x for x in dict.fromkeys(want) if x not in em_set]:
        print('ERROR: %s: the window asks for a string %s does not ship: %r'
              % (name, os.path.basename(sh), s), file=sys.stderr)
        bad = 1
    for s in [x for x in em if x not in want_set]:
        print('ERROR: %s: %s ships a string the window never asks for: %r'
              % (name, os.path.basename(sh), s), file=sys.stderr)
        bad = 1
    if len(em) != len(em_set):
        for s in sorted(x for x in em_set if em.count(x) > 1):
            print('ERROR: %s: duplicate line in the STRINGS here-doc: %r'
                  % (name, s), file=sys.stderr)
        bad = 1
    n = stray_qstr(qml)
    if n:
        print('ERROR: %s: %d qsTr() call(s) in %s. Nothing in this product '
              'compiles or loads a .qm, so those strings ship in English in '
              'every language. Use app.t()/app.tf() and add the sentence to '
              'the STRINGS here-doc.' % (name, n, os.path.basename(qml)),
              file=sys.stderr)
        bad = 1

    if bad:
        print('Fix by editing the STRINGS here-doc in %s, then re-running '
              'tools/i18n-extract.sh and tools/i18n-build.sh.' % sh_rel,
              file=sys.stderr)
        return None
    return len(em)


def main():
    check = '--check' in sys.argv
    bad = 0
    for name, sh_rel, qml_rel in WINDOWS:
        n = check_window(name, sh_rel, qml_rel)
        if n is None:
            bad = 1
        else:
            print('i18n-wizard: %s: %d strings, all shipped and all used'
                  % (name, n))
    if bad:
        return 1 if check else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
