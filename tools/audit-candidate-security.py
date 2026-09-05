#!/usr/bin/env python3
"""Read-only Debian security/availability audit of an extracted private candidate.

Run in Debian with python3, dpkg and gpgv. This never updates APT, installs
packages, runs candidate code, or grants release approval. Only a fresh evidence
directory is written. Repository metadata is signature/hash/date checked; the
tracker is an HTTPS observation, not a signed Debian package index.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import subprocess
import urllib.request
from urllib.parse import urlparse

PRIORITY = {"chromium", "runc", "containerd", "cups", "firefox-esr", "linux"}
REPOS = {
    "trixie": "https://deb.debian.org/debian/dists/trixie/",
    "trixie-updates": "https://deb.debian.org/debian/dists/trixie-updates/",
    "trixie-security": "https://security.debian.org/debian-security/dists/trixie-security/",
}
TRACKER = "https://security-tracker.debian.org/tracker/data/json"
_EMBEDDED_SPEC = importlib.util.spec_from_file_location(
    "dagric_security_embedded_inventory", Path(__file__).with_name("check-embedded-sources.py"))
EMBEDDED = importlib.util.module_from_spec(_EMBEDDED_SPEC)
_EMBEDDED_SPEC.loader.exec_module(EMBEDDED)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def deb822(text: str) -> list[dict[str, str]]:
    paragraphs, fields, previous = [], {}, None
    for line in text.splitlines() + [""]:
        if not line:
            if fields:
                paragraphs.append(fields)
            fields, previous = {}, None
        elif line.startswith((" ", "\t")):
            if previous is None:
                raise ValueError("orphan continuation line")
            fields[previous] += "\n" + line[1:]
        else:
            key, separator, value = line.partition(":")
            if not separator or key in fields:
                raise ValueError("invalid or duplicate Debian field")
            fields[key], previous = value.strip(), key
    return paragraphs


@lru_cache(maxsize=32768)
def validate_version(version: str) -> None:
    if not isinstance(version, str) or not version:
        raise ValueError(f"invalid Debian version: {version!r}")
    run = subprocess.run(["dpkg", "--validate-version", version], capture_output=True)
    # --compare-versions can still return 0/1 after warning about malformed
    # syntax. A successful comparison is not itself validation of its inputs.
    if run.returncode != 0:
        raise ValueError(f"invalid Debian version: {version!r}")


@lru_cache(maxsize=32768)
def older(a: str, b: str) -> bool:
    validate_version(a)
    validate_version(b)
    run = subprocess.run(["dpkg", "--compare-versions", a, "lt", b], capture_output=True)
    if run.returncode not in (0, 1):
        raise ValueError(f"invalid Debian version comparison: {a!r}, {b!r}")
    return run.returncode == 0


def declared_source_references(status_raw: bytes, edition: str) -> list[dict]:
    """Reuse the strict exact-version parser; never guess embedded versions."""
    references = []
    for package in EMBEDDED.parse_status(status_raw, edition):
        for field, source, version in package["declarations"]:
            record = {"binary": package["binary_name"], "binary_version": package["binary_version"],
                      "architecture": package["binary_architecture"], "field": field,
                      "source": source, "source_version": version}
            if record not in references:
                references.append(record)
    return references


def load_candidate(directory: Path) -> tuple[dict, dict]:
    receipt_path = directory / "immutable-input-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", receipt.get("source_commit", "")):
        raise ValueError("missing exact candidate source commit")
    inventories = {}
    for edition in ("free", "pro"):
        bound = receipt["editions"][edition]
        manifest = (directory / "manifests" / f"{edition}.packages").read_bytes()
        if sha(manifest) != bound["manifest_sha256"]:
            raise ValueError(f"{edition}: manifest no longer matches immutable receipt")
        inventory_path = directory / "manifests" / f"{edition}-installed-source-versions.tsv"
        raw = inventory_path.read_bytes()
        rows = []
        for line in raw.decode("utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) != 5 or parts[4] != "installed" or not all(parts):
                raise ValueError(f"{edition}: malformed installed inventory")
            rows.append(dict(zip(("binary", "version", "source", "source_version", "status"), parts)))
        actual = Counter((r["binary"], r["version"]) for r in rows)
        expected = Counter(tuple(line.split()) for line in manifest.decode().splitlines())
        if actual != expected or len(rows) != bound["binary_package_rows"]:
            raise ValueError(f"{edition}: installed inventory does not match exact manifest")
        # Source attribution comes from the extracted dpkg database, not names
        # guessed from binary versions (which would mishandle binNMUs/epochs).
        status_path = directory / "manifests" / f"{edition}-dpkg-status"
        status_raw = status_path.read_bytes()
        sources = {}
        references = declared_source_references(status_raw, edition)
        for package in deb822(status_raw.decode("utf-8")):
            package = {key.lower(): value for key, value in package.items()}
            if package.get("status", "").split()[-1:] != ["installed"]:
                continue
            source_field = package.get("source", package["package"])
            match = re.fullmatch(r"([^ ]+)(?: \(([^)]+)\))?", source_field)
            if match is None:
                raise ValueError("invalid dpkg source field")
            name, version = match.group(1), match.group(2) or package["version"]
            sources[(package["package"], package["version"], package["architecture"])] = (name, version)
        matched_keys = []
        for row in rows:
            binary, _, qualifier = row["binary"].partition(":")
            matches = [(key, value) for key, value in sources.items()
                       if key[:2] == (binary, row["version"]) and (not qualifier or key[2] == qualifier)]
            if len(matches) != 1 or matches[0][1] != (row["source"], row["source_version"]):
                raise ValueError(f"{edition}: source attribution differs from dpkg status")
            row["architecture"] = matches[0][0][2]
            matched_keys.append(matches[0][0])
        if len(set(matched_keys)) != len(matched_keys) or set(matched_keys) != set(sources):
            raise ValueError(f"{edition}: installed dpkg identities do not match the manifest one-to-one")
        inventories[edition] = {"rows": rows, "inventory_sha256": sha(raw),
                                "dpkg_status_sha256": sha(status_raw),
                                "declared_embedded_metadata_fields": len({
                                    (r["binary"], r["architecture"], r["field"]) for r in references}),
                                "embedded_source_references": references}
    return receipt, inventories


def validate_release(fields: dict, suite: str, now: datetime) -> dict:
    if fields.get("Codename") != suite or fields.get("Origin") != "Debian":
        raise ValueError("signed index is for an unexpected origin/codename")
    date = parsedate_to_datetime(fields["Date"])
    if date > now + timedelta(minutes=10):
        raise ValueError("signed index has a future Date")
    expiry = parsedate_to_datetime(fields["Valid-Until"]) if "Valid-Until" in fields else None
    if expiry is not None and expiry < now:
        raise ValueError("signed index has expired")
    # Stable point releases omit Valid-Until. Record that limitation rather than
    # inventing a validity period; volatile security/updates must have one.
    if suite != "trixie" and expiry is None:
        raise ValueError("volatile signed index has no Valid-Until")
    sums = {}
    for line in fields["SHA256"].splitlines():
        if not line.strip():
            continue
        digest, size, filename = line.split()
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or filename in sums:
            raise ValueError("invalid or duplicate signed checksum")
        sums[filename] = (digest, int(size))
    return {"checksums": sums, "date": fields["Date"], "valid_until": fields.get("Valid-Until")}


def verify_blob(data: bytes, expected: tuple[str, int]) -> None:
    if len(data) != expected[1] or sha(data) != expected[0]:
        raise ValueError("index bytes do not match the signed Release checksum/size")


def fetch(url: str, output: Path) -> tuple[bytes, dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "Dagric-private-security-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        # Fixed official endpoints only, including after CDN redirects.
        parsed = urlparse(response.url)
        if parsed.scheme != "https" or parsed.hostname not in {"deb.debian.org", "security.debian.org", "security-tracker.debian.org"}:
            raise ValueError("unexpected repository redirect")
        data = response.read(256 * 1024 * 1024 + 1)
        if len(data) > 256 * 1024 * 1024:
            raise ValueError("repository response exceeds audit bound")
        meta = {"url": url, "final_url": response.url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "last_modified": response.headers.get("Last-Modified"), "sha256": sha(data), "bytes": len(data)}
    output.write_bytes(data)
    return data, meta


def package_key(name: str, architecture: str) -> str:
    return name.split(":")[0] + ":" + architecture


def record_available(versions: dict, row: dict, suite: str, component: str) -> None:
    key = package_key(row["Package"], row["Architecture"])
    prior = versions.get(key)
    if prior is None or older(prior["version"], row["Version"]):
        versions[key] = {"version": row["Version"], "suite": suite,
                         "component": component, "architecture": row["Architecture"],
                         "source": row.get("Source", row["Package"])}


def signed_indexes(output: Path, keyring: Path, wanted: set[str], architectures: set[str]) -> tuple[dict, list]:
    versions, evidence = {}, []
    for suite, base in REPOS.items():
        directory = output / suite
        directory.mkdir(mode=0o700)
        _, meta = fetch(base + "InRelease", directory / "InRelease")
        run = subprocess.run(["gpgv", "--keyring", str(keyring), "--status-fd=1", "--output",
                              str(directory / "Release"), str(directory / "InRelease")], capture_output=True, text=True)
        (directory / "signature-verification.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
        if run.returncode or "[GNUPG:] VALIDSIG " not in run.stdout:
            raise ValueError(f"{suite}: Debian signature verification failed")
        fields = deb822((directory / "Release").read_text(encoding="utf-8"))
        if len(fields) != 1:
            raise ValueError("invalid signed Release document")
        valid = validate_release(fields[0], suite, datetime.now(timezone.utc))
        meta.update({"signature_verified": True, "keyring_sha256": sha(keyring.read_bytes()),
                     "date": valid["date"], "valid_until": valid["valid_until"], "indexes": []})
        for architecture in sorted(architectures - {"all"}):
            for component in ("main", "contrib", "non-free", "non-free-firmware"):
                index = f"{component}/binary-{architecture}/Packages.xz"
                if index not in valid["checksums"]:
                    raise ValueError(f"{suite}: expected component/architecture absent from signed index: {index}")
                blob, index_meta = fetch(base + index, directory / f"{component}-{architecture}-Packages.xz")
                verify_blob(blob, valid["checksums"][index])
                meta["indexes"].append(index_meta)
                for row in deb822(lzma.decompress(blob).decode("utf-8")):
                    if row["Package"] in wanted:
                        record_available(versions, row, suite, component)
        evidence.append(meta)
    return versions, evidence


def issue_rows(sources: set[tuple[str, str]], tracker: dict) -> list[dict]:
    findings = []
    for source, installed in sorted(sources):
        for cve, entry in tracker.get(source, {}).items():
            release = entry.get("releases", {}).get("trixie")
            if not release:
                continue
            fixed = release.get("fixed_version")
            comparison_error = None
            try:
                if fixed not in (None, "", "0") and not isinstance(fixed, str):
                    raise ValueError(f"invalid Debian tracker fixed_version: {fixed!r}")
                behind_fix = fixed not in (None, "", "0") and older(installed, fixed)
            except ValueError as exc:
                # Tracker entries can contain malformed versions. Preserve the
                # finding as unresolved comparison evidence, never drop it or
                # treat a tracker-level "resolved" label as candidate safety.
                behind_fix, comparison_error = None, str(exc)
            # Keep every open/undetermined record, even unknown urgency or no-DSA.
            # A resolved record with an older candidate version is still relevant.
            if release.get("status") == "resolved" and not behind_fix and comparison_error is None:
                continue
            findings.append({"source": source, "installed_source_version": installed, "cve": cve,
                             "status": release.get("status", "unknown"),
                             "urgency": release.get("urgency", "unknown"),
                             "fixed_version": fixed, "candidate_older_than_trixie_fixed_version": behind_fix,
                             "version_comparison_error": comparison_error,
                             "nodsa": release.get("nodsa"), "nodsa_reason": release.get("nodsa_reason"),
                             "description": entry.get("description", ""),
                             "url": "https://security-tracker.debian.org/tracker/" + cve})
    return findings


def embedded_findings(references: list[dict], tracker: dict) -> dict:
    sources = {(r["source"], r["source_version"]) for r in references}
    identities = [{"source": source, "source_version": version,
                   "referenced_by": [r for r in references
                                     if (r["source"], r["source_version"]) == (source, version)]}
                  for source, version in sorted(sources)]
    findings = issue_rows(sources, tracker)
    for finding in findings:
        finding["referenced_by"] = [r for r in references if (r["source"], r["source_version"]) == (
            finding["source"], finding["installed_source_version"])]
    return {"declared_embedded_sources": identities, "embedded_source_identity_count": len(sources),
            "embedded_sources_without_tracker_records": sorted({s for s, _ in sources if s not in tracker}),
            "embedded_issue_count": len(findings),
            "embedded_issue_urgencies": dict(Counter(i["urgency"] for i in findings)),
            "embedded_issues": findings}


def priority_findings(rows: list[dict], issues: list[dict], available: dict) -> list[dict]:
    """Keep every summary's evidence at its labelled exact source version."""
    priority = []
    sources = {(row["source"], row["source_version"]) for row in rows}
    for source, installed in sorted(sources):
        if source not in PRIORITY:
            continue
        priority.append({"source": source, "installed_source_version": installed,
                         "binaries": [{**row, "available": available.get(package_key(row["binary"], row["architecture"]))}
                                      for row in rows if (row["source"], row["source_version"]) == (source, installed)],
                         "findings": [issue for issue in issues if (issue["source"], issue["installed_source_version"]) == (source, installed)]})
    return priority


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Fresh evidence directory; must not exist")
    parser.add_argument("--keyring", type=Path, default=Path("/usr/share/keyrings/debian-archive-keyring.gpg"))
    args = parser.parse_args()
    implementation_hashes = {str(path): sha(path.read_bytes()) for path in (
        Path(__file__).resolve(), Path(EMBEDDED.__file__).resolve())}
    receipt, inventories = load_candidate(args.candidate.resolve())
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    wanted = {r["binary"].split(":")[0] for inv in inventories.values() for r in inv["rows"]}
    architectures = {r["architecture"] for inv in inventories.values() for r in inv["rows"]}
    available, indexes = signed_indexes(args.output, args.keyring, wanted, architectures)
    tracker_blob, tracker_evidence = fetch(TRACKER, args.output / "debian-security-tracker.json")
    tracker = json.loads(tracker_blob)
    report = {"schema": "dagric.candidate-security.v1", "release_approved": False,
              "source_commit": receipt["source_commit"], "candidate_receipt": receipt,
              "audit_tool_sha256": implementation_hashes[str(Path(__file__).resolve())],
              "implementation_hashes": implementation_hashes, "repository_evidence": indexes,
              "tracker_evidence": tracker_evidence, "editions": {},
              "limitations": ["Input binding verifies extracted manifests against their recorded receipt; it does not re-extract or hash the original images.",
                              "Debian tracker HTTPS JSON is not a signed advisory attestation.",
                              "Primary sources and exact declared Built-Using/Static-Built-Using versions are triaged separately; findings overlap and must not be summed as unique vulnerabilities. Undeclared vendor code is outside this inventory.",
                              "No runtime reachability, exploit, multi-user, hardware, firmware-rights or licensing approval.",
                              "Known records, missing records and low/no-DSA urgency are not proof of safety.",
                              "No APT refresh, package installation, suite mixing, service change or release approval."]}
    for edition, inventory in inventories.items():
        rows = inventory.pop("rows")
        sources = {(r["source"], r["source_version"]) for r in rows}
        issues = issue_rows(sources, tracker)
        updates, missing = [], []
        for row in rows:
            candidate = available.get(package_key(row["binary"], row["architecture"]))
            if candidate is None:
                missing.append(row["binary"])
            elif older(row["version"], candidate["version"]):
                updates.append({"binary": row["binary"], "installed": row["version"], "available": candidate})
        priority = priority_findings(rows, issues, available)
        result = {**inventory, "binary_count": len(rows), "source_name_count": len({s for s, _ in sources}),
                  "binary_architectures": dict(Counter(r["architecture"] for r in rows)),
                  "sources_without_tracker_records": sorted({s for s, _ in sources if s not in tracker}),
                  "issue_count": len(issues), "issue_urgencies": dict(Counter(i["urgency"] for i in issues)),
                  "issues": issues, "available_binary_updates": updates, "binary_names_absent_from_indexes": missing,
                  "priority": priority,
                  **embedded_findings(inventory["embedded_source_references"], tracker)}
        report["editions"][edition] = result
    if any(sha(Path(path).read_bytes()) != expected for path, expected in implementation_hashes.items()):
        raise ValueError("audit implementation changed during collection; no final report written")
    (args.output / "candidate-security-audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.output / "candidate-security-audit.json"), "release_approved": False,
                      "summary": {e: {k: r[k] for k in ("binary_count", "source_name_count", "issue_count", "issue_urgencies", "embedded_source_identity_count", "embedded_issue_count", "embedded_issue_urgencies")}
                                  | {"newer_available_binary_count": len(r["available_binary_updates"])}
                                  for e, r in report["editions"].items()}}, indent=2))
    return 0  # Successful audit collection is NOT a security/release pass.


if __name__ == "__main__":
    raise SystemExit(main())
