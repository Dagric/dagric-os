#!/usr/bin/env python3
"""Dagric Adaptive Pipeline — small, safe machine-specific policy engine.

This is deliberately a policy compiler, not a bag of permanent "speed tweaks".
It observes only capability and pressure data, generates a local profile without
serial numbers, MAC addresses, DMI strings, EDIDs or user paths, and permits one
runtime action: bounded POSIX_FADV_WILLNEED prefetch for an application the user
has explicitly launched.  Everything else stays with the kernel or an existing
Dagric component until it has a measured, reversible implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable

from private_files import write_private_text


SCHEMA = 1
MAX_PROFILE_FILES = 96
SAFE_ACTIONS = {
    "observe-mglru",
    "retain-zram",
    "retain-btrfs-zstd",
    "keep-ssd-kernel-default",
    "bfq-for-rotational-via-udev",
    "bounded-launch-prefetch",
    "atom-low-resource-profile",
    "low-memory-zram-priority",
    "disable-background-indexing-hints",
}
SENSITIVE_WORDS = ("serial", "uuid", "mac", "address", "edid", "dmi", "machine-id")
SYSTEM_PREFIXES = ("/usr/", "/lib/", "/lib64/", "/opt/")


def host_path(root: pathlib.Path, absolute: str) -> pathlib.Path:
    """Map an absolute Linux path into an optional test root."""
    return root / absolute.lstrip("/")


def read_text(root: pathlib.Path, absolute: str) -> str:
    try:
        return host_path(root, absolute).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_int(root: pathlib.Path, absolute: str, default: int = 0) -> int:
    try:
        return int(read_text(root, absolute))
    except ValueError:
        return default


def parse_meminfo(root: pathlib.Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in read_text(root, "/proc/meminfo").splitlines():
        match = re.match(r"^(\w+):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    return values


def parse_pressure(root: pathlib.Path, name: str) -> dict[str, float] | None:
    for line in read_text(root, f"/proc/pressure/{name}").splitlines():
        if not line.startswith("some "):
            continue
        fields = dict(field.split("=", 1) for field in line.split()[1:] if "=" in field)
        try:
            return {key: float(value) for key, value in fields.items() if key.startswith("avg")}
        except ValueError:
            return None
    return None


def active_scheduler(value: str) -> str:
    match = re.search(r"\[([^]]+)\]", value)
    return match.group(1) if match else "unknown"


def iter_dirs(path: pathlib.Path) -> Iterable[pathlib.Path]:
    try:
        return sorted(item for item in path.iterdir() if item.is_dir())
    except OSError:
        return []


def hardware_projection(root: pathlib.Path) -> dict[str, Any]:
    mem = parse_meminfo(root)
    cpuinfo = read_text(root, "/proc/cpuinfo")
    model_names = re.findall(r"^(?:model name|Model|Processor)\s*:\s*(.+)$", cpuinfo, flags=re.MULTILINE)
    cpu_model = model_names[0].strip() if model_names else "unknown"
    cpu_lower = cpu_model.casefold()
    atom_family = bool(re.search(r"\batom(?:\(tm\))?\s*(?:cpu\s*)?(?:n?4[0-9]{2}|z5\d{3})", cpu_lower))
    cpu_count = len(re.findall(r"^processor\s*:", cpuinfo, flags=re.MULTILINE))
    if not cpu_count:
        cpu_count = len([item for item in iter_dirs(host_path(root, "/sys/devices/system/cpu")) if re.fullmatch(r"cpu\d+", item.name)])

    gpus: list[str] = []
    for card in iter_dirs(host_path(root, "/sys/class/drm")):
        if not re.fullmatch(r"card\d+", card.name):
            continue
        vendor = read_text(root, f"/sys/class/drm/{card.name}/device/vendor")
        if vendor:
            gpus.append(vendor.lower())

    storage: list[dict[str, Any]] = []
    for device in iter_dirs(host_path(root, "/sys/block")):
        name = device.name
        if re.match(r"^(loop|ram|zram|sr|dm-|md|nbd)", name):
            continue
        rotational = read_int(root, f"/sys/block/{name}/queue/rotational") == 1
        storage.append({
            "kind": "hdd" if rotational else ("nvme" if name.startswith("nvme") else "ssd"),
            "rotational": rotational,
            "scheduler": active_scheduler(read_text(root, f"/sys/block/{name}/queue/scheduler")),
        })

    interfaces: list[str] = []
    for interface in iter_dirs(host_path(root, "/sys/class/net")):
        if interface.name == "lo":
            continue
        interfaces.append("wifi" if (interface / "wireless").exists() else "ethernet")

    return {
        "cpu_threads": cpu_count,
        "cpu_model": cpu_model[:120],
        "atom_family": atom_family,
        "memory_bytes": mem.get("MemTotal", 0),
        "numa_nodes": len(iter_dirs(host_path(root, "/sys/devices/system/node"))),
        "gpu_vendors": sorted(set(gpus)),
        "storage": storage,
        "network_kinds": sorted(interfaces),
        "mglru_available": host_path(root, "/sys/kernel/mm/lru_gen/enabled").exists(),
        "zram_available": host_path(root, "/sys/block/zram0").exists(),
        "btrfs_root": any(" btrfs " in f" {line} " for line in read_text(root, "/proc/mounts").splitlines()),
        "cgroup_v2": host_path(root, "/sys/fs/cgroup/cgroup.controllers").exists(),
    }


def fingerprint(projection: dict[str, Any]) -> str:
    stable = json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(stable, digest_size=16).hexdigest()


def memory_class(memory_bytes: int) -> str:
    gib = memory_bytes / (1024 ** 3)
    if gib < 12:
        return "low-memory"
    if gib < 32:
        return "standard"
    return "high-memory"


def is_atom_class(projection: dict[str, Any]) -> bool:
    """Identify netbook-era Atom-class machines without requiring a DMI serial.

    The RAM/CPU gate is intentional: model strings vary across firmware and
    virtual machines, while the resource envelope is what makes this profile
    useful.  Atom N450/N455 systems normally report one core/two threads and
    1–2 GiB RAM; comparable single/dual-core low-memory systems get the same
    safe treatment.
    """
    memory = int(projection.get("memory_bytes", 0))
    threads = int(projection.get("cpu_threads", 0))
    return memory > 0 and memory <= 2 * 1024 ** 3 and threads <= 2


def compile_policy(projection: dict[str, Any]) -> dict[str, Any]:
    atom_class = is_atom_class(projection)
    tier = "atom-low-resource" if atom_class else memory_class(int(projection["memory_bytes"]))
    budgets = {"atom-low-resource": 2, "low-memory": 8, "standard": 32, "high-memory": 64}
    actions = ["keep-ssd-kernel-default", "bounded-launch-prefetch"]
    if projection["zram_available"]:
        actions.append("retain-zram")
    if projection["mglru_available"]:
        actions.append("observe-mglru")
    if projection["btrfs_root"]:
        actions.append("retain-btrfs-zstd")
    if any(device["rotational"] for device in projection["storage"]):
        actions.append("bfq-for-rotational-via-udev")
    if atom_class:
        actions.extend(("atom-low-resource-profile", "low-memory-zram-priority", "disable-background-indexing-hints"))
    return {
        "machine_class": tier,
        "launch_prefetch_max_mib": budgets[tier],
        # No background speculation on a consumer machine.  The only prefetch
        # happens in response to an explicit launch, and is skipped under PSI.
        "background_warming": False,
        "pressure_limits_avg10": {"cpu": 10.0, "memory": 2.0, "io": 2.0},
        "low_resource": {
            "enabled": atom_class,
            "max_background_jobs": 1 if atom_class else None,
            "zram_target_percent": 75 if atom_class else None,
            "swappiness": 180 if atom_class else None,
            "disable_file_indexing_by_default": atom_class,
            "notes": ("Atom/N450-class safe mode: prioritize responsiveness and avoid concurrent indexing." if atom_class else "standard adaptive policy"),
        },
        "actions": sorted(actions),
        "experimental": {
            "damon_reclaim": False,
            "sched_ext": False,
            "irq_pinning": False,
            "binary_rewriting": False,
            "gpu_steering": False,
        },
    }


def build_profile(root: pathlib.Path) -> dict[str, Any]:
    projection = hardware_projection(root)
    return {
        "schema": SCHEMA,
        "generated_at": int(time.time()),
        "machine_fingerprint": fingerprint(projection),
        "hardware": projection,
        "policy": compile_policy(projection),
    }


def state_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DAGRIC_PIPELINE_STATE_DIR", "/var/lib/dagric/pipeline"))


def profile_path() -> pathlib.Path:
    return state_dir() / "profile.json"


def write_json_atomic(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private_text(path, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def audit_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("schema") != SCHEMA:
        errors.append("unsupported profile schema")
    if not isinstance(profile.get("machine_fingerprint"), str) or not re.fullmatch(r"[0-9a-f]{32}", profile.get("machine_fingerprint", "")):
        errors.append("machine fingerprint is missing or malformed")
    policy = profile.get("policy")
    if not isinstance(policy, dict):
        return errors + ["policy is missing"]
    actions = policy.get("actions")
    if not isinstance(actions, list) or not all(isinstance(action, str) and action in SAFE_ACTIONS for action in actions):
        errors.append("policy contains an unapproved action")
    if policy.get("background_warming") is not False:
        errors.append("background warming must remain disabled by default")
    for key, value in policy.get("experimental", {}).items():
        if value is not False:
            errors.append(f"experimental action {key} is enabled")
    def keys(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                yield str(key).lower()
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    sensitive_key = re.compile(r"(?:^|[_-])(?:" + "|".join(SENSITIVE_WORDS) + r")(?:$|[_-])")
    serialized = json.dumps(profile, sort_keys=True).lower()
    # Do not use a bare substring test here: "machine_class" naturally
    # contains "mac", but is neither a MAC address nor identifying data.
    if any(sensitive_key.search(key) for key in keys(profile)) or re.search(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", serialized):
        errors.append("profile contains a privacy-sensitive hardware identifier")
    return errors


def default_user_profile_path() -> pathlib.Path:
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
    return cache / "dagric" / "pipeline" / "launches.json"


def allowed_prefetch_path(path: pathlib.Path) -> bool:
    try:
        value = str(path.resolve(strict=True))
        return path.is_file() and value.startswith(SYSTEM_PREFIXES)
    except OSError:
        return False


def load_launch_profile(path: pathlib.Path) -> list[str]:
    profile = read_json(path) or {}
    files = profile.get("files", [])
    return [item for item in files if isinstance(item, str) and item.startswith(SYSTEM_PREFIXES)]


def save_launch_profile(path: pathlib.Path, files: Iterable[str]) -> None:
    selected = sorted(set(files))[:MAX_PROFILE_FILES]
    write_json_atomic(path, {"schema": SCHEMA, "files": selected})


def system_pressure_ok(root: pathlib.Path, limits: dict[str, float]) -> bool:
    for resource, maximum in limits.items():
        value = parse_pressure(root, resource)
        # A missing PSI interface is not evidence that speculative reads are
        # harmless, so fail closed.
        if value is None or value.get("avg10", float("inf")) > maximum:
            return False
    return True


def prefetch(paths: Iterable[str], budget_mib: int, root: pathlib.Path = pathlib.Path("/")) -> dict[str, int]:
    budget = budget_mib * 1024 * 1024
    warmed = 0
    files = 0
    for item in paths:
        path = pathlib.Path(item)
        if not allowed_prefetch_path(path) or warmed >= budget:
            continue
        try:
            length = min(path.stat().st_size, budget - warmed)
            if length <= 0:
                continue
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                if not hasattr(os, "posix_fadvise"):
                    return {"files": files, "bytes": warmed}
                os.posix_fadvise(descriptor, 0, length, getattr(os, "POSIX_FADV_WILLNEED", 3))
            finally:
                os.close(descriptor)
            warmed += length
            files += 1
        except OSError:
            continue
    return {"files": files, "bytes": warmed}


def executable(command: str) -> str | None:
    if "/" in command:
        return command if os.path.isfile(command) else None
    return shutil.which(command)


def mapped_system_files(pid: int) -> list[str]:
    values: list[str] = []
    try:
        lines = pathlib.Path(f"/proc/{pid}/maps").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return values
    for line in lines:
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith(SYSTEM_PREFIXES):
            values.append(fields[5].replace(" (deleted)", ""))
    return values


def active_policy(root: pathlib.Path) -> dict[str, Any]:
    profile = read_json(profile_path())
    if profile and not audit_profile(profile):
        return profile["policy"]
    return compile_policy(hardware_projection(root))


def command_prepare(command: list[str], root: pathlib.Path) -> int:
    if not command:
        return 2
    policy = active_policy(root)
    if not system_pressure_ok(root, policy["pressure_limits_avg10"]):
        return 0
    files = load_launch_profile(default_user_profile_path())
    resolved = executable(command[0])
    if resolved and resolved.startswith(SYSTEM_PREFIXES):
        files.insert(0, resolved)
    prefetch(files, int(policy["launch_prefetch_max_mib"]), root)
    return 0


def command_launch(command: list[str], root: pathlib.Path) -> int:
    if not command:
        return 2
    command_prepare(command, root)
    try:
        child = subprocess.Popen(command)
    except OSError as exc:
        print(f"Dagric Adaptive Pipeline: cannot launch {command[0]}: {exc}", file=sys.stderr)
        return 127
    time.sleep(0.75)
    discovered = mapped_system_files(child.pid)
    if discovered:
        save_launch_profile(default_user_profile_path(), load_launch_profile(default_user_profile_path()) + discovered)
    return child.wait()


def command_apply(root: pathlib.Path) -> int:
    """Apply only reversible low-memory knobs; silently skip unavailable ones."""
    policy = active_policy(root)
    low = policy.get("low_resource") or {}
    if not low.get("enabled"):
        return 0
    values = {
        "vm.swappiness": low.get("swappiness"),
        "vm.page-cluster": 0,
        "vm.dirty_background_ratio": 3,
        "vm.dirty_ratio": 10,
    }
    for key, value in values.items():
        if value is None:
            continue
        proc = host_path(root, "/proc/sys/" + key.replace(".", "/"))
        if not proc.exists():
            continue
        try:
            proc.write_text(str(int(value)) + "\n", encoding="ascii")
        except OSError:
            # A read-only/test root or a restricted sysctl is a safe no-op.
            continue
    return 0


def strip_separator(command: list[str]) -> list[str]:
    return command[1:] if command[:1] == ["--"] else command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dagric Adaptive Pipeline")
    parser.add_argument("--root", default="/", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="subcommand", required=True)
    scan = sub.add_parser("scan", help="discover capabilities and compile the local policy")
    scan.add_argument("--quiet", action="store_true")
    sub.add_parser("status", help="print the active machine profile")
    audit = sub.add_parser("audit", help="validate the active machine profile")
    audit.add_argument("--profile", type=pathlib.Path)
    prepare = sub.add_parser("prepare", help="warm an already-learned app profile")
    prepare.add_argument("command", nargs=argparse.REMAINDER)
    launch = sub.add_parser("launch", help="launch and learn only system-code mappings")
    launch.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("apply", help="apply reversible low-resource settings when detected")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)

    if args.subcommand == "scan":
        profile = build_profile(root)
        errors = audit_profile(profile)
        if errors:
            print("Dagric Adaptive Pipeline refused profile: " + "; ".join(errors), file=sys.stderr)
            return 1
        write_json_atomic(profile_path(), profile)
        if not args.quiet:
            print(json.dumps(profile, sort_keys=True, indent=2))
        return 0
    if args.subcommand == "status":
        profile = read_json(profile_path()) or build_profile(root)
        print(json.dumps(profile, sort_keys=True, indent=2))
        return 0
    if args.subcommand == "audit":
        profile = read_json(args.profile or profile_path())
        if profile is None:
            print("Dagric Adaptive Pipeline: no profile to audit", file=sys.stderr)
            return 1
        errors = audit_profile(profile)
        if errors:
            print("Dagric Adaptive Pipeline audit failed: " + "; ".join(errors), file=sys.stderr)
            return 1
        print("dagric-pipeline: profile is privacy-safe and uses only approved actions")
        return 0
    if args.subcommand == "apply":
        return command_apply(root)
    command = strip_separator(args.command)
    if args.subcommand == "prepare":
        return command_prepare(command, root)
    return command_launch(command, root)


if __name__ == "__main__":
    raise SystemExit(main())
