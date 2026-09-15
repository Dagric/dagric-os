#!/usr/bin/env python3
"""Build an exact package/section inventory from an ISO rootfs dpkg status."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


class InventoryError(RuntimeError):
    pass


def parse_manifest(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InventoryError(f"cannot read package manifest {path}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        fields = line.split("\t")
        if len(fields) != 2 or not all(fields):
            raise InventoryError(f"invalid package manifest row {line_number}")
        identity = (fields[0], fields[1])
        if identity in seen:
            raise InventoryError(
                f"duplicate package manifest identity {fields[0]}={fields[1]}"
            )
        seen.add(identity)
        records.append(identity)
    if not records:
        raise InventoryError("package manifest is empty")
    return records


def parse_status(path: Path) -> list[dict[str, str]]:
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InventoryError(f"cannot read dpkg status {path}: {exc}") from exc
    records: list[dict[str, str]] = []
    for paragraph_number, paragraph in enumerate(
        payload.replace("\r\n", "\n").split("\n\n"), 1
    ):
        if not paragraph.strip():
            continue
        fields: dict[str, str] = {}
        for line in paragraph.splitlines():
            if line[:1].isspace():
                continue
            key, separator, value = line.partition(":")
            if not separator or not key or key in fields:
                raise InventoryError(
                    f"invalid dpkg status field in paragraph {paragraph_number}"
                )
            fields[key] = value.strip()
        if fields.get("Status") != "install ok installed":
            continue
        missing = [
            key
            for key in ("Package", "Version", "Architecture", "Section")
            if not fields.get(key)
        ]
        if missing:
            raise InventoryError(
                f"installed dpkg record {paragraph_number} lacks {', '.join(missing)}"
            )
        records.append(fields)
    if not records:
        raise InventoryError("dpkg status has no installed packages")
    return records


def reconcile(
    manifest: list[tuple[str, str]], status: list[dict[str, str]]
) -> list[tuple[str, str, str]]:
    expected = set(manifest)
    resolved: dict[tuple[str, str], str] = {}
    for fields in status:
        package = fields["Package"]
        version = fields["Version"]
        architecture = fields["Architecture"]
        candidates = {
            identity
            for identity in ((package, version), (f"{package}:{architecture}", version))
            if identity in expected
        }
        if len(candidates) != 1:
            rendered = f"{package}:{architecture}={version}"
            if not candidates:
                raise InventoryError(
                    f"installed dpkg record is absent from filesystem.packages: {rendered}"
                )
            raise InventoryError(f"ambiguous package identity in manifest: {rendered}")
        identity = next(iter(candidates))
        if identity in resolved:
            raise InventoryError(
                f"duplicate installed dpkg identity: {identity[0]}={identity[1]}"
            )
        section = fields["Section"]
        if any(character in section for character in "\t\r\n"):
            raise InventoryError(f"invalid section for {identity[0]}={identity[1]}")
        resolved[identity] = section

    missing = expected - resolved.keys()
    if missing:
        preview = ", ".join(f"{name}={version}" for name, version in sorted(missing)[:5])
        raise InventoryError(
            "filesystem.packages contains identities absent from the packed dpkg status: "
            + preview
        )
    return sorted((name, version, resolved[(name, version)]) for name, version in manifest)


def write_atomic(path: Path, records: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write("\t".join(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = parse_manifest(args.manifest)
        records = reconcile(manifest, parse_status(args.status))
        write_atomic(args.output, records)
    except InventoryError as exc:
        parser.error(str(exc))
    print(f"recorded {len(records)} exact package sections in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
