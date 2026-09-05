#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dagric OS — catch a Dockerfile instruction swallowed by a line continuation.
#
#     sh tools/check-dockerfile.sh
#
# WHY THIS EXISTS
# ---------------
# Docker strips comment lines from inside a backslash continuation and joins
# what is left. So this:
#
#     RUN apt-get install -y \
#     # a comment explaining the next package
#     RUN apt-get install -y \
#             live-build \
#
# becomes ONE command whose package list starts "RUN apt-get install -y
# live-build", and the build dies with the almost unreadable
#
#     E: Unable to locate package RUN
#     E: Unable to locate package apt-get
#
# That is not a hypothetical either. Two separate fixes to this repo's
# Dockerfile — one adding gettext, one adding curl — each landed a correct
# comment block above the RUN they were changing. Each was verified on its own.
# Together they left a second RUN buried inside the first one's continuation,
# and both editions failed to build with an error naming no file and no fix.
#
# The general lesson is the one worth keeping: an edit can be individually
# correct and still be wrong in combination, so what gets checked has to be the
# RESULTING FILE, not the change.
set -e
cd "$(dirname "$0")/.."

# The instruction keywords Docker recognises at the start of a line. A
# continuation line beginning with one of these is almost certainly a mistake:
# they are never valid as an argument to the previous instruction.
KEYWORDS='FROM|RUN|CMD|LABEL|MAINTAINER|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL'

fail=0
found=0
for df in docker/Dockerfile docker/*.Dockerfile test/Dockerfile Dockerfile; do
    [ -f "$df" ] || continue
    found=$((found + 1))
    # awk carries "am I inside a continuation" across lines, which is the whole
    # point — the defect is invisible one line at a time.
    awk -v file="$df" -v kw="$KEYWORDS" '
        function isinstr(s) { return s ~ ("^[ \t]*(" kw ")[ \t]") }
        {
            line = $0
            # Comments are stripped by Docker inside a continuation, so they
            # neither start nor end one. Skip without touching the state.
            if (line ~ /^[ \t]*#/) next

            if (cont && isinstr(line)) {
                printf "%s:%d: %s appears inside the continuation started on line %d\n",
                       file, NR, $1, contline
                bad++
            }

            # A trailing backslash continues onto the next line.
            if (line ~ /\\[ \t]*$/) {
                if (!cont) contline = NR
                cont = 1
            } else {
                cont = 0
            }
        }
        END {
            if (cont)
                printf "%s: file ends inside an unterminated line continuation (line %d)\n",
                       file, contline
            exit (bad > 0 || cont) ? 1 : 0
        }
    ' "$df" || fail=1

    [ "$fail" = 1 ] || echo "  ok   $df"
done

if [ "$found" = 0 ]; then
    echo "  no Dockerfile found — nothing to check"
    exit 0
fi

[ "$fail" = 0 ] || {
    echo "" >&2
    echo "A Dockerfile instruction is being consumed as an argument to the one" >&2
    echo "above it. Docker will join them and the build dies with a package" >&2
    echo "name like 'RUN' or 'apt-get'." >&2
    exit 1
}
