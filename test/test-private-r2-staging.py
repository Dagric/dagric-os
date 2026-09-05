#!/usr/bin/env python3
"""Unit tests for the private R2 candidate-bucket invariants."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "private_r2", ROOT / "tools/check-private-r2-staging.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def blocked(managed: dict, custom: dict) -> bool:
    try:
        MODULE.validate_states(managed, custom)
    except MODULE.StagingError:
        return True
    return False


def main() -> int:
    MODULE.validate_states({"enabled": False}, {"domains": []})
    assert blocked({"enabled": True}, {"domains": []})
    assert blocked({"enabled": False}, {"domains": [{"domain": "public.example"}]})
    assert blocked({}, {"domains": []})
    assert blocked({"enabled": False}, {})
    MODULE.validate_states(
        {"enabled": False},
        {"domains": [{"domain": "downloads.example", "enabled": False}]},
        require_no_custom_domains=False,
    )
    try:
        MODULE.validate_states(
            {"enabled": False},
            {"domains": [{"domain": "downloads.example", "enabled": True}]},
            require_no_custom_domains=False,
        )
    except MODULE.StagingError:
        pass
    else:
        raise AssertionError("enabled live Free custom domain was accepted as held")
    for live in ("dagric-downloads", "dagric-pro"):
        try:
            MODULE.check("a" * 32, live, "unused")
        except MODULE.StagingError as exc:
            assert "differ from both live" in str(exc)
        else:
            raise AssertionError(f"live bucket {live} was accepted as staging")
    print("private-r2-staging tests: public-domain and live-bucket cases blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
