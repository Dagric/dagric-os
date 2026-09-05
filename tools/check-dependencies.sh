#!/bin/sh
# Ask the package registry about currently known production dependency flaws.
set -eu
cd "$(dirname "$0")/../promo"

command -v npm >/dev/null 2>&1 || {
    echo "npm is required for the dependency vulnerability audit" >&2
    exit 1
}

npm audit --package-lock-only --omit=dev --ignore-scripts --audit-level=moderate
echo "dependency-audit: no known moderate-or-higher production vulnerabilities"
