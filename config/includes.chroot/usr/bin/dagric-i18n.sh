#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — the one place every dagric-* shell tool picks up its language.
# This file is SOURCED, never run:
#
#     . /usr/bin/dagric-i18n.sh
#
# WHY IT LIVES IN /usr/bin AND NOT /usr/lib
# -----------------------------------------
# The same reason 0510-app-names.hook.chroot gives for dagric-app-names:
# .gitattributes pins config/includes.chroot/usr/bin/* to LF endings and
# build.sh chmod +x's that directory. A shell file checked out with CRLF dies
# in the chroot as "/bin/sh^M", and this one is sourced by every tool in the
# product — it is the last file that may rot on a contributor's Windows
# checkout. /usr/bin is the one directory the repo already guarantees both for.
#
# HOW TRANSLATION ACTUALLY WORKS HERE
# -----------------------------------
# /usr/bin/gettext.sh (from gettext-base) is a FUNCTION LIBRARY, not a program.
# Sourcing it defines eval_gettext/eval_ngettext; plain `gettext` and `ngettext`
# stay external binaries. All four read $TEXTDOMAIN and $TEXTDOMAINDIR, so in
# shell those two variables ARE the bindtextdomain() call.
#
# eval_gettext does NOT use eval, despite the name: it pipes the translation
# through envsubst, which can only expand variables already named in the msgid.
# A translator — or a community .po from a stranger — therefore cannot get code
# execution out of a msgstr. That is why interpolated strings are safe to hand
# to translation at all.
#
# THE THREE RULES FOR CALLERS (each of these has bitten a real project)
# --------------------------------------------------------------------
#   1. eval_gettext msgids MUST be in SINGLE quotes:
#          eval_gettext 'Copying $name over'     -> translated
#          eval_gettext "Copying $name over"     -> silently ENGLISH, because
#      the shell expands $name before gettext sees it and the lookup misses.
#      No error, no warning; anyone testing in English never notices.
#      Plain `gettext` has no such trap — double quotes are fine there, and are
#      what we use for the many strings containing an apostrophe.
#
#   2. NEVER let a translated string become a printf FORMAT.
#          printf "$(gettext 'Copied %s files')" "$n"      # translator owns %s
#          printf '%s\n' "$(gettext 'Copied files')"       # correct
#      Always print with a literal '%s\n' format.
#
#   3. NEVER use bash's $"..." . dash tokenises $"Set Up Dagric" into THREE
#      words ($Set, Up, Dagric) and `dash -n` says nothing at all. There is no
#      dash equivalent; that is what gettext is for.
#
# Everything here is POSIX sh. Verified with `dash -n`.

TEXTDOMAIN=dagric
TEXTDOMAINDIR=/usr/share/locale
export TEXTDOMAIN TEXTDOMAINDIR

if [ -r /usr/bin/gettext.sh ]; then
    . /usr/bin/gettext.sh
else
    # gettext-base is Priority: standard and auto/config builds with
    # --apt-recommends false, so it arrives implicitly. If it ever stops
    # arriving, a tool that REFUSES TO RUN because a catalogue is missing is
    # far worse than one that speaks English: these are the scripts that
    # install drivers and rescue files off a Windows partition. Degrade, never
    # die. (The eval in the fallback only ever sees msgids from Dagric's own
    # source — no translated text reaches it, by construction.)
    gettext()      { printf '%s' "$1"; }
    ngettext()     { if [ "$3" = 1 ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
    eval_gettext()  { eval "printf '%s' \"$1\""; }
    eval_ngettext() {
        if [ "$3" = 1 ]; then eval "printf '%s' \"$1\""; else eval "printf '%s' \"$2\""; fi
    }
fi

# dg_say — print one translated line.
#
# printf, not echo: dash's builtin echo interprets backslash escapes, and
# German and French translations are exactly where a stray backslash turns up.
# The format string is a literal, so a translation can never become one.
dg_say() { printf '%s\n' "$1"; }

# dg_lang — the owner's language, as "lang_COUNTRY", with no encoding.
#
# Same precedence gettext itself uses: LANGUAGE first, then LC_ALL, then
# LC_MESSAGES, then LANG.
#
# LANGUAGE used to be skipped entirely here, on the reasoning that it is a
# colon-separated PREFERENCE LIST ("de:en") and not a locale, so treating it as
# one would send dg_localised looking for a directory called "de:en". That
# reasoning is right and the conclusion drawn from it was wrong: gettext DOES
# honour LANGUAGE, so on a desktop with LANG=en_US and LANGUAGE=de every
# gettext string came out German while dg_lang answered "en_US" — and the user
# guide, the welcome page and the manual all opened in English on a machine
# that was otherwise speaking German. That reads as a broken translation.
#
# The fix is to read LANGUAGE and take its FIRST entry, not to ignore it. The
# C/POSIX guard is gettext's own rule: LANGUAGE is disregarded when the locale
# is C, which is why LC_ALL=C turns translation off completely.
dg_lang() {
    _dg_l=${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}
    _dg_l=${_dg_l%%.*}      # drop .UTF-8
    _dg_l=${_dg_l%%@*}      # drop @modifier
    case "$_dg_l" in
        ''|C|POSIX) ;;      # translation is off; LANGUAGE must not resurrect it
        *)
            if [ -n "${LANGUAGE:-}" ]; then
                _dg_x=${LANGUAGE%%:*}   # "de:en" -> "de", never the whole list
                _dg_x=${_dg_x%%.*}
                _dg_x=${_dg_x%%@*}
                [ -n "$_dg_x" ] && _dg_l=$_dg_x
            fi
            ;;
    esac
    printf '%s' "$_dg_l"
}

# dg_localised — the best available copy of a file that ships per-language.
#
#     dg_localised /usr/share/dagric/welcome index.html
#       -> /usr/share/dagric/welcome/de_AT/index.html   if that exists
#       -> /usr/share/dagric/welcome/de/index.html      else if that exists
#       -> /usr/share/dagric/welcome/index.html         otherwise
#
# This is the HTML equivalent of what gettext does for strings and what the
# desktop spec does for Name[xx], and it has the same property that matters:
# a language nobody has translated falls all the way back to English rather
# than to a blank page. Prints nothing and returns 1 if even the English copy
# is missing, so the caller can say so instead of opening file:///.
dg_localised() {
    _dg_root=$1
    _dg_file=$2
    _dg_l=$(dg_lang)
    for _dg_c in "$_dg_l" "${_dg_l%%_*}"; do
        [ -n "$_dg_c" ] || continue
        if [ -f "$_dg_root/$_dg_c/$_dg_file" ]; then
            printf '%s' "$_dg_root/$_dg_c/$_dg_file"
            return 0
        fi
    done
    if [ -f "$_dg_root/$_dg_file" ]; then
        printf '%s' "$_dg_root/$_dg_file"
        return 0
    fi
    return 1
}

# dg_tr — translate a string that came out of a DATA FILE rather than out of
# this source tree: a .look/.style NAME or DESCRIPTION, a wallpaper title.
#
# The guard is not defensive padding. gettext("") returns the catalogue HEADER
# — "Project-Id-Version: dagric 1.0\nReport-Msgid-Bugs-To: ..." — so a layout
# file with no DESCRIPTION= line would put the .mo metadata into a menu row.
# Every one of these values is optional in its file format, so this WILL happen.
#
# The strings themselves reach the .pot via tools/i18n-extract.sh, which reads
# the same data files; xgettext cannot see through a variable.
#
# AND THE OUTPUT IS STRIPPED OF CONTROL CHARACTERS, which is the half that was
# missing. Callers sanitise the string going IN — dagric-firstrun:299 wraps the
# wallpaper name in flat() before handing it here — and then write what comes
# back out raw, between ASCII unit separators, into the \037-delimited tables
# the wizard reads. So the cleaning was happening on the wrong side of the
# translation.
#
# A msgstr is the one string in this product that arrives from outside the
# source tree, and .po supports C escapes that msgfmt compiles into real bytes:
# a \n or a \037 in a translation is a genuine record or field separator once
# it lands in walls.tsv, and the wizard's table silently gains a phantom row or
# loses a column. That needs no hostility to happen — one community translator
# with a stray escape does it.
#
# Every one of the ten dg_tr call sites is a single-line name or description
# (wallpaper titles, .look/.style NAME and DESCRIPTION), so nothing legitimate
# loses anything here. The long multi-line strings go through plain gettext,
# which this does not touch.
dg_tr() { if [ -n "$1" ]; then gettext "$1" | tr -d '\001-\037\177'; fi; }

# dg_live_warn — say so when an install is about to land in RAM.
#
# In the live session / is a tmpfs overlay, so everything apt or flatpak
# downloads AND everything it then unpacks is held in this machine's memory. It
# does not survive a reboot, and on a 4 GB laptop a few hundred megabytes of
# application is enough to make the trial session unstable. None of the install
# helpers said so, which put the worst version of that surprise in front of
# exactly the person who is still deciding whether to buy: they try an app, the
# live session starts swapping or dies, and the conclusion they draw is that
# Dagric is unstable.
#
# Detection is the same `/run/live/medium` test dagric-hub, dagric-migrate,
# dagric-firstrun and dagric-hardware-check already use.
#
# ALWAYS returns 0. This informs, it never blocks — somebody who wants to try an
# app on the live stick is entitled to, and being told what it costs is the
# whole point.
dg_live_warn() {
    [ -d /run/live/medium ] || return 0
    dg_say ""
    # TRANSLATORS: shown only in the live USB session, before an install.
    dg_say "$(gettext "NOTE — this is the live trial running from the USB stick.
Anything installed now is kept in this computer's memory rather than on a disk:
it disappears when you shut down, and on a machine without much RAM a large
application can make the trial session unstable. Installing Dagric first avoids
both, and the app is then permanent.")"
    dg_say ""
    return 0
}

# dg_is_yes — did the owner say yes at a "[y/N]" prompt?
#
# Translating the PROMPT without translating the ANSWER is a real bug, not a
# nicety: a German owner reading "[j/N]" types j, the script reads it as "no",
# and the install they asked for silently does not happen. English y/yes are
# always accepted too, so a missing or wrong catalogue can only ever add
# answers, never take one away.
#
# tr runs under LC_ALL=C on purpose — it is folding ASCII y/j/o/s, and a
# UTF-8 locale would drag character-set handling into a two-character compare.
dg_is_yes() {
    _dg_a=$(printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]')
    case "$_dg_a" in
        y|yes) return 0 ;;
        '')    return 1 ;;
    esac
    # `if`, not `[ ] && return`: half these callers run under `set -e`, and an
    # AND-OR list whose test fails is exactly the shape that gets argued about.
    #
    # TRANSLATORS: a space-separated list of the words that mean YES at a
    # "[y/N]" prompt in your language, lower case, shortest first. English
    # "y" and "yes" are always accepted as well — do not remove them, and do
    # not translate them. German: "j ja y yes". French: "o oui y yes".
    for _dg_w in $(gettext "y yes"); do
        if [ "$_dg_a" = "$_dg_w" ]; then return 0; fi
    done
    return 1
}
