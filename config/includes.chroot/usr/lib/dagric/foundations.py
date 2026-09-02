#!/usr/bin/python3
"""Safe foundations for Dagric Blueprint, Black Box, and Life Support.

This module intentionally stops before applying a Blueprint or changing a sick
machine. Reconstruction and emergency mutations require the transactional root
and recovery tests that Dagric does not yet have.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import pathlib
import re
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Iterator

try:
    import fcntl  # Linux runtime; unavailable in the Windows source test host.
except ImportError:  # pragma: no cover - Windows-only fallback
    fcntl = None


BLUEPRINT_SCHEMA = 1
BLACKBOX_SCHEMA = 1
BLACKBOX_MAX_EVENTS = 2048
DETAIL_RETENTION_SECONDS = 15 * 60
SUMMARY_RETENTION_SECONDS = 7 * 24 * 60 * 60
ALLOWED_BLUEPRINT_TOP = {"dagric_blueprint", "system", "applications", "hardware_policies", "user_preferences", "omitted"}
ALLOWED_MARKS = {"update_started", "update_finished", "recovery_started", "recovery_finished", "policy_quarantined"}
BLUEPRINT_OMISSIONS = [
    "personal files and application data (use Dagric Backup)",
    "passwords, encryption material, account credentials and network secrets",
    "application permissions until portal-safe export is implemented",
    "custom filesystem paths and arbitrary shell configuration",
]
SENSITIVE_KEY = re.compile(r"(?:password|secret|token|key|ssid|wifi|serial|hostname|username|email|document|clipboard|browser|command|argument|path)", re.I)
EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
MAC = re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.I)
PERSONAL_PATH = re.compile(r"(?:^|\s)/(?:home|Users)/[^\s/]+", re.I)


def utc_now(timestamp: float | None = None) -> str:
    value = time.time() if timestamp is None else timestamp
    return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rooted(root: pathlib.Path, absolute: str) -> pathlib.Path:
    return root / absolute.lstrip("/")


def safe_read(path: pathlib.Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def write_json_exclusive(path: pathlib.Path, value: dict[str, Any]) -> None:
    if not path.parent.is_dir():
        raise ValueError("destination directory does not exist")
    if path.exists() or path.is_symlink():
        raise ValueError("destination already exists; Dagric will not overwrite it")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def privacy_errors(value: Any) -> list[str]:
    errors: list[str] = []

    def walk(node: Any, location: str = "data") -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if SENSITIVE_KEY.search(str(key)):
                    errors.append(f"sensitive field {location}.{key}")
                walk(child, f"{location}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{location}[{index}]")
        elif isinstance(node, str) and (EMAIL.search(node) or MAC.search(node) or PERSONAL_PATH.search(node)):
            errors.append(f"sensitive value {location}")

    walk(value)
    return errors


# ---------------------------------------------------------------- Blueprint
def parse_installed_packages(root: pathlib.Path) -> list[str]:
    text = safe_read(rooted(root, "/var/lib/dpkg/status"), 32_000_000)
    packages: list[str] = []
    for block in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith((" ", "\t")):
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        package = fields.get("Package", "")
        if fields.get("Status") == "install ok installed" and re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,127}", package):
            packages.append(package)
    return sorted(set(packages))


def flatpak_applications(root: pathlib.Path, state_home: pathlib.Path) -> list[str]:
    bases = (rooted(root, "/var/lib/flatpak/app"), state_home / ".local/share/flatpak/app")
    apps: set[str] = set()
    for base in bases:
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,159}", child.name):
                apps.add(child.name)
    return sorted(apps)


def ini_value(path: pathlib.Path, section: str, key: str) -> str:
    current = ""
    for line in safe_read(path, 256_000).splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
        elif current == section and "=" in stripped:
            item, value = stripped.split("=", 1)
            if item == key:
                return value.strip()[:160]
    return ""


def appearance_name(scheme: str) -> str:
    return {"DagricDark": "obsidian", "DagricLight": "frost", "DagricHighContrast": "high-contrast"}.get(scheme, "custom")


def build_blueprint(root: pathlib.Path, state_home: pathlib.Path) -> dict[str, Any]:
    scheme = ini_value(state_home / ".config/kdeglobals", "General", "ColorScheme")
    if not scheme:
        scheme = ini_value(rooted(root, "/etc/skel/.config/kdeglobals"), "General", "ColorScheme")
    animation = ini_value(state_home / ".config/kdeglobals", "KDE", "AnimationDurationFactor")
    reduced_motion = animation in {"0", "0.0", "0.00"}
    channel_text = safe_read(rooted(root, "/etc/dagric-channel"), 128).strip().lower()
    channel = channel_text if channel_text in {"stable", "preview", "lab"} else "stable"
    value = {
        "dagric_blueprint": BLUEPRINT_SCHEMA,
        "system": {
            "channel": channel,
            "appearance": appearance_name(scheme),
            "power_profile": "automatic",
        },
        "applications": {
            "debian_packages": parse_installed_packages(root),
            "flatpaks": flatpak_applications(root, state_home),
        },
        "hardware_policies": {"graphics": "automatic", "storage": "adaptive", "memory": "balanced"},
        "user_preferences": {"reduced_motion": reduced_motion},
        "omitted": list(BLUEPRINT_OMISSIONS),
    }
    return value


def validate_blueprint(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["Blueprint must be a JSON object"]
    unknown = set(value) - ALLOWED_BLUEPRINT_TOP
    if unknown:
        errors.append("unknown top-level fields: " + ", ".join(sorted(unknown)))
    if value.get("dagric_blueprint") != BLUEPRINT_SCHEMA:
        errors.append("unsupported dagric_blueprint schema")
    system = value.get("system")
    if not isinstance(system, dict):
        errors.append("system must be an object")
    else:
        allowed_system = {"channel", "appearance", "power_profile"}
        if set(system) - allowed_system:
            errors.append("system contains unsupported fields")
        if system.get("channel") not in {"stable", "preview", "lab"}:
            errors.append("invalid channel")
        if system.get("appearance") not in {"obsidian", "frost", "high-contrast", "custom"}:
            errors.append("invalid appearance")
        if system.get("power_profile") not in {"automatic", "quiet", "balanced", "maximum"}:
            errors.append("invalid power profile")
    applications = value.get("applications")
    if not isinstance(applications, dict) or set(applications) - {"debian_packages", "flatpaks"}:
        errors.append("applications must contain only debian_packages and flatpaks")
    elif isinstance(applications, dict):
        patterns = {
            "debian_packages": re.compile(r"[a-z0-9][a-z0-9+.-]{0,127}"),
            "flatpaks": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,159}"),
        }
        for key, pattern in patterns.items():
            rows = applications.get(key)
            if not isinstance(rows, list) or len(rows) > 20_000 or any(not isinstance(item, str) or not pattern.fullmatch(item) for item in rows):
                errors.append(f"invalid {key} list")
    hardware = value.get("hardware_policies")
    expected_hardware = {"graphics", "storage", "memory"}
    if not isinstance(hardware, dict) or set(hardware) != expected_hardware:
        errors.append("hardware_policies must contain exactly graphics, storage and memory")
    else:
        choices = {
            "graphics": {"automatic", "compatibility", "performance"},
            "storage": {"adaptive", "conservative"},
            "memory": {"balanced", "low-memory"},
        }
        for key, allowed in choices.items():
            if hardware.get(key) not in allowed:
                errors.append(f"invalid {key} hardware policy")
    preferences = value.get("user_preferences")
    if not isinstance(preferences, dict) or set(preferences) != {"reduced_motion"}:
        errors.append("user_preferences must contain exactly reduced_motion")
    elif not isinstance(preferences.get("reduced_motion"), bool):
        errors.append("reduced_motion must be boolean")
    omitted = value.get("omitted")
    if omitted != BLUEPRINT_OMISSIONS:
        errors.append("omitted safety boundary is missing or changed")
    errors.extend(privacy_errors(value))
    return errors


def blueprint_plan(current: dict[str, Any], wanted: dict[str, Any]) -> dict[str, Any]:
    errors = validate_blueprint(wanted)
    if errors:
        raise ValueError("; ".join(errors))
    current_apps = current["applications"]
    wanted_apps = wanted["applications"]
    return {
        "mode": "dry-run only",
        "system_changes": {
            key: {"current": current["system"].get(key), "wanted": wanted["system"].get(key)}
            for key in sorted(wanted["system"])
            if current["system"].get(key) != wanted["system"].get(key)
        },
        "applications_to_add": {
            key: sorted(set(wanted_apps[key]) - set(current_apps[key]))
            for key in ("debian_packages", "flatpaks")
        },
        "applications_not_in_blueprint": {
            key: sorted(set(current_apps[key]) - set(wanted_apps[key]))
            for key in ("debian_packages", "flatpaks")
        },
        "destructive_actions": [],
        "apply_available": False,
        "reason": "Dagric will not apply Blueprints until transactional system roots and recovery gates pass",
    }


# --------------------------------------------------------------- Black Box
def blackbox_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DAGRIC_BLACKBOX_STATE_DIR", "/var/lib/dagric/blackbox"))


def parse_pressure(root: pathlib.Path, resource: str) -> dict[str, float] | None:
    text = safe_read(rooted(root, f"/proc/pressure/{resource}"), 16_000)
    for line in text.splitlines():
        if not line.startswith("some "):
            continue
        values: dict[str, float] = {}
        for item in line.split()[1:]:
            if "=" not in item:
                continue
            key, raw = item.split("=", 1)
            if key in {"avg10", "avg60", "avg300"}:
                try:
                    values[key] = round(float(raw), 3)
                except ValueError:
                    return None
        return values if "avg10" in values else None
    return None


def pressure_event(root: pathlib.Path, timestamp: float | None = None) -> dict[str, Any]:
    pressure = {name: parse_pressure(root, name) for name in ("cpu", "memory", "io")}
    pressure = {key: value for key, value in pressure.items() if value is not None}
    uptime_text = safe_read(rooted(root, "/proc/uptime"), 256).split()
    try:
        uptime = round(float(uptime_text[0]), 1)
    except (IndexError, ValueError):
        uptime = 0.0
    return {
        "schema": BLACKBOX_SCHEMA,
        "type": "performance_summary",
        "at": utc_now(timestamp),
        "retention": "7-days",
        "pressure": pressure,
        "uptime_seconds": uptime,
    }


def validate_event(event: Any) -> list[str]:
    if not isinstance(event, dict):
        return ["event is not an object"]
    common = {"schema", "type", "at", "retention"}
    event_type = event.get("type")
    allowed = set(common)
    if event_type == "performance_summary":
        allowed |= {"pressure", "uptime_seconds"}
    elif event_type in ALLOWED_MARKS:
        pass
    else:
        return ["event type is not approved"]
    errors = []
    if set(event) - allowed:
        errors.append("event contains unapproved fields")
    if event.get("schema") != BLACKBOX_SCHEMA:
        errors.append("unsupported event schema")
    if not isinstance(event.get("at"), str) or len(event["at"]) > 32:
        errors.append("invalid timestamp")
    elif parse_time(event["at"]) <= 0:
        errors.append("unparseable timestamp")
    expected_retention = "7-days" if event_type == "performance_summary" else "15-minutes"
    if event.get("retention") != expected_retention:
        errors.append("invalid retention class")
    if event_type == "performance_summary":
        pressure = event.get("pressure")
        if not isinstance(pressure, dict) or set(pressure) - {"cpu", "memory", "io"}:
            errors.append("invalid pressure summary")
        else:
            for resource, samples in pressure.items():
                if not isinstance(samples, dict) or "avg10" not in samples or set(samples) - {"avg10", "avg60", "avg300"}:
                    errors.append(f"invalid {resource} pressure fields")
                    continue
                if any(not isinstance(sample, (int, float)) or isinstance(sample, bool) or sample < 0 or sample > 100 for sample in samples.values()):
                    errors.append(f"invalid {resource} pressure value")
        uptime = event.get("uptime_seconds")
        if not isinstance(uptime, (int, float)) or isinstance(uptime, bool) or uptime < 0:
            errors.append("invalid uptime")
    errors.extend(privacy_errors(event))
    return errors


def parse_time(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def prune_events(events: list[dict[str, Any]], timestamp: float | None = None) -> list[dict[str, Any]]:
    timestamp = time.time() if timestamp is None else timestamp
    kept: list[dict[str, Any]] = []
    for event in events:
        if validate_event(event):
            continue
        age = max(0.0, timestamp - parse_time(event["at"]))
        retention = SUMMARY_RETENTION_SECONDS if event["type"] == "performance_summary" else DETAIL_RETENTION_SECONDS
        if age <= retention:
            kept.append(event)
    return kept[-BLACKBOX_MAX_EVENTS:]


@contextlib.contextmanager
def state_lock(directory: pathlib.Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = directory / "write.lock"
    with lock.open("a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_events(directory: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in safe_read(directory / "events.jsonl", 2_000_000).splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def append_event(event: dict[str, Any], directory: pathlib.Path | None = None, timestamp: float | None = None) -> int:
    errors = validate_event(event)
    if errors:
        raise ValueError("; ".join(errors))
    directory = directory or blackbox_dir()
    with state_lock(directory):
        events = prune_events(load_events(directory) + [event], timestamp)
        descriptor, temporary = tempfile.mkstemp(prefix=".events.", dir=directory, text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                for row in events:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, directory / "events.jsonl")
        finally:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return len(events)


def mark_event(name: str, timestamp: float | None = None) -> dict[str, Any]:
    if name not in ALLOWED_MARKS:
        raise ValueError("mark is not approved")
    return {"schema": BLACKBOX_SCHEMA, "type": name, "at": utc_now(timestamp), "retention": "15-minutes"}


def blackbox_status(directory: pathlib.Path | None = None) -> dict[str, Any]:
    directory = directory or blackbox_dir()
    events = prune_events(load_events(directory))
    newest = events[-1]["at"] if events else "never"
    return {
        "schema": BLACKBOX_SCHEMA,
        "events": len(events),
        "newest": newest,
        "maximum_events": BLACKBOX_MAX_EVENTS,
        "detailed_retention_seconds": DETAIL_RETENTION_SECONDS,
        "summary_retention_seconds": SUMMARY_RETENTION_SECONDS,
        "network_upload": False,
        "content_collection": False,
    }


# ------------------------------------------------------------- Life Support
def root_mount(root: pathlib.Path) -> dict[str, Any]:
    for line in safe_read(rooted(root, "/proc/mounts"), 512_000).splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/":
            options = fields[3].split(",")
            return {"filesystem": fields[2][:32], "read_only": "ro" in options}
    return {"filesystem": "unknown", "read_only": False}


def assess_life_support(root: pathlib.Path, free_percent: float | None = None, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    mount = root_mount(root)
    if mount["read_only"]:
        findings.append({"severity": "critical", "code": "root-read-only", "message": "The root filesystem is mounted read-only."})
    if free_percent is None:
        try:
            stats = os.statvfs(root)
            free_percent = 100.0 * stats.f_bavail / max(1, stats.f_blocks)
        except OSError:
            free_percent = 100.0
    if free_percent < 2:
        findings.append({"severity": "critical", "code": "storage-exhausted", "message": "Less than 2% writable storage remains."})
    elif free_percent < 8:
        findings.append({"severity": "caution", "code": "storage-low", "message": "Less than 8% writable storage remains."})
    if events is None:
        events = prune_events(load_events(blackbox_dir()))
    summaries = [event for event in events if event.get("type") == "performance_summary"][-3:]
    for resource in ("memory", "io", "cpu"):
        values = [float(event.get("pressure", {}).get(resource, {}).get("avg10", 0)) for event in summaries]
        peak = max(values, default=0.0)
        if peak >= 20:
            findings.append({"severity": "critical", "code": f"{resource}-pressure-critical", "message": f"Recent {resource} pressure reached {peak:.1f}%."})
        elif peak >= 5:
            findings.append({"severity": "caution", "code": f"{resource}-pressure", "message": f"Recent {resource} pressure reached {peak:.1f}%."})
    state = "critical" if any(item["severity"] == "critical" for item in findings) else ("caution" if findings else "normal")
    actions = []
    if state == "critical":
        actions = [
            "Pause nonessential writes and experiments",
            "Open the backup tool and protect personal files",
            "Use Dagric Rewind or recovery before attempting repairs",
        ]
    elif state == "caution":
        actions = ["Review storage and pressure before starting updates or games"]
    return {
        "state": state,
        "findings": findings,
        "recommended_actions": actions,
        "automatic_changes_applied": False,
        "limitations": "SMART, temperature, battery, GPU reset, memory-error and failed-boot triggers require privileged hardware integration and physical validation",
    }


# --------------------------------------------------------------------- CLIs
def load_json_file(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read Blueprint: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Blueprint must be a JSON object")
    return value


def blueprint_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Dagric Blueprint safe exporter and planner")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    parser.add_argument("--state-home", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("show")
    export = sub.add_parser("export")
    export.add_argument("destination", type=pathlib.Path)
    audit = sub.add_parser("audit")
    audit.add_argument("blueprint", type=pathlib.Path)
    plan = sub.add_parser("plan")
    plan.add_argument("blueprint", type=pathlib.Path)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    state_home = pathlib.Path(args.state_home) if args.state_home else pathlib.Path.home()
    current = build_blueprint(root, state_home)
    command = args.command or "show"
    try:
        if command == "audit":
            errors = validate_blueprint(load_json_file(args.blueprint))
            if errors:
                print("dagric-blueprint: " + "; ".join(errors), file=os.sys.stderr)
                return 1
            print("dagric-blueprint: schema and privacy audit passed")
        elif command == "plan":
            print(json.dumps(blueprint_plan(current, load_json_file(args.blueprint)), indent=2, sort_keys=True))
        elif command == "export":
            errors = validate_blueprint(current)
            if errors:
                raise ValueError("; ".join(errors))
            write_json_exclusive(args.destination, current)
            print(f"Dagric Blueprint created locally: {args.destination}")
        else:
            print(json.dumps(current, indent=2, sort_keys=True))
    except ValueError as exc:
        print(f"dagric-blueprint: {exc}", file=os.sys.stderr)
        return 2
    return 0


def blackbox_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Dagric private circular Black Box")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    parser.add_argument("--state-dir", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("sample")
    sub.add_parser("status")
    mark = sub.add_parser("mark")
    mark.add_argument("name", choices=sorted(ALLOWED_MARKS))
    args = parser.parse_args(argv)
    directory = pathlib.Path(args.state_dir) if args.state_dir else blackbox_dir()
    try:
        if args.command == "status":
            print(json.dumps(blackbox_status(directory), indent=2, sort_keys=True))
        elif args.command == "mark":
            append_event(mark_event(args.name), directory)
        else:
            append_event(pressure_event(pathlib.Path(args.root)), directory)
    except (OSError, ValueError) as exc:
        print(f"dagric-blackbox: {exc}", file=os.sys.stderr)
        return 1
    return 0


def life_support_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Dagric read-only Life Support assessment")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = assess_life_support(pathlib.Path(args.root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if report["state"] == "critical" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dagric foundation tools")
    parser.add_argument("component", choices=("blueprint", "blackbox", "life-support"))
    args, rest = parser.parse_known_args(argv)
    return {"blueprint": blueprint_main, "blackbox": blackbox_main, "life-support": life_support_main}[args.component](rest)


if __name__ == "__main__":
    raise SystemExit(main())
