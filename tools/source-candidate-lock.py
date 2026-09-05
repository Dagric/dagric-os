#!/usr/bin/env python3
"""Create/check a canonical private candidate source lock, entirely offline.

Revalidates exact maps, supplied extracted inventories and all source-cache
bytes. A successful prior report is never accepted as authority. ISO identities
remain supplied receipt values: actual-image extraction and release, legal,
signature, source-delivery and physical approval are separate gates.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dagric_source_lock_bundle", ROOT / "tools/audit-source-bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)
Error, require = bundle.Error, bundle.require
FORMAT = "dagric-private-candidate-source-lock-v1"
FALSE_FIELDS = ("release_approved", "corresponding_source_complete", "source_authenticity_verified",
                "public_delivery_verified", "independent_image_extraction_verified")
LOCK_KEYS = {"format", "private", *FALSE_FIELDS, "source_commit", "editions", "input_documents", "sources", "objects", "limits"}
LIMITS = [
    "Binds supplied extracted-inventory identity and source bytes, not independent extraction or hashing of ISO images.",
    "The source commit is the externally supplied exact build receipt identity, not proof of an embedded marker or reproducible build.",
    "Includes primary and declared Built-Using/Static-Built-Using sources; undeclared code and complete corresponding-source obligations require separate review.",
    "No source-index, verification-report or self digest is embedded; consumers may hash this canonical lock without a circular dependency.",
    "No network, publication, source authenticity, qualified legal/rights, public delivery, retention, physical or release approval is performed.",
]


def canonical(document) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def lock_shape(document):
    require(isinstance(document, dict) and set(document) == LOCK_KEYS, "unsupported/missing source-lock members")
    require(document.get("format") == FORMAT and document.get("private") is True, "source lock must use the private canonical format")
    require(all(document.get(field) is False for field in FALSE_FIELDS), "source lock cannot claim authenticity, delivery, image or release approval")


def safe_filename(value):
    require(isinstance(value, str) and bool(value) and value not in {".", ".."}
            and not any(character in value for character in "/\\\x00")
            and value == value.strip(), "invalid candidate artifact filename")
    return value


def source_lock(args):
    """Recompute the lock from validated immutable input documents and cache."""
    require(1 <= args.workers <= 8, "workers must be between 1 and 8")
    require(args.cache.is_dir(), "existing complete source-cache directory is required")
    bundle.regular(args.cache / ".source-lock-probe")
    sources, binding, inventory = bundle.candidate_inputs(args)
    index, index_hash = bundle.read_json(args.index)
    require(index_hash == binding["source_index_sha256"], "source index changed during input validation")
    artifacts = {row["edition"]: row for row in index["release"]["artifacts"]}
    for artifact in artifacts.values():
        safe_filename(artifact.get("filename"))
    # Never enable network or import a legacy cache. Missing objects fail; this
    # prerequisite only consumes fully verified existing private source bytes.
    cache = bundle.ObjectCache(args.cache, download=False)
    report = bundle.audit(sources, binding, inventory, cache, args.workers)
    require(report["status"] == "exact-declared-source-objects-verified"
            and not report["failures"] and report["content_objects_missing"] == 0,
            "complete exact source-cache verification is required; missing or inconsistent source objects")
    require(report["release_approved"] is False and report["corresponding_source_complete"] is False
            and report["openpgp_signatures_verified"] is False and report["public_delivery_verified"] is False,
            "upstream private audit contract must not claim source or release approval")
    require(report["network_bytes_transferred"] == 0, "source-lock creation must not use the network")
    content = {row["sha256"]: row for row in report["objects"]}
    require(len(content) == len(report["objects"]), "duplicate audited content object")
    object_table = {}

    def object_reference(row, kind):
        size = row.get("size_bytes")
        require(type(size) is int and size > 0, "source lock needs exact positive object sizes")
        digest = row["sha256"]
        require(bool(bundle.embedded.SHA256.fullmatch(digest)), "invalid source object digest")
        filename = safe_filename(row["filename"])
        reference = {"filename": filename, "sha256": digest, "size_bytes": size, "upstream_url": row["url"]}
        obj = object_table.setdefault(digest, {"sha256": digest, "size_bytes": size, "kinds": set(), "filenames": set(), "upstream_urls": set()})
        require(obj["size_bytes"] == size, "shared object has inconsistent sizes")
        obj["kinds"].add(kind)
        obj["filenames"].add(filename)
        obj["upstream_urls"].add(row["url"])
        return reference

    records = []
    for record in report["sources"]:
        identity = (record["source_name"], record["source_version"])
        require(identity in sources, "unrecognized audited source identity")
        files = []
        for declared in record["objects"]:
            actual = content.get(declared["sha256"])
            require(actual is not None and actual["state"].startswith("verified-"), "source object lacks verified content")
            files.append(object_reference({**declared, "size_bytes": actual["size_bytes"]}, declared["kind"]))
        descriptor = object_reference(record["dsc"], "dsc") if record["dsc"] is not None else None
        records.append({"source_name": identity[0], "source_version": identity[1], "origin": sources[identity]["origin"],
                        "dsc": descriptor, "files": sorted(files, key=lambda row: (row["filename"], row["sha256"]))})
    require(len(records) == len(sources), "source lock is missing source identities")
    editions = {}
    for edition in ("free", "pro"):
        declarations = []
        for row in inventory["entries"]:
            for reference in row["referenced_by"]:
                if reference["edition"] == edition:
                    declarations.append({"source_name": row["source_name"], "source_version": row["source_version"],
                                         **{key: reference[key] for key in ("field", "binary_name", "binary_architecture", "binary_version")}})
        declarations.sort(key=lambda row: (row["binary_name"], row["binary_architecture"], row["binary_version"],
                                            row["field"], row["source_name"], row["source_version"]))
        editions[edition] = {"iso_filename": safe_filename(artifacts[edition].get("filename")),
                            "iso_size_bytes": binding["iso_size_bytes_from_supplied_index"][edition],
                            "iso_sha256_from_supplied_receipts": binding["iso_sha256_from_supplied_receipts"][edition],
                            "package_manifest_sha256": binding["package_manifest_sha256"][edition],
                            "dpkg_status_sha256": binding["dpkg_status_sha256"][edition], "declared_embedded_sources": declarations}

    # Re-read inputs after the potentially long full-cache hash pass. The
    # canonical lock deliberately excludes the index/report digest, but every
    # identity copied from the checked index still has to remain unchanged.
    expected_inputs = {args.map_path: binding["primary_map_sha256"], args.supplement: binding["supplement_sha256"], args.index: index_hash}
    for edition in ("free", "pro"):
        expected_inputs[getattr(args, f"{edition}_manifest")] = binding["package_manifest_sha256"][edition]
        expected_inputs[getattr(args, f"{edition}_status")] = binding["dpkg_status_sha256"][edition]
    require(all(bundle.embedded.sha256(bundle.read(path)) == expected for path, expected in expected_inputs.items()),
            "source input changed during source-lock verification")
    result = {"format": FORMAT, "private": True, **{field: False for field in FALSE_FIELDS},
              "source_commit": inventory["source_commit"], "editions": editions,
              "input_documents": {"primary_map_sha256": binding["primary_map_sha256"], "supplement_sha256": binding["supplement_sha256"]},
              "sources": sorted(records, key=lambda row: (row["source_name"], row["source_version"])),
              "objects": [{**row, "kinds": sorted(row["kinds"]), "filenames": sorted(row["filenames"]), "upstream_urls": sorted(row["upstream_urls"])}
                          for _digest, row in sorted(object_table.items())], "limits": LIMITS}
    lock_shape(result)
    return result


def verify_lock(path, args):
    document, original_hash = bundle.read_json(path)
    lock_shape(document)
    require(bundle.read(path) == canonical(document), "source lock is not canonical JSON")
    expected = source_lock(args)
    require(canonical(document) == canonical(expected), "source lock differs from freshly verified candidate inputs/content")
    require(bundle.embedded.sha256(bundle.read(path)) == original_hash, "source lock changed during validation")
    return expected


def write_new(path, document):
    payload = canonical(document)
    bundle.regular(path)
    require(not path.exists(), "output must be a new private source-lock path")
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle.regular(path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".source-lock-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        bundle.regular(path)
        # Atomic exclusive publication of already complete bytes. Unlike
        # os.replace/rename on POSIX, link cannot overwrite an existing report.
        os.link(temporary, path)
    finally:
        temporary.unlink()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("create", "check"))
    for edition in ("free", "pro"):
        result.add_argument(f"--{edition}-status", type=Path, required=True)
        result.add_argument(f"--{edition}-manifest", type=Path, required=True)
        result.add_argument(f"--{edition}-iso-sha256", required=True)
    result.add_argument("--map", dest="map_path", type=Path, required=True)
    result.add_argument("--supplement", type=Path, required=True)
    result.add_argument("--index", type=Path, required=True)
    result.add_argument("--dagric-commit", required=True)
    result.add_argument("--cache", type=Path, required=True)
    result.add_argument("--workers", type=int, default=4)
    result.add_argument("--output", type=Path, help="create mode only: new private canonical lock")
    result.add_argument("--lock", type=Path, help="check mode only: existing private canonical lock")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.mode == "create":
            require(args.output is not None and args.lock is None, "create requires --output and refuses --lock")
            bundle.regular(args.output)
            require(not args.output.exists(), "output must be a new private source-lock path")
            document = source_lock(args)
            write_new(args.output, document)
        else:
            require(args.lock is not None and args.output is None, "check requires --lock and refuses --output")
            document = verify_lock(args.lock, args)
        print(f"source-lock: {args.mode} passed: {len(document['sources'])} exact sources, {len(document['objects'])} unique DSC/content objects; sha256={bundle.embedded.sha256(canonical(document))}")
        print("source-lock: private extracted-inventory/content binding only; NOT source, delivery, image provenance or release approval")
        return 0
    except (Error, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"source-lock: BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
