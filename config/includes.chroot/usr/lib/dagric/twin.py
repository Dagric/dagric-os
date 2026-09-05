#!/usr/bin/env python3
"""Dagric Twin — proof-carrying, local launch-policy experiments.

Twin is intentionally a small first implementation of the Dagric vision.  It
does not simulate arbitrary workloads and it never changes kernel, driver,
CPU, GPU, cgroup or update settings.  Its single candidate is the existing
bounded launch prefetch.  The owner explicitly records unchanged baselines and
explicit prefetch canaries; Twin retains a result only when the local evidence
supports it, otherwise it expires or quarantines the candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from statistics import median
from typing import Any, Iterable

import pipeline
from private_files import write_private_text


SCHEMA = 1
POLICY_ID = "bounded-launch-prefetch-v1"
MIN_SAMPLES = 5
MAX_SAMPLES = 24
RETAIN_SECONDS = 7 * 24 * 60 * 60
QUARANTINE_SECONDS = 24 * 60 * 60
SENSITIVE_WORDS = ("serial", "uuid", "mac", "address", "edid", "dmi", "machine-id", "path", "argv")


def state_dir() -> pathlib.Path:
    base = pathlib.Path(os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state"))
    return pathlib.Path(os.environ.get("DAGRIC_TWIN_STATE_DIR", base / "dagric" / "twin"))


def state_path() -> pathlib.Path:
    return state_dir() / "trials.json"


def now() -> int:
    return int(time.time())


def write_atomic(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    write_private_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def empty_state() -> dict[str, Any]:
    return {"schema": SCHEMA, "updated_at": now(), "applications": {}}


def load_state(path: pathlib.Path | None = None) -> dict[str, Any]:
    target = path or state_path()
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_state()
    return loaded if isinstance(loaded, dict) else empty_state()


def save_state(value: dict[str, Any], path: pathlib.Path | None = None) -> None:
    value["updated_at"] = now()
    write_atomic(path or state_path(), value)


def strip_separator(command: list[str]) -> list[str]:
    return command[1:] if command[:1] == ["--"] else command


def application_key(command: list[str]) -> str | None:
    if not command:
        return None
    resolved = pipeline.executable(command[0])
    if not resolved or not pipeline.allowed_prefetch_path(pathlib.Path(resolved)):
        return None
    # A keyed identifier permits per-application evidence without persisting a
    # command path, argument, document name, browser URL or other user data.
    return hashlib.blake2b(resolved.encode("utf-8"), digest_size=16).hexdigest()


def pressure_snapshot(root: pathlib.Path) -> dict[str, float] | None:
    values: dict[str, float] = {}
    for resource in ("cpu", "memory", "io"):
        sample = pipeline.parse_pressure(root, resource)
        if sample is None or "avg10" not in sample:
            return None
        values[resource] = float(sample["avg10"])
    return values


def allowed_canary(root: pathlib.Path) -> bool:
    policy = pipeline.active_policy(root)
    return pipeline.system_pressure_ok(root, policy["pressure_limits_avg10"])


def contract(root: pathlib.Path) -> dict[str, Any]:
    policy = pipeline.active_policy(root)
    return {
        "policy_id": POLICY_ID,
        "scope": "one explicit launch of system-installed executable code",
        "resources": ["page-cache"],
        # This is the maximum lifetime of the *policy action*, not a deadline
        # imposed on the owner's application.  Twin never kills an app to make
        # a benchmark look better.
        "max_duration_ms": 1000,
        "max_prefetch_mib": int(policy["launch_prefetch_max_mib"]),
        "safety_limits": {
            "pressure_guard": "PSI avg10 must stay below the existing Dagric policy limits",
            "background_warming": False,
            "ttl_seconds": RETAIN_SECONDS,
        },
        "rollback": "skip prefetch for this application and quarantine the candidate",
    }


def application_entry(state: dict[str, Any], key: str, root: pathlib.Path) -> dict[str, Any]:
    applications = state.setdefault("applications", {})
    if not isinstance(applications, dict):
        state["applications"] = applications = {}
    entry = applications.setdefault(key, {"contract": contract(root), "trials": [], "decision": {"state": "shadow"}})
    entry["contract"] = contract(root)
    entry.setdefault("trials", [])
    entry.setdefault("decision", {"state": "shadow"})
    return entry


def expire(entry: dict[str, Any], timestamp: int | None = None) -> None:
    timestamp = now() if timestamp is None else timestamp
    decision = entry.get("decision", {})
    until = decision.get("expires_at")
    if isinstance(until, int) and until <= timestamp:
        entry["decision"] = {"state": "shadow", "reason": "previous decision expired", "at": timestamp}


def p95(values: Iterable[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * 0.95 + 0.999999)))
    return ordered[index]


def pressure_regressed(baseline: list[dict[str, Any]], canary: list[dict[str, Any]]) -> bool:
    for resource in ("cpu", "memory", "io"):
        before = [float(item["pressure_after"][resource]) for item in baseline if isinstance(item.get("pressure_after"), dict)]
        after = [float(item["pressure_after"][resource]) for item in canary if isinstance(item.get("pressure_after"), dict)]
        if before and after and p95(after) > p95(before) + 0.5:
            return True
    return False


def evaluate_entry(entry: dict[str, Any], timestamp: int | None = None) -> dict[str, Any]:
    timestamp = now() if timestamp is None else timestamp
    expire(entry, timestamp)
    trials = [item for item in entry.get("trials", []) if item.get("exit_code") == 0]
    baseline = [item for item in trials if item.get("mode") == "baseline"][-MAX_SAMPLES:]
    canary = [item for item in trials if item.get("mode") == "canary"][-MAX_SAMPLES:]
    if len(baseline) < MIN_SAMPLES or len(canary) < MIN_SAMPLES:
        entry["decision"] = {
            "state": "shadow",
            "reason": "insufficient successful baseline and canary samples",
            "baseline_samples": len(baseline),
            "canary_samples": len(canary),
            "at": timestamp,
        }
        return entry["decision"]

    baseline_p95 = p95([float(item["wall_ms"]) for item in baseline])
    canary_p95 = p95([float(item["wall_ms"]) for item in canary])
    improvement = 0.0 if baseline_p95 <= 0 else (baseline_p95 - canary_p95) / baseline_p95
    regression = pressure_regressed(baseline, canary)
    if regression or canary_p95 >= baseline_p95 * 1.02:
        entry["decision"] = {
            "state": "quarantined",
            "reason": "pressure or launch-duration regression",
            "baseline_p95_ms": round(baseline_p95, 3),
            "canary_p95_ms": round(canary_p95, 3),
            "improvement_fraction": round(improvement, 5),
            "expires_at": timestamp + QUARANTINE_SECONDS,
            "at": timestamp,
        }
    elif improvement >= 0.05:
        confidence = min(0.99, 0.50 + 0.04 * min(len(baseline), len(canary)) + improvement * 0.5)
        entry["decision"] = {
            "state": "retained",
            "reason": "local p95 improvement without detected pressure regression",
            "baseline_p95_ms": round(baseline_p95, 3),
            "canary_p95_ms": round(canary_p95, 3),
            "improvement_fraction": round(improvement, 5),
            "confidence": round(confidence, 3),
            "expires_at": timestamp + RETAIN_SECONDS,
            "at": timestamp,
        }
    else:
        entry["decision"] = {
            "state": "shadow",
            "reason": "candidate did not clear the 5% local p95 improvement threshold",
            "baseline_p95_ms": round(baseline_p95, 3),
            "canary_p95_ms": round(canary_p95, 3),
            "improvement_fraction": round(improvement, 5),
            "at": timestamp,
        }
    return entry["decision"]


def run_trial(command: list[str], mode: str, root: pathlib.Path, state: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    key = application_key(command)
    if key is None:
        raise ValueError("Twin accepts only a system-installed executable under /usr, /lib, /lib64 or /opt")
    entry = application_entry(state, key, root)
    expire(entry)
    decision = entry["decision"]
    before = pressure_snapshot(root)
    applied = mode == "canary" and decision.get("state") != "quarantined" and allowed_canary(root)
    # Include policy setup in the measurement.  Excluding prefetch time would
    # turn an optimization overhead into an invisible benchmark advantage.
    started = time.monotonic()
    if applied:
        pipeline.command_prepare(command, root)
    try:
        child = subprocess.Popen(command)
    except OSError as exc:
        raise ValueError(f"cannot launch {command[0]}: {exc}") from exc
    exit_code = child.wait()
    elapsed = (time.monotonic() - started) * 1000
    after = pressure_snapshot(root)
    record = {
        "mode": "canary" if applied else ("baseline" if mode == "baseline" else "bypassed"),
        "wall_ms": round(elapsed, 3),
        "exit_code": exit_code,
        "pressure_before": before,
        "pressure_after": after,
        "at": now(),
    }
    trials = entry["trials"]
    trials.append(record)
    entry["trials"] = trials[-(MAX_SAMPLES * 2):]
    evaluate_entry(entry)
    return exit_code, record


def audit_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if state.get("schema") != SCHEMA:
        errors.append("unsupported Twin state schema")
    raw = json.dumps(state, sort_keys=True).lower()
    key_pattern = re.compile(r"(?:^|[_-])(?:" + "|".join(SENSITIVE_WORDS) + r")(?:$|[_-])")
    def keys(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                yield str(key).lower()
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)
    if any(key_pattern.search(item) for item in keys(state)) or re.search(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", raw):
        errors.append("Twin state contains privacy-sensitive data")
    for key, entry in state.get("applications", {}).items() if isinstance(state.get("applications"), dict) else []:
        if not re.fullmatch(r"[0-9a-f]{32}", str(key)):
            errors.append("application key is not a privacy-preserving digest")
        if entry.get("contract", {}).get("policy_id") != POLICY_ID:
            errors.append("unapproved policy contract")
        if entry.get("contract", {}).get("safety_limits", {}).get("background_warming") is not False:
            errors.append("Twin must not enable background warming")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dagric Twin local launch-policy evaluator")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("status", help="print local proof-carrying policy state")
    audit = sub.add_parser("audit", help="validate Twin's privacy and safety state")
    audit.add_argument("--state", type=pathlib.Path)
    shadow = sub.add_parser("shadow", help="show whether a bounded canary would be eligible")
    shadow.add_argument("command", nargs=argparse.REMAINDER)
    for name, help_text in (("baseline", "run an explicit unchanged baseline"), ("canary", "run one guarded prefetch canary")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("command", nargs=argparse.REMAINDER)
    evaluate = sub.add_parser("evaluate", help="evaluate evidence for an explicit system application")
    evaluate.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    state = load_state(args.state if args.subcommand == "audit" else None)

    if args.subcommand == "audit":
        errors = audit_state(state)
        if errors:
            print("dagric-twin audit failed: " + "; ".join(errors), file=sys.stderr)
            return 1
        print("dagric-twin: state is privacy-safe and contains only the approved bounded policy")
        return 0
    if args.subcommand == "status":
        for entry in state.get("applications", {}).values():
            expire(entry)
        save_state(state)
        print(json.dumps(state, sort_keys=True, indent=2))
        return 0
    command = strip_separator(args.command)
    key = application_key(command)
    if key is None:
        print("dagric-twin: use a system-installed executable; no user paths or arguments are retained", file=sys.stderr)
        return 2
    entry = application_entry(state, key, root)
    expire(entry)
    if args.subcommand == "shadow":
        result = {"eligible": allowed_canary(root), "contract": entry["contract"], "decision": entry["decision"]}
        save_state(state)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    if args.subcommand == "evaluate":
        result = evaluate_entry(entry)
        save_state(state)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    try:
        exit_code, result = run_trial(command, args.subcommand, root, state)
    except ValueError as exc:
        print(f"dagric-twin: {exc}", file=sys.stderr)
        return 2
    save_state(state)
    print(json.dumps({"trial": result, "decision": entry["decision"]}, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
