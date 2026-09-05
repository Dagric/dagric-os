#!/usr/bin/env python3
"""Inventory exact Built-Using/Static-Built-Using source declarations, offline.

Supply dpkg/status files extracted from the immutable Free and Pro images and
their receipt hashes explicitly. This does NOT extract or hash ISO files,
download source archives, verify signatures, decide rights, or approve release.
The ordinary binary/source map remains unchanged. Output must be a NEW private
report path; a missing supplement still produces an inventory and a failing exit.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCE_KEYS = {"source_name", "source_version", "origin", "locator", "integrity"}
SOURCE_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]*")
ARCHITECTURE = re.compile(r"[a-z0-9][a-z0-9-]*")
VERSION = re.compile(r"[0-9][A-Za-z0-9.+:~\-]*")
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
DECLARATION = re.compile(r"\s*([a-z0-9][a-z0-9+.-]*)\s*\(=\s*([^\s()]+)\)\s*")
DECLARATION_FIELDS = ("Built-Using", "Static-Built-Using")
LIMITS = [
    "Checks only exact source identities declared in installed Built-Using and Static-Built-Using fields; undeclared embedded code is outside this inventory.",
    "ISO SHA-256 values are supplied receipt values, not hashes independently computed from ISO bytes by this tool.",
    "Input hashes bind this report to the supplied status files, map, supplement, and source commit; extraction provenance requires separate artifact evidence.",
    "Source locator and digest metadata is checked offline; archive availability, downloaded content, signatures, and complete corresponding-source obligations are not verified here.",
    "Static-Built-Using alone does not determine a legal obligation; qualified package-rights, firmware, and artwork review remains separate.",
    "Passing this inventory does not approve distribution or release, supersede physical security evidence, or change the public source map.",
]


class InventoryError(ValueError):
    """An input cannot safely support an exact inventory."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InventoryError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def read_json(path: Path):
    body = path.read_bytes()
    return json.loads(body.decode("utf-8"), object_pairs_hook=unique_json), sha256(body)


def parse_status(payload: bytes, edition: str) -> list[dict]:
    """Parse Deb822, retaining architecture even for non-Multi-Arch packages."""
    records = []
    seen = {}
    fields = {}
    current = None

    def finish():
        nonlocal fields, current
        if not fields:
            return
        status = fields.get("status", "").split()
        require(len(status) == 3, f"{edition}: paragraph lacks a valid Status field")
        require(status[0] in {"unknown", "install", "hold", "deinstall", "purge"}
                and status[1] in {"ok", "reinstreq"}
                and status[2] in {"not-installed", "config-files", "half-installed", "unpacked",
                                  "half-configured", "triggers-awaited", "triggers-pending", "installed"},
                f"{edition}: paragraph has an unsupported Status value")
        if status[2] == "installed":
            require(status[1] == "ok", f"{edition}: installed package has an unhealthy Status")
            name, version, arch = (fields.get(key, "") for key in ("package", "version", "architecture"))
            require(bool(SOURCE_NAME.fullmatch(name)), f"{edition}: invalid installed package name {name!r}")
            require(bool(VERSION.fullmatch(version)), f"{edition}: {name}: invalid exact binary version {version!r}")
            require(bool(ARCHITECTURE.fullmatch(arch)), f"{edition}: {name}: missing/invalid architecture")
            multiarch = fields.get("multi-arch", "no")
            require(multiarch in {"no", "same", "foreign", "allowed"}, f"{edition}: {name}: unsupported Multi-Arch value")
            identity = (name, arch)
            if identity in seen:
                detail = "contradictory" if fields != seen[identity] else "repeated"
                raise InventoryError(f"{edition}: duplicate {detail} installed identity {name}:{arch}")
            seen[identity] = fields.copy()
            refs = []
            for field in DECLARATION_FIELDS:
                if field.lower() not in fields:
                    continue
                for raw in fields[field.lower()].split(","):
                    match = DECLARATION.fullmatch(raw)
                    require(match is not None, f"{edition}: {name}:{arch}: unsupported {field} declaration {raw!r}")
                    source_name, source_version = match.groups()
                    require(bool(VERSION.fullmatch(source_version)), f"{edition}: {name}:{arch}: invalid exact {field} version {source_version!r}")
                    refs.append((field, source_name, source_version))
            records.append({
                "binary_name": f"{name}:{arch}" if multiarch == "same" else name,
                "binary_architecture": arch,
                "binary_version": version,
                "declarations": refs,
            })
        fields, current = {}, None

    for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            finish()
        elif line.startswith((" ", "\t")):
            require(current is not None, f"{edition}:{number}: orphan continuation line")
            fields[current] += " " + line.strip()
        else:
            match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9-]*):[ \t]*(.*)", line)
            require(match is not None, f"{edition}:{number}: malformed control field")
            current, value = match.groups()
            current = current.lower()
            require(current not in fields, f"{edition}:{number}: duplicate control field {current}")
            fields[current] = value.strip()
    finish()
    require(bool(records), f"{edition}: status file contains no installed packages")
    return records


def load_auditor():
    spec = importlib.util.spec_from_file_location("dagric_embedded_auditor", ROOT / "tools/audit-site.py")
    require(spec is not None and spec.loader is not None, "cannot load source metadata validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot_parts(value: object, *, archive_only=False):
    require(isinstance(value, str), "source locator must be a URL string")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.netloc == "snapshot.debian.org"
            and not parsed.query and not parsed.fragment,
            f"source locator must use official Snapshot HTTPS without credentials/query/fragment: {value!r}")
    path = unquote(parsed.path)
    require("\\" not in path and not any(part in {".", ".."} for part in path.split("/")),
            f"unsafe Snapshot path {value!r}")
    pattern = r"/archive/([a-z0-9][a-z0-9-]*)/([0-9]{8}T[0-9]{6}Z)/"
    match = re.fullmatch(pattern if archive_only else pattern + r"pool/[^\s]+", path)
    require(match is not None, f"source locator lacks a timestamp-pinned Snapshot archive/pool path: {value!r}")
    return parsed, path


def validate_source(record: dict, commit: str, auditor, label: str, *, supplement=False):
    require(isinstance(record, dict), f"{label}: source record must be an object")
    require(set(record) == SOURCE_KEYS, f"{label}: source record must contain exactly {sorted(SOURCE_KEYS)}")
    failures = []
    auditor.validate_source_map_entry(
        {"binary_name": "embedded-source", "binary_version": "0", **record},
        label, 1, commit, failures,
    )
    require(not failures, "; ".join(failures))
    source_identity = (record["source_name"], record["source_version"])
    if record["origin"] == "dagric":
        require(not supplement, f"{label}: supplementary records must be Debian Snapshot sources")
        require(source_identity == ("dagric-os", commit), f"{label}: Dagric source identity is not the selected commit")
    else:
        require(bool(VERSION.fullmatch(record["source_version"])), f"{label}: invalid exact Debian source version")
        locator, integrity = record["locator"], record["integrity"]
        files = integrity.get("source_files")
        require(isinstance(files, list) and bool(files), f"{label}: source_files metadata is required")
        require(bool(locator.get("dsc_url")), f"{label}: .dsc locator is required")
        if supplement:
            require(set(locator) == {"dsc_url", "debian_archive_url"}, f"{label}: incomplete Snapshot locator metadata")
            require(set(integrity) == {"dsc_sha256", "source_files"}, f"{label}: incomplete Snapshot digest metadata")
            _dsc_parsed, dsc_path = snapshot_parts(locator["dsc_url"])
            _archive_parsed, archive_path = snapshot_parts(locator["debian_archive_url"], archive_only=True)
            require(dsc_path.startswith(archive_path) and dsc_path.endswith(".dsc"), f"{label}: .dsc archive identity mismatch")
            expected_dsc = f"{source_identity[0]}_{source_identity[1].split(':', 1)[-1]}.dsc"
            require(dsc_path.rsplit("/", 1)[-1] == expected_dsc, f"{label}: .dsc filename does not match exact source identity")
            for source_file in files:
                filename = source_file["filename"]
                require(filename not in {".", ".."} and "/" not in filename and "\\" not in filename,
                        f"{label}: unsafe source filename")
                _parsed, path = snapshot_parts(source_file["url"])
                require(path.rsplit("/", 1)[0] == dsc_path.rsplit("/", 1)[0]
                        and path.rsplit("/", 1)[-1] == filename,
                        f"{label}: source file URL/filename/archive mismatch")
    return source_identity


def primary_sources(document, packages, commit, auditor):
    require(isinstance(document, dict), "primary source map must be an object")
    if "debian_layer" in document:
        layer = document["debian_layer"]
        require(isinstance(layer, dict), "primary map debian_layer must be an object")
        document = layer.get("exact_binary_to_source_map")
    require(isinstance(document, dict) and document.get("format") == "dagric-exact-binary-source-map-v1", "unsupported primary source map format")
    editions = document.get("editions")
    require(isinstance(editions, dict) and set(editions) == {"free", "pro"}, "primary map must contain Free and Pro editions")
    sources = {}
    for edition, installed in packages.items():
        edition_map = editions[edition]
        require(isinstance(edition_map, dict) and isinstance(edition_map.get("entries"), list), f"{edition}: missing primary map entries")
        binaries = set()
        for position, entry in enumerate(edition_map["entries"], 1):
            failures = []
            binary = auditor.validate_source_map_entry(entry, edition, position, commit, failures)
            require(not failures, "; ".join(failures))
            require(binary not in binaries, f"{edition}: duplicate primary binary identity {binary}")
            binaries.add(binary)
            record = {key: entry[key] for key in SOURCE_KEYS}
            source = validate_source(record, commit, auditor, f"{edition} primary {position}")
            require(source not in sources or sources[source] == record, f"contradictory primary source metadata for {source}")
            sources[source] = record
        expected = set()
        for row in installed:
            name, version = row["binary_name"], row["binary_version"]
            candidates = {(name, version)}
            if ":" not in name:
                # dpkg-query also qualifies foreign-architecture packages that
                # are Multi-Arch: allowed (not just Multi-Arch: same). status
                # has no native-architecture setting; match exactly one spelling
                # from the primary map, never stripping a conflicting suffix.
                candidates.add((f"{name}:{row['binary_architecture']}", version))
            matches = candidates & binaries
            require(len(matches) == 1, f"{edition}: primary map must exactly match one installed identity for {name}:{row['binary_architecture']}={version}, found {sorted(matches)}")
            selected = next(iter(matches))
            expected.add(selected)
            row["binary_name"] = selected[0]
        require(len(expected) == len(installed), f"{edition}: architecture identity would collapse in primary map")
        require(binaries == expected, f"{edition}: primary map does not exactly match installed name/version identities (missing {sorted(expected - binaries)[:8]}, extra {sorted(binaries - expected)[:8]})")
    return sources


def supplementary_sources(document, commit, auditor):
    if document is None:
        return {}
    require(isinstance(document, dict), "supplement must be an object")
    require(set(document) <= {"format", "source_commit", "generated_utc", "entries"}, "supplement contains unsupported fields")
    require(document.get("format") == "dagric-embedded-source-supplement-v1", "unsupported supplement format")
    require(document.get("source_commit") == commit, "supplement source commit does not match selected source commit")
    require(isinstance(document.get("entries"), list), "supplement entries must be a list")
    sources = {}
    for position, record in enumerate(document["entries"], 1):
        source = validate_source(record, commit, auditor, f"supplement {position}", supplement=True)
        require(source not in sources, f"duplicate supplementary source identity {source}")
        sources[source] = record
    return sources


def build_report(status_bytes, primary_map, supplement, commit, iso_hashes, map_hash, supplement_hash):
    require(bool(COMMIT.fullmatch(commit)), "--dagric-commit must be 40 lowercase hexadecimal characters")
    for edition in ("free", "pro"):
        require(bool(SHA256.fullmatch(iso_hashes[edition])), f"--{edition}-iso-sha256 must be 64 lowercase hexadecimal characters")
    packages = {edition: parse_status(status_bytes[edition], edition) for edition in ("free", "pro")}
    auditor = load_auditor()
    primary = primary_sources(primary_map, packages, commit, auditor)
    supplementary = supplementary_sources(supplement, commit, auditor)
    for identity in primary.keys() & supplementary.keys():
        require(primary[identity] == supplementary[identity], f"contradictory primary/supplementary metadata for {identity}")
    dependencies = {}
    counts = {}
    for edition, installed in packages.items():
        counts[edition] = {"installed_binaries": len(installed), "binaries_with_declarations": 0,
                           "Built-Using": 0, "Static-Built-Using": 0}
        for package in installed:
            if package["declarations"]:
                counts[edition]["binaries_with_declarations"] += 1
            for field, name, version in package["declarations"]:
                identity = (name, version)
                counts[edition][field] += 1
                row = dependencies.setdefault(identity, {
                    "source_name": name, "source_version": version,
                    "coverage": "primary" if identity in primary else "supplement" if identity in supplementary else "missing",
                    "referenced_by": [],
                })
                row["referenced_by"].append({"edition": edition, "field": field,
                    **{key: package[key] for key in ("binary_name", "binary_architecture", "binary_version")}})
    entries = [dependencies[key] for key in sorted(dependencies)]
    missing = sum(row["coverage"] == "missing" for row in entries)
    return {
        "format": "dagric-embedded-source-inventory-v1",
        "status": "missing-exact-source-records" if missing else "declared-source-metadata-covered",
        "private": True, "release_approved": False, "corresponding_source_complete": False,
        "source_commit": commit,
        "inputs": {"iso_sha256_from_supplied_receipts": iso_hashes,
                   "dpkg_status_sha256": {edition: sha256(body) for edition, body in status_bytes.items()},
                   "primary_map_sha256": map_hash, "supplement_sha256": supplement_hash},
        "declarations_by_edition": counts,
        "unique_declared_embedded_source_identities": len(entries),
        "already_in_primary_map": sum(row["coverage"] == "primary" for row in entries),
        "covered_by_supplement": sum(row["coverage"] == "supplement" for row in entries),
        "missing_exact_source_identities": missing,
        "entries": entries, "limits": LIMITS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for edition in ("free", "pro"):
        parser.add_argument(f"--{edition}-status", type=Path, required=True)
        parser.add_argument(f"--{edition}-iso-sha256", required=True)
    parser.add_argument("--map", dest="map_path", type=Path, required=True)
    parser.add_argument("--dagric-commit", required=True)
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="new private report; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        require(not args.output.exists() and not args.output.is_symlink(), "--output must be a new report path")
        status_bytes = {"free": args.free_status.read_bytes(), "pro": args.pro_status.read_bytes()}
        primary, map_hash = read_json(args.map_path)
        supplement, supplement_hash = read_json(args.supplement) if args.supplement else (None, None)
        report = build_report(status_bytes, primary, supplement, args.dagric_commit,
            {"free": args.free_iso_sha256, "pro": args.pro_iso_sha256}, map_hash, supplement_hash)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        missing = report["missing_exact_source_identities"]
        print(f"embedded-sources: {report['status']}: {report['unique_declared_embedded_source_identities']} unique declared identities, {missing} missing; report {args.output}")
        print("embedded-sources: metadata coverage only; NOT full corresponding-source clearance or release approval")
        return 1 if missing else 0
    except (InventoryError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"embedded-sources: BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
