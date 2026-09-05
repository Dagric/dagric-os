#!/usr/bin/env python3
"""Regression tests for the candidate-bound physical release gate."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check-physical-release.py"
COMMIT = "a" * 40
TAG = "v1.0-test"
CHECK_EDITIONS = {
    "bios_live_boot": ["free", "pro"],
    "uefi_install_reboot_login": ["free", "pro"],
    "secure_boot_install_reboot_login": ["free", "pro"],
    "display_native_resolution_acceleration": ["free", "pro"],
    "ethernet_connectivity": ["free", "pro"],
    "wifi_connectivity": ["free", "pro"],
    "audio_input_output": ["free", "pro"],
    "bluetooth_pair_transfer": ["free", "pro"],
    "suspend_resume": ["free", "pro"],
    "keyboard_only_navigation": ["free", "pro"],
    "orca_audible_navigation": ["free", "pro"],
    "text_scaling_200_percent": ["free", "pro"],
    "reduced_motion": ["free", "pro"],
    "x11_session": ["free", "pro"],
    "wayland_session": ["free", "pro"],
    "multi_user_home_isolation": ["free", "pro"],
    "multi_user_polkit_denial": ["free", "pro"],
    "family_controls_multi_user": ["free", "pro"],
    "opensnitch_socket_permissions": ["pro"],
    "opensnitch_key_permissions": ["pro"],
    "opensnitch_non_admin_denied": ["pro"],
}


def fixture(root: Path) -> tuple[Path, dict[str, object]]:
    artifacts = [
        {
            "edition": edition,
            "filename": f"dagric-os{'-pro' if edition == 'pro' else ''}-1.0-amd64.iso",
            "bytes": 100 if edition == "free" else 200,
            "sha256": ("b" if edition == "free" else "c") * 64,
        }
        for edition in ("free", "pro")
    ]
    release = root / "release.json"
    release.write_text(
        json.dumps({"source": {"commit": COMMIT}, "artifacts": artifacts}),
        encoding="utf-8",
    )
    machine_url = "https://records.dagric.com/physical/v1-test"
    evidence = {
        "schema": "dagric-physical-release-evidence-v1",
        "decision": "passed",
        "reviewed_by_human": True,
        "candidate_commit": COMMIT,
        "release_tag": TAG,
        "completed_utc": "2026-09-04T12:00:00Z",
        "reviewer": {"name": "Human Tester", "role": "QA and accessibility engineer"},
        "artifacts": {
            record["edition"]: {
                field: record[field] for field in ("filename", "bytes", "sha256")
            }
            for record in artifacts
        },
        "machines": [
            {
                "machine_id": "intel-nvidia-01",
                "physical": True,
                "manufacturer_model": "Example Intel workstation",
                "firmware": "UEFI 1.0",
                "cpu_vendor": "intel",
                "cpu": "Intel test processor",
                "gpu_vendors": ["intel", "nvidia"],
                "memory": "16 GiB",
                "storage": "512 GB NVMe",
                "evidence_url": machine_url + "/intel",
            },
            {
                "machine_id": "amd-radeon-01",
                "physical": True,
                "manufacturer_model": "Example AMD workstation",
                "firmware": "UEFI 2.0",
                "cpu_vendor": "amd",
                "cpu": "AMD test processor",
                "gpu_vendors": ["amd"],
                "memory": "32 GiB",
                "storage": "1 TB NVMe",
                "evidence_url": machine_url + "/amd",
            },
        ],
        "checks": {
            check_id: {
                "result": "pass",
                "editions": editions,
                "machine_ids": ["intel-nvidia-01", "amd-radeon-01"],
                "evidence_urls": [machine_url + "/" + check_id],
                "notes": "Observed the complete physical test with expected behavior.",
            }
            for check_id, editions in CHECK_EDITIONS.items()
        },
    }
    return release, evidence


def run(release: Path, evidence: dict[str, object] | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if evidence is None:
        env.pop("PHYSICAL_RELEASE_EVIDENCE_JSON", None)
    else:
        env["PHYSICAL_RELEASE_EVIDENCE_JSON"] = json.dumps(evidence)
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "check",
            "--candidate-commit",
            COMMIT,
            "--release-tag",
            TAG,
            "--release-record",
            str(release),
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        release, good = fixture(Path(folder))
        result = run(release, good)
        require(result.returncode == 0 and "passed" in result.stdout, result.stderr)

        result = run(release, None)
        require(result.returncode != 0 and "absent" in result.stderr, result.stderr)

        stale = copy.deepcopy(good)
        stale["artifacts"]["free"]["sha256"] = "d" * 64
        result = run(release, stale)
        require(result.returncode != 0 and "stale" in result.stderr, result.stderr)

        missing = copy.deepcopy(good)
        del missing["checks"]["orca_audible_navigation"]
        result = run(release, missing)
        require(result.returncode != 0 and "missing required" in result.stderr, result.stderr)

        failed = copy.deepcopy(good)
        failed["checks"]["suspend_resume"]["result"] = "fail"
        result = run(release, failed)
        require(result.returncode != 0 and "did not pass" in result.stderr, result.stderr)

        incomplete = copy.deepcopy(good)
        incomplete["machines"] = incomplete["machines"][:1]
        for record in incomplete["checks"].values():
            record["machine_ids"] = ["intel-nvidia-01"]
        result = run(release, incomplete)
        require(result.returncode != 0 and "AMD processors" in result.stderr, result.stderr)

        template = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "template",
                "--candidate-commit",
                COMMIT,
                "--release-tag",
                TAG,
                "--release-record",
                str(release),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        require(template.returncode == 0, template.stderr)
        pending = json.loads(template.stdout)
        require(pending["decision"] == "pending-human-physical-testing", template.stdout)
        require(set(pending["checks"]) == set(CHECK_EDITIONS), template.stdout)

    print("physical-release-gate tests: 7 passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
