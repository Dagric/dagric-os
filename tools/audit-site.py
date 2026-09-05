#!/usr/bin/env python3
"""Fast, cross-platform structural audit for the static Dagric website."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
IGNORED_PAGES = {"family.html"}
OBSOLETE_VIDEOS = {
    "/assets/dagric-promo.mp4",
    "/assets/dagric-looks.mp4",
    "/assets/dagric-install-walkthrough.mp4",
}
SOCIAL_LINKS = {
    "https://www.youtube.com/@DagricOS",
    "https://www.tiktok.com/@dagricosofficial",
    "https://www.instagram.com/dagricosofficial/",
    "https://www.snapchat.com/@dagricos",
    "https://www.linkedin.com/in/dorien-richardson",
    "https://github.com/Dagric/dagric-os",
}
VIDEO_REQUIRED_FIELDS = {
    "name",
    "description",
    "thumbnailUrl",
    "uploadDate",
    "duration",
    "contentUrl",
}
SOURCE_DISCLOSURE_LINK = 'href="/licenses#corresponding-source"'
# This is the only release allowed to use the explicitly incomplete interim
# source index. A future release cannot pass by merely copying the old prose and
# changing JSON values: it must publish a complete generated source map and set
# both records to `complete`.
INTERIM_SOURCE_RELEASE = {
    "version": "1.0",
    "source_commit": "3f19b305464b82478ce83db8d970a2abbf326cf9",
    "free_sha256": "68380d47e6eb6f98bb5c6de0fe93e4feaaed4e849317f7faefaa7a502ba117d0",
    "pro_sha256": "e373edfea1cba30cade6f3fe6ad13fb6f836e68edafcb300be2cb49fc9858c5e",
}
INTERIM_LEGAL_SUPPLEMENT_COMMIT = "2446b49c76ba13426ae6a4562cc0164286b78040"
PACKAGE_NAME_RE = re.compile(
    r"^[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?$"
)
SOURCE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEBIAN_SOURCE_HOSTS = {
    "archive.debian.org",
    "deb.debian.org",
    "ftp.debian.org",
    "security.debian.org",
    "snapshot.debian.org",
    "sources.debian.org",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_count = 0
        self.description_count = 0
        self.h1_count = 0
        self.ids: list[str] = []
        self.local_refs: list[str] = []
        self.image_alt_missing = 0
        self.videos: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "title":
            self.title_count += 1
        elif tag == "meta" and data.get("name", "").lower() == "description":
            self.description_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img" and "alt" not in data:
            self.image_alt_missing += 1
        elif tag == "video":
            self.videos.append(data)

        if data.get("id"):
            self.ids.append(str(data["id"]))

        for key in ("href", "src", "poster"):
            value = data.get(key)
            if value and value.startswith("/") and not value.startswith("//"):
                self.local_refs.append(value)


def local_target(ref: str) -> Path | None:
    path = urlsplit(ref).path
    if path == "/":
        return SITE / "index.html"
    candidate = SITE / path.lstrip("/")
    if candidate.is_dir():
        candidate = candidate / "index.html"
    elif not candidate.exists() and not candidate.suffix:
        candidate = candidate.with_suffix(".html")
    return candidate if candidate.exists() else None


def json_ld_items(document: object) -> list[dict[str, object]]:
    """Flatten top-level JSON-LD objects and @graph entries for assertions."""
    if isinstance(document, list):
        return [item for value in document for item in json_ld_items(value)]
    if not isinstance(document, dict):
        return []
    graph = document.get("@graph")
    if isinstance(graph, list):
        return [document, *[item for item in graph if isinstance(item, dict)]]
    return [document]


def local_asset_from_url(url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.netloc and parsed.netloc != "dagric.com":
        return None
    return local_target(parsed.path)


def load_json(path: Path, failures: list[str]) -> dict[str, object]:
    """Load one public JSON record without turning a missing/broken file into a traceback."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"{path.relative_to(ROOT).as_posix()}: cannot read valid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{path.relative_to(ROOT).as_posix()}: expected a JSON object")
        return {}
    return value


def validate_json_schema_if_available(
    document: dict[str, object],
    schema: dict[str, object],
    label: str,
    failures: list[str],
) -> None:
    """Apply the public schema when jsonschema is installed; semantic gates remain stdlib-only."""
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        return
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        failures.append(f"{label}: invalid JSON Schema: {exc.message}")
        return
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        failures.append(f"{label}: schema violation at {location}: {error.message}")


def artifact_map(release: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts = release.get("artifacts")
    if not isinstance(artifacts, list):
        return {}
    return {
        str(item.get("edition")): item
        for item in artifacts
        if isinstance(item, dict) and item.get("edition")
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_binary_identity(name: object, version: object) -> tuple[str, str] | None:
    """Return the canonical identity used by both dpkg manifests and the source map.

    Debian's `${binary:Package}` may include a `:architecture` qualifier.  It is
    significant and must not be discarded: doing so could collapse distinct
    amd64/i386 packages into one mapping entry.
    """
    if not isinstance(name, str) or not isinstance(version, str):
        return None
    canonical_name = name.strip().lower()
    canonical_version = version.strip()
    if not PACKAGE_NAME_RE.fullmatch(canonical_name):
        return None
    if not canonical_version or any(char.isspace() for char in canonical_version):
        return None
    return canonical_name, canonical_version


def parse_binary_package_manifest(
    path: Path, label: str, failures: list[str]
) -> list[tuple[str, str]]:
    """Parse and normalize one release-pinned name<TAB>version inventory."""
    identities: list[tuple[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        failures.append(f"source index: cannot read {label} package manifest: {exc}")
        return identities

    for line_number, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 2:
            failures.append(
                f"source index: {label} package manifest line {line_number} is not "
                "canonical name<TAB>version"
            )
            continue
        identity = normalized_binary_identity(parts[0], parts[1])
        if identity is None or identity != (parts[0], parts[1]):
            failures.append(
                f"source index: {label} package manifest line {line_number} is not normalized"
            )
            continue
        identities.append(identity)

    duplicates = [identity for identity, count in Counter(identities).items() if count > 1]
    if duplicates:
        preview = ", ".join(f"{name}={version}" for name, version in duplicates[:3])
        failures.append(f"source index: {label} package manifest has duplicate entries: {preview}")
    return identities


def is_https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not any(
        char.isspace() for char in value
    )


def is_debian_source_url(value: object) -> bool:
    if not is_https_url(value):
        return False
    return (urlsplit(str(value)).hostname or "").lower() in DEBIAN_SOURCE_HOSTS


def reject_unknown_keys(
    value: dict[str, object], allowed: set[str], label: str, failures: list[str]
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        failures.append(f"{label}: unsupported field(s): {', '.join(unknown)}")


def validate_source_map_entry(
    entry: object,
    edition: str,
    position: int,
    release_commit: str,
    failures: list[str],
) -> tuple[str, str] | None:
    label = f"source index: {edition} map entry {position}"
    if not isinstance(entry, dict):
        failures.append(f"{label} is not an object")
        return None
    reject_unknown_keys(
        entry,
        {
            "binary_name",
            "binary_version",
            "source_name",
            "source_version",
            "origin",
            "locator",
            "integrity",
        },
        label,
        failures,
    )

    identity = normalized_binary_identity(
        entry.get("binary_name"), entry.get("binary_version")
    )
    if identity is None or identity != (
        entry.get("binary_name"),
        entry.get("binary_version"),
    ):
        failures.append(f"{label} has a non-normalized binary name or version")
        identity = None

    source_name = entry.get("source_name")
    source_version = entry.get("source_version")
    if not isinstance(source_name, str) or not SOURCE_NAME_RE.fullmatch(source_name):
        failures.append(f"{label} lacks a normalized source package name")
    if not isinstance(source_version, str) or (
        not source_version or source_version != source_version.strip()
        or any(char.isspace() for char in source_version)
    ):
        failures.append(f"{label} lacks an exact source version")

    locator = entry.get("locator")
    integrity = entry.get("integrity")
    if not isinstance(locator, dict):
        failures.append(f"{label} lacks a source locator object")
        locator = {}
    if not isinstance(integrity, dict):
        failures.append(f"{label} lacks an integrity object")
        integrity = {}
    reject_unknown_keys(
        locator,
        {
            "dsc_url",
            "debian_archive_url",
            "dagric_source_archive_url",
            "dagric_commit",
        },
        f"{label} locator",
        failures,
    )
    reject_unknown_keys(
        integrity,
        {"dsc_sha256", "source_archive_sha256", "source_files"},
        f"{label} integrity",
        failures,
    )

    origin = entry.get("origin")
    if origin == "debian":
        dsc_url = locator.get("dsc_url")
        archive_url = locator.get("debian_archive_url")
        if not dsc_url and not archive_url:
            failures.append(f"{label} has no Debian archive/snapshot locator or .dsc URL")
        if dsc_url and (
            not is_debian_source_url(dsc_url)
            or not urlsplit(str(dsc_url)).path.endswith(".dsc")
        ):
            failures.append(f"{label} has an invalid official Debian .dsc URL")
        if archive_url and not is_debian_source_url(archive_url):
            failures.append(f"{label} has an invalid official Debian archive locator")
        if not SHA256_RE.fullmatch(str(integrity.get("dsc_sha256", ""))):
            failures.append(f"{label} lacks a SHA-256 digest for the .dsc")
    elif origin == "dagric":
        archive_url = locator.get("dagric_source_archive_url")
        commit = locator.get("dagric_commit")
        if not is_https_url(archive_url):
            failures.append(f"{label} lacks an HTTPS Dagric source archive")
        if not isinstance(commit, str) or not SHA1_RE.fullmatch(commit):
            failures.append(f"{label} lacks a full Dagric source commit")
        elif commit != release_commit:
            failures.append(f"{label} Dagric commit does not match the release commit")
        if isinstance(archive_url, str) and release_commit not in archive_url:
            failures.append(f"{label} Dagric source archive is not release-commit-pinned")
        if not SHA256_RE.fullmatch(str(integrity.get("source_archive_sha256", ""))):
            failures.append(f"{label} lacks a SHA-256 digest for the Dagric source archive")
    else:
        failures.append(f"{label} has unsupported source origin {origin!r}")

    source_files = integrity.get("source_files")
    if source_files is not None:
        if not isinstance(source_files, list) or not source_files:
            failures.append(f"{label} source_files must be a non-empty list when present")
        else:
            seen_files: set[str] = set()
            for file_position, source_file in enumerate(source_files, 1):
                file_label = f"{label} source file {file_position}"
                if not isinstance(source_file, dict):
                    failures.append(f"{file_label} is not an object")
                    continue
                reject_unknown_keys(
                    source_file, {"filename", "url", "sha256"}, file_label, failures
                )
                filename = source_file.get("filename")
                if not isinstance(filename, str) or not filename or filename != Path(filename).name:
                    failures.append(f"{file_label} has an invalid filename")
                elif filename in seen_files:
                    failures.append(f"{label} repeats source file {filename!r}")
                else:
                    seen_files.add(filename)
                file_url = source_file.get("url")
                if origin == "debian":
                    if not is_debian_source_url(file_url):
                        failures.append(f"{file_label} does not use an official Debian source URL")
                elif not is_https_url(file_url):
                    failures.append(f"{file_label} does not use HTTPS")
                if not SHA256_RE.fullmatch(str(source_file.get("sha256", ""))):
                    failures.append(f"{file_label} lacks a SHA-256 digest")

    return identity


def validate_exact_source_map(
    exact_map: object,
    indexed_artifacts: dict[str, dict[str, object]],
    manifest_identities: dict[str, list[tuple[str, str]]],
    release_commit: str,
    failures: list[str],
) -> None:
    """Require a cryptographically anchored 1:1 map for every binary inventory entry."""
    if not isinstance(exact_map, dict):
        failures.append("source index: complete status requires an exact source map object")
        return
    reject_unknown_keys(
        exact_map,
        {"format", "generated_utc", "editions"},
        "source index: exact source map",
        failures,
    )
    if exact_map.get("format") != "dagric-exact-binary-source-map-v1":
        failures.append("source index: exact source map has an unsupported format")
    generated = exact_map.get("generated_utc")
    if not isinstance(generated, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", generated
    ):
        failures.append("source index: exact source map lacks a UTC generation timestamp")

    editions = exact_map.get("editions")
    if not isinstance(editions, dict) or set(editions) != {"free", "pro"}:
        failures.append("source index: exact source map must contain only Free and Pro editions")
        return

    for edition in ("free", "pro"):
        edition_map = editions.get(edition)
        label = f"source index: {edition} exact source map"
        if not isinstance(edition_map, dict):
            failures.append(f"{label} is not an object")
            continue
        reject_unknown_keys(
            edition_map,
            {"binary_package_manifest", "binary_package_manifest_sha256", "entries"},
            label,
            failures,
        )
        artifact = indexed_artifacts.get(edition, {})
        if edition_map.get("binary_package_manifest") != artifact.get(
            "binary_package_manifest"
        ):
            failures.append(f"{label} points at the wrong binary package manifest")
        if edition_map.get("binary_package_manifest_sha256") != artifact.get(
            "binary_package_manifest_sha256"
        ):
            failures.append(f"{label} package-manifest digest does not match the release index")

        entries = edition_map.get("entries")
        if not isinstance(entries, list) or not entries:
            failures.append(f"{label} has no mapping entries")
            continue
        mapped = [
            identity
            for position, entry in enumerate(entries, 1)
            if (
                identity := validate_source_map_entry(
                    entry, edition, position, release_commit, failures
                )
            )
            is not None
        ]
        mapped_counter = Counter(mapped)
        duplicate_mappings = [
            identity for identity, count in mapped_counter.items() if count > 1
        ]
        if duplicate_mappings:
            preview = ", ".join(
                f"{name}={version}" for name, version in duplicate_mappings[:3]
            )
            failures.append(f"{label} maps a binary more than once: {preview}")

        expected_counter = Counter(manifest_identities.get(edition, []))
        if mapped_counter != expected_counter:
            missing = list((expected_counter - mapped_counter).elements())
            extra = list((mapped_counter - expected_counter).elements())
            details: list[str] = []
            if missing:
                details.append(
                    "missing "
                    + ", ".join(f"{name}={version}" for name, version in missing[:3])
                )
            if extra:
                details.append(
                    "extra " + ", ".join(f"{name}={version}" for name, version in extra[:3])
                )
            failures.append(
                f"{label} is not a 1:1 match for its normalized .packages manifest"
                + (f" ({'; '.join(details)})" if details else "")
            )


def check_source_access(failures: list[str]) -> None:
    """Keep binary delivery, release identity, source access, and notices inseparable."""
    download = (SITE / "download.html").read_text(encoding="utf-8")
    thanks = (SITE / "thanks-pro.html").read_text(encoding="utf-8")
    licenses = (SITE / "licenses.html").read_text(encoding="utf-8")

    try:
        release_record = json.loads(
            (SITE / "manifest/release.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"source access: cannot read release status: {exc}")
        release_record = {}
    source_complete = (
        (release_record.get("source_index") or {}).get("status") == "complete"
    )
    distribution = release_record.get("distribution") or {}
    distribution_held = distribution.get("status") == "held"
    if distribution.get("status") not in {"held", "available"}:
        failures.append("source access: release distribution status is missing or invalid")
    if distribution_held and not distribution.get("reason_codes"):
        failures.append("source access: held distribution has no reason codes")
    if distribution.get("status") == "available" and distribution.get("reason_codes"):
        failures.append("source access: available distribution still has hold reasons")
    if distribution.get("status") == "available" and not source_complete:
        failures.append("source access: distribution cannot be available without exact source")

    if distribution_held:
        held_markers = {
            "site/download.html Free hold": (
                'role="link" aria-disabled="true">Download temporarily paused</span>'
            ),
            "site/download.html Pro hold": (
                'role="link" aria-disabled="true">New sales temporarily paused</span>'
            ),
            "site/thanks-pro.html paid-delivery hold": (
                'id="dl" href="/contact">Contact customer support</a>'
            ),
        }
        held_pages = {
            "site/download.html Free hold": download,
            "site/download.html Pro hold": download,
            "site/thanks-pro.html paid-delivery hold": thanks,
        }
        for label, marker in held_markers.items():
            page_text = held_pages[label]
            start = page_text.find(marker)
            if start < 0:
                failures.append(f"{label}: fail-closed control not found")
                continue
            nearby = page_text[start : start + len(marker) + 700]
            if SOURCE_DISCLOSURE_LINK not in nearby:
                failures.append(
                    f"{label}: no adjacent corresponding-source status link"
                )
        combined = download + "\n" + thanks
        if re.search(r"https://buy\.stripe\.com/", combined):
            failures.append("source access: checkout remains reachable during source hold")
        if re.search(r"https://[^\s\"']+\.r2\.dev/[^\s\"']+\.iso", combined):
            failures.append("source access: direct ISO remains reachable during source hold")
    else:
        delivery_markers = {
            "site/download.html Free delivery": "dagric-os-1.0-amd64.iso\">Download free</a>",
            "site/download.html Pro checkout": ">Buy &amp; download — $39</a>",
        }
        for label, marker in delivery_markers.items():
            start = download.find(marker)
            if start < 0:
                failures.append(f"{label}: delivery control not found")
                continue
            nearby = download[start + len(marker) : start + len(marker) + 400]
            if SOURCE_DISCLOSURE_LINK not in nearby:
                failures.append(f"{label}: no adjacent corresponding-source-and-notices link")

        pro_marker = 'id="dl" href="/support">Download Dagric OS Pro (3.9 GB)</a>'
        start = thanks.find(pro_marker)
        if start < 0:
            failures.append("site/thanks-pro.html: paid delivery control not found")
        elif SOURCE_DISCLOSURE_LINK not in thanks[
            start + len(pro_marker) : start + len(pro_marker) + 400
        ]:
            failures.append(
                "site/thanks-pro.html: no adjacent corresponding-source-and-notices link"
            )

    required_license_fragments = (
        'id="corresponding-source"',
        "/manifest/source-index-1.0.json",
        "3f19b305464b82478ce83db8d970a2abbf326cf9",
        "/COPYING",
        "2446b49c76ba13426ae6a4562cc0164286b78040",
        "documents were added after the release",
        "not presented as source used to build",
    )
    if source_complete:
        required_license_fragments += (
            "Exact binary-to-source map",
            "Binary delivery and new sales remain paused",
        )
    else:
        required_license_fragments += (
            "We do not describe it as a complete source bundle.",
            "Binary delivery and new sales are paused",
        )
    for fragment in required_license_fragments:
        if fragment not in licenses:
            failures.append(f"site/licenses.html: missing source disclosure {fragment!r}")

    release = load_json(SITE / "manifest" / "release.json", failures)
    index = load_json(SITE / "manifest" / "source-index-1.0.json", failures)
    load_json(SITE / "manifest" / "release.schema.json", failures)
    source_schema = load_json(SITE / "manifest" / "source-index.schema.json", failures)
    if not release or not index:
        return
    if source_schema:
        validate_json_schema_if_available(index, source_schema, "source index", failures)

    source_index = release.get("source_index")
    if not isinstance(source_index, dict):
        failures.append("site/manifest/release.json: missing source_index object")
        return
    if source_index.get("url") != "https://dagric.com/manifest/source-index-1.0.json":
        failures.append("site/manifest/release.json: source_index URL is not release-pinned")
    if source_index.get("release_locked") is not True:
        failures.append("site/manifest/release.json: source_index is not marked release_locked")

    release_source = release.get("source")
    index_release = index.get("release")
    if not isinstance(release_source, dict) or not isinstance(index_release, dict):
        failures.append("source records: missing release/source identity objects")
        return
    if index_release.get("version") != release.get("version"):
        failures.append("source index: version does not match release.json")
    if index_release.get("source_commit") != release_source.get("commit"):
        failures.append("source index: source commit does not match release.json")

    release_artifacts = artifact_map(release)
    indexed_artifacts = artifact_map(index_release)
    manifest_identities: dict[str, list[tuple[str, str]]] = {}
    if set(release_artifacts) != {"free", "pro"} or set(indexed_artifacts) != {"free", "pro"}:
        failures.append("source index: Free and Pro artifact records are both required")
    for edition in ("free", "pro"):
        actual = release_artifacts.get(edition, {})
        indexed = indexed_artifacts.get(edition, {})
        for field in ("filename", "sha256"):
            if indexed.get(field) != actual.get(field):
                failures.append(f"source index: {edition} {field} does not match release.json")
        package_manifests = release.get("package_manifests")
        manifest = package_manifests.get(edition, {}) if isinstance(package_manifests, dict) else {}
        if indexed.get("binary_package_manifest") != manifest.get("url"):
            failures.append(f"source index: {edition} package-manifest URL does not match")
        if indexed.get("binary_package_manifest_sha256") != manifest.get("sha256"):
            failures.append(f"source index: {edition} package-manifest hash does not match")

        manifest_url = manifest.get("url")
        manifest_path = (
            local_asset_from_url(str(manifest_url)) if isinstance(manifest_url, str) else None
        )
        if manifest_path is None:
            failures.append(f"source index: {edition} package manifest is not deployed locally")
        else:
            expected_hash = str(manifest.get("sha256", ""))
            if file_sha256(manifest_path) != expected_hash:
                failures.append(f"source index: {edition} package manifest bytes do not match hash")
            expected_count = manifest.get("packages")
            manifest_identities[edition] = parse_binary_package_manifest(
                manifest_path, edition, failures
            )
            actual_count = len(manifest_identities[edition])
            if expected_count != actual_count:
                failures.append(f"source index: {edition} package manifest count does not match")

    dagric_layer = index.get("dagric_layer")
    commit = str(release_source.get("commit", ""))
    pinned_fields = (
        "commit_tree",
        "source_archive",
        "licensing_map",
    )
    if not isinstance(dagric_layer, dict):
        failures.append("source index: missing Dagric source and notice links")
    else:
        for field in pinned_fields:
            if commit not in str(dagric_layer.get(field, "")):
                failures.append(f"source index: Dagric {field} is not commit-pinned")
        release_documents = dagric_layer.get("release_legal_documents")
        supplement = dagric_layer.get("legal_documentation_supplement")
        if isinstance(release_documents, dict) and isinstance(supplement, dict):
            failures.append("source index: legal documents cannot be both release-native and supplemental")
        elif isinstance(release_documents, dict):
            document_commit = str(release_documents.get("commit", ""))
            if (
                release_documents.get("status") != "part-of-release-source"
                or document_commit != commit
            ):
                failures.append(
                    "source index: release legal documents must be part of the exact source commit"
                )
            for field in ("gpl_text", "repository_license_notice", "third_party_notices"):
                if document_commit not in str(release_documents.get(field, "")):
                    failures.append(
                        f"source index: release legal document {field} is not source-commit-pinned"
                    )
        elif isinstance(supplement, dict):
            supplement_commit = str(supplement.get("commit", ""))
            if supplement_commit == commit or not SHA1_RE.fullmatch(supplement_commit):
                failures.append(
                    "source index: legal-document supplement must identify its distinct commit"
                )
            if (
                supplement.get("status") != "post-release-documentation-only"
                or supplement.get("not_part_of_release_build") is not True
            ):
                failures.append(
                    "source index: legal-document supplement is not clearly separated from build source"
                )
            for field in ("gpl_text", "repository_license_notice", "third_party_notices"):
                if supplement_commit not in str(supplement.get(field, "")):
                    failures.append(
                        f"source index: legal-document supplement {field} is not supplement-commit-pinned"
                    )
        else:
            failures.append("source index: missing release legal documents or honest supplement")

    debian_layer = index.get("debian_layer")
    next_gate = index.get("next_release_gate")
    index_status = source_index.get("status")
    exact_status = (
        debian_layer.get("exact_binary_to_source_map_status")
        if isinstance(debian_layer, dict)
        else None
    )
    if index_status == "interim":
        identity = {
            "version": str(release.get("version", "")),
            "source_commit": commit,
            "free_sha256": str(release_artifacts.get("free", {}).get("sha256", "")),
            "pro_sha256": str(release_artifacts.get("pro", {}).get("sha256", "")),
        }
        if identity != INTERIM_SOURCE_RELEASE:
            failures.append(
                "source index: an interim map is allowed only for the frozen 1.0 release; "
                "publish a complete exact source map before another binary release"
            )
        if exact_status != "not-yet-generated":
            failures.append("source index: interim status must state that the exact map is missing")
        if isinstance(debian_layer, dict) and "exact_binary_to_source_map" in debian_layer:
            failures.append("source index: interim status cannot carry a purported exact source map")
        if not isinstance(dagric_layer, dict) or not isinstance(
            dagric_layer.get("legal_documentation_supplement"), dict
        ) or dagric_layer["legal_documentation_supplement"].get(
            "commit"
        ) != INTERIM_LEGAL_SUPPLEMENT_COMMIT:
            failures.append(
                "source index: frozen 1.0 must pin its known post-release legal-document supplement"
            )
        if not isinstance(next_gate, dict) or (
            next_gate.get("status") != "blocked-pending-exact-source-map"
            or next_gate.get("block_if_release_identity_changes") is not True
        ):
            failures.append("source index: incomplete mapping does not block the next release")
        else:
            locked = next_gate.get("locked_release_identity")
            expected_locked = {key: value for key, value in identity.items() if key != "version"}
            if locked != expected_locked:
                failures.append("source index: interim release lock does not match the binaries")
    elif index_status == "complete":
        if exact_status != "complete":
            failures.append("source index: complete release record lacks a complete exact source map")
        exact_map = (
            debian_layer.get("exact_binary_to_source_map")
            if isinstance(debian_layer, dict)
            else None
        )
        validate_exact_source_map(
            exact_map,
            indexed_artifacts,
            manifest_identities,
            commit,
            failures,
        )
        if not isinstance(next_gate, dict) or (
            next_gate.get("status") != "complete"
            or next_gate.get("block_if_release_identity_changes") is not False
            or "locked_release_identity" in next_gate
        ):
            failures.append(
                "source index: a complete source map must close the next-release gate cleanly"
            )
    else:
        failures.append("site/manifest/release.json: source_index status must be interim or complete")


def main() -> int:
    failures: list[str] = []
    pages = [p for p in SITE.rglob("*.html") if p.name not in IGNORED_PAGES]
    seen_titles: dict[str, str] = {}
    seen_descriptions: dict[str, str] = {}
    structured_items: dict[str, list[dict[str, object]]] = {}

    check_source_access(failures)

    for page in pages:
        parser = PageParser()
        text = page.read_text(encoding="utf-8")
        parser.feed(text)
        rel = page.relative_to(ROOT).as_posix()
        title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        description_match = re.search(
            r'<meta\s+name="description"\s+content="([^"]+)"', text, re.I
        )
        canonical_matches = re.findall(
            r'<link\s+rel="canonical"\s+href="([^"]+)"', text, re.I
        )

        if parser.title_count != 1:
            failures.append(f"{rel}: expected one title, found {parser.title_count}")
        if parser.description_count != 1:
            failures.append(f"{rel}: expected one meta description, found {parser.description_count}")
        if parser.h1_count != 1:
            failures.append(f"{rel}: expected one h1, found {parser.h1_count}")
        if page.name != "404.html" and len(canonical_matches) != 1:
            failures.append(
                f"{rel}: expected one canonical URL, found {len(canonical_matches)}"
            )
        if parser.image_alt_missing:
            failures.append(f"{rel}: {parser.image_alt_missing} image(s) missing alt")
        duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
        if duplicates:
            failures.append(f"{rel}: duplicate ids: {', '.join(duplicates)}")

        for ref in parser.local_refs:
            if local_target(ref) is None:
                failures.append(f"{rel}: missing local target {ref}")

        for video in parser.videos:
            for required in ("controls", "playsinline", "width", "height"):
                if required not in video:
                    failures.append(f"{rel}: video missing {required}")

        if any(old in text for old in OBSOLETE_VIDEOS):
            failures.append(f"{rel}: references an obsolete composed video")
        if re.search(r"\bDGR Operations\b", text, re.IGNORECASE):
            failures.append(f"{rel}: contains retired business name DGR Operations")
        if re.search(r"\bImpressions\s+Direct\s+360\s+LLC\b", text, re.IGNORECASE):
            failures.append(f"{rel}: contains inaccurate spaced legal entity name")
        if page.name == "privacy.html":
            for claim in (
                "This is the complete list.",
                "All but one are a fetch",
                "the only thing on this page that transmits something you typed",
                "the one item on this page that is a report",
                "the only identifier anything on this list sends",
                "the one thing in this list that starts by itself",
                "Profile you, fingerprint you, or track you across the web.",
            ):
                if claim.casefold() in text.casefold():
                    failures.append(
                        f"{rel}: contains overbroad privacy exclusivity claim {claim!r}"
                    )

        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
            if title in seen_titles:
                failures.append(
                    f"{rel}: duplicate title also used by {seen_titles[title]}: {title}"
                )
            seen_titles[title] = rel
        if description_match:
            description = description_match.group(1).strip()
            if description in seen_descriptions:
                failures.append(
                    f"{rel}: duplicate description also used by "
                    f"{seen_descriptions[description]}"
                )
            seen_descriptions[description] = rel

        page_items: list[dict[str, object]] = []
        for block in re.findall(
            r'<script\s+type="application/ld\+json"\s*>(.*?)</script>',
            text,
            re.I | re.S,
        ):
            try:
                page_items.extend(json_ld_items(json.loads(block)))
            except json.JSONDecodeError as exc:
                failures.append(f"{rel}: invalid JSON-LD: {exc}")
        structured_items[page.relative_to(SITE).as_posix()] = page_items

        if page.parent == SITE and page.name not in {"family.html", "thanks-pro.html"}:
            missing_socials = sorted(link for link in SOCIAL_LINKS if link not in text)
            if missing_socials:
                failures.append(
                    f"{rel}: missing site-wide social links: {', '.join(missing_socials)}"
                )

    # /search is the public crawl hub as well as the visitor-facing filter. Its
    # links must cover every indexable top-level page so a page cannot silently
    # become an orphan while still appearing in the sitemap.
    search_page = (SITE / "search.html").read_text(encoding="utf-8")
    for page in sorted(SITE.glob("*.html")):
        if page.name in {"404.html", "family.html", "search.html", "thanks-pro.html"}:
            continue
        slug = "/" if page.name == "index.html" else "/" + page.stem
        if f'href="{slug}"' not in search_page and f'href="{slug}#' not in search_page:
            failures.append(f"site/search.html: missing crawl link to {slug}")

    homepage_types = {
        str(item.get("@type")) for item in structured_items.get("index.html", [])
    }
    for required_type in ("WebSite", "Organization", "SoftwareApplication"):
        if required_type not in homepage_types:
            failures.append(f"site/index.html: missing {required_type} structured data")

    required_page_types = {
        "faq.html": "FAQPage",
        "pro.html": "SoftwareApplication",
        "switch-from-windows.html": "Article",
    }
    for page_name, required_type in required_page_types.items():
        page_types = {
            str(item.get("@type")) for item in structured_items.get(page_name, [])
        }
        if required_type not in page_types:
            failures.append(f"site/{page_name}: missing {required_type} structured data")

    video_objects = [
        item
        for item in structured_items.get("videos.html", [])
        if item.get("@type") == "VideoObject"
    ]
    if len(video_objects) != 3:
        failures.append(
            f"site/videos.html: expected 3 VideoObject entries, found {len(video_objects)}"
        )
    for position, video in enumerate(video_objects, start=1):
        missing = sorted(field for field in VIDEO_REQUIRED_FIELDS if not video.get(field))
        if missing:
            failures.append(
                f"site/videos.html: VideoObject {position} missing {', '.join(missing)}"
            )
        for field in ("thumbnailUrl", "contentUrl"):
            value = video.get(field)
            if isinstance(value, str) and local_asset_from_url(value) is None:
                failures.append(
                    f"site/videos.html: VideoObject {position} has missing {field} {value}"
                )

    try:
        sitemap = ET.parse(SITE / "sitemap.xml")
        namespaces = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "video": "http://www.google.com/schemas/sitemap-video/1.1",
        }
        video_nodes = sitemap.findall(
            ".//sm:url[sm:loc='https://dagric.com/videos']/video:video", namespaces
        )
        if len(video_nodes) != 3:
            failures.append(
                f"site/sitemap.xml: expected 3 video entries for /videos, found {len(video_nodes)}"
            )
        for position, node in enumerate(video_nodes, start=1):
            for field in (
                "thumbnail_loc",
                "title",
                "description",
                "content_loc",
                "duration",
                "publication_date",
            ):
                if node.find(f"video:{field}", namespaces) is None:
                    failures.append(
                        f"site/sitemap.xml: video {position} missing video:{field}"
                    )
    except ET.ParseError as exc:
        failures.append(f"site/sitemap.xml: invalid XML: {exc}")

    try:
        opensearch = ET.parse(SITE / "opensearch.xml")
        ns = {"os": "http://a9.com/-/spec/opensearch/1.1/"}
        templates = [
            element.get("template", "")
            for element in opensearch.findall("os:Url", ns)
        ]
        if "https://dagric.com/search?q={searchTerms}" not in templates:
            failures.append("site/opensearch.xml: missing Dagric search URL template")
    except ET.ParseError as exc:
        failures.append(f"site/opensearch.xml: invalid XML: {exc}")

    if failures:
        print("Website audit FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"Website audit passed: {len(pages)} pages, local references, metadata, "
        "headings, structured data, video discovery, internal links, and media checked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
