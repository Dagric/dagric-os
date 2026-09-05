#!/bin/sh
# One command for Dagric's non-destructive release audit.
# Optional gates:
#   --package-names  query Debian trixie for every declared package
#   --artifacts      inspect out/week-audit Free/Pro ISOs (requires root)
# Developer mode:
#   --source-only    omit the untracked generated exact-source-map candidate;
#                    this is not an artifact audit or release approval
set -eu
cd "$(dirname "$0")/.."

packages=0
artifacts=0
source_only=0
for arg in "$@"; do
    case "$arg" in
        --package-names) packages=1 ;;
        --artifacts) artifacts=1 ;;
        --source-only) source_only=1 ;;
        *) echo "usage: $0 [--source-only] [--package-names] [--artifacts]" >&2; exit 2 ;;
    esac
done
if [ "$source_only" -eq 1 ] && [ "$artifacts" -eq 1 ]; then
    echo "audit-all: --source-only and --artifacts cannot be combined" >&2
    exit 2
fi

run() {
    echo ""
    echo "== $1 =="
    shift
    "$@"
}

run "source and security" python3 tools/check-source.py
run "audit command mode regressions" python3 test/test-audit-all-modes.py
run "non-destructive native build paths" python3 test/test-build-directory.py
run "offline manual application coverage" python3 tools/check-manual-coverage.py
run "offline manual coverage regressions" python3 test/test-manual-coverage.py
run "selectable Dagric icon families" python3 tools/check-icon-themes.py
run "licensing and media rights" python3 tools/check-release-rights.py
run "optional game-platform boundary" python3 tools/check-game-platform-policy.py
if [ "$source_only" -eq 1 ]; then
    echo "NOT CHECKED: generated candidate out/exact-source-map-1.0.json (--source-only)."
    echo "Tracked source-index identity, website media, and release-gate regression checks remain selected."
else
    run "primary binary-to-source map (not embedded-source clearance)" python3 tools/check-generated-source-map.py
fi
run "source-map identity regressions" python3 test/test-generate-exact-source-map.py
run "source-map gate regressions" python3 test/test-source-map-gate.py
run "private R2 staging regressions" python3 test/test-private-r2-staging.py
run "commercial release gate regressions" python3 test/test-commercial-release-gate.py
run "physical release gate regressions" python3 test/test-physical-release-gate.py
run "release workflow ordering" python3 test/test-release-workflow-gate.py
run "commercial locale gate regressions" python3 test/test-release-locales.py
run "product concept contracts" python3 tools/check-concepts.py
run "source-check mutation suite" python3 test/test-source-check.py
run "browser migration privacy" python3 test/test-migrate-browser-security.py
run "Steam migration privacy" python3 test/test-migrate-continuity-privacy.py
run "private state files and atomic reports" python3 test/test-private-state-writes.py
run "OpenSnitch administrator socket boundary" python3 test/test-opensnitch-boundary.py
run "OpenSnitch package lifecycle" python3 test/test-opensnitch-package.py
run "OpenSnitch installer administrator policy" python3 test/test-opensnitch-calamares.py
run "security artifact gate regressions" python3 test/test-security-artifacts.py
run "installed-system audit truthfulness" python3 test/test-installed-audit.py
run "candidate security inventory and signed-index regressions" python3 test/test-candidate-security-audit.py
run "embedded-source inventory regressions" python3 test/test-embedded-sources.py
run "full source-object bundle regressions" python3 test/test-source-bundle.py
run "canonical private source-lock regressions" python3 test/test-source-candidate-lock.py
run "exact DSC signature evidence regressions" python3 test/test-dsc-signatures.py
run "actual source-image binding regressions" python3 test/test-source-bundle-images.py
run "real image/source evidence integration" python3 test/test-source-evidence-integration.py
run "source completeness fail-closed guards" python3 test/test-source-completeness-guards.py
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
run "Worker security boundaries" node test/test-workers.mjs
run "marketing opportunity discovery boundaries" node --test test/test-marketing-opportunity-discovery.mjs
run "JavaScript dependency vulnerabilities" sh tools/check-dependencies.sh
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
if [ "$source_only" -eq 1 ]; then
    echo "NOT CHECKED: generated ISO payloads, boot/runtime evidence, physical tests, or release approval."
    echo "audit-all: source-only developer checks passed; NOT a release approval"
else
    echo "audit-all: every selected gate passed"
fi
