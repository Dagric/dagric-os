#!/bin/sh
# One command for Dagric's non-destructive release audit.
# Optional gates:
#   --package-names  query Debian trixie for every declared package
#   --artifacts      inspect out/week-audit Free/Pro ISOs (requires root)
set -eu
cd "$(dirname "$0")/.."

packages=0
artifacts=0
for arg in "$@"; do
    case "$arg" in
        --package-names) packages=1 ;;
        --artifacts) artifacts=1 ;;
        *) echo "usage: $0 [--package-names] [--artifacts]" >&2; exit 2 ;;
    esac
done

run() {
    echo ""
    echo "== $1 =="
    shift
    "$@"
}

run "source and security" python3 tools/check-source.py
run "product concept contracts" python3 tools/check-concepts.py
run "source-check mutation suite" python3 test/test-source-check.py
run "Docker build definition" sh tools/check-dockerfile.sh
run "website release safety" sh tools/check-site.sh
run "Rewind safety boundary" sh tools/check-rewind.sh
run "adaptive machine pipeline" sh tools/check-pipeline.sh
run "Dagric trust loop and Support Mode" sh tools/check-trust.sh
run "safe in-place Dagric Update" sh tools/check-update.sh
run "Dagric Update unit tests" python3 test/test-update-core.py
run "Dagric Flow visual contract" python3 tools/check-flow.py
run "Dagric dependability foundations" sh tools/check-foundations.sh
run "JavaScript syntax" sh tools/check-javascript.sh
run "shell syntax and error rules" sh tools/check-shell.sh
run "translation catalogues" sh tools/i18n-build.sh --check
run "desktop-entry localization" python3 tools/i18n-desktop.py --check
run "window/catalogue localization" python3 tools/i18n-wizard.py --check

if [ "$packages" -eq 1 ]; then
    run "Debian package resolution" sh tools/check-package-names.sh
fi
if [ "$artifacts" -eq 1 ]; then
    run "built ISO artifacts" sh tools/check-artifacts.sh out/week-audit
fi

echo ""
echo "audit-all: every selected gate passed"
