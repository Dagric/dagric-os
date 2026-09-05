#!/usr/bin/env python3
"""Bind a private source-bundle report to actual immutable image bytes.

Read-only image inspection in Debian/WSL; no mount, guest execution or publication.
This validates image/inventory identity, not archive contents, build provenance,
signatures, exhaustive source compliance, or human release approval.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_bundle", ROOT / "tools/audit-source-bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)
Error = bundle.Error
require = bundle.require
SHA256 = re.compile(r"[0-9a-f]{64}")
MANIFEST_LIMIT = 4 * 1024 * 1024
STATUS_LIMIT = 64 * 1024 * 1024
EDITION_LIMIT = 99
COMMAND_OUTPUT_LIMIT = 128 * 1024
COMMAND_ERROR_LIMIT = 64 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    bundle.regular(path)
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def identity(path):
    bundle.regular(path)
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def validate_report(report):
    require(report.get("format") == "dagric-private-source-bundle-audit-v1", "unsupported source-bundle report")
    require(report.get("private") is True and report.get("release_approved") is False,
            "source report must remain private and non-approving")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", report.get("source_commit", ""))), "invalid source commit")
    inputs = report.get("inputs", {})
    for key in ("iso_sha256_from_supplied_receipts", "dpkg_status_sha256", "package_manifest_sha256"):
        values = inputs.get(key, {})
        require(set(values) == {"free", "pro"}, f"missing/extra editions in {key}")
        require(all(isinstance(value, str) and SHA256.fullmatch(value) for value in values.values()), f"invalid digest in {key}")
    sizes = inputs.get("iso_size_bytes_from_supplied_index", {})
    require(set(sizes) == {"free", "pro"} and all(type(size) is int and size > 0 for size in sizes.values()), "invalid image sizes")
    for key in ("primary_map_sha256", "supplement_sha256", "source_index_sha256"):
        require(isinstance(inputs.get(key), str) and bool(SHA256.fullmatch(inputs[key])), f"missing input binding {key}")
    return inputs


def command(argv, *, max_bytes=COMMAND_OUTPUT_LIMIT, timeout=600):
    """Bound both pipes while reading; never buffer an entire oversized file.

    This tool targets Debian/WSL, where selectors support process pipes. Read
    at most one byte past either limit, then terminate and reap that extractor.
    A short deadline also applies when a process closes its pipes but remains
    alive. No partial output is returned as a successful extraction.
    """
    require(type(max_bytes) is int and max_bytes > 0 and timeout > 0, "invalid extractor limits")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": max_bytes, "stderr": COMMAND_ERROR_LIMIT}
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, timeout)
                for key, _events in selector.select(remaining):
                    label = key.data
                    chunk = os.read(key.fileobj.fileno(), min(65536, limits[label] - len(buffers[label]) + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffers[label].extend(chunk)
                    require(len(buffers[label]) <= limits[label], f"{argv[0]} {label} exceeds {limits[label]} byte limit")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, timeout)
        returncode = process.wait(timeout=remaining)
        require(returncode == 0, f"{argv[0]} failed ({returncode}): {buffers['stderr'].decode(errors='replace')[-1500:]}")
        return bytes(buffers["stdout"])
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()


def read_inventory(path, maximum):
    bundle.regular(path)
    size = path.stat().st_size
    require(0 < size <= maximum, "empty/oversized package inventory")
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    require(len(payload) == size and len(payload) <= maximum, "package inventory changed or exceeded its limit while reading")
    return payload


def extract_image(iso, scratch):
    package_path = scratch / "filesystem.packages"
    squash_path = scratch / "filesystem.squashfs"
    command(["xorriso", "-osirrox", "on", "-indev", str(iso), "-extract", "/live/filesystem.packages", str(package_path)])
    manifest = read_inventory(package_path, MANIFEST_LIMIT)
    command(["xorriso", "-osirrox", "on", "-indev", str(iso), "-extract", "/live/filesystem.squashfs", str(squash_path)])
    bundle.regular(squash_path)
    status = command(["unsquashfs", "-cat", str(squash_path), "var/lib/dpkg/status"], max_bytes=STATUS_LIMIT)
    edition = command(["unsquashfs", "-cat", str(squash_path), "etc/dagric-edition"], max_bytes=EDITION_LIMIT)
    require(bool(status), "empty package inventory")
    require(bool(edition), "empty edition marker")
    return manifest, status, edition


def verify_edition(edition, iso, inputs, scratch, extractor=extract_image):
    before = identity(iso)
    require(before[2] == inputs["iso_size_bytes_from_supplied_index"][edition], f"{edition}: ISO byte count differs")
    expected = inputs["iso_sha256_from_supplied_receipts"][edition]
    require(file_digest(iso) == expected, f"{edition}: actual ISO SHA-256 differs")
    manifest, status, marker = extractor(iso, scratch)
    require(marker.decode("ascii").strip() == edition, f"{edition}: embedded edition marker differs")
    manifest_hash, status_hash = sha256(manifest), sha256(status)
    require(manifest_hash == inputs["package_manifest_sha256"][edition], f"{edition}: immutable package manifest differs")
    require(status_hash == inputs["dpkg_status_sha256"][edition], f"{edition}: immutable dpkg status differs")
    require(identity(iso) == before and file_digest(iso) == expected, f"{edition}: ISO changed during inspection")
    return {"edition": edition, "iso": str(iso), "bytes": before[2], "sha256": expected,
            "package_manifest_sha256": manifest_hash, "dpkg_status_sha256": status_hash,
            "embedded_edition": edition, "unchanged_during_inspection": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-report", type=Path, required=True)
    parser.add_argument("--free-iso", type=Path, required=True)
    parser.add_argument("--pro-iso", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        bundle.regular(args.output)
        require(not args.output.exists(), "output must be a new private report path")
        report_bytes = bundle.read(args.bundle_report)
        report = json.loads(report_bytes.decode("utf-8"), object_pairs_hook=bundle.embedded.unique_json)
        inputs = validate_report(report)
        rows = []
        with tempfile.TemporaryDirectory(prefix="dagric-source-image-bind-") as folder:
            for edition in ("free", "pro"):
                scratch = Path(folder) / edition
                scratch.mkdir(mode=0o700)
                iso = getattr(args, f"{edition}_iso").absolute()
                rows.append(verify_edition(edition, iso, inputs, scratch))
                print(f"source-image-bind: {edition}: actual image, edition, manifest and dpkg status match", flush=True)
        require(bundle.read(args.bundle_report) == report_bytes, "bundle report changed during inspection")
        result = {"format": "dagric-source-bundle-image-binding-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
                  "private": True, "image_inventory_binding_verified": True, "release_approved": False,
                  "corresponding_source_complete": False, "source_commit_from_bundle_report": report["source_commit"],
                  "bundle_report_sha256": sha256(report_bytes), "bundle_status_not_reassessed": report.get("status"),
                  "editions": rows, "limits": [
                      "Hashes and extracts both actual images; compares inventories byte-for-byte with the source-bundle report bindings.",
                      "Does not recheck source-cache objects: rerun audit-source-bundle.py for their current contents and coverage.",
                      "Source commit is an external build receipt; this check does not prove a reproducible build or an embedded commit marker.",
                      "Does not validate OpenPGP signatures, public source delivery, exhaustive rights, physical tests or release readiness."]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, indent=2) + "\n"
        bundle.regular(args.output)
        descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(encoded)
        print(f"source-image-bind: private receipt {args.output}; NOT release approval")
        return 0
    except (Error, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"source-image-bind: BLOCKED: {exc}; no approval written", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
