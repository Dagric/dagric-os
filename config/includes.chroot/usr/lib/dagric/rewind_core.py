#!/usr/bin/python3
"""Pure data helpers for Dagric Rewind.

This module deliberately knows nothing about privileges or the desktop.  The
privileged controller imports it, and the unit tests exercise it without
needing Btrfs, Snapper, or root.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable


NOISE_PREFIXES = (
    "/run/",
    "/tmp/",
    "/var/cache/",
    "/var/log/",
    "/var/tmp/",
    # Rewind's own in-progress marker is created after the pre snapshot.  It is
    # implementation bookkeeping, not a change the owner made.
    "/var/lib/dagric/rewind/",
    # timekpr refreshes these scratch records in the background.  Showing them
    # makes an otherwise empty receipt look like a parental-control change.
    "/var/lib/timekpr/work/",
    # grub-btrfs regenerates this index whenever a snapshot is created.  It is
    # a consequence of making the checkpoint, not part of the user's action.
    "/boot/grub/grub-btrfs.cfg",
)

CATEGORIES = (
    ("Software", ("/usr/", "/opt/", "/var/lib/dpkg/", "/var/lib/apt/", "/var/lib/flatpak/")),
    ("Settings", ("/etc/",)),
    ("Boot", ("/boot/",)),
    ("System state", ("/var/",)),
)

PRESETS = {
    "software": {
        "label": "Software install",
        "prompt": "Install or remove an application, then finish the session to review it.",
    },
    "settings": {
        "label": "Settings change",
        "prompt": "Change system settings, then finish the session to review them.",
    },
    "driver": {
        "label": "Driver update",
        "prompt": "Update a driver, then finish the session before restarting.",
    },
    "experiment": {
        "label": "Try something",
        "prompt": "Experiment freely, then finish the session to see what changed.",
    },
    "known-good": {
        "label": "Known-good checkpoint",
        "prompt": "Keep a named checkpoint before a change you may want to reverse.",
    },
}


def utc_now() -> str:
    """Return an ISO 8601 timestamp with a stable UTC suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _looks_like_snapshot(value: Any) -> bool:
    return isinstance(value, dict) and "number" in value and (
        "date" in value or "type" in value or "description" in value
    )


def normalize_snapper_json(value: Any) -> list[dict[str, Any]]:
    """Extract snapshot rows from the JSON layouts used by Snapper releases.

    Snapper has emitted both a top-level array and nested objects such as
    ``{"root": {"snapshots": [...]}}``.  Walking the structure makes Dagric
    tolerant of those presentation differences while still returning only
    dictionaries that look like actual snapshots.
    """
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if _looks_like_snapshot(node):
            found.append(node)
            return
        if isinstance(node, dict):
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    unique: dict[int, dict[str, Any]] = {}
    for row in found:
        try:
            number = int(row.get("number", -1))
        except (TypeError, ValueError):
            continue
        if number < 0:
            continue
        normalized = dict(row)
        normalized["number"] = number
        unique[number] = normalized
    return [unique[number] for number in sorted(unique)]


def category_for(path: str) -> str:
    normalized = "/" + path.lstrip("/")
    for label, prefixes in CATEGORIES:
        if any(normalized == prefix[:-1] or normalized.startswith(prefix) for prefix in prefixes):
            return label
    return "Other"


def _kind_from_status(status: str) -> str:
    # Snapper's first column is a compact change mask.  '+' and '-' are the
    # unambiguous creation/deletion markers; every other non-dot flag means the
    # path was modified (content, type, permissions, owner, xattrs, or ACL).
    if "+" in status:
        return "added"
    if "-" in status:
        return "deleted"
    return "modified"


def parse_snapper_status(lines: Iterable[str], path_limit: int = 80) -> dict[str, Any]:
    """Summarize ``snapper status PRE..POST`` without exposing file contents."""
    counts: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    paths: list[dict[str, str]] = []
    ignored = 0

    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        status, path = parts[0], parts[1].strip()
        if not path:
            continue
        normalized = "/" + path.lstrip("/")
        if any(normalized == prefix[:-1] or normalized.startswith(prefix) for prefix in NOISE_PREFIXES):
            ignored += 1
            continue
        kind = _kind_from_status(status)
        category = category_for(normalized)
        counts[kind] += 1
        categories[category] += 1
        if len(paths) < path_limit:
            paths.append({"path": normalized, "kind": kind, "category": category})

    total = sum(counts.values())
    return {
        "total": total,
        "added": counts["added"],
        "modified": counts["modified"],
        "deleted": counts["deleted"],
        "ignoredNoise": ignored,
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        ],
        "paths": paths,
        "truncated": total > len(paths),
    }


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def public_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields the unprivileged UI needs."""
    number = safe_int(row.get("number"))
    pre_number = safe_int(row.get("pre-number", row.get("pre_number")))
    return {
        "number": number,
        "type": str(row.get("type", "single"))[:20],
        "date": str(row.get("date", ""))[:64],
        "description": str(row.get("description", "System checkpoint"))[:160],
        "preNumber": pre_number,
        "readOnly": bool(row.get("read-only", row.get("read_only", True))),
    }


def automatic_apt_sessions(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn Dagric's existing apt pre/post snapshots into Rewind receipts.

    Only the exact descriptions written by ``dagric-snapshot-setup`` qualify.
    An arbitrary pair of snapshots must never become reviewable merely because
    an unprivileged window supplied two numbers.
    """
    snapshots = list(rows)
    by_number = {safe_int(row.get("number")): row for row in snapshots}
    sessions: list[dict[str, Any]] = []
    for post in snapshots:
        if str(post.get("type", "")) != "post" or str(post.get("description", "")) != "apt (post)":
            continue
        pre_number = safe_int(post.get("pre-number", post.get("pre_number")))
        pre = by_number.get(pre_number)
        if not pre or str(pre.get("type", "")) != "pre" or str(pre.get("description", "")) != "apt (pre)":
            continue
        post_number = safe_int(post.get("number"))
        if pre_number <= 0 or post_number <= 0:
            continue
        sessions.append({
            "preset": "automatic",
            "label": "Software update (automatic)",
            "pre": pre_number,
            "post": post_number,
            "startedAt": str(pre.get("date", ""))[:64],
            "finishedAt": str(post.get("date", ""))[:64],
        })
    return sorted(sessions, key=lambda row: (row["finishedAt"], row["post"]), reverse=True)


def is_automatic_apt_pair(rows: Iterable[dict[str, Any]], pre_number: int, post_number: int) -> bool:
    return any(
        row["pre"] == pre_number and row["post"] == post_number
        for row in automatic_apt_sessions(rows)
    )
