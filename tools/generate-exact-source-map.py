#!/usr/bin/env python3
"""Generate Dagric's exact binary-to-Debian-source map from Snapshot.

The input manifests are extracted from the immutable release ISOs.  For each
exact binary name/version this tool asks snapshot.debian.org which Debian
source package/version produced it, locates the archived ``.dsc``, downloads
that small signed control file, verifies its SHA-256 locally, and records every
source file hash named by ``Checksums-Sha256``.

The output is deliberately a standalone candidate object.  Publishing it or
changing a release record to ``complete`` is a separate reviewed operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "https://snapshot.debian.org"
USER_AGENT = "Dagric-exact-source-map/1.0 (+https://dagric.com/contact)"
SHA1_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
TIMESTAMP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z")
ARCHIVE_PRIORITY = {
    "debian": 0,
    "debian-security": 1,
    "debian-ports": 2,
    "debian-archive": 3,
}
DAGRIC_BINARY_PACKAGES = {
    "dagric-branding",
    "dagric-desktop-defaults",
    "dagric-security-policy",
    "dagric-tools",
}


class SourceMapError(RuntimeError):
    """Fail-closed source-map error."""


def parse_manifest(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = raw.split()
        if len(parts) != 2:
            raise SourceMapError(f"{path}:{number}: expected name<TAB>version")
        identity = (parts[0], parts[1])
        if identity in seen:
            raise SourceMapError(f"{path}:{number}: duplicate package {parts[0]}={parts[1]}")
        seen.add(identity)
        records.append(identity)
    if not records:
        raise SourceMapError(f"{path}: empty package manifest")
    return records


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SnapshotClient:
    def __init__(self, cache: Path, retries: int = 5, timeout: int = 45) -> None:
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.retries = retries
        self.timeout = timeout
        self._write_lock = Lock()

    def _cache_path(self, namespace: str, url: str, suffix: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        folder = self.cache / namespace
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{key}.{suffix}"

    def get_bytes(self, url: str, namespace: str = "files") -> bytes:
        cache_path = self._cache_path(namespace, url, "bin")
        if cache_path.is_file():
            return cache_path.read_bytes()
        request = Request(url, headers={"User-Agent": USER_AGENT})
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                if not payload:
                    raise SourceMapError(f"empty response from {url}")
                with self._write_lock:
                    if not cache_path.exists():
                        temp = cache_path.with_suffix(cache_path.suffix + ".tmp")
                        temp.write_bytes(payload)
                        temp.replace(cache_path)
                return payload
            except (HTTPError, URLError, TimeoutError, OSError, SourceMapError) as exc:
                last_error = exc
                if isinstance(exc, HTTPError) and exc.code == 404:
                    break
                if attempt + 1 < self.retries:
                    time.sleep(min(8.0, 0.5 * (2**attempt)))
        raise SourceMapError(f"request failed for {url}: {last_error}")

    def get_json(self, url: str) -> dict[str, object]:
        cache_path = self._cache_path("json", url, "json")
        if cache_path.is_file():
            payload = cache_path.read_bytes()
        else:
            payload = self.get_bytes(url, namespace="json-download")
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise SourceMapError(f"invalid JSON from {url}: {exc}") from exc
            with self._write_lock:
                if not cache_path.exists():
                    temp = cache_path.with_suffix(cache_path.suffix + ".tmp")
                    temp.write_text(
                        json.dumps(parsed, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                    temp.replace(cache_path)
            return parsed
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SourceMapError(f"invalid cached JSON for {url}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SourceMapError(f"expected a JSON object from {url}")
        return parsed


def encoded(value: str) -> str:
    return quote(value, safe="")


def resolve_binary(
    client: SnapshotClient, identity: tuple[str, str], dagric_commit: str
) -> tuple[tuple[str, str], tuple[str, str]]:
    full_name, binary_version = identity
    binary_name = full_name.split(":", 1)[0]
    if binary_name in DAGRIC_BINARY_PACKAGES:
        return identity, ("dagric-os", dagric_commit)
    url = f"{SNAPSHOT}/mr/binary/{encoded(binary_name)}/"
    document = client.get_json(url)
    rows = document.get("result")
    if not isinstance(rows, list):
        raise SourceMapError(f"{binary_name}: Snapshot response lacks result array")
    matches: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("binary_version") != binary_version:
            continue
        source_name = row.get("source")
        source_version = row.get("version")
        if isinstance(source_name, str) and isinstance(source_version, str):
            matches.add((source_name, source_version))
    if len(matches) != 1:
        detail = ", ".join(f"{name}={version}" for name, version in sorted(matches))
        raise SourceMapError(
            f"{full_name}={binary_version}: expected one source mapping, found "
            f"{len(matches)}{': ' + detail if detail else ''}"
        )
    return identity, next(iter(matches))


def choose_archive_record(records: list[dict[str, object]]) -> dict[str, object]:
    usable: list[dict[str, object]] = []
    for record in records:
        archive = record.get("archive_name")
        timestamp = record.get("first_seen")
        path = record.get("path")
        name = record.get("name")
        if not all(isinstance(value, str) for value in (archive, timestamp, path, name)):
            continue
        if str(archive).endswith("-debug") or not TIMESTAMP_RE.fullmatch(str(timestamp)):
            continue
        if not str(path).startswith("/pool/") or "/" in str(name):
            continue
        usable.append(record)
    if not usable:
        raise SourceMapError(".dsc has no usable official archive occurrence")
    return min(
        usable,
        key=lambda row: (
            ARCHIVE_PRIORITY.get(str(row["archive_name"]), 99),
            str(row["first_seen"]),
        ),
    )


def parse_dsc_source_files(payload: bytes, archive_base: str) -> list[dict[str, str]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceMapError(f".dsc is not UTF-8 text: {exc}") from exc
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line == "Checksums-Sha256:"),
        None,
    )
    if start is None:
        raise SourceMapError(".dsc lacks Checksums-Sha256")
    files: list[dict[str, str]] = []
    for line in lines[start + 1 :]:
        if not line.startswith((" ", "\t")):
            break
        parts = line.split()
        if len(parts) != 3 or not SHA256_RE.fullmatch(parts[0]):
            raise SourceMapError(f"invalid Checksums-Sha256 line: {line!r}")
        filename = parts[2]
        if filename in {".", ".."} or "/" in filename or "\\" in filename:
            raise SourceMapError(f"unsafe source filename in .dsc: {filename!r}")
        files.append(
            {
                "filename": filename,
                "url": f"{archive_base}/{encoded(filename)}",
                "sha256": parts[0],
            }
        )
    if not files:
        raise SourceMapError(".dsc names no source files in Checksums-Sha256")
    return files


def resolve_source(
    client: SnapshotClient, source_identity: tuple[str, str], dagric_commit: str
) -> tuple[tuple[str, str], dict[str, object]]:
    source_name, source_version = source_identity
    if source_identity == ("dagric-os", dagric_commit):
        archive_url = f"https://github.com/Dagric/dagric-os/archive/{dagric_commit}.tar.gz"
        archive = client.get_bytes(archive_url, namespace="dagric-source")
        return source_identity, {
            "source_name": source_name,
            "source_version": source_version,
            "origin": "dagric",
            "locator": {
                "dagric_source_archive_url": archive_url,
                "dagric_commit": dagric_commit,
            },
            "integrity": {"source_archive_sha256": hashlib.sha256(archive).hexdigest()},
        }
    url = (
        f"{SNAPSHOT}/mr/package/{encoded(source_name)}/{encoded(source_version)}"
        "/srcfiles?fileinfo=1"
    )
    document = client.get_json(url)
    results = document.get("result")
    fileinfo = document.get("fileinfo")
    if not isinstance(results, list) or not isinstance(fileinfo, dict):
        raise SourceMapError(f"{source_name}={source_version}: incomplete srcfiles response")
    dsc_candidates: list[tuple[str, list[dict[str, object]]]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        digest = result.get("hash")
        records = fileinfo.get(digest) if isinstance(digest, str) else None
        if not SHA1_RE.fullmatch(str(digest)) or not isinstance(records, list):
            continue
        typed_records = [record for record in records if isinstance(record, dict)]
        if any(str(record.get("name", "")).endswith(".dsc") for record in typed_records):
            dsc_candidates.append((str(digest), typed_records))
    if len(dsc_candidates) != 1:
        raise SourceMapError(
            f"{source_name}={source_version}: expected one archived .dsc hash, "
            f"found {len(dsc_candidates)}"
        )
    _snapshot_sha1, occurrences = dsc_candidates[0]
    occurrence = choose_archive_record(occurrences)
    archive = str(occurrence["archive_name"])
    timestamp = str(occurrence["first_seen"])
    pool_path = str(occurrence["path"]).rstrip("/")
    dsc_name = str(occurrence["name"])
    archive_base = f"{SNAPSHOT}/archive/{encoded(archive)}/{timestamp}{pool_path}"
    dsc_url = f"{archive_base}/{encoded(dsc_name)}"
    dsc_payload = client.get_bytes(dsc_url, namespace="dsc")
    record: dict[str, object] = {
        "source_name": source_name,
        "source_version": source_version,
        "origin": "debian",
        "locator": {
            "dsc_url": dsc_url,
            "debian_archive_url": f"{SNAPSHOT}/archive/{encoded(archive)}/{timestamp}/",
        },
        "integrity": {
            "dsc_sha256": hashlib.sha256(dsc_payload).hexdigest(),
            "source_files": parse_dsc_source_files(dsc_payload, archive_base),
        },
    }
    return source_identity, record


def parallel_map(label: str, workers: int, function, values):
    values = list(values)
    output: dict[object, object] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(function, value): value for value in values}
        for completed, future in enumerate(as_completed(futures), 1):
            value = futures[future]
            try:
                key, result = future.result()
                output[key] = result
            except Exception as exc:  # fail closed and report the exact identity
                failures.append(f"{value!r}: {exc}")
            if completed % 100 == 0 or completed == len(values):
                print(
                    f"source-map: {label} {completed}/{len(values)} "
                    f"({len(failures)} unresolved)",
                    flush=True,
                )
    if failures:
        preview = "\n".join(f"  - {failure}" for failure in failures[:50])
        remainder = len(failures) - min(len(failures), 50)
        if remainder:
            preview += f"\n  - ... and {remainder} more"
        raise SourceMapError(f"{label} failed for {len(failures)} records:\n{preview}")
    return output


def build_edition(
    manifest_path: Path,
    identities: list[tuple[str, str]],
    binary_sources: dict[tuple[str, str], tuple[str, str]],
    sources: dict[tuple[str, str], dict[str, object]],
    public_url: str,
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for binary_name, binary_version in identities:
        source_identity = binary_sources[(binary_name, binary_version)]
        source = sources[source_identity]
        entries.append(
            {
                "binary_name": binary_name,
                "binary_version": binary_version,
                "source_name": source["source_name"],
                "source_version": source["source_version"],
                "origin": source["origin"],
                "locator": source["locator"],
                "integrity": source["integrity"],
            }
        )
    return {
        "binary_package_manifest": public_url,
        "binary_package_manifest_sha256": sha256_file(manifest_path),
        "entries": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--free-manifest",
        type=Path,
        default=ROOT / "site/manifest/dagric-os-1.0.packages",
    )
    parser.add_argument(
        "--pro-manifest",
        type=Path,
        default=ROOT / "site/manifest/dagric-os-pro-1.0.packages",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "out/exact-source-map-1.0.json",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "out/source-map-cache",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--dagric-commit",
        default=None,
        help="exact 40-character build-source commit (defaults to site/manifest/release.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 16:
        raise SourceMapError("--workers must be between 1 and 16")
    free = parse_manifest(args.free_manifest)
    pro = parse_manifest(args.pro_manifest)
    dagric_commit = args.dagric_commit
    if dagric_commit is None:
        release = json.loads((ROOT / "site/manifest/release.json").read_text(encoding="utf-8"))
        dagric_commit = release.get("source", {}).get("commit")
    if not isinstance(dagric_commit, str) or not SHA1_RE.fullmatch(dagric_commit):
        raise SourceMapError("--dagric-commit must be the exact 40-character build-source commit")
    all_identities = sorted(set(free) | set(pro))
    client = SnapshotClient(args.cache)
    binary_sources = parallel_map(
        "binary mappings",
        args.workers,
        lambda identity: resolve_binary(client, identity, dagric_commit),
        all_identities,
    )
    source_identities = sorted(set(binary_sources.values()))
    sources = parallel_map(
        "source records",
        args.workers,
        lambda identity: resolve_source(client, identity, dagric_commit),
        source_identities,
    )
    exact_map = {
        "format": "dagric-exact-binary-source-map-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "editions": {
            "free": build_edition(
                args.free_manifest,
                free,
                binary_sources,
                sources,
                "https://dagric.com/manifest/dagric-os-1.0.packages",
            ),
            "pro": build_edition(
                args.pro_manifest,
                pro,
                binary_sources,
                sources,
                "https://dagric.com/manifest/dagric-os-pro-1.0.packages",
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(exact_map, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(
        f"source-map: wrote {args.output} with {len(free)} Free entries, "
        f"{len(pro)} Pro entries and {len(sources)} unique Debian sources",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SourceMapError as exc:
        print(f"source-map: BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
