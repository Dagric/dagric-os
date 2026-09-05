#!/bin/sh
# Build an isolated private candidate under Debian/WSL without altering out/.
# The historical command defaults to Pro; pass free for its companion image.
set -eu
EDITION=${1:-pro}
case "$EDITION" in
    free|pro) ;;
    *) echo 'usage: resume-private-pro-build.sh [free|pro]' >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { echo 'Expected at most one edition argument.' >&2; exit 2; }
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
    echo 'Commit or isolate tracked changes before building a committed candidate.' >&2
    exit 1
fi
RUN=$(mktemp -d "/var/tmp/dagric-private-$EDITION.XXXXXX")
case "$RUN" in /var/tmp/dagric-private-pro.*|/var/tmp/dagric-private-free.*) ;; *) exit 1 ;; esac
printf 'Private build directory: %s\n' "$RUN"
git clone --quiet --no-hardlinks "$REPO" "$RUN/source"
cd "$RUN/source"
printf 'Source revision: '
git rev-parse HEAD
# build.sh reserves a new working directory; failed candidates are preserved.
test ! -e "$RUN/build"
export DAGRIC_BUILD_DIR="$RUN/build"
exec sh ./build.sh "$EDITION"
