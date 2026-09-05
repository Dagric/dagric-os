#!/usr/bin/env python3
"""Validate human physical qualification for an exact Dagric release candidate.

Virtual machines can test build and boot mechanics, but they cannot prove retail
firmware, physical peripherals, audible screen-reader output, suspend/resume, or
multi-user security boundaries. This fail-closed gate consumes a protected
environment secret and binds every required physical result to the exact release
commit, tag, artifact hashes, machines, and HTTPS evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
MACHINE_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")
DISALLOWED_HUMAN = {"ai", "chatgpt", "codex", "openai", "pending", "tbd", "unknown"}
SENSITIVE_MACHINE_KEYS = {"serial", "serial_number", "mac", "mac_address", "ip", "ip_address", "username"}

# Each row names the editions that must be represented by physical evidence.
# OpenSnitch is Pro-only; all shared desktop/security behavior is proven in both
# editions so an edition-specific packaging regression cannot hide behind a Free
# result.
REQUIRED_CHECKS: dict[str, tuple[str, ...]] = {
    "bios_live_boot": ("free", "pro"),
    "uefi_install_reboot_login": ("free", "pro"),
    "secure_boot_install_reboot_login": ("free", "pro"),
    "display_native_resolution_acceleration": ("free", "pro"),
    "ethernet_connectivity": ("free", "pro"),
    "wifi_connectivity": ("free", "pro"),
    "audio_input_output": ("free", "pro"),
    "bluetooth_pair_transfer": ("free", "pro"),
    "suspend_resume": ("free", "pro"),
    "keyboard_only_navigation": ("free", "pro"),
    "orca_audible_navigation": ("free", "pro"),
    "text_scaling_200_percent": ("free", "pro"),
    "reduced_motion": ("free", "pro"),
    "x11_session": ("free", "pro"),
    "wayland_session": ("free", "pro"),
    "multi_user_home_isolation": ("free", "pro"),
    "multi_user_polkit_denial": ("free", "pro"),
    "family_controls_multi_user": ("free", "pro"),
    "opensnitch_socket_permissions": ("pro",),
    "opensnitch_key_permissions": ("pro",),
    "opensnitch_non_admin_denied": ("pro",),
}


class GateError(ValueError):
    """A physical qualification invariant is absent, stale, or failed."""


def object_value(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    return value


def list_value(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise GateError(f"{label} must be an array")
    return value


def https_url(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise GateError(f"{label} must be an HTTPS URL")
    parsed = urlsplit(value)
    lowered = value.casefold()
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or any(marker in lowered for marker in ("example.com", "replace", "todo", "tbd"))
    ):
        raise GateError(f"{label} must be a non-placeholder HTTPS URL")
    return value


def utc_time(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GateError(f"{label} must be an ISO UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GateError(f"{label} is invalid") from exc
    if parsed > datetime.now(timezone.utc):
        raise GateError(f"{label} is in the future")
    return value


def load_json(path: Path, label: str) -> dict[str, object]:
    try:
        return object_value(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read {label} {path}: {exc}") from exc


def release_artifacts(release: dict[str, object]) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for raw in list_value(release.get("artifacts"), "release.artifacts"):
        record = object_value(raw, "release artifact")
        edition = record.get("edition")
        if edition not in {"free", "pro"} or edition in records:
            raise GateError("release must contain exactly one Free and one Pro artifact")
        if not SHA256_RE.fullmatch(str(record.get("sha256", ""))):
            raise GateError(f"release {edition} artifact has an invalid SHA-256")
        records[str(edition)] = record
    if set(records) != {"free", "pro"}:
        raise GateError("release must contain exactly one Free and one Pro artifact")
    return records


def validate(args: argparse.Namespace, raw_json: str) -> str:
    if not raw_json.strip():
        raise GateError(
            f"{args.evidence_env} is absent; physical qualification cannot be inferred from VM evidence"
        )
    try:
        evidence = object_value(json.loads(raw_json), "physical release evidence")
    except json.JSONDecodeError as exc:
        raise GateError(f"physical release evidence is not valid JSON: {exc}") from exc
    if evidence.get("schema") != "dagric-physical-release-evidence-v1":
        raise GateError("physical release evidence has the wrong schema")
    if evidence.get("decision") != "passed" or evidence.get("reviewed_by_human") is not True:
        raise GateError("physical release evidence must be passed and human reviewed")
    if not COMMIT_RE.fullmatch(args.candidate_commit):
        raise GateError("candidate commit must be a full lowercase Git commit")
    if evidence.get("candidate_commit") != args.candidate_commit:
        raise GateError("physical evidence is for a different candidate commit")
    if evidence.get("release_tag") != args.release_tag:
        raise GateError("physical evidence is for a different release tag")
    utc_time(evidence.get("completed_utc"), "physical evidence completed_utc")

    reviewer = object_value(evidence.get("reviewer"), "physical evidence reviewer")
    reviewer_text = f"{reviewer.get('name', '')} {reviewer.get('role', '')}".strip()
    if len(str(reviewer.get("name", "")).strip()) < 3 or any(
        marker in reviewer_text.casefold() for marker in DISALLOWED_HUMAN
    ):
        raise GateError("physical evidence must name a real human reviewer")
    if not re.search(r"\b(?:qa|quality|security|accessibility|test|engineer)\b", reviewer_text, re.I):
        raise GateError("physical reviewer role must state QA, security, accessibility, test, or engineering scope")

    release = load_json(args.release_record, "release record")
    source = object_value(release.get("source"), "release.source")
    if source.get("commit") != args.candidate_commit:
        raise GateError("release record source commit does not match the candidate")
    expected_artifacts = release_artifacts(release)
    supplied_artifacts = object_value(evidence.get("artifacts"), "physical evidence artifacts")
    if set(supplied_artifacts) != {"free", "pro"}:
        raise GateError("physical evidence must bind exactly the Free and Pro artifacts")
    for edition, expected in expected_artifacts.items():
        actual = object_value(supplied_artifacts.get(edition), f"physical {edition} artifact")
        for field in ("filename", "bytes", "sha256"):
            if actual.get(field) != expected.get(field):
                raise GateError(f"physical {edition} artifact {field} is stale")

    machines = list_value(evidence.get("machines"), "physical evidence machines")
    if not machines:
        raise GateError("physical evidence has no machines")
    machine_ids: set[str] = set()
    cpu_vendors: set[str] = set()
    gpu_vendors: set[str] = set()
    for position, raw in enumerate(machines, 1):
        machine = object_value(raw, f"machine {position}")
        forbidden = SENSITIVE_MACHINE_KEYS.intersection(machine)
        if forbidden:
            raise GateError(
                f"machine {position} includes prohibited personal/device identifiers: "
                + ", ".join(sorted(forbidden))
            )
        machine_id = str(machine.get("machine_id", ""))
        if not MACHINE_RE.fullmatch(machine_id) or machine_id in machine_ids:
            raise GateError(f"machine {position} has an invalid or duplicate anonymous machine_id")
        if machine.get("physical") is not True:
            raise GateError(f"machine {machine_id} is not explicitly physical")
        for field in ("manufacturer_model", "firmware", "cpu", "memory", "storage"):
            if len(str(machine.get(field, "")).strip()) < 3:
                raise GateError(f"machine {machine_id} lacks {field}")
        cpu_vendor = str(machine.get("cpu_vendor", "")).casefold()
        if cpu_vendor not in {"intel", "amd"}:
            raise GateError(f"machine {machine_id} has unsupported cpu_vendor")
        raw_gpu_vendors = list_value(machine.get("gpu_vendors"), f"machine {machine_id} gpu_vendors")
        local_gpu = {str(item).casefold() for item in raw_gpu_vendors}
        if not local_gpu or not local_gpu.issubset({"intel", "amd", "nvidia"}):
            raise GateError(f"machine {machine_id} has invalid gpu_vendors")
        https_url(machine.get("evidence_url"), f"machine {machine_id} evidence")
        machine_ids.add(machine_id)
        cpu_vendors.add(cpu_vendor)
        gpu_vendors.update(local_gpu)
    if not {"intel", "amd"}.issubset(cpu_vendors):
        raise GateError("physical matrix must cover both Intel and AMD processors")
    if not {"intel", "amd", "nvidia"}.issubset(gpu_vendors):
        raise GateError("physical matrix must cover Intel, AMD, and NVIDIA graphics")

    checks = object_value(evidence.get("checks"), "physical evidence checks")
    missing = sorted(set(REQUIRED_CHECKS) - set(checks))
    if missing:
        raise GateError("physical evidence is missing required checks: " + ", ".join(missing))
    for check_id, editions in REQUIRED_CHECKS.items():
        record = object_value(checks.get(check_id), f"physical check {check_id}")
        if record.get("result") != "pass":
            raise GateError(f"physical check {check_id} did not pass")
        if record.get("editions") != list(editions):
            raise GateError(f"physical check {check_id} has incomplete edition coverage")
        used = list_value(record.get("machine_ids"), f"physical check {check_id} machine_ids")
        if not used or any(item not in machine_ids for item in used):
            raise GateError(f"physical check {check_id} has missing or unknown machines")
        urls = list_value(record.get("evidence_urls"), f"physical check {check_id} evidence_urls")
        if not urls:
            raise GateError(f"physical check {check_id} has no evidence URLs")
        for index, url in enumerate(urls, 1):
            https_url(url, f"physical check {check_id} evidence URL {index}")
        if len(str(record.get("notes", "")).strip()) < 8:
            raise GateError(f"physical check {check_id} lacks useful notes")

    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()


def template(args: argparse.Namespace) -> None:
    release = load_json(args.release_record, "release record")
    artifacts = release_artifacts(release)
    document = {
        "schema": "dagric-physical-release-evidence-v1",
        "decision": "pending-human-physical-testing",
        "reviewed_by_human": False,
        "candidate_commit": args.candidate_commit,
        "release_tag": args.release_tag,
        "completed_utc": "REPLACE_WITH_UTC_TIMESTAMP",
        "reviewer": {"name": "REPLACE", "role": "REPLACE"},
        "artifacts": {
            edition: {field: record.get(field) for field in ("filename", "bytes", "sha256")}
            for edition, record in artifacts.items()
        },
        "machines": [
            {
                "machine_id": "REPLACE_WITH_ANONYMOUS_ID",
                "physical": True,
                "manufacturer_model": "REPLACE",
                "firmware": "REPLACE",
                "cpu_vendor": "REPLACE_WITH_INTEL_OR_AMD",
                "cpu": "REPLACE",
                "gpu_vendors": ["REPLACE_WITH_INTEL_AMD_OR_NVIDIA"],
                "memory": "REPLACE",
                "storage": "REPLACE",
                "evidence_url": "REPLACE",
            }
        ],
        "checks": {
            check_id: {
                "result": "pending",
                "editions": list(editions),
                "machine_ids": ["REPLACE_WITH_ANONYMOUS_ID"],
                "evidence_urls": ["REPLACE"],
                "notes": "REPLACE with what was exercised and observed",
            }
            for check_id, editions in REQUIRED_CHECKS.items()
        },
    }
    rendered = json.dumps(document, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"physical-release: wrote pending physical-test template to {args.output}")
    else:
        print(rendered, end="")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="mode", required=True)
    for name in ("check", "template"):
        command = sub.add_parser(name)
        command.add_argument("--candidate-commit", required=True)
        command.add_argument("--release-tag", required=True)
        command.add_argument(
            "--release-record", type=Path, default=ROOT / "site/manifest/release.json"
        )
        if name == "check":
            command.add_argument(
                "--evidence-env", default="PHYSICAL_RELEASE_EVIDENCE_JSON"
            )
        else:
            command.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.mode == "template":
            template(args)
        else:
            digest = validate(args, os.environ.get(args.evidence_env, ""))
            machines = len(json.loads(os.environ[args.evidence_env])["machines"])
            print(f"physical-release: passed; evidence={digest} machines={machines}")
    except (GateError, OSError) as exc:
        print(f"physical-release: BLOCKED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
