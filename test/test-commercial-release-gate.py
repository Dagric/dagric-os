#!/usr/bin/env python3
"""Focused regression tests for the commercial artifact/release hard gate."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check-commercial-release.py"
COMMIT = "a" * 40
TAG = "v1.9-test"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_entry(name: str, version: str) -> dict[str, object]:
    return {
        "binary_name": name,
        "binary_version": version,
        "source_name": name.split(":", 1)[0],
        "source_version": version,
        "origin": "debian",
        "locator": {
            "dsc_url": f"https://snapshot.debian.org/archive/debian/test/{name}_1.dsc"
        },
        "integrity": {"dsc_sha256": "b" * 64},
    }


class Fixture:
    def __init__(self, root: Path, package: str = "bash", section: str = "utils") -> None:
        self.root = root
        self.iso: dict[str, Path] = {}
        self.manifest: dict[str, Path] = {}
        self.sections: dict[str, Path] = {}
        self.provenance: dict[str, Path] = {}
        for edition in ("free", "pro"):
            self.iso[edition] = root / f"dagric-os{'-pro' if edition == 'pro' else ''}-1.0-amd64.iso"
            self.iso[edition].write_bytes((edition + " candidate").encode())
            self.manifest[edition] = root / f"{edition}.packages"
            self.manifest[edition].write_text(f"{package}\t1.0\n", encoding="utf-8")
            self.sections[edition] = root / f"PACKAGE_SECTIONS-{edition}.tsv"
            self.sections[edition].write_text(
                f"{package}\t1.0\t{section}\n", encoding="utf-8"
            )
            self.provenance[edition] = root / f"SOURCE_COMMIT-{edition}"
            self.provenance[edition].write_text(COMMIT + "\n", encoding="utf-8")

        self.firefox = root / "policies.json"
        self.firefox.write_text('{"policies":{}}\n', encoding="utf-8")
        self.art = root / "branding/icons/apps/game.png"
        self.art.parent.mkdir(parents=True)
        self.art.write_bytes(b"original generic game art")
        self.game_policy = root / "game-integrations.json"
        self.game_policy.write_text(
            json.dumps(
                {
                    "artworkClearance": {
                        "assets": [
                            {"asset": "branding/icons/apps/game.png", "sha256": digest(self.art)}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        self.checksums = root / "SHA256SUMS"
        self.checksums.write_text(
            "".join(f"{digest(self.iso[e])}  {self.iso[e].name}\n" for e in ("free", "pro")),
            encoding="utf-8",
        )

        artifacts: list[dict[str, object]] = []
        index_artifacts: list[dict[str, object]] = []
        maps: dict[str, object] = {}
        package_records: dict[str, object] = {}
        for edition in ("free", "pro"):
            manifest_url = f"https://dagric.com/manifest/{edition}.packages"
            manifest_hash = digest(self.manifest[edition])
            artifacts.append(
                {
                    "edition": edition,
                    "filename": self.iso[edition].name,
                    "bytes": self.iso[edition].stat().st_size,
                    "sha256": digest(self.iso[edition]),
                }
            )
            index_artifacts.append(
                {
                    "edition": edition,
                    "filename": self.iso[edition].name,
                    "sha256": digest(self.iso[edition]),
                    "binary_package_manifest": manifest_url,
                    "binary_package_manifest_sha256": manifest_hash,
                }
            )
            package_records[edition] = {
                "url": manifest_url,
                "packages": 1,
                "sha256": manifest_hash,
            }
            maps[edition] = {
                "binary_package_manifest": manifest_url,
                "binary_package_manifest_sha256": manifest_hash,
                "entries": [source_entry(package, "1.0")],
            }

        self.index = root / "source-index.json"
        index = {
            "release": {"version": "1.0", "source_commit": COMMIT, "artifacts": index_artifacts},
            "debian_layer": {
                "exact_binary_to_source_map_status": "complete",
                "exact_binary_to_source_map": {
                    "format": "dagric-exact-binary-source-map-v1",
                    "generated_utc": "2026-09-04T00:00:00Z",
                    "editions": maps,
                },
            },
            "next_release_gate": {
                "status": "complete",
                "block_if_release_identity_changes": False,
            },
        }
        self.index.write_text(json.dumps(index), encoding="utf-8")
        self.release = root / "release.json"
        self.release.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "source": {"commit": COMMIT},
                    "artifacts": artifacts,
                    "package_manifests": package_records,
                    "source_index": {"url": "https://dagric.com/manifest/source-index.json", "status": "complete"},
                }
            ),
            encoding="utf-8",
        )

    def approval(self) -> str:
        firmware_editions: dict[str, object] = {}
        restricted_editions: dict[str, object] = {}
        for edition in ("free", "pro"):
            identities = [line.split() for line in self.manifest[edition].read_text(encoding="utf-8").splitlines()]
            packages = sorted(
                f"{name}={version}"
                for name, version in identities
                if "firmware" in name.split(":", 1)[0]
                or "microcode" in name.split(":", 1)[0]
            )
            inventory_bytes = "".join(item + "\n" for item in packages).encode()
            firmware_editions[edition] = {
                "packages": packages,
                "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
                "installer_or_downloader_packages": sorted(
                    item
                    for item in packages
                    if "installer" in item.split("=", 1)[0]
                    or "downloader" in item.split("=", 1)[0]
                ),
            }
            restricted = []
            for line in self.sections[edition].read_text(encoding="utf-8").splitlines():
                name, version, section = line.split("\t")
                if section.split("/", 1)[0] in {"contrib", "non-free", "non-free-firmware"}:
                    restricted.append(f"{name}={version}\t{section}")
            restricted.sort()
            restricted_bytes = "".join(item + "\n" for item in restricted).encode()
            restricted_editions[edition] = {
                "packages": restricted,
                "sha256": hashlib.sha256(restricted_bytes).hexdigest(),
                "installer_or_downloader_packages": sorted(
                    item
                    for item in restricted
                    if "installer" in item.split("=", 1)[0]
                    or "downloader" in item.split("=", 1)[0]
                ),
            }
        return json.dumps(
            {
                "schema": "dagric-commercial-legal-approval-v1",
                "decision": "approved",
                "scope": "commercial-distribution",
                "reviewed_by_human": True,
                "candidate_commit": COMMIT,
                "release_tag": TAG,
                "approved_utc": "2026-09-04T00:00:00Z",
                "reviewer": {"name": "Qualified Reviewer", "role": "IP legal counsel"},
                "firefox_trademark": {
                    "decision": "written-permission",
                    "configuration_sha256": digest(self.firefox),
                    "evidence_url": "https://records.dagric.com/legal/firefox-approval",
                },
                "game_art_ip": {
                    "decision": "approved",
                    "policy_sha256": digest(self.game_policy),
                    "assets": [
                        {"asset": "branding/icons/apps/game.png", "sha256": digest(self.art)}
                    ],
                    "evidence_url": "https://records.dagric.com/legal/game-art-approval",
                },
                "game_platform_terms_reviewed": True,
                "third_party_notices_reviewed": True,
                "nvidia_redistribution_reviewed": True,
                "firmware_microcode": {
                    "decision": "approved",
                    "notices_reviewed": True,
                    "evidence_url": "https://records.dagric.com/legal/firmware-review",
                    "editions": firmware_editions,
                },
                "restricted_repository_packages": {
                    "decision": "approved",
                    "notices_reviewed": True,
                    "evidence_url": "https://records.dagric.com/legal/restricted-packages",
                    "editions": restricted_editions,
                },
            }
        )

    def base(self) -> list[str]:
        return [
            "--candidate-commit", COMMIT,
            "--release-tag", TAG,
            "--release-record", str(self.release),
            "--source-index", str(self.index),
            "--firefox-policy", str(self.firefox),
            "--candidate-source-root", str(self.root),
            "--game-policy", str(self.game_policy),
        ]

    def edition_args(self, edition: str) -> list[str]:
        return [
            sys.executable, str(TOOL), "edition", *self.base(),
            "--edition", edition,
            "--iso", str(self.iso[edition]),
            "--package-manifest", str(self.manifest[edition]),
            "--package-sections", str(self.sections[edition]),
            "--provenance", str(self.provenance[edition]),
            "--checksums", str(self.checksums),
        ]

    def promotion_args(self, authorization_output: Path | None = None) -> list[str]:
        args = [
            sys.executable, str(TOOL), "promotion", *self.base(),
            "--checksums", str(self.checksums),
            "--free-manifest", str(self.manifest["free"]),
            "--pro-manifest", str(self.manifest["pro"]),
            "--free-package-sections", str(self.sections["free"]),
            "--pro-package-sections", str(self.sections["pro"]),
            "--free-iso", str(self.iso["free"]),
            "--pro-iso", str(self.iso["pro"]),
            "--free-provenance", str(self.provenance["free"]),
            "--pro-provenance", str(self.provenance["pro"]),
        ]
        if authorization_output is not None:
            args.extend(["--authorization-output", str(authorization_output)])
        return args


def run(args: list[str], approval: str | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if approval is None:
        env.pop("COMMERCIAL_RELEASE_APPROVAL_JSON", None)
    else:
        env["COMMERCIAL_RELEASE_APPROVAL_JSON"] = approval
    return subprocess.run(args, text=True, capture_output=True, env=env, check=False)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder))
        result = run(fixture.edition_args("free"), fixture.approval())
        require(result.returncode == 0, result.stderr)

        authorization = Path(folder) / "authorization.json"
        result = run(fixture.promotion_args(authorization), fixture.approval())
        require(result.returncode == 0, result.stderr)
        stamp = json.loads(authorization.read_text(encoding="utf-8"))
        require(
            stamp["schema"] == "dagric-commercial-release-authorization-v1",
            str(stamp),
        )
        require(stamp["candidate_commit"] == COMMIT, str(stamp))
        require(
            stamp["artifacts"]["free"]["sha256"] == digest(fixture.iso["free"]),
            str(stamp),
        )

        result = run(fixture.edition_args("free"), None)
        require(result.returncode != 0 and "human" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder))
        unmodified = json.loads(fixture.approval())
        fixture.firefox.unlink()
        unmodified["firefox_trademark"]["decision"] = "unmodified-distribution-reviewed"
        unmodified["firefox_trademark"]["configuration_sha256"] = "absent"
        result = run(fixture.edition_args("free"), json.dumps(unmodified))
        require(result.returncode == 0, result.stderr)

        unmodified["firefox_trademark"]["decision"] = "written-permission"
        result = run(fixture.edition_args("free"), json.dumps(unmodified))
        require(
            result.returncode != 0 and "unmodified-distribution-reviewed" in result.stderr,
            result.stderr,
        )

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder), package="steam-installer")
        result = run(fixture.edition_args("free"), fixture.approval())
        require(result.returncode != 0 and "steam-installer" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder))
        fixture.iso["free"].write_bytes(b"changed after release record")
        result = run(fixture.edition_args("free"), fixture.approval())
        require(result.returncode != 0 and "SHA-256" in result.stderr, result.stderr)
        result = run(
            fixture.promotion_args(Path(folder) / "authorization.json"),
            fixture.approval(),
        )
        require(result.returncode != 0 and "SHA-256" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder))
        index = json.loads(fixture.index.read_text(encoding="utf-8"))
        index["debian_layer"]["exact_binary_to_source_map_status"] = "not-yet-generated"
        fixture.index.write_text(json.dumps(index), encoding="utf-8")
        result = run(fixture.promotion_args(), fixture.approval())
        require(result.returncode != 0 and "complete exact" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(
            Path(folder), package="firmware-example", section="non-free-firmware/kernel"
        )
        approval = json.loads(fixture.approval())
        approval["firmware_microcode"]["editions"]["free"]["packages"] = []
        result = run(fixture.edition_args("free"), json.dumps(approval))
        require(result.returncode != 0 and "complete free inventory" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(
            Path(folder), package="firmware-b43-installer", section="contrib/kernel"
        )
        approval = json.loads(fixture.approval())
        approval["firmware_microcode"]["editions"]["free"][
            "installer_or_downloader_packages"
        ] = []
        result = run(fixture.edition_args("free"), json.dumps(approval))
        require(result.returncode != 0 and "installer/downloader" in result.stderr, result.stderr)

        template = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "approval-template",
                "--candidate-commit",
                COMMIT,
                "--release-tag",
                TAG,
                "--free-manifest",
                str(fixture.manifest["free"]),
                "--pro-manifest",
                str(fixture.manifest["pro"]),
                "--free-package-sections",
                str(fixture.sections["free"]),
                "--pro-package-sections",
                str(fixture.sections["pro"]),
                "--candidate-source-root",
                str(fixture.root),
                "--firefox-policy",
                str(fixture.firefox),
                "--game-policy",
                str(fixture.game_policy),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        require(template.returncode == 0, template.stderr)
        pending = json.loads(template.stdout)
        require(pending["decision"] == "pending-human-review", template.stdout)
        require(
            pending["firmware_microcode"]["editions"]["free"][
                "installer_or_downloader_packages"
            ]
            == ["firmware-b43-installer=1.0"],
            template.stdout,
        )

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder), package="libfishcamp1t64", section="non-free/libs")
        approval = json.loads(fixture.approval())
        approval["restricted_repository_packages"]["editions"]["free"]["packages"] = []
        result = run(fixture.edition_args("free"), json.dumps(approval))
        require(result.returncode != 0 and "complete free Section" in result.stderr, result.stderr)

    with tempfile.TemporaryDirectory() as folder:
        fixture = Fixture(Path(folder))
        fixture.sections["free"].write_text("different\t1.0\tutils\n", encoding="utf-8")
        result = run(fixture.edition_args("free"), fixture.approval())
        require(result.returncode != 0 and "not a 1:1 match" in result.stderr, result.stderr)

    print("commercial-release-gate tests: 15 passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
