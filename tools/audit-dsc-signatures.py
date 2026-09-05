#!/usr/bin/env python3
"""Offline, candidate-bound DSC OpenPGP evidence; never release approval.

Authenticates a downloaded (not installed) debian-keyring .deb against an
already collected signed Debian index, extracts only into a fresh audit
directory, and verifies exact cached DSCs. No keyserver, APT refresh, host
installation, candidate mutation or release promotion is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


security = module("dagric_security_index", ROOT / "tools/audit-candidate-security.py")
bundle = module("dagric_source_binding", ROOT / "tools/audit-source-bundle.py")
sha = security.sha
CANONICAL_SIGNER = "AD3219669D1E8CF06CF90BC88D3628DB7EAFE30A"
CANONICAL_PRIMARY = "A4626CBAFF376039D2D7554497BA9CE761A0963B"
CANONICAL_ROLES = ("debian-keyring", "debian-maintainers", "debian-role-keys", "debian-nonupload")


def run(command, timeout=120):
    return subprocess.run(command, capture_output=True, timeout=timeout)


def validate_keyring_release(fields: dict, suite: str, now: datetime) -> dict:
    if suite not in ("trixie", "sid"):
        raise ValueError("unsupported audit-data keyring suite")
    release = security.validate_release(fields, suite, now)
    if suite == "sid" and parsedate_to_datetime(release["date"]) < now - timedelta(hours=48):
        raise ValueError("sid audit-data keyring index is older than 48 hours")
    return release


def prepare_keyrings(package: Path, evidence: Path, output: Path, archive_keyring: Path, suite="trixie"):
    """Do not execute maintainer scripts; authenticate before data extraction."""
    release_output = output / "verified-Release"
    checked = run(["gpgv", "--weak-digest", "SHA1", "--keyring", str(archive_keyring), "--status-fd=1",
                   "--output", str(release_output), str(evidence / "InRelease")])
    (output / "archive-signature-status.txt").write_bytes(checked.stdout + checked.stderr)
    if checked.returncode or b"[GNUPG:] VALIDSIG " not in checked.stdout:
        raise ValueError("Debian InRelease verification failed")
    fields = security.deb822(release_output.read_text(encoding="utf-8"))
    if len(fields) != 1:
        raise ValueError("invalid Release document")
    release = validate_keyring_release(fields[0], suite, datetime.now(timezone.utc))
    index_path = evidence / "main-amd64-Packages.xz"
    index = bundle.read(index_path)
    security.verify_blob(index, release["checksums"]["main/binary-amd64/Packages.xz"])
    matches = [row for row in security.deb822(lzma.decompress(index).decode())
               if row.get("Package") == "debian-keyring" and row.get("Architecture") == "all"]
    if len(matches) != 1:
        raise ValueError("expected one official debian-keyring package in signed index")
    entry = matches[0]
    payload = bundle.read(package)
    security.verify_blob(payload, (entry["SHA256"], int(entry["Size"])))
    # Use a private verified copy, eliminating a download-file swap during
    # dpkg-deb's subsequent open. Extraction runs no package maintainer scripts.
    copy = output / "verified-debian-keyring.deb"
    copy.write_bytes(payload)
    extracted = output / "keyring-data"
    checked = run(["dpkg-deb", "--extract", str(copy), str(extracted)])
    if checked.returncode:
        raise ValueError("authenticated keyring package extraction failed")
    keyrings = []
    for role in ("debian-keyring", "debian-maintainers", "debian-role-keys", "debian-nonupload"):
        path = extracted / "usr/share/keyrings" / f"{role}.pgp"
        bundle.regular(path)
        if not path.is_file():
            raise ValueError("authenticated keyring package lacks expected keyring")
        keyrings.append({"role": role, "path": str(path), "sha256": sha(path.read_bytes())})
    return keyrings, {"package": entry, "audit_data_suite": suite,
                      "inrelease_sha256": sha((evidence / "InRelease").read_bytes()),
                      "index_sha256": sha(index), "archive_keyring_sha256": sha(archive_keyring.read_bytes()),
                      "release_date": release["date"], "valid_until": release["valid_until"],
                      "package_bytes_sha256_verified_before_extraction": True}


def parse_keys(text: str, role: str) -> dict:
    result, pending, primary = {}, None, None
    for line in text.splitlines():
        fields = line.split(":")
        if fields[0] in ("pub", "sub"):
            if len(fields) < 12:
                raise ValueError("truncated OpenPGP key metadata")
            pending = {"kind": fields[0], "validity": fields[1], "created": int(fields[5] or 0),
                       "expires": int(fields[6] or 0), "capabilities": fields[11], "role": role}
            if fields[0] == "pub":
                primary = None
        elif fields[0] == "fpr" and pending is not None:
            fingerprint = fields[9]
            if not re.fullmatch(r"[0-9A-F]{40,64}", fingerprint):
                raise ValueError("invalid full OpenPGP fingerprint")
            if pending["kind"] == "pub":
                primary = fingerprint
            if primary is None:
                raise ValueError("subkey before primary fingerprint")
            result[fingerprint] = {**pending, "primary_fingerprint": primary}
            pending = None
    return result


def key_metadata(keyrings: list, output: Path) -> dict:
    home = output / "empty-gpg-home"
    home.mkdir(mode=0o700)
    keys = {}
    for ring in keyrings:
        result = run(["gpg", "--no-options", "--homedir", str(home), "--batch", "--no-auto-key-retrieve",
                      "--no-auto-key-import", "--with-colons", "--fixed-list-mode", "--with-fingerprint",
                      "--with-subkey-fingerprint", "--show-keys", ring["path"]])
        (output / (ring["role"] + ".key-metadata.txt")).write_bytes(result.stdout)
        (output / (ring["role"] + ".key-metadata-errors.txt")).write_bytes(result.stderr)
        if result.returncode:
            raise ValueError("offline GnuPG key metadata inspection failed")
        # Historic UIDs can contain non-UTF-8 bytes. Identity decisions use only
        # strict ASCII fingerprints/numeric fields; preserve raw output and do
        # not let an unused display UID prevent inspection of every key.
        for fingerprint, record in parse_keys(result.stdout.decode("utf-8", "replace"), ring["role"]).items():
            if fingerprint in keys and keys[fingerprint] != record:
                raise ValueError("ambiguous key role/state in packaged keyrings")
            keys[fingerprint] = record
    return keys


def signature_status(stdout: str) -> tuple[list, set, list]:
    valid, tokens, missing = [], set(), []
    for line in stdout.splitlines():
        if not line.startswith("[GNUPG:] "):
            continue
        fields = line[len("[GNUPG:] "):].split()
        if not fields:
            continue
        tokens.add(fields[0])
        if fields[0] == "VALIDSIG":
            if len(fields) < 10:
                raise ValueError("truncated VALIDSIG status")
            valid.append({"fingerprint": fields[1], "created": int(fields[3]), "expires": int(fields[4]),
                          "public_key_algorithm": fields[7], "digest_algorithm": fields[8],
                          "primary_fingerprint": fields[10] if len(fields) > 10 else fields[1]})
        elif fields[0] == "NO_PUBKEY" and len(fields) > 1:
            missing.append(fields[1])
    return valid, tokens, missing


def classify(returncode: int, stdout: str, keys: dict, now: int) -> tuple[str, list, list, list]:
    signatures, tokens, missing = signature_status(stdout)
    warnings = set()
    if "BADSIG" in tokens:
        return "bad-signature", signatures, missing, []
    if "NO_PUBKEY" in tokens:
        return "unavailable-key", signatures, missing, []
    if returncode != 0 or not signatures:
        return "verification-error", signatures, missing, []
    for signature in signatures:
        for fingerprint in {signature["fingerprint"], signature["primary_fingerprint"]}:
            key = keys.get(fingerprint)
            if key is None:
                warnings.add("key-state-unavailable")
                continue
            if key["validity"] == "r":
                warnings.add("revoked-key")
            if key["validity"] == "e" or (key["expires"] and key["expires"] < now):
                warnings.add("expired-key")
            if key["role"] == "debian-nonupload":
                warnings.add("non-uploading-key")
            if key["created"] > signature["created"]:
                warnings.add("signature-before-key")
        if signature["expires"] and signature["expires"] < now:
            warnings.add("expired-signature")
        if signature["created"] > now:
            warnings.add("future-signature")
    for category in ("revoked-key", "expired-key", "expired-signature", "non-uploading-key",
                     "key-state-unavailable", "signature-before-key", "future-signature"):
        if category in warnings:
            return category, signatures, missing, sorted(warnings)
    return "cryptographically-valid-with-packaged-key-state", signatures, missing, []


def canonical_manifest_entries(text: str) -> dict[str, str]:
    allowed = {f"keyrings/{role}.{extension}" for role in (*CANONICAL_ROLES, "emeritus-keyring")
               for extension in ("gpg", "pgp")}
    entries = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{128}", parts[0]):
            raise ValueError("invalid canonical SHA512 manifest line")
        digest, filename = parts
        if filename not in allowed or filename in entries:
            raise ValueError("unknown or duplicate canonical keyring filename")
        entries[filename] = digest
    if set(entries) != allowed:
        raise ValueError("canonical keyring manifest file set changed")
    for role in (*CANONICAL_ROLES, "emeritus-keyring"):
        if entries[f"keyrings/{role}.gpg"] != entries[f"keyrings/{role}.pgp"]:
            raise ValueError("canonical .gpg/.pgp aliases have different digests")
    return entries


def validate_canonical_signer(returncode: int, status: str, keys: dict, now: int) -> dict:
    category, signatures, _missing, _warnings = classify(returncode, status, keys, now)
    if category != "cryptographically-valid-with-packaged-key-state" or len(signatures) != 1:
        raise ValueError("canonical manifest signature/key state is not accepted")
    signature = signatures[0]
    if (signature["fingerprint"], signature["primary_fingerprint"]) != (CANONICAL_SIGNER, CANONICAL_PRIMARY):
        raise ValueError("canonical manifest signer is not the pinned official maintainer")
    if signature["digest_algorithm"] != "10":
        raise ValueError("canonical manifest must use its reviewed SHA512 signature algorithm")
    if not now - 31 * 86400 <= signature["created"] <= now:
        raise ValueError("canonical manifest signature is stale or future-dated")
    if any(keys[fingerprint]["role"] != "debian-keyring" for fingerprint in (CANONICAL_SIGNER, CANONICAL_PRIMARY)):
        raise ValueError("canonical signer is not in the authenticated developer keyring")
    return signature


def canonical_blob(payload: bytes, expected: str) -> None:
    if not 0 < len(payload) <= 40 * 1024 * 1024 or hashlib.sha512(payload).hexdigest() != expected:
        raise ValueError("canonical keyring bytes differ from signed manifest or exceed bound")


def prepare_canonical_keyrings(bootstrap: list, manifest: Path, directory: Path, output: Path, now: int):
    bootstrap_output = output / "bootstrap-key-state"
    bootstrap_output.mkdir(mode=0o700)
    bootstrap_keys = key_metadata(bootstrap, bootstrap_output)
    work = output / "canonical-keyrings"
    work.mkdir(mode=0o700)
    payload = bundle.read(manifest)
    if not 0 < len(payload) <= 64 * 1024:
        raise ValueError("canonical signed manifest exceeds size bound")
    copy = work / "signed-sha512sums.txt"
    copy.write_bytes(payload)
    command = ["gpgv", "--weak-digest", "SHA1", "--homedir", str(bootstrap_output / "empty-gpg-home"),
               "--status-fd=1", "--output", str(work / "verified-sha512sums.txt")]
    for ring in bootstrap:
        command += ["--keyring", ring["path"]]
    checked = run(command + [str(copy)])
    (work / "manifest-status.txt").write_bytes(checked.stdout)
    (work / "manifest-stderr.txt").write_bytes(checked.stderr)
    status = checked.stdout.decode("utf-8", "replace")
    signature = validate_canonical_signer(checked.returncode, status, bootstrap_keys, now)
    entries = canonical_manifest_entries((work / "verified-sha512sums.txt").read_text(encoding="utf-8"))
    rings = []
    total = 0
    # Emeritus keys in the signed file set are deliberately NOT loaded into the
    # active verifier. Historical membership needs a separate reviewed policy.
    for role in CANONICAL_ROLES:
        body = bundle.read(directory / (role + ".pgp"))
        expected = entries[f"keyrings/{role}.pgp"]
        canonical_blob(body, expected)
        total += len(body)
        if total > 64 * 1024 * 1024:
            raise ValueError("canonical keyring set exceeds total bound")
        target = work / (role + ".pgp")
        target.write_bytes(body)
        rings.append({"role": role, "path": str(target), "sha256": sha(body), "sha512": expected})
    return rings, {"manifest_sha256": sha(payload), "manifest_signature": signature,
                   "pinned_maintainer": "John Sullivan", "max_manifest_age_days": 31,
                   "emeritus_keys_loaded": False, "network_used": False}, status


def cached_dsc_path(candidate: Path, record: dict) -> Path:
    digest_path = candidate / "full-source-cache" / (record["integrity"]["dsc_sha256"] + ".blob")
    if digest_path.exists():
        return digest_path
    # Legacy Snapshot cache is URL-addressed, not content-addressed; every
    # selected object is still content-rehashed and identity-checked below.
    return candidate / "snapshot-cache/dsc" / (sha(record["locator"]["dsc_url"].encode()) + ".bin")


def verify_one(record, candidate, output, keyrings, keys, now, key_state_source="packaged"):
    digest = record["integrity"]["dsc_sha256"]
    result = {"source_name": record["source_name"], "source_version": record["source_version"],
              "dsc_sha256": digest, "dsc_url": record["locator"]["dsc_url"]}
    try:
        payload = bundle.read(cached_dsc_path(candidate, record))
        bundle.verify_dsc(payload, record)
        result["exact_identity_and_digest_verified"] = True
        if not payload.startswith(b"-----BEGIN PGP SIGNED MESSAGE-----"):
            return {**result, "status": "unsigned"}
        directory = output / "dsc" / digest
        directory.mkdir(mode=0o700)
        path = directory / "source.dsc"
        path.write_bytes(payload)
        command = ["gpgv", "--homedir", str(output / "empty-gpg-home"), "--status-fd=1",
                   "--weak-digest", "SHA1", "--output", str(directory / "verified-control")]
        for ring in keyrings:
            command += ["--keyring", ring["path"]]
        checked = run(command + [str(path)], timeout=45)
        (directory / "gpgv-status.txt").write_bytes(checked.stdout)
        (directory / "gpgv-stderr.txt").write_bytes(checked.stderr)
        status, signatures, missing, warnings = classify(checked.returncode, checked.stdout.decode("utf-8", "replace"), keys, now)
        if status == "cryptographically-valid-with-packaged-key-state" and key_state_source == "canonical":
            status = "cryptographically-valid-with-canonical-key-state"
        # Cryptography must authenticate the same Source/Version and source-file
        # digest set used by the candidate map, not merely any valid envelope.
        if checked.returncode == 0 and signatures:
            clear = (directory / "verified-control").read_bytes()
            clear_record = {**record, "integrity": {**record["integrity"], "dsc_sha256": sha(clear)}}
            bundle.verify_dsc(clear, clear_record)
        return {**result, "status": status, "gpgv_returncode": checked.returncode,
                "signatures": signatures, "missing_key_ids": missing, "warnings": warnings,
                "log_directory": str(directory)}
    except (OSError, ValueError, KeyError, bundle.Error, subprocess.TimeoutExpired) as exc:
        return {**result, "status": "binding-or-verification-error", "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--keyring-deb", type=Path, required=True)
    parser.add_argument("--signed-index-dir", type=Path, required=True)
    parser.add_argument("--keyring-suite", choices=("trixie", "sid"), default="trixie",
                        help="Suite of authenticated keyring DATA only; never changes APT or OS package sources")
    parser.add_argument("--canonical-manifest", type=Path, help="Optional already-downloaded signed canonical SHA512 manifest")
    parser.add_argument("--canonical-keyring-dir", type=Path, help="Optional already-downloaded four canonical .pgp keyrings")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be 1..8")
    if bool(args.canonical_manifest) != bool(args.canonical_keyring_dir):
        parser.error("canonical manifest and canonical keyring directory must be supplied together")
    candidate, output = args.candidate.resolve(), args.output_dir.resolve()
    receipt = json.loads(bundle.read(candidate / "immutable-input-receipt.json"))
    values = {"map_path": candidate / "exact-source-map.private.json",
              "supplement": candidate / "embedded-source-supplement.private.json",
              "index": candidate / "source-index.private.json", "dagric_commit": receipt["source_commit"]}
    for edition in ("free", "pro"):
        values[edition + "_status"] = candidate / "manifests" / f"{edition}-dpkg-status"
        values[edition + "_manifest"] = candidate / "manifests" / f"{edition}.packages"
        values[edition + "_iso_sha256"] = receipt["editions"][edition]["checksum_receipt"].split()[0]
    sources, binding, _inventory = bundle.candidate_inputs(SimpleNamespace(**values))
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    (output / "dsc").mkdir(mode=0o700)
    keyrings, keyring_binding = prepare_keyrings(args.keyring_deb.resolve(), args.signed_index_dir.resolve(),
                                                output, Path("/usr/share/keyrings/debian-archive-keyring.gpg"), args.keyring_suite)
    now = datetime.now(timezone.utc)
    mode = "canonical" if args.canonical_manifest else "packaged"
    canonical_binding = None
    if mode == "canonical":
        keyrings, canonical_binding, canonical_status = prepare_canonical_keyrings(
            keyrings, args.canonical_manifest.absolute(), args.canonical_keyring_dir.absolute(), output, int(now.timestamp()))
    keys = key_metadata(keyrings, output)
    if mode == "canonical":
        # The bootstrap authenticates the new bytes; also refuse a signer that
        # the authenticated current keyring marks revoked/expired/removed.
        validate_canonical_signer(0, canonical_status, keys, int(now.timestamp()))
    records = [record for _identity, record in sorted(sources.items()) if record["origin"] == "debian"]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda record: verify_one(record, candidate, output, keyrings, keys, int(now.timestamp()), mode), records))
    report = {"schema": "dagric.private-dsc-signatures.v1", "release_approved": False,
              "checked_at": now.isoformat(), "inputs": binding, "audit_tool_sha256": sha(Path(__file__).read_bytes()),
              "keyring_provenance": keyring_binding, "keyrings": keyrings, "dsc_count": len(results),
              "key_state_source": mode, "canonical_keyring_provenance": canonical_binding,
              "statuses": dict(Counter(result["status"] for result in results)), "entries": results,
              "limitations": ["gpgv checks cryptography but ignores key expiry/revocation; these are separately inspected from the authenticated key metadata.",
                              "Key-state evidence is dated by the selected package or authenticated canonical manifest, not an assurance of real-time revocation freshness.",
                              "Key membership does not establish per-package upload authority, historic authorization, redistribution rights, or human release approval.",
                              "SHA1 signatures are explicitly rejected; no allow-weak-digest or ignore-time-conflict option is used.",
                              "No automatic key retrieval/import, owner trust alteration, host package installation, public upload, or gate override.",
                              "Only declared exact Debian DSCs are checked; Dagric's Git archive, undeclared vendor code and complete corresponding-source delivery remain separate."]}
    path = output / "dsc-signatures.private.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "dsc_count": len(results), "statuses": report["statuses"],
                      "release_approved": False}, indent=2))
    return 0  # Evidence collection only, never a release-approval command.


if __name__ == "__main__":
    raise SystemExit(main())
