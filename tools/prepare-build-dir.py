#!/usr/bin/env python3
"""Reserve a NEW native build directory; never clean or reuse existing data."""

from __future__ import annotations

import argparse
import pathlib
import sys


def prepare(source: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    if not target.is_absolute():
        raise ValueError("build directory must be an absolute path")
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("source must be a directory")
    # Resolve the parent before creating anything, including symlinked parents.
    # mkdir below is exclusive: another process winning the race is an error.
    parent = target.parent.resolve(strict=True)
    destination = parent / target.name
    resolved = destination.resolve()
    if resolved == source or resolved in source.parents or source in resolved.parents:
        raise ValueError("build directory must be outside the source tree and its ancestors")
    if destination.exists() or destination.is_symlink():
        raise ValueError("build directory already exists; choose a new path (nothing was removed)")
    destination.mkdir(mode=0o755, exist_ok=False)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    try:
        print(prepare(args.source, args.destination))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"build-directory: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
