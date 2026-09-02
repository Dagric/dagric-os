#!/usr/bin/python3
"""Dagric Trust Loop: local status, history summary, and Support Mode export.

The report is deliberately allow-listed.  It does not scrape the journal or a
home directory, because filtering an unlimited data source after collection is
not the same privacy boundary as never collecting it.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import re
import tarfile
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = 1
MAX_LABEL = 160
SENSITIVE_KEY = re.compile(
    r"(?:^|[_-])(?:serial|hostname|username|email|ssid|wifi|mac|address|token|"
    r"password|secret|clipboard|browser|document|command|argument|path)(?:$|[_-])",
    re.IGNORECASE,
)
EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
MAC = re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.IGNORECASE)
HOME_PATH = re.compile(r"(?:^|\s)/(?:home|Users)/[^\s/]+", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rooted(root: pathlib.Path, absolute: str) -> pathlib.Path:
    return root / absolute.lstrip("/")


def read_text(root: pathlib.Path, absolute: str, limit: int = 256_000) -> str:
    path = rooted(root, absolute)
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: pathlib.Path, limit: int = 512_000) -> dict[str, Any]:
    try:
        if path.stat().st_size > limit:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def safe_label(value: str, fallback: str = "Detected (details withheld)") -> str:
    compact = " ".join(value.split())[:MAX_LABEL]
    if not compact or EMAIL.search(compact) or MAC.search(compact) or HOME_PATH.search(compact):
        return fallback
    if any(ch in compact for ch in ("/", "\\", "\x00")):
        return fallback
    return compact


def os_release(root: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in read_text(root, "/etc/os-release", 32_000).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return {
        "name": safe_label(values.get("PRETTY_NAME", values.get("NAME", "Dagric OS")), "Dagric OS"),
        "version": safe_label(values.get("VERSION_ID", "unknown"), "unknown"),
    }


def cpu_summary(root: pathlib.Path) -> dict[str, Any]:
    text = read_text(root, "/proc/cpuinfo")
    models: list[str] = []
    processors = 0
    for line in text.splitlines():
        if line.lower().startswith("processor") and ":" in line:
            processors += 1
        if line.lower().startswith(("model name", "hardware")) and ":" in line:
            models.append(line.split(":", 1)[1].strip())
    return {
        "model": safe_label(models[0]) if models else "Not detected",
        "logical_processors": processors,
        "evidence": "local detection",
        "lab_rating": "not evaluated",
    }


def memory_summary(root: pathlib.Path) -> dict[str, Any]:
    match = re.search(r"(?m)^MemTotal:\s*(\d+)\s+kB$", read_text(root, "/proc/meminfo"))
    mib = int(match.group(1)) // 1024 if match else 0
    return {"total_mib": mib, "evidence": "local detection"}


def gpu_summary(root: pathlib.Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    base = rooted(root, "/sys/class/drm")
    try:
        devices = sorted(base.glob("card[0-9]*/device/uevent"))
    except OSError:
        devices = []
    for path in devices[:8]:
        values: dict[str, str] = {}
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
        except OSError:
            continue
        rows.append({
            "driver": safe_label(values.get("DRIVER", "unknown"), "unknown"),
            "pci_id": safe_label(values.get("PCI_ID", "unknown"), "unknown"),
            "evidence": "local detection",
            "lab_rating": "not evaluated",
        })
    return rows


def root_storage(root: pathlib.Path) -> dict[str, Any]:
    found = {"filesystem": "unknown", "compression": "unknown"}
    for line in read_text(root, "/proc/mounts").splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[1] != "/":
            continue
        found["filesystem"] = safe_label(fields[2], "unknown")
        options = fields[3].split(",")
        compression = next((item for item in options if item.startswith("compress")), "not enabled")
        found["compression"] = safe_label(compression, "unknown")
        break
    return found


def secure_boot_state(root: pathlib.Path) -> str:
    efi = rooted(root, "/sys/firmware/efi")
    if not efi.is_dir():
        return "legacy BIOS or unavailable"
    variables = rooted(root, "/sys/firmware/efi/efivars")
    try:
        candidates = list(variables.glob("SecureBoot-*"))
    except OSError:
        candidates = []
    for path in candidates[:2]:
        try:
            data = path.read_bytes()[:8]
        except OSError:
            continue
        if len(data) >= 5:
            return "enabled" if data[4] == 1 else "disabled"
    return "UEFI; state unavailable"


def configured_backup(state_home: pathlib.Path) -> bool:
    markers = (
        state_home / ".config" / "kup" / "kupsettings.xml",
        state_home / ".config" / "Vorta" / "settings.db",
        state_home / ".config" / "vorta" / "settings.db",
    )
    return any(path.is_file() for path in markers)


def protection_summary(root: pathlib.Path, state_home: pathlib.Path, storage: dict[str, Any]) -> dict[str, Any]:
    btrfs = storage["filesystem"] == "btrfs"
    snapper = rooted(root, "/etc/snapper/configs/root").is_file()
    recovery = rooted(root, "/usr/bin/snapper").exists() and rooted(root, "/usr/bin/btrfs").exists()
    backup = configured_backup(state_home)
    return {
        "restore_points": "ready" if btrfs and snapper else "not ready",
        "restore_reason": "Btrfs and root Snapper configuration detected" if btrfs and snapper else "requires Btrfs and root Snapper configuration",
        "personal_backup": "configured; restore not yet verified" if backup else "not configured",
        "recovery_tools": "available" if recovery else "not confirmed",
        "separation": "restore points are not reported as backups",
    }


def jsonl_count_latest(path: pathlib.Path, time_keys: Iterable[str]) -> tuple[int, str]:
    count = 0
    latest = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
    except OSError:
        return 0, ""
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        count += 1
        for key in time_keys:
            value = row.get(key)
            if isinstance(value, str) and value > latest:
                latest = value[:64]
    return count, latest


def history_summary(root: pathlib.Path, state_home: pathlib.Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    profile = read_json(rooted(root, "/var/lib/dagric/pipeline/profile.json"))
    if profile:
        actions = profile.get("actions", [])
        if not isinstance(actions, list):
            actions = []
        events.append({
            "component": "Adaptive Pipeline",
            "what": "Machine policy compiled",
            "why": "Match bounded Dagric policy to locally detected hardware",
            "when": str(profile.get("generated_at", "unknown"))[:64],
            "effect": [safe_label(str(item), "withheld") for item in actions[:16]],
            "reversible": True,
            "rollback": "regenerate the approved baseline profile",
        })
    twin = read_json(state_home / ".local" / "state" / "dagric" / "twin" / "state.json")
    applications = twin.get("applications", {}) if isinstance(twin, dict) else {}
    if isinstance(applications, dict) and applications:
        states = Counter()
        newest = 0
        for entry in applications.values():
            if not isinstance(entry, dict):
                continue
            decision = entry.get("decision", {})
            if isinstance(decision, dict):
                states[str(decision.get("state", "shadow"))[:24]] += 1
                if isinstance(decision.get("at"), int):
                    newest = max(newest, decision["at"])
        events.append({
            "component": "Dagric Twin",
            "what": "Launch-policy evidence evaluated",
            "why": "Retain only measured improvements and quarantine regressions",
            "when": datetime.fromtimestamp(newest, timezone.utc).isoformat().replace("+00:00", "Z") if newest else "unknown",
            "effect": dict(sorted(states.items())),
            "reversible": True,
            "rollback": "expire or quarantine the bounded launch policy",
        })
    rewind_count, rewind_latest = jsonl_count_latest(
        rooted(root, "/var/lib/dagric/rewind/history.jsonl"), ("finishedAt", "finished_at", "startedAt")
    )
    if rewind_count:
        events.append({
            "component": "Dagric Rewind",
            "what": f"{rewind_count} completed change session(s)",
            "why": "Keep a reviewable system restore history",
            "when": rewind_latest or "unknown",
            "effect": "system snapshots only; personal files are outside this summary",
            "reversible": True,
            "rollback": "use Dagric Rewind or the recovery environment",
        })
    return events


def support_manifest() -> dict[str, list[str]]:
    return {
        "included": [
            "Dagric and kernel versions",
            "hardware classes without serial numbers",
            "boot mode and root filesystem",
            "restore and backup readiness",
            "aggregate Dagric Pipeline, Twin, and Rewind state",
        ],
        "excluded": [
            "personal files and filenames",
            "browser activity, clipboard, and command history",
            "email addresses, account names, and home-directory paths",
            "Wi-Fi names, credentials, tokens, and security keys",
            "hardware serial numbers and stable machine fingerprints",
            "unfiltered system journal entries",
        ],
    }


def build_report(root: pathlib.Path = pathlib.Path("/"), state_home: pathlib.Path | None = None) -> dict[str, Any]:
    state_home = state_home or pathlib.Path.home()
    storage = root_storage(root)
    kernel = safe_label(read_text(root, "/proc/sys/kernel/osrelease", 4096).strip(), "unknown")
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "system": {**os_release(root), "kernel": kernel},
        "hardware_passport": {
            "cpu": cpu_summary(root),
            "memory": memory_summary(root),
            "graphics": gpu_summary(root),
            "storage": storage,
            "secure_boot": secure_boot_state(root),
            "verification_note": "Detection is not Dagric Lab verification; unrated hardware is never called Verified.",
        },
        "protection": protection_summary(root, state_home, storage),
        "history": history_summary(root, state_home),
        "support_manifest": support_manifest(),
    }


def privacy_errors(value: Any) -> list[str]:
    errors: list[str] = []

    def walk(node: Any, location: str = "report") -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                key_text = str(key)
                if SENSITIVE_KEY.search(key_text):
                    errors.append(f"sensitive field name at {location}.{key_text}")
                walk(child, f"{location}.{key_text}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{location}[{index}]")
        elif isinstance(node, str):
            if EMAIL.search(node) or MAC.search(node) or HOME_PATH.search(node):
                errors.append(f"sensitive value at {location}")

    walk(value)
    return errors


def preview(report: dict[str, Any]) -> str:
    passport = report["hardware_passport"]
    protection = report["protection"]
    lines = [
        "DAGRIC SUPPORT MODE -- PREVIEW",
        "",
        f"System: {report['system']['name']} {report['system']['version']}",
        f"Kernel: {report['system']['kernel']}",
        f"CPU: {passport['cpu']['model']} ({passport['cpu']['logical_processors']} logical processors)",
        f"Memory: {passport['memory']['total_mib']} MiB",
        f"Graphics devices: {len(passport['graphics'])}",
        f"Root filesystem: {passport['storage']['filesystem']}",
        f"Secure Boot: {passport['secure_boot']}",
        "",
        f"Restore points: {protection['restore_points']}",
        f"Personal backup: {protection['personal_backup']}",
        f"Recovery tools: {protection['recovery_tools']}",
        f"Dagric-managed history entries: {len(report['history'])}",
        "",
        "Included:",
    ]
    lines.extend(f"  + {item}" for item in report["support_manifest"]["included"])
    lines.append("Excluded:")
    lines.extend(f"  - {item}" for item in report["support_manifest"]["excluded"])
    lines.extend(("", "Nothing has been uploaded. Export creates a local archive only."))
    return "\n".join(lines)


def add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o600
    info.mtime = 0
    archive.addfile(info, io.BytesIO(payload))


def export_report(report: dict[str, Any], destination: pathlib.Path) -> None:
    if destination.suffixes[-2:] != [".tar", ".gz"]:
        raise ValueError("destination must end in .tar.gz")
    if not destination.parent.is_dir():
        raise ValueError("destination directory does not exist")
    if destination.exists() or destination.is_symlink():
        raise ValueError("destination already exists; Support Mode will not overwrite it")
    errors = privacy_errors(report)
    if errors:
        raise ValueError("privacy audit failed: " + "; ".join(errors))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle, tarfile.open(fileobj=handle, mode="w:gz") as archive:
            payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
            add_bytes(archive, "dagric-support/report.json", payload)
            add_bytes(archive, "dagric-support/README.txt", (preview(report) + "\n").encode("utf-8"))
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dagric privacy-safe Support Mode")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    parser.add_argument("--state-home", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("preview", help="show exactly what a support export would contain")
    sub.add_parser("json", help="print the allow-listed report")
    sub.add_parser("audit", help="prove the current report contains no forbidden identifiers")
    export = sub.add_parser("export", help="create a local privacy-filtered .tar.gz archive")
    export.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    state_home = pathlib.Path(args.state_home) if args.state_home else None
    report = build_report(root, state_home)
    errors = privacy_errors(report)
    command = args.command or "preview"
    if command == "audit":
        if errors:
            print("dagric-support: privacy audit failed: " + "; ".join(errors), file=os.sys.stderr)
            return 1
        print("dagric-support: report is allow-listed and privacy-safe")
        return 0
    if errors:
        print("dagric-support: refused report: " + "; ".join(errors), file=os.sys.stderr)
        return 1
    if command == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif command == "export":
        try:
            export_report(report, args.destination)
        except (OSError, ValueError) as exc:
            print(f"dagric-support: {exc}", file=os.sys.stderr)
            return 2
        print(f"Dagric support package created locally: {args.destination}")
    else:
        print(preview(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
