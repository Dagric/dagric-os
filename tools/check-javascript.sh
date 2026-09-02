#!/bin/sh
# Syntax-check browser, Worker, and build JavaScript without executing it.
set -eu
cd "$(dirname "$0")/.."

command -v node >/dev/null 2>&1 || {
    echo "node is required for JavaScript syntax checks" >&2
    exit 1
}

FILES=$(find config infra packages promo site tools -type f \
    \( -name '*.js' -o -name '*.mjs' \) \
    ! -path '*/node_modules/*' ! -path '*/.wrangler/*' ! -path 'site/repo/*')
[ -n "$FILES" ] || {
    echo "javascript-check: no JavaScript files found" >&2
    exit 1
}

count=0
old_ifs=$IFS
IFS='
'
for file in $FILES; do
    node --check "$file"
    count=$((count + 1))
done
IFS=$old_ifs
echo "javascript-check: $count files parse"
