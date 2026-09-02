#!/bin/sh
# Repeatedly exercise deterministic safety gates to expose flaky assumptions,
# temp-file collisions, environment leakage, and order-dependent test failures.
set -eu
cd "$(dirname "$0")/.."

rounds=${1:-25}
case "$rounds" in
    ''|*[!0-9]*|0) echo "usage: $0 [positive-round-count]" >&2; exit 2 ;;
esac

tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT HUP INT TERM

run_quiet() {
    label=$1
    shift
    log="$tmp/$label.log"
    if ! "$@" >"$log" 2>&1; then
        echo "stress-test: $label failed" >&2
        cat "$log" >&2
        exit 1
    fi
}

i=1
while [ "$i" -le "$rounds" ]; do
    run_quiet "source-$i" python3 tools/check-source.py
    run_quiet "concepts-$i" python3 tools/check-concepts.py
    run_quiet "mutations-$i" python3 test/test-source-check.py
    run_quiet "rewind-core-$i" python3 test/test-rewind-core.py
    run_quiet "rewind-controller-$i" python3 test/test-rewind-controller.py
    run_quiet "trust-$i" python3 test/test-trust.py
    run_quiet "foundations-$i" python3 test/test-foundations.py
    if [ $((i % 10)) -eq 0 ] || [ "$i" -eq "$rounds" ]; then
        echo "stress-test: $i/$rounds rounds passed"
    fi
    i=$((i + 1))
done

# Finish with the broader parsers after the high-frequency stateful tests.
run_quiet javascript sh tools/check-javascript.sh
run_quiet shell sh tools/check-shell.sh
run_quiet flow python3 tools/check-flow.py
run_quiet site sh tools/check-site.sh
run_quiet i18n sh tools/i18n-build.sh --check
run_quiet desktop-i18n python3 tools/i18n-desktop.py --check
run_quiet window-i18n python3 tools/i18n-wizard.py --check
run_quiet foundations python3 tools/check-foundations.py

checks=$((rounds * 7 + 8))
echo "stress-test: passed $checks gate executions across $rounds rounds"
