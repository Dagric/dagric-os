#!/usr/bin/env python3
"""Hard gate a Dagric commercial release against its *built* artifacts.

Repository preflights are useful, but they cannot prove which packages or bytes
ended up in an ISO.  This command deliberately runs after an ISO is built and
before it is uploaded.  ``promotion`` mode repeats the release-record, source-
map, package-manifest and human-approval checks before a release is created or
promoted.

The legal approval is supplied through a protected GitHub Environment secret,
not committed to the repository.  This script never prints that JSON; it emits
only its SHA-256 fingerprint so the approval used for a run can be archived.
It is an engineering control, not a substitute for advice from qualified
counsel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
PACKAGE_RE = re.compile(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?")
SOURCE_RE = re.compile(r"[a-z0-9][a-z0-9+.-]*")
SECTION_RE = re.compile(r"[a-z0-9][a-z0-9+.-]*(?:/[a-z0-9][a-z0-9+.-]*)*")
DEBIAN_SOURCE_HOSTS = {
    "deb.debian.org",
    "snapshot.debian.org",
    "sources.debian.org",
}

# These are proprietary storefront/client payloads, not the open-source
# compatibility and library-management tools (Lutris, Heroic, Wine, etc.).
# Architecture suffixes are removed before comparison.  steam-devices is
# intentionally not in this set: it contains controller udev rules, not Steam.
FORBIDDEN_CLIENT_PACKAGES = {
    "steam",
    "steam-installer",
    "steam-launcher",
    "steamcmd",
    "gog-galaxy",
    "epic-games-launcher",
    "amazon-games",
    "amazon-games-app",
    "ea-app",
    "origin",
    "ubisoft-connect",
    "battle-net",
    "rockstar-games-launcher",
}

ALLOWED_FIREFOX_DECISIONS = {
    "written-permission",
    "unbranded-build-reviewed",
    "unmodified-distribution-reviewed",
    "firefox-removed",
}
DISALLOWED_REVIEWER_MARKERS = {
    "ai",
    "chatgpt",
    "codex",
    "openai",
    "dagric release engineering",
    "pending",
    "tbd",
    "unknown",
}


class GateError(ValueError):
    """A release invariant is missing or does not match the candidate."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"{label} must be a JSON object")
    return value


def exact_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    return value


def exact_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise GateError(f"{label} must be an array")
    return value


def package_identity(name: object, version: object, label: str) -> tuple[str, str]:
    if not isinstance(name, str) or not PACKAGE_RE.fullmatch(name):
        raise GateError(f"{label} has an invalid binary package name")
    if not isinstance(version, str) or not version or version != version.strip():
        raise GateError(f"{label} has an invalid binary package version")
    if any(char.isspace() for char in version):
        raise GateError(f"{label} package version contains whitespace")
    return name, version


def parse_package_manifest(path: Path, label: str) -> list[tuple[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GateError(f"cannot read {label} package manifest {path}: {exc}") from exc
    identities: list[tuple[str, str]] = []
    for number, line in enumerate(lines, 1):
        parts = line.split()
        if len(parts) != 2:
            raise GateError(
                f"{label} package manifest line {number} is not name<TAB>version"
            )
        identities.append(
            package_identity(parts[0], parts[1], f"{label} manifest line {number}")
        )
    if not identities:
        raise GateError(f"{label} package manifest is empty")
    duplicates = [item for item, count in Counter(identities).items() if count > 1]
    if duplicates:
        preview = ", ".join(f"{name}={version}" for name, version in duplicates[:3])
        raise GateError(f"{label} package manifest contains duplicate entries: {preview}")
    return identities


def reject_proprietary_clients(
    identities: list[tuple[str, str]], label: str
) -> None:
    forbidden: list[str] = []
    for name, _version in identities:
        base = name.split(":", 1)[0]
        if base in FORBIDDEN_CLIENT_PACKAGES or base.startswith("steam-libs"):
            forbidden.append(name)
    if forbidden:
        raise GateError(
            f"{label} artifact contains forbidden proprietary client package(s): "
            + ", ".join(sorted(set(forbidden)))
        )


def parse_package_sections(
    path: Path,
    label: str,
    identities: list[tuple[str, str]],
) -> dict[tuple[str, str], str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GateError(f"cannot read {label} package-section inventory {path}: {exc}") from exc
    records: dict[tuple[str, str], str] = {}
    for number, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 3:
            raise GateError(
                f"{label} package-section line {number} is not name<TAB>version<TAB>section"
            )
        identity = package_identity(
            parts[0], parts[1], f"{label} package-section line {number}"
        )
        section = parts[2]
        if not SECTION_RE.fullmatch(section):
            raise GateError(f"{label} package-section line {number} has an invalid section")
        if identity in records:
            raise GateError(f"{label} package-section inventory repeats {identity[0]}")
        records[identity] = section
    expected = Counter(identities)
    actual = Counter(records.keys())
    if actual != expected:
        missing = list((expected - actual).elements())
        extra = list((actual - expected).elements())
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(f"{n}={v}" for n, v in missing[:3]))
        if extra:
            details.append("extra " + ", ".join(f"{n}={v}" for n, v in extra[:3]))
        raise GateError(
            f"{label} package-section inventory is not a 1:1 match for filesystem.packages"
            + (f" ({'; '.join(details)})" if details else "")
        )
    return records


def artifact_records(document: dict[str, object], label: str) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for item in exact_list(document.get("artifacts"), f"{label}.artifacts"):
        record = exact_dict(item, f"{label}.artifacts entry")
        edition = record.get("edition")
        if edition not in {"free", "pro"}:
            raise GateError(f"{label} has unsupported artifact edition {edition!r}")
        if edition in records:
            raise GateError(f"{label} repeats the {edition} artifact")
        records[str(edition)] = record
    if set(records) != {"free", "pro"}:
        raise GateError(f"{label} must describe exactly the Free and Pro artifacts")
    return records


def source_index_path(release: dict[str, object], override: Path | None) -> Path:
    if override is not None:
        return override
    record = exact_dict(release.get("source_index"), "release.source_index")
    url = record.get("url")
    if not isinstance(url, str):
        raise GateError("release.source_index.url is missing")
    name = Path(urlsplit(url).path).name
    if not name or name != Path(name).name:
        raise GateError("release.source_index.url does not identify a local index file")
    return ROOT / "site" / "manifest" / name


def validate_release_identity(
    release: dict[str, object],
    index: dict[str, object],
    candidate_commit: str,
    release_tag: str,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    if not COMMIT_RE.fullmatch(candidate_commit):
        raise GateError("candidate commit must be a full lowercase 40-character Git commit")
    release_source = exact_dict(release.get("source"), "release.source")
    if release_source.get("commit") != candidate_commit:
        raise GateError("release.json source commit does not match the built candidate")
    index_release = exact_dict(index.get("release"), "source index release")
    if index_release.get("source_commit") != candidate_commit:
        raise GateError("source index commit does not match the built candidate")
    version = release.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version):
        raise GateError("release.json has an invalid product version")
    if index_release.get("version") != version:
        raise GateError("source index version does not match release.json")
    tag_match = re.fullmatch(r"v([0-9]+)(?:\.[0-9A-Za-z_-]+)*", release_tag)
    if tag_match is None or tag_match.group(1) != version.split(".", 1)[0]:
        raise GateError(
            "release tag major version does not match the recorded product version"
        )

    source_record = exact_dict(release.get("source_index"), "release.source_index")
    if source_record.get("status") != "complete":
        raise GateError("commercial release requires source_index.status=complete")
    debian = exact_dict(index.get("debian_layer"), "source index debian_layer")
    if debian.get("exact_binary_to_source_map_status") != "complete":
        raise GateError("commercial release requires a complete exact binary-to-source map")
    exact_map = exact_dict(
        debian.get("exact_binary_to_source_map"), "exact binary-to-source map"
    )
    if exact_map.get("format") != "dagric-exact-binary-source-map-v1":
        raise GateError("exact binary-to-source map uses an unsupported format")
    next_gate = exact_dict(index.get("next_release_gate"), "source index next_release_gate")
    if next_gate.get("status") != "complete" or next_gate.get(
        "block_if_release_identity_changes"
    ) is not False:
        raise GateError("source index still records the next binary release as blocked")
    if "locked_release_identity" in next_gate:
        raise GateError("complete source index must not retain a frozen interim identity")

    release_artifacts = artifact_records(release, "release")
    index_artifacts = artifact_records(index_release, "source index release")
    expected_filenames = {
        "free": f"dagric-os-{version}-amd64.iso",
        "pro": f"dagric-os-pro-{version}-amd64.iso",
    }
    for edition, filename in expected_filenames.items():
        if release_artifacts[edition].get("filename") != filename:
            raise GateError(
                f"{edition} filename does not match release.json version {version}"
            )
    editions = exact_dict(exact_map.get("editions"), "exact source map editions")
    if set(editions) != {"free", "pro"}:
        raise GateError("exact source map must contain exactly Free and Pro editions")
    mapped_editions = {
        name: exact_dict(value, f"exact source map {name}")
        for name, value in editions.items()
    }
    return release_artifacts, index_artifacts, mapped_editions


def validate_source_map_edition(
    edition: str,
    identities: list[tuple[str, str]],
    candidate_commit: str,
    edition_map: dict[str, object],
) -> None:
    entries = exact_list(edition_map.get("entries"), f"{edition} source-map entries")
    if not entries:
        raise GateError(f"{edition} source map has no entries")
    mapped: list[tuple[str, str]] = []
    for position, raw in enumerate(entries, 1):
        entry = exact_dict(raw, f"{edition} source-map entry {position}")
        mapped.append(
            package_identity(
                entry.get("binary_name"),
                entry.get("binary_version"),
                f"{edition} source-map entry {position}",
            )
        )
        source_name = entry.get("source_name")
        source_version = entry.get("source_version")
        if not isinstance(source_name, str) or not SOURCE_RE.fullmatch(source_name):
            raise GateError(f"{edition} source-map entry {position} lacks source_name")
        if not isinstance(source_version, str) or not source_version.strip() or any(
            char.isspace() for char in source_version
        ):
            raise GateError(f"{edition} source-map entry {position} lacks source_version")
        locator = exact_dict(entry.get("locator"), f"{edition} map locator {position}")
        integrity = exact_dict(entry.get("integrity"), f"{edition} map integrity {position}")
        origin = entry.get("origin")
        if origin == "dagric":
            if locator.get("dagric_commit") != candidate_commit:
                raise GateError(
                    f"{edition} source-map entry {position} has the wrong Dagric commit"
                )
            archive = locator.get("dagric_source_archive_url")
            if not isinstance(archive, str) or candidate_commit not in archive:
                raise GateError(
                    f"{edition} source-map entry {position} lacks a commit-pinned archive"
                )
            if not SHA256_RE.fullmatch(str(integrity.get("source_archive_sha256", ""))):
                raise GateError(
                    f"{edition} source-map entry {position} lacks source archive SHA-256"
                )
        elif origin == "debian":
            dsc = locator.get("dsc_url")
            archive = locator.get("debian_archive_url")
            urls = [url for url in (dsc, archive) if isinstance(url, str)]
            if not urls or not all(
                urlsplit(url).scheme == "https"
                and (urlsplit(url).hostname or "").casefold() in DEBIAN_SOURCE_HOSTS
                for url in urls
            ):
                raise GateError(
                    f"{edition} source-map entry {position} lacks an official Debian locator"
                )
            if isinstance(dsc, str) and not urlsplit(dsc).path.endswith(".dsc"):
                raise GateError(
                    f"{edition} source-map entry {position} has a non-.dsc dsc_url"
                )
            if not SHA256_RE.fullmatch(str(integrity.get("dsc_sha256", ""))):
                raise GateError(
                    f"{edition} source-map entry {position} lacks a .dsc SHA-256"
                )
        else:
            raise GateError(
                f"{edition} source-map entry {position} has unsupported origin {origin!r}"
            )

    expected = Counter(identities)
    actual = Counter(mapped)
    if actual != expected:
        missing = list((expected - actual).elements())
        extra = list((actual - expected).elements())
        detail: list[str] = []
        if missing:
            detail.append(
                "missing " + ", ".join(f"{n}={v}" for n, v in missing[:3])
            )
        if extra:
            detail.append("extra " + ", ".join(f"{n}={v}" for n, v in extra[:3]))
        raise GateError(
            f"{edition} source map is not a 1:1 match for the built package manifest"
            + (f" ({'; '.join(detail)})" if detail else "")
        )


def validate_manifest_binding(
    edition: str,
    manifest_path: Path,
    identities: list[tuple[str, str]],
    release: dict[str, object],
    release_artifact: dict[str, object],
    index_artifact: dict[str, object],
    edition_map: dict[str, object],
) -> str:
    digest = sha256_file(manifest_path)
    manifests = exact_dict(release.get("package_manifests"), "release.package_manifests")
    release_manifest = exact_dict(manifests.get(edition), f"release {edition} manifest")
    expected_url = release_manifest.get("url")
    expected_digest = release_manifest.get("sha256")
    if expected_digest != digest:
        raise GateError(f"{edition} built package manifest hash is not release-pinned")
    if release_manifest.get("packages") != len(identities):
        raise GateError(f"{edition} built package count does not match release.json")
    for label, record in (
        ("source-index artifact", index_artifact),
        ("exact source-map edition", edition_map),
    ):
        if record.get("binary_package_manifest") != expected_url:
            raise GateError(f"{edition} {label} points at a different package manifest")
        if record.get("binary_package_manifest_sha256") != digest:
            raise GateError(f"{edition} {label} has a stale package-manifest hash")
    if release_artifact.get("filename") != index_artifact.get("filename"):
        raise GateError(f"{edition} artifact filename differs between release records")
    return digest


def https_evidence(value: object, label: str) -> None:
    if not isinstance(value, str):
        raise GateError(f"human approval {label} evidence URL is missing")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise GateError(f"human approval {label} evidence must use HTTPS")
    lowered = value.casefold()
    if "example.com" in lowered or any(word in lowered for word in ("todo", "tbd")):
        raise GateError(f"human approval {label} evidence is a placeholder")


def current_artwork_assets(
    game_policy: Path, candidate_source_root: Path
) -> tuple[str, list[dict[str, str]]]:
    policy = load_json(game_policy, "game integration policy")
    clearance = exact_dict(policy.get("artworkClearance"), "artwork clearance")
    policy_assets = exact_list(clearance.get("assets"), "artwork clearance assets")
    expected_assets: list[dict[str, str]] = []
    for position, raw_asset in enumerate(policy_assets, 1):
        asset = exact_dict(raw_asset, f"artwork clearance asset {position}")
        relative = asset.get("asset")
        recorded_hash = asset.get("sha256")
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise GateError(f"artwork clearance asset {position} has an unsafe path")
        asset_path = candidate_source_root / relative
        if not asset_path.is_file():
            raise GateError(f"reviewed game artwork is missing: {relative}")
        actual_hash = sha256_file(asset_path)
        if recorded_hash != actual_hash:
            raise GateError(f"artwork policy hash is stale for {relative}")
        expected_assets.append({"asset": relative, "sha256": actual_hash})
    if not expected_assets:
        raise GateError("game artwork policy has no assets to review")
    return sha256_file(game_policy), expected_assets


def validate_human_approval(
    raw_json: str,
    candidate_commit: str,
    release_tag: str,
    firefox_policy: Path,
    game_policy: Path,
    candidate_source_root: Path,
) -> tuple[str, dict[str, object]]:
    if not raw_json.strip():
        raise GateError(
            "COMMERCIAL_RELEASE_APPROVAL_JSON is absent; a qualified human legal/"
            "trademark reviewer must attest this exact candidate"
        )
    try:
        approval = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise GateError(f"commercial legal approval is not valid JSON: {exc}") from exc
    approval = exact_dict(approval, "commercial legal approval")
    if approval.get("schema") != "dagric-commercial-legal-approval-v1":
        raise GateError("commercial legal approval has the wrong schema")
    if approval.get("decision") != "approved":
        raise GateError("commercial legal approval decision is not approved")
    if approval.get("scope") != "commercial-distribution":
        raise GateError("commercial legal approval does not cover commercial distribution")
    if approval.get("reviewed_by_human") is not True:
        raise GateError("commercial legal approval must explicitly attest human review")
    if approval.get("candidate_commit") != candidate_commit:
        raise GateError("commercial legal approval is for a different candidate commit")
    if approval.get("release_tag") != release_tag:
        raise GateError("commercial legal approval is for a different release tag")
    if not re.fullmatch(r"v[0-9][0-9A-Za-z._-]*", release_tag):
        raise GateError("commercial release tag must start with v and a digit")

    reviewer = exact_dict(approval.get("reviewer"), "commercial approval reviewer")
    name = str(reviewer.get("name", "")).strip()
    role = str(reviewer.get("role", "")).strip()
    if len(name) < 3 or name.casefold() in DISALLOWED_REVIEWER_MARKERS:
        raise GateError("commercial approval must name the qualified human reviewer")
    if not re.search(
        r"\b(?:legal|counsel|attorney|trademark|intellectual property|ip)\b",
        role,
        re.IGNORECASE,
    ):
        raise GateError("commercial approval reviewer role must state legal/IP/trademark scope")
    if any(marker in (name + " " + role).casefold() for marker in ("chatgpt", "codex", "openai")):
        raise GateError("an AI system cannot supply the required human legal approval")

    approved_utc = approval.get("approved_utc")
    if not isinstance(approved_utc, str) or not approved_utc.endswith("Z"):
        raise GateError("commercial approval approved_utc must be an ISO UTC timestamp")
    try:
        approved_at = datetime.fromisoformat(approved_utc[:-1] + "+00:00")
    except ValueError as exc:
        raise GateError("commercial approval approved_utc is invalid") from exc
    if approved_at > datetime.now(timezone.utc):
        raise GateError("commercial approval timestamp is in the future")

    firefox = exact_dict(approval.get("firefox_trademark"), "Firefox trademark approval")
    firefox_decision = firefox.get("decision")
    if firefox_decision not in ALLOWED_FIREFOX_DECISIONS:
        raise GateError("Firefox trademark approval has no accepted release disposition")
    policy_present = firefox_policy.is_file()
    expected_policy = sha256_file(firefox_policy) if policy_present else "absent"
    if firefox.get("configuration_sha256") != expected_policy:
        raise GateError("Firefox trademark approval is not bound to the current policy")
    if policy_present and firefox_decision not in {
        "written-permission",
        "unbranded-build-reviewed",
    }:
        raise GateError(
            "a modified Firefox configuration requires written permission or a "
            "reviewed unbranded build disposition"
        )
    if not policy_present and firefox_decision != "unmodified-distribution-reviewed":
        raise GateError(
            "an absent Dagric Firefox policy requires the exact "
            "unmodified-distribution-reviewed disposition"
        )
    https_evidence(firefox.get("evidence_url"), "Firefox trademark")

    artwork = exact_dict(approval.get("game_art_ip"), "game-art IP approval")
    if artwork.get("decision") != "approved":
        raise GateError("game-art IP approval decision is not approved")
    policy_digest, expected_assets = current_artwork_assets(
        game_policy, candidate_source_root
    )
    if artwork.get("assets") != expected_assets:
        raise GateError(
            "game-art IP approval must bind the complete ordered policy asset/hash set"
        )
    if artwork.get("policy_sha256") != policy_digest:
        raise GateError("game-art IP approval is not bound to the current policy")
    https_evidence(artwork.get("evidence_url"), "game-art IP")

    for field in (
        "game_platform_terms_reviewed",
        "third_party_notices_reviewed",
        "nvidia_redistribution_reviewed",
    ):
        if approval.get(field) is not True:
            raise GateError(f"commercial legal approval must set {field}=true")
    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest(), approval


def firmware_inventory(identities: list[tuple[str, str]]) -> list[str]:
    """Return every resolved firmware/microcode binary, not a hand-curated subset."""
    return sorted(
        f"{name}={version}"
        for name, version in identities
        if "firmware" in name.split(":", 1)[0]
        or "microcode" in name.split(":", 1)[0]
    )


def validate_firmware_approval(
    approval: dict[str, object],
    edition: str,
    identities: list[tuple[str, str]],
) -> str:
    record = exact_dict(
        approval.get("firmware_microcode"), "firmware/microcode legal approval"
    )
    if record.get("decision") != "approved" or record.get("notices_reviewed") is not True:
        raise GateError(
            "firmware/microcode approval must approve redistribution and notice review"
        )
    https_evidence(record.get("evidence_url"), "firmware/microcode")
    editions = exact_dict(record.get("editions"), "firmware/microcode approval editions")
    if set(editions) != {"free", "pro"}:
        raise GateError("firmware/microcode approval must cover exactly Free and Pro")
    edition_record = exact_dict(
        editions.get(edition), f"firmware/microcode approval {edition}"
    )
    inventory = firmware_inventory(identities)
    if edition_record.get("packages") != inventory:
        raise GateError(
            f"firmware/microcode approval does not cover the complete {edition} inventory"
        )
    canonical = "".join(item + "\n" for item in inventory).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if edition_record.get("sha256") != digest:
        raise GateError(f"firmware/microcode approval has a stale {edition} inventory hash")
    installer_packages = sorted(
        item
        for item in inventory
        if "installer" in item.split("=", 1)[0]
        or "downloader" in item.split("=", 1)[0]
    )
    if edition_record.get("installer_or_downloader_packages") != installer_packages:
        raise GateError(
            f"firmware/microcode approval does not separately identify all {edition} "
            "installer/downloader packages"
        )
    return digest


def firmware_approval_edition(
    identities: list[tuple[str, str]],
) -> dict[str, object]:
    inventory = firmware_inventory(identities)
    canonical = "".join(item + "\n" for item in inventory).encode("utf-8")
    return {
        "packages": inventory,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "installer_or_downloader_packages": sorted(
            item
            for item in inventory
            if "installer" in item.split("=", 1)[0]
            or "downloader" in item.split("=", 1)[0]
        ),
    }


def restricted_section_inventory(
    sections: dict[tuple[str, str], str]
) -> list[str]:
    return sorted(
        f"{name}={version}\t{section}"
        for (name, version), section in sections.items()
        if section.split("/", 1)[0] in {"contrib", "non-free", "non-free-firmware"}
    )


def restricted_approval_edition(
    sections: dict[tuple[str, str], str]
) -> dict[str, object]:
    inventory = restricted_section_inventory(sections)
    canonical = "".join(item + "\n" for item in inventory).encode("utf-8")
    return {
        "packages": inventory,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "installer_or_downloader_packages": sorted(
            item
            for item in inventory
            if "installer" in item.split("=", 1)[0]
            or "downloader" in item.split("=", 1)[0]
        ),
    }


def validate_restricted_section_approval(
    approval: dict[str, object],
    edition: str,
    sections: dict[tuple[str, str], str],
) -> str:
    record = exact_dict(
        approval.get("restricted_repository_packages"),
        "contrib/non-free legal approval",
    )
    if record.get("decision") != "approved" or record.get("notices_reviewed") is not True:
        raise GateError(
            "contrib/non-free approval must approve redistribution and notice review"
        )
    https_evidence(record.get("evidence_url"), "contrib/non-free")
    editions = exact_dict(record.get("editions"), "contrib/non-free approval editions")
    if set(editions) != {"free", "pro"}:
        raise GateError("contrib/non-free approval must cover exactly Free and Pro")
    expected = restricted_approval_edition(sections)
    actual = exact_dict(editions.get(edition), f"contrib/non-free approval {edition}")
    if actual.get("packages") != expected["packages"]:
        raise GateError(
            f"contrib/non-free approval does not cover the complete {edition} Section inventory"
        )
    if actual.get("sha256") != expected["sha256"]:
        raise GateError(f"contrib/non-free approval has a stale {edition} inventory hash")
    if actual.get("installer_or_downloader_packages") != expected[
        "installer_or_downloader_packages"
    ]:
        raise GateError(
            f"contrib/non-free approval does not separately identify all {edition} "
            "installer/downloader packages"
        )
    return str(expected["sha256"])


def write_approval_template(args: argparse.Namespace) -> None:
    if not COMMIT_RE.fullmatch(args.candidate_commit):
        raise GateError("candidate commit must be a full lowercase Git commit")
    if not re.fullmatch(r"v[0-9][0-9A-Za-z._-]*", args.release_tag):
        raise GateError("commercial release tag must start with v and a digit")
    manifests: dict[str, list[tuple[str, str]]] = {}
    sections: dict[str, dict[tuple[str, str], str]] = {}
    for edition, path, section_path in (
        ("free", args.free_manifest, args.free_package_sections),
        ("pro", args.pro_manifest, args.pro_package_sections),
    ):
        manifests[edition] = parse_package_manifest(path, edition)
        reject_proprietary_clients(manifests[edition], edition)
        sections[edition] = parse_package_sections(
            section_path, edition, manifests[edition]
        )
    policy_digest, assets = current_artwork_assets(
        args.game_policy, args.candidate_source_root
    )
    policy_digest_firefox = (
        sha256_file(args.firefox_policy) if args.firefox_policy.is_file() else "absent"
    )
    template = {
        "schema": "dagric-commercial-legal-approval-v1",
        "decision": "pending-human-review",
        "scope": "commercial-distribution",
        "reviewed_by_human": False,
        "candidate_commit": args.candidate_commit,
        "release_tag": args.release_tag,
        "approved_utc": "REPLACE_WITH_UTC_TIMESTAMP",
        "reviewer": {"name": "REPLACE", "role": "REPLACE"},
        "firefox_trademark": {
            "decision": "pending",
            "configuration_sha256": policy_digest_firefox,
            "evidence_url": "REPLACE",
        },
        "game_art_ip": {
            "decision": "pending",
            "policy_sha256": policy_digest,
            "assets": assets,
            "evidence_url": "REPLACE",
        },
        "game_platform_terms_reviewed": False,
        "third_party_notices_reviewed": False,
        "nvidia_redistribution_reviewed": False,
        "firmware_microcode": {
            "decision": "pending",
            "notices_reviewed": False,
            "evidence_url": "REPLACE",
            "editions": {
                edition: firmware_approval_edition(identities)
                for edition, identities in manifests.items()
            },
        },
        "restricted_repository_packages": {
            "decision": "pending",
            "notices_reviewed": False,
            "evidence_url": "REPLACE",
            "editions": {
                edition: restricted_approval_edition(section_map)
                for edition, section_map in sections.items()
            },
        },
    }
    rendered = json.dumps(template, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"commercial-release: wrote pending human-review template to {args.output}")
    else:
        print(rendered, end="")


def parse_checksums(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GateError(f"cannot read checksum manifest {path}: {exc}") from exc
    for number, line in enumerate(lines, 1):
        parts = line.split()
        if len(parts) != 2 or not SHA256_RE.fullmatch(parts[0]):
            raise GateError(f"checksum manifest line {number} is invalid")
        name = parts[1].lstrip("*")
        if name != Path(name).name or name in records:
            raise GateError(f"checksum manifest line {number} has an unsafe/duplicate name")
        records[name] = parts[0]
    return records


def common_context(args: argparse.Namespace) -> tuple[
    dict[str, object],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    str,
    dict[str, object],
]:
    release = load_json(args.release_record, "release record")
    index = load_json(source_index_path(release, args.source_index), "source index")
    release_artifacts, index_artifacts, edition_maps = validate_release_identity(
        release, index, args.candidate_commit, args.release_tag
    )
    raw_approval = os.environ.get(args.approval_env, "")
    approval_digest, approval = validate_human_approval(
        raw_approval,
        args.candidate_commit,
        args.release_tag,
        args.firefox_policy,
        args.game_policy,
        args.candidate_source_root,
    )
    return (
        release,
        release_artifacts,
        index_artifacts,
        edition_maps,
        approval_digest,
        approval,
    )


def check_edition(args: argparse.Namespace) -> None:
    (
        release,
        release_artifacts,
        index_artifacts,
        maps,
        approval_digest,
        approval,
    ) = common_context(args)
    provenance = args.provenance.read_text(encoding="utf-8").strip()
    if provenance != args.candidate_commit:
        raise GateError("build provenance sidecar does not match the candidate commit")
    identities = parse_package_manifest(args.package_manifest, args.edition)
    reject_proprietary_clients(identities, args.edition)
    sections = parse_package_sections(args.package_sections, args.edition, identities)
    firmware_digest = validate_firmware_approval(approval, args.edition, identities)
    restricted_digest = validate_restricted_section_approval(
        approval, args.edition, sections
    )
    manifest_digest = validate_manifest_binding(
        args.edition,
        args.package_manifest,
        identities,
        release,
        release_artifacts[args.edition],
        index_artifacts[args.edition],
        maps[args.edition],
    )
    validate_source_map_edition(
        args.edition, identities, args.candidate_commit, maps[args.edition]
    )

    artifact = release_artifacts[args.edition]
    if args.iso.name != artifact.get("filename"):
        raise GateError(f"{args.edition} ISO filename is not release-pinned")
    digest = sha256_file(args.iso)
    if artifact.get("sha256") != digest or index_artifacts[args.edition].get("sha256") != digest:
        raise GateError(f"{args.edition} ISO SHA-256 is not bound to both release records")
    if artifact.get("bytes") != args.iso.stat().st_size:
        raise GateError(f"{args.edition} ISO byte size does not match release.json")
    checksums = parse_checksums(args.checksums)
    if checksums.get(args.iso.name) != digest:
        raise GateError(f"{args.edition} ISO is not correctly recorded in SHA256SUMS")
    print(
        f"commercial-release: {args.edition} candidate passed; "
        f"iso={digest} packages={len(identities)} manifest={manifest_digest} "
        f"firmware={firmware_digest} restricted={restricted_digest} "
        f"approval={approval_digest}"
    )


def check_promotion(args: argparse.Namespace) -> None:
    (
        release,
        release_artifacts,
        index_artifacts,
        maps,
        approval_digest,
        approval,
    ) = common_context(args)
    checksums = parse_checksums(args.checksums)
    expected_names = {str(record.get("filename")) for record in release_artifacts.values()}
    if set(checksums) != expected_names:
        raise GateError("promotion SHA256SUMS must contain exactly the Free and Pro ISOs")
    artifact_paths = {
        "free": (args.free_iso, args.free_provenance),
        "pro": (args.pro_iso, args.pro_provenance),
    }
    supplied_artifact_paths = [
        value for pair in artifact_paths.values() for value in pair if value is not None
    ]
    if supplied_artifact_paths and len(supplied_artifact_paths) != 4:
        raise GateError(
            "promotion ISO/provenance arguments must be supplied for both editions"
        )
    if args.authorization_output is not None and len(supplied_artifact_paths) != 4:
        raise GateError(
            "an upload authorization requires both candidate ISOs and provenance sidecars"
        )

    authorized_artifacts: dict[str, object] = {}
    for edition, path, section_path in (
        ("free", args.free_manifest, args.free_package_sections),
        ("pro", args.pro_manifest, args.pro_package_sections),
    ):
        identities = parse_package_manifest(path, edition)
        reject_proprietary_clients(identities, edition)
        sections = parse_package_sections(section_path, edition, identities)
        validate_firmware_approval(approval, edition, identities)
        validate_restricted_section_approval(approval, edition, sections)
        validate_manifest_binding(
            edition,
            path,
            identities,
            release,
            release_artifacts[edition],
            index_artifacts[edition],
            maps[edition],
        )
        validate_source_map_edition(edition, identities, args.candidate_commit, maps[edition])
        filename = str(release_artifacts[edition].get("filename"))
        if checksums.get(filename) != release_artifacts[edition].get("sha256"):
            raise GateError(f"promotion checksum for {edition} is not release-pinned")

        iso_path, provenance_path = artifact_paths[edition]
        if iso_path is not None and provenance_path is not None:
            provenance = provenance_path.read_text(encoding="utf-8").strip()
            if provenance != args.candidate_commit:
                raise GateError(
                    f"{edition} build provenance sidecar does not match the candidate commit"
                )
            artifact = release_artifacts[edition]
            if iso_path.name != filename:
                raise GateError(f"{edition} ISO filename is not release-pinned")
            iso_digest = sha256_file(iso_path)
            if (
                artifact.get("sha256") != iso_digest
                or index_artifacts[edition].get("sha256") != iso_digest
            ):
                raise GateError(
                    f"{edition} ISO SHA-256 is not bound to both release records"
                )
            if artifact.get("bytes") != iso_path.stat().st_size:
                raise GateError(f"{edition} ISO byte size does not match release.json")
            if checksums.get(filename) != iso_digest:
                raise GateError(
                    f"{edition} ISO is not correctly recorded in promotion SHA256SUMS"
                )
            authorized_artifacts[edition] = {
                "filename": filename,
                "bytes": iso_path.stat().st_size,
                "sha256": iso_digest,
                "package_manifest": path.name,
                "package_manifest_sha256": sha256_file(path),
                "package_sections": section_path.name,
                "package_sections_sha256": sha256_file(section_path),
                "provenance": provenance_path.name,
                "provenance_sha256": sha256_file(provenance_path),
            }

    if args.authorization_output is not None:
        resolved_index = source_index_path(release, args.source_index)
        authorization = {
            "schema": "dagric-commercial-release-authorization-v1",
            "release_tag": args.release_tag,
            "candidate_commit": args.candidate_commit,
            "approval_sha256": approval_digest,
            "release_record_sha256": sha256_file(args.release_record),
            "source_index_sha256": sha256_file(resolved_index),
            "checksums_sha256": sha256_file(args.checksums),
            "artifacts": authorized_artifacts,
        }
        args.authorization_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.authorization_output.with_name(
            args.authorization_output.name + ".tmp"
        )
        temporary.write_text(
            json.dumps(authorization, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.authorization_output)
    print(
        "commercial-release: promotion record passed; Free/Pro hashes, package "
        f"maps, forbidden-client scan and human approval={approval_digest}"
    )


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument(
        "--release-record",
        type=Path,
        default=ROOT / "site/manifest/release.json",
    )
    parser.add_argument("--source-index", type=Path)
    parser.add_argument(
        "--approval-env", default="COMMERCIAL_RELEASE_APPROVAL_JSON"
    )
    parser.add_argument(
        "--firefox-policy",
        type=Path,
        default=ROOT
        / "config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json",
    )
    parser.add_argument("--candidate-source-root", type=Path, default=ROOT)
    parser.add_argument(
        "--game-policy",
        type=Path,
        default=ROOT
        / "config/includes.chroot/usr/share/dagric/policy/game-integrations.json",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="mode", required=True)
    edition = subparsers.add_parser("edition", help="check one just-built ISO")
    add_common(edition)
    edition.add_argument("--edition", choices=("free", "pro"), required=True)
    edition.add_argument("--iso", type=Path, required=True)
    edition.add_argument("--package-manifest", type=Path, required=True)
    edition.add_argument("--package-sections", type=Path, required=True)
    edition.add_argument("--provenance", type=Path, required=True)
    edition.add_argument("--checksums", type=Path, required=True)
    edition.set_defaults(handler=check_edition)

    promotion = subparsers.add_parser(
        "promotion", help="recheck both records before release/promotion"
    )
    add_common(promotion)
    promotion.add_argument("--checksums", type=Path, required=True)
    promotion.add_argument("--free-manifest", type=Path, required=True)
    promotion.add_argument("--pro-manifest", type=Path, required=True)
    promotion.add_argument("--free-package-sections", type=Path, required=True)
    promotion.add_argument("--pro-package-sections", type=Path, required=True)
    promotion.add_argument("--free-iso", type=Path)
    promotion.add_argument("--pro-iso", type=Path)
    promotion.add_argument("--free-provenance", type=Path)
    promotion.add_argument("--pro-provenance", type=Path)
    promotion.add_argument(
        "--authorization-output",
        type=Path,
        help=(
            "write a deterministic candidate-upload authorization after full "
            "ISO/provenance validation"
        ),
    )
    promotion.set_defaults(handler=check_promotion)

    template = subparsers.add_parser(
        "approval-template",
        help="write a fail-closed template with exact artifact-derived review scope",
    )
    template.add_argument("--candidate-commit", required=True)
    template.add_argument("--release-tag", required=True)
    template.add_argument("--free-manifest", type=Path, required=True)
    template.add_argument("--pro-manifest", type=Path, required=True)
    template.add_argument("--free-package-sections", type=Path, required=True)
    template.add_argument("--pro-package-sections", type=Path, required=True)
    template.add_argument("--candidate-source-root", type=Path, default=ROOT)
    template.add_argument(
        "--firefox-policy",
        type=Path,
        default=ROOT
        / "config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json",
    )
    template.add_argument(
        "--game-policy",
        type=Path,
        default=ROOT
        / "config/includes.chroot/usr/share/dagric/policy/game-integrations.json",
    )
    template.add_argument("--output", type=Path)
    template.set_defaults(handler=write_approval_template)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.handler(args)
    except (GateError, OSError) as exc:
        print(f"commercial-release: BLOCKED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
