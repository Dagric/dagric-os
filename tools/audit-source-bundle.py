#!/usr/bin/env python3
"""Audit/download exact private candidate source objects; never approve release.

Default is offline. --download requires an explicit transfer budget. Completed
cache objects are rehashed on every run; interrupted transfers are discarded,
not trusted as a resume prefix. No archives are extracted or executed. Inputs
are supplied immutable-image inventories, not independently extracted ISO bytes.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from threading import Condition, Lock
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dagric_bundle_embedded", ROOT / "tools/check-embedded-sources.py")
embedded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embedded)
Error = embedded.InventoryError
require = embedded.require
DSC_LIMIT = 2 * 1024 * 1024
CHUNK = 1024 * 1024
DAGRIC_PACKAGES = {"dagric-branding", "dagric-desktop-defaults", "dagric-security-policy", "dagric-tools"}
LIMITS = [
    "ISO hashes are supplied receipt values checked against the supplied source index; this tool does not hash or extract ISO images.",
    "SHA-256 and DSC sizes verify object content against candidate metadata, not OpenPGP signatures or signer authority.",
    "HTTPS is restricted to official Snapshot and exact Dagric GitHub archive URLs; pre-existing caches are rehashed, not treated as authenticated retrieval receipts.",
    "network_bytes_transferred counts response-body bytes returned by explicit reads, not wire traffic or HTTP headers; failed reads consume conservative budget reservations reported separately, not measured transferred bytes.",
    "Coverage includes primary and declared Built-Using/Static-Built-Using sources only; undeclared vendored code and complete corresponding-source obligations need separate review.",
    "Private local availability is not public delivery, retention, legal approval, or release authorization. No publication or promotion is performed.",
]


def regular(path: Path) -> None:
    """Reject symlinks/reparse points in every existing path component."""
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise Error(f"unsafe linked path: {part}")
        if part.exists():
            info = part.lstat()
            require(not getattr(info, "st_file_attributes", 0) & 0x400, f"unsafe reparse path: {part}")
    if path.exists():
        require(path.is_file(), f"expected regular file: {path}")
        require(path.stat().st_nlink == 1, f"hard-linked input/cache object refused: {path}")


def read(path: Path) -> bytes:
    regular(path)
    return path.read_bytes()


def read_json(path: Path):
    payload = read(path)
    return json.loads(payload.decode("utf-8"), object_pairs_hook=embedded.unique_json), embedded.sha256(payload)


def control(text: str) -> dict[str, str]:
    fields, current = {}, None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")):
            require(current is not None, "orphan control continuation")
            fields[current] += "\n" + line.strip()
            continue
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9-]*):[ \t]*(.*)", line)
        require(match is not None, "malformed source control field")
        current, value = match.groups()
        current = current.lower()
        require(current not in fields, f"duplicate source control field {current}")
        fields[current] = value
    return fields


def verify_dsc(payload: bytes, record: dict) -> list[dict]:
    require(0 < len(payload) <= DSC_LIMIT, "DSC exceeds size limit or is empty")
    require(embedded.sha256(payload) == record["integrity"]["dsc_sha256"], "DSC SHA-256 mismatch")
    text = payload.decode("utf-8").replace("\r\n", "\n")
    if text.startswith("-----BEGIN PGP SIGNED MESSAGE-----\n"):
        _headers, separator, text = text.partition("\n\n")
        require(bool(separator), "malformed clearsigned DSC header")
        text, separator, signature = text.partition("\n-----BEGIN PGP SIGNATURE-----")
        require(bool(separator) and "-----END PGP SIGNATURE-----" in signature, "malformed DSC signature armor")
        text = "\n".join(line[2:] if line.startswith("- ") else line for line in text.splitlines())
    fields = control(text)
    require(fields.get("source") == record["source_name"] and fields.get("version") == record["source_version"],
            "DSC Source/Version does not match exact candidate identity")
    checksums = {}
    for line in fields.get("checksums-sha256", "").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        require(len(parts) == 3 and bool(embedded.SHA256.fullmatch(parts[0]))
                and bool(re.fullmatch(r"[0-9]+", parts[1])), "invalid DSC checksum/size row")
        digest, size, filename = parts
        require(filename not in {".", ".."} and not any(c in filename for c in "/\\\x00"), "unsafe DSC filename")
        require(filename not in checksums, f"duplicate DSC filename {filename}")
        require(int(size) > 0, "DSC source size must be positive")
        checksums[filename] = (digest, int(size))
    expected = record["integrity"]["source_files"]
    require(bool(checksums) and set(checksums) == {row["filename"] for row in expected}, "DSC source file set differs from candidate metadata")
    result = []
    for row in expected:
        digest, size = checksums[row["filename"]]
        require(digest == row["sha256"], f"DSC source digest mismatch for {row['filename']}")
        result.append({**row, "size_bytes": size, "kind": "debian-source"})
    return result


def verify_primary_status(status_bytes, exact_map, commit):
    """Do not accept an arbitrary source identity for an installed binary."""
    for edition in ("free", "pro"):
        entries = {(row["binary_name"], row["binary_version"]): row for row in exact_map["editions"][edition]["entries"]}
        for paragraph in re.split(r"\n\s*\n", status_bytes[edition].decode("utf-8").replace("\r\n", "\n")):
            if not paragraph.strip():
                continue
            fields = control(paragraph)
            if fields.get("status", "").split()[-1:] != ["installed"]:
                continue
            name, version, arch = (fields[key] for key in ("package", "version", "architecture"))
            candidates = {(name, version), (f"{name}:{arch}", version)} & entries.keys()
            require(len(candidates) == 1, f"{edition}: ambiguous installed source identity")
            entry = entries[next(iter(candidates))]
            if entry["origin"] == "dagric":
                require(name in DAGRIC_PACKAGES and entry["source_name"] == "dagric-os"
                        and entry["source_version"] == commit, "unsupported local Dagric source mapping")
                continue
            match = re.fullmatch(r"([a-z0-9][a-z0-9+.-]*)(?:\s+\(([^\s()]+)\))?", fields.get("source", name))
            require(match is not None, f"{edition}: malformed installed Source field")
            source_name, source_version = match.groups()
            require((entry["source_name"], entry["source_version"]) == (source_name, source_version or version),
                    f"{edition}: primary source disagrees with immutable dpkg Source for {name}={version}")


def candidate_inputs(args):
    primary, map_hash = read_json(args.map_path)
    if "debian_layer" in primary:
        primary = primary["debian_layer"]["exact_binary_to_source_map"]
    supplement, supplement_hash = read_json(args.supplement)
    index, index_hash = read_json(args.index)
    commit = args.dagric_commit
    iso_hashes = {edition: getattr(args, f"{edition}_iso_sha256") for edition in ("free", "pro")}
    status_bytes = {edition: read(getattr(args, f"{edition}_status")) for edition in ("free", "pro")}
    inventory = embedded.build_report(status_bytes, primary, supplement, commit, iso_hashes, map_hash, supplement_hash)
    require(inventory["missing_exact_source_identities"] == 0, "missing exact declared embedded-source metadata")
    release = index.get("release", {})
    require(release.get("source_commit") == commit, "source-index commit mismatch")
    artifacts = release.get("artifacts")
    require(isinstance(artifacts, list) and len(artifacts) == 2
            and {row.get("edition") for row in artifacts} == {"free", "pro"}, "source index needs exactly one artifact per edition")
    artifacts = {row["edition"]: row for row in artifacts}
    auditor, failures, manifest_identities, manifest_hashes = embedded.load_auditor(), [], {}, {}
    for edition in ("free", "pro"):
        artifact = artifacts[edition]
        require(artifact.get("sha256") == iso_hashes[edition], f"{edition}: source-index ISO hash mismatch")
        require(type(artifact.get("bytes")) is int and artifact["bytes"] > 0, f"{edition}: invalid ISO size")
        path = getattr(args, f"{edition}_manifest")
        payload = read(path)
        manifest_hashes[edition] = embedded.sha256(payload)
        require(artifact.get("binary_package_manifest_sha256") == manifest_hashes[edition], f"{edition}: manifest digest mismatch")
        rows = [tuple(line.split()) for line in payload.decode("utf-8").splitlines()]
        require(bool(rows) and all(len(row) == 2 for row in rows) and len(set(rows)) == len(rows), f"{edition}: malformed/duplicate manifest rows")
        manifest_identities[edition] = rows
    auditor.validate_exact_source_map(primary, artifacts, manifest_identities, commit, failures)
    require(not failures, "; ".join(failures))
    verify_primary_status(status_bytes, primary, commit)
    packages = {edition: embedded.parse_status(body, edition) for edition, body in status_bytes.items()}
    sources = embedded.primary_sources(primary, packages, commit, auditor)
    additions = embedded.supplementary_sources(supplement, commit, auditor)
    declared = {(row["source_name"], row["source_version"]) for row in inventory["entries"]}
    require(not (additions.keys() - declared), "supplement contains undeclared extraneous source identities")
    sources.update(additions)
    for identity, record in sources.items():
        if record["origin"] == "debian":
            # Apply the stricter pinned URL rules to primary records too.
            embedded.validate_source(record, commit, auditor, str(identity), supplement=True)
        else:
            require(record["locator"]["dagric_source_archive_url"] == f"https://github.com/Dagric/dagric-os/archive/{commit}.tar.gz",
                    "Dagric archive must use the exact official commit URL")
    binding = {**inventory["inputs"], "source_index_sha256": index_hash, "package_manifest_sha256": manifest_hashes,
               "iso_size_bytes_from_supplied_index": {edition: artifacts[edition]["bytes"] for edition in ("free", "pro")}}
    return sources, binding, inventory


def allowed_url(url: str):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and not parsed.query and not parsed.fragment, "non-HTTPS or decorated download URL refused")
    path = unquote(parsed.path)
    require("\\" not in path and not any(part in {".", ".."} for part in path.split("/")), "unsafe source download path")
    if parsed.netloc == "snapshot.debian.org":
        if re.fullmatch(r"/file/[0-9a-f]{40}(?:/[A-Za-z0-9][A-Za-z0-9.+:~_-]*)?/?", path):
            return
        embedded.snapshot_parts(url)
        return
    patterns = {"github.com": r"/Dagric/dagric-os/archive/[0-9a-f]{40}\.tar\.gz",
                "codeload.github.com": r"/Dagric/dagric-os/tar\.gz/[0-9a-f]{40}"}
    require(parsed.netloc in patterns and re.fullmatch(patterns[parsed.netloc], path), "unapproved source download host/path")


class SafeRedirect(HTTPRedirectHandler):
    def http_error_302(self, request, response, code, message, headers):
        # urllib normally drains the entire redirect body using fp.read(),
        # outside ObjectCache's explicitly budgeted reads. Discard that body
        # by closing the response instead. Keep urllib's URL normalization,
        # loop limits, method rules, and our redirect_request identity checks.
        class NoDrain:
            def read(self, *args, **kwargs):
                return b""

            def close(self):
                response.close()

            def __getattr__(self, name):
                return getattr(response, name)

        try:
            return super().http_error_302(request, NoDrain(), code, message, headers)
        finally:
            response.close()

    # The standard-library aliases otherwise retain its original method and
    # bypass this override for these redirect status codes.
    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, request, response, code, message, headers, newurl):
        allowed_url(newurl)
        old, new = urlsplit(request.full_url), urlsplit(newurl)
        require(old.netloc == new.netloc or (old.netloc == "github.com" and new.netloc == "codeload.github.com"), "source download crossed unrelated origins")
        if old.netloc == "snapshot.debian.org":
            original, target = unquote(old.path), unquote(new.path)
            target_file = re.fullmatch(r"/file/[0-9a-f]{40}/([^/]+)/?", target)
            if target_file:
                require(original.rsplit("/", 1)[-1] == target_file.group(1), "Snapshot redirect changed source filename")
        if old.netloc in {"github.com", "codeload.github.com"}:
            require(re.search(r"[0-9a-f]{40}", old.path).group() == re.search(r"[0-9a-f]{40}", new.path).group(), "redirect changed source commit")
        return super().redirect_request(request, response, code, message, headers, newurl)


class ObjectCache:
    def __init__(self, root, legacy=None, download=False, budget=0, timeout=30, opener=None):
        self.root, self.legacy, self.download, self.budget, self.timeout = root.absolute(), legacy, download, budget, timeout
        regular(self.root / ".probe")
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock, self.transferred, self.reserved = Lock(), 0, 0
        self.failed_read_budget_charges = 0
        self.condition = Condition(self.lock)
        self.opener = opener or build_opener(SafeRedirect())

    def path(self, digest):
        require(isinstance(digest, str) and bool(embedded.SHA256.fullmatch(digest)), "invalid object digest")
        return self.root / f"{digest}.blob"

    def verify(self, path, digest, size=None, maximum=None):
        regular(path)
        if not path.exists():
            return None
        require(maximum is None or path.stat().st_size <= maximum, f"cached object exceeds size limit: {path.name}")
        count, hash_value = 0, hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                count += len(chunk)
                hash_value.update(chunk)
        require(count > 0 and hash_value.hexdigest() == digest, f"cached object SHA-256 mismatch: {path.name}")
        require(size is None or count == size, f"cached object size mismatch: {path.name}")
        return count

    def network_chunk(self, source, requested):
        """Reserve reads across workers so even failed transfers respect budget."""
        with self.condition:
            while self.budget - self.transferred - self.failed_read_budget_charges - self.reserved <= 0 and self.reserved:
                self.condition.wait()
            available = self.budget - self.transferred - self.failed_read_budget_charges - self.reserved
            require(available > 0, "download transfer budget exhausted")
            reserved = min(requested, available)
            self.reserved += reserved
        received, read_completed = 0, False
        try:
            chunk = source.read(reserved)
            received = len(chunk)
            read_completed = True
            require(received <= reserved, "transport returned more bytes than requested")
            return chunk
        finally:
            with self.condition:
                self.reserved -= reserved
                self.transferred += received
                if not read_completed:
                    # A timeout or truncated chunked response may consume
                    # bytes before raising, sometimes without exposing those
                    # partial bytes. Never recycle that uncertain allowance
                    # or misreport its full reservation as measured traffic.
                    self.failed_read_budget_charges += reserved
                self.condition.notify_all()

    def get(self, obj, namespace=None):
        path, digest, expected_size = self.path(obj["sha256"]), obj["sha256"], obj.get("size_bytes")
        allowed_url(obj["url"])
        maximum = DSC_LIMIT if obj["kind"] == "dsc" else expected_size
        cached = self.verify(path, digest, expected_size, maximum)
        if cached is not None:
            return {"state": "verified-cache", "size_bytes": cached, "cache_object": path.name}
        legacy = None
        if self.legacy and namespace:
            legacy = self.legacy / namespace / (embedded.sha256(obj["url"].encode()) + ".bin")
            legacy_size = self.verify(legacy, digest, expected_size, maximum)
            if legacy_size is None:
                legacy = None
        if legacy is None and not self.download:
            return {"state": "missing", "size_bytes": expected_size, "cache_object": path.name}
        if legacy is None and maximum is None:
            maximum = self.budget  # Dagric archive size is not present in old maps.
        if legacy is None:
            with self.lock:
                require(self.transferred + self.failed_read_budget_charges < self.budget, "download transfer budget exhausted")
        descriptor, temporary = tempfile.mkstemp(prefix=".download-", dir=self.root)
        temporary = Path(temporary)
        count, hash_value = 0, hashlib.sha256()
        try:
            source = legacy.open("rb") if legacy else self.opener.open(Request(obj["url"], headers={"User-Agent": "Dagric-private-source-audit/1.0", "Accept-Encoding": "identity"}), timeout=self.timeout)
            with os.fdopen(descriptor, "wb") as destination, source:
                descriptor = None
                length = None
                if not legacy:
                    require(source.status == 200, "source download did not return HTTP 200")
                    allowed_url(source.geturl())
                    require(source.headers.get("Content-Encoding", "identity") == "identity", "encoded source transport refused")
                    length = source.headers.get("Content-Length")
                    require(length is None or (length.isdecimal() and (expected_size is None or int(length) == expected_size)), "HTTP Content-Length differs from DSC size")
                while True:
                    # A verified Content-Length (or stat-checked legacy input)
                    # frames the object. Otherwise probe one extra byte so a
                    # correct prefix with unexpected trailing bytes is rejected.
                    if expected_size is not None and count == expected_size and (legacy or length is not None):
                        break
                    requested = min(CHUNK, expected_size - count + 1) if expected_size is not None else CHUNK
                    chunk = source.read(requested) if legacy else self.network_chunk(source, requested)
                    if not chunk:
                        break
                    count += len(chunk)
                    require(maximum is None or count <= maximum, "source object exceeds expected size/limit")
                    hash_value.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            require(count > 0 and hash_value.hexdigest() == digest, "download/import SHA-256 mismatch")
            require(expected_size is None or count == expected_size, "download/import size mismatch")
            with self.lock:
                regular(path)
                if path.exists():
                    self.verify(path, digest, expected_size)
                else:
                    os.replace(temporary, path)
            return {"state": "verified-import" if legacy else "verified-download", "size_bytes": count, "cache_object": path.name}
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()


def parallel(values, workers, function):
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(function, value): value for value in values}
        for future in as_completed(futures):
            value = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"identity": value.get("source_name", value.get("filename", "object")), "error": str(exc)})
    return results, failures


def audit(sources, binding, inventory, cache, workers):
    def metadata(record):
        if record["origin"] == "dagric":
            return {"source_name": record["source_name"], "source_version": record["source_version"], "objects": [{
                "kind": "dagric-source", "filename": f"dagric-os-{record['source_version']}.tar.gz",
                "url": record["locator"]["dagric_source_archive_url"], "sha256": record["integrity"]["source_archive_sha256"],
                "size_bytes": None}], "dsc": None}
        obj = {"kind": "dsc", "filename": unquote(urlsplit(record["locator"]["dsc_url"]).path).rsplit("/", 1)[-1],
               "url": record["locator"]["dsc_url"], "sha256": record["integrity"]["dsc_sha256"]}
        result = cache.get(obj, "dsc")
        require(result["state"] != "missing", f"missing DSC {obj['filename']}")
        objects = verify_dsc(read(cache.path(obj["sha256"])), record)
        return {"source_name": record["source_name"], "source_version": record["source_version"], "objects": objects, "dsc": {**obj, **result}}

    records, failures = parallel(list(sources.values()), workers, metadata)
    objects = {}
    for record in records:
        for obj in record["objects"]:
            key = obj["sha256"]
            if key in objects:
                require(objects[key]["size_bytes"] == obj["size_bytes"], "same content digest has contradictory source sizes")
                objects[key]["aliases"].append({"filename": obj["filename"], "url": obj["url"]})
            else:
                objects[key] = {**obj, "aliases": [{"filename": obj["filename"], "url": obj["url"]}]}
    # Do not fetch tarballs while any DSC is missing or contradictory.
    def content(obj):
        return {**obj, **cache.get(obj, "dagric-source" if obj["kind"] == "dagric-source" else None)}
    checked, content_failures = parallel(list(objects.values()), workers, content) if not failures else ([], [])
    failures.extend(content_failures)
    missing = sum(row["state"] == "missing" for row in checked)
    all_verified = not failures and not missing and len(checked) == len(objects) and len(records) == len(sources)
    return {"format": "dagric-private-source-bundle-audit-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "exact-declared-source-objects-verified" if all_verified else "incomplete",
            "private": True, "release_approved": False, "corresponding_source_complete": False,
            "openpgp_signatures_verified": False, "public_delivery_verified": False,
            "source_commit": inventory["source_commit"], "inputs": binding,
            "declarations_by_edition": inventory["declarations_by_edition"], "declared_embedded_sources": inventory["entries"],
            "source_identity_count": len(sources), "dsc_objects_verified": sum(row["dsc"] is not None for row in records),
            "unique_content_objects_expected": len(objects), "content_objects_verified": sum(row["state"].startswith("verified-") for row in checked),
            "content_objects_missing": missing, "known_content_bytes": sum(row["size_bytes"] or 0 for row in checked),
            "content_objects_with_unknown_size": sum(row["size_bytes"] is None for row in checked),
            "network_bytes_transferred": cache.transferred,
            "network_failed_read_budget_charges": cache.failed_read_budget_charges,
            "network_budget_bytes_charged": cache.transferred + cache.failed_read_budget_charges,
            "network_budget_bytes_limit": cache.budget,
            "sources": sorted(records, key=lambda row: (row["source_name"], row["source_version"])),
            "objects": sorted(checked, key=lambda row: row["sha256"]), "failures": failures, "limits": LIMITS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for edition in ("free", "pro"):
        parser.add_argument(f"--{edition}-status", type=Path, required=True)
        parser.add_argument(f"--{edition}-manifest", type=Path, required=True)
        parser.add_argument(f"--{edition}-iso-sha256", required=True)
    parser.add_argument("--map", dest="map_path", type=Path, required=True)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--dagric-commit", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--legacy-snapshot-cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--max-download-bytes", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        require(1 <= args.workers <= 8 and 1 <= args.timeout <= 120, "workers must be 1..8 and timeout 1..120 seconds")
        require(args.max_download_bytes >= 0 and (not args.download or args.max_download_bytes > 0), "--download requires positive --max-download-bytes")
        regular(args.output)
        require(not args.output.exists(), "output must be a new private report path")
        sources, binding, inventory = candidate_inputs(args)
        cache = ObjectCache(args.cache, args.legacy_snapshot_cache, args.download, args.max_download_bytes, args.timeout)
        report = audit(sources, binding, inventory, cache, args.workers)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        regular(args.output)
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print(f"source-bundle: {report['status']}: {report['source_identity_count']} sources; {report['dsc_objects_verified']} DSC; {report['content_objects_verified']}/{report['unique_content_objects_expected']} content objects; {len(report['failures'])} failures")
        print(f"source-bundle: private report {args.output}; NOT release approval, OpenPGP verification or public source delivery")
        return 0 if report["status"] == "exact-declared-source-objects-verified" else 1
    except (Error, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"source-bundle: BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
