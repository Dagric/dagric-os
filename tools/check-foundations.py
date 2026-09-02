#!/usr/bin/env python3
"""Source contract for Dagric's safe dependability foundations."""

from __future__ import annotations

import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
INCLUDE = ROOT / "config/includes.chroot"


def require(path: pathlib.Path, *tokens: str) -> list[str]:
    if not path.is_file():
        return [f"missing {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    return [f"{path.relative_to(ROOT)} lacks {token!r}" for token in tokens if token not in text]


def main() -> int:
    errors: list[str] = []
    foundations = INCLUDE / "usr/lib/dagric/foundations.py"
    errors += require(foundations, "BLUEPRINT_SCHEMA", "BLACKBOX_MAX_EVENTS", "apply_available", "automatic_changes_applied")
    for command in ("dagric-blueprint", "dagric-blackbox", "dagric-life-support"):
        errors += require(INCLUDE / f"usr/bin/{command}", "foundations.py")
    blackbox_service = INCLUDE / "etc/systemd/system/dagric-blackbox.service"
    errors += require(blackbox_service, "ProtectSystem=strict", "ReadWritePaths=/var/lib/dagric/blackbox", "MemoryMax=64M", "CPUQuota=5%", "IOSchedulingClass=idle")
    errors += require(INCLUDE / "etc/systemd/system/dagric-blackbox.timer", "OnUnitActiveSec=5m", "Persistent=false")
    errors += require(INCLUDE / "etc/systemd/system/dagric-pipeline.service", "MemoryMax=96M", "CPUQuota=10%", "IOSchedulingClass=idle")
    errors += require(ROOT / "packages/dagric-tools/DEBIAN/postinst", "install -d -m 0700 /var/lib/dagric/blackbox", "dagric-blackbox.timer")

    budget_path = INCLUDE / "usr/share/dagric/budgets/services.json"
    try:
        budget = json.loads(budget_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"invalid service budget: {exc}")
        budget = {}
    services = budget.get("services", {}) if isinstance(budget, dict) else {}
    declared = {path.name for path in (INCLUDE / "etc/systemd/system").glob("dagric-*.service")}
    if set(services) != declared:
        errors.append(f"service budget coverage differs: declared={sorted(declared)} budgeted={sorted(services)}")
    for name, row in services.items():
        if not isinstance(row, dict):
            errors.append(f"{name}: budget is not an object")
            continue
        if row.get("network") != "none":
            errors.append(f"{name}: background network is not forbidden")
        for field in ("cpu_percent_max", "memory_mib_max", "wakeups_per_minute_max"):
            value = row.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                errors.append(f"{name}: invalid {field}")
        if row.get("measured") is not False or row.get("decision") != "provisional":
            errors.append(f"{name}: unmeasured budget must remain explicitly provisional")

    if errors:
        for error in errors:
            print(f"foundations-check: {error}", file=sys.stderr)
        return 1
    print(f"foundations-check: Blueprint/Black Box/Life Support contracts passed; {len(services)} service budgets covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
