#!/bin/sh
# Parse every shipped shell entry point and run ShellCheck's error-level rules.
# Warnings remain review material; syntax errors and definite breakage stop CI.
set -eu
cd "$(dirname "$0")/.."

command -v shellcheck >/dev/null 2>&1 || {
    echo "shellcheck is required: apt install shellcheck" >&2
    exit 1
}

FILES=$(grep -IlrE '^#!.*(sh|bash)' auto config packages tools test docker infra \
    --exclude='*.mo' 2>/dev/null || true)
[ -n "$FILES" ] || {
    echo "shell-check: no shell entry points found" >&2
    exit 1
}

count=0
old_ifs=$IFS
IFS='
'
for file in $FILES; do
    first=$(head -n 1 "$file")
    case "$first" in
        *bash*) bash -n "$file" ;;
        *)      sh -n "$file" ;;
    esac
    shellcheck -S error "$file"
    count=$((count + 1))
done
IFS=$old_ifs

echo "shell-check: $count entry points parse and pass error-level analysis"
