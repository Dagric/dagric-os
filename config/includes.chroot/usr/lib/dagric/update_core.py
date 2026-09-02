#!/usr/bin/env python3
"""Dagric's deliberately conservative in-place update path.

This tool updates the installed Dagric/Debian packages within the current
release.  It is not ``dagric-upgrade``: that command is the separately gated
major Debian release migration.  Keeping those two operations apart means a
normal "get me current" click can never silently rewrite APT sources, switch
Debian suites, or approve package removals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
from typing import Sequence


PROGRAM = "/usr/bin/dagric-update"
STATE_DIR = Path("/var/lib/dagric/updates")
MINIMUM_FREE_BYTES = 2 * 1024 * 1024 * 1024


class UpdateError(RuntimeError):
    """A blocked or failed update, reported without hiding the safe state."""


@dataclass(frozen=True)
class Plan:
    upgraded: tuple[str, ...] = ()
    installed: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    held_back: tuple[str, ...] = ()
    summary_upgraded: int = 0
    summary_installed: int = 0
    summary_removed: int = 0
    summary_held_back: int = 0

    @property
    def changes(self) -> int:
        return max(
            len(self.upgraded) + len(self.installed),
            self.summary_upgraded + self.summary_installed,
        )


_SECTION_MAP = {
    "The following packages will be upgraded:": "upgraded",
    "The following NEW packages will be installed:": "installed",
    "The following packages will be REMOVED:": "removed",
    "The following packages have been kept back:": "held_back",
}
_SUMMARY_RE = re.compile(
    r"(?P<upgraded>\d+) upgraded, (?P<installed>\d+) newly installed, "
    r"(?P<removed>\d+) to remove and (?P<held>\d+) not upgraded"
)


def _package_tokens(line: str) -> list[str]:
    """Return package names from an APT section line, excluding versions."""
    names: list[str] = []
    for token in line.split():
        token = token.split("(", 1)[0].rstrip(",")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.:@-]*", token):
            names.append(token)
    return names


def parse_plan(text: str) -> Plan:
    """Parse APT's human plan only for safety reporting, never for execution."""
    buckets: dict[str, list[str]] = {value: [] for value in _SECTION_MAP.values()}
    current: str | None = None
    summary = (0, 0, 0, 0)
    for raw in text.splitlines():
        line = raw.rstrip()
        if line in _SECTION_MAP:
            current = _SECTION_MAP[line]
            continue
        match = _SUMMARY_RE.search(line)
        if match:
            summary = tuple(int(match.group(key)) for key in ("upgraded", "installed", "removed", "held"))
            current = None
            continue
        if current is None:
            continue
        if not line.strip():
            current = None
            continue
        if line.startswith((" ", "\t")):
            buckets[current].extend(_package_tokens(line))
        else:
            current = None

    def unique(name: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(buckets[name]))

    return Plan(
        upgraded=unique("upgraded"),
        installed=unique("installed"),
        removed=unique("removed"),
        held_back=unique("held_back"),
        summary_upgraded=summary[0],
        summary_installed=summary[1],
        summary_removed=summary[2],
        summary_held_back=summary[3],
    )


def safe_upgrade_command(*, simulate: bool = False, download_only: bool = False) -> list[str]:
    """Return the only package-change command this updater is permitted to run.

    ``upgrade --with-new-pkgs`` can add dependencies but cannot remove an
    installed package.  In particular, this must never become full-upgrade or
    autoremove: those can remove software a person chose to keep.
    """
    command = ["apt-get"]
    if simulate:
        command.append("--simulate")
    if not simulate:
        command.append("--yes")
    if download_only:
        command.append("--download-only")
    if not simulate:
        command.extend([
            "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold",
        ])
    command.extend(["--with-new-pkgs", "upgrade"])
    return command


def snapshot_available() -> bool:
    return (
        shutil.which("snapper") is not None
        and subprocess.run(
            ["findmnt", "-n", "-o", "FSTYPE", "/"], capture_output=True, text=True, check=False
        ).stdout.strip() == "btrfs"
        and Path("/etc/snapper/configs/root").is_file()
    )


def run(command: Sequence[str], *, capture: bool = True) -> str:
    result = subprocess.run(command, text=True, capture_output=capture, check=False)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode:
        detail = output.strip() or f"exit status {result.returncode}"
        raise UpdateError(f"{' '.join(command[:2])} failed: {detail}")
    return output


def require_clean_preflight() -> None:
    if os.geteuid() != 0:
        raise UpdateError(f"run as administrator: sudo {PROGRAM}")
    audit = run(["dpkg", "--audit"])
    if audit.strip():
        raise UpdateError(
            "package configuration is incomplete. Repair it first with: "
            "sudo dpkg --configure -a && sudo apt-get -f install"
        )
    available = shutil.disk_usage("/").free
    if available < MINIMUM_FREE_BYTES:
        raise UpdateError(
            f"only {available // (1024 * 1024)} MiB is free on /. "
            "Free at least 2 GiB before updating."
        )


def refresh_and_plan() -> Plan:
    # apt validates the repository's signed InRelease/Release metadata before
    # accepting an index.  This deliberately uses APT rather than a custom URL
    # downloader, hash list, or unsigned package path.
    run(["apt-get", "update"])
    plan = parse_plan(run(safe_upgrade_command(simulate=True)))
    if plan.removed or plan.summary_removed:
        raise UpdateError(
            "the update plan includes package removals. Dagric refused it; "
            "use the separate major-release upgrader or investigate the package conflict."
        )
    return plan


def plan_text(plan: Plan) -> str:
    lines = [
        f"Available safe updates: {plan.changes}",
        f"Packages to remove: {len(plan.removed) or plan.summary_removed}",
        "User home folders: not copied, deleted, or replaced.",
        "Local package configuration: keep the existing version when a package provides a new default.",
    ]
    if plan.held_back or plan.summary_held_back:
        names = ", ".join(plan.held_back[:12])
        extra = f" ({names})" if names else ""
        lines.append(f"Held back for manual review: {len(plan.held_back) or plan.summary_held_back}{extra}")
    return "\n".join(lines)


def create_checkpoint() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run(["snapper", "-c", "root", "create", "-t", "single", "-d", f"before Dagric update ({stamp})"])
    return stamp


def write_report(*, outcome: str, plan: Plan, checkpoint: str | None, detail: str = "") -> Path:
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    report = STATE_DIR / f"{now.strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}.txt"
    body = [
        "Dagric Update report",
        f"Time (UTC): {now.isoformat()}",
        f"Outcome: {outcome}",
        f"Recovery checkpoint: {checkpoint or 'not available'}",
        "Scope: signed APT packages in the current Debian release only.",
        "Home folders: not copied, deleted, or replaced by Dagric Update.",
        "Configuration policy: existing package configuration is retained where dpkg supports it.",
        "Removal policy: no package-removal command was used.",
        "",
        plan_text(plan),
    ]
    if detail:
        body.extend(["", f"Detail: {detail}"])
    report.write_text("\n".join(body) + "\n", encoding="utf-8")
    os.chmod(report, 0o600)
    return report


def check() -> int:
    require_clean_preflight()
    plan = refresh_and_plan()
    print(plan_text(plan))
    if plan.changes == 0:
        print("Dagric is already current on this update channel.")
    return 0


def apply(*, assume_yes: bool, allow_without_snapshot: bool) -> int:
    require_clean_preflight()
    plan = refresh_and_plan()
    if plan.changes == 0:
        print("Dagric is already current on this update channel. Nothing changed.")
        return 0
    checkpoint: str | None = None
    if not snapshot_available() and not allow_without_snapshot:
        raise UpdateError(
            "this installation has no Btrfs/Snapper recovery checkpoint. "
            "Nothing changed. Back up your files, then explicitly re-run with --allow-without-snapshot."
        )
    if not assume_yes:
        print(plan_text(plan))
        answer = input("Type UPDATE to download and apply these safe updates: ").strip()
        if answer != "UPDATE":
            print("Nothing changed.")
            return 0
    try:
        # Downloading is completed before any installed package changes. It
        # reduces the chance a network interruption leaves dpkg mid-update.
        run(safe_upgrade_command(download_only=True), capture=False)
        if snapshot_available():
            checkpoint = create_checkpoint()
        run(safe_upgrade_command(), capture=False)
    except UpdateError as exc:
        report = write_report(outcome="failed", plan=plan, checkpoint=checkpoint, detail=str(exc))
        recovery = "Reboot and choose the Dagric snapshot in GRUB." if checkpoint else "Use your own backup if recovery is needed."
        raise UpdateError(f"update stopped. {recovery} Report: {report}") from exc
    report = write_report(outcome="updated", plan=plan, checkpoint=checkpoint)
    print("Update completed. Restart when convenient if a kernel or graphics stack changed.")
    if checkpoint:
        print("A recovery checkpoint was created before package changes.")
    print(f"Report: {report}")
    return 0


def _dialog(args: list[str]) -> bool:
    return subprocess.run(["kdialog", *args], check=False).returncode == 0


def gui() -> int:
    if os.geteuid() == 0:
        raise UpdateError("open Dagric Update from your desktop, not as root")
    if shutil.which("kdialog") is None or shutil.which("pkexec") is None:
        raise UpdateError(f"desktop update is unavailable; run: sudo {PROGRAM}")
    message = (
        "Dagric Update installs signed updates for the version of Dagric already on this PC.\n\n"
        "It does not reinstall Dagric, erase files, change your Debian release, or remove packages. "
        "Your existing package settings are kept when safe."
    )
    if not _dialog(["--title", "Dagric Update", "--yesno", message + "\n\nCheck and apply updates now?"]):
        return 0
    arguments = ["pkexec", PROGRAM, "--apply", "--yes"]
    if not snapshot_available():
        warning = (
            "This installation has no Btrfs/Snapper recovery checkpoint. Your home files will still not be "
            "touched by this updater, but automatic rollback is unavailable. Make a backup before continuing."
        )
        if not _dialog(["--title", "Dagric Update", "--yesno", warning + "\n\nContinue without a checkpoint?"]):
            return 0
        arguments.append("--allow-without-snapshot")
    result = subprocess.run(arguments, text=True, capture_output=True, check=False)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode:
        _dialog(["--title", "Dagric Update", "--error", output[-3500:] or "The update did not complete. Nothing further was changed by Dagric Update."])
        return result.returncode
    _dialog(["--title", "Dagric Update", "--msgbox", output[-3500:] or "Update completed."])
    return 0


def main(argv: Sequence[str]) -> int:
    args = list(argv)
    if args in (["--help"], ["-h"]):
        print(f"Usage: {PROGRAM} [--check | --apply [--yes] [--allow-without-snapshot] | --gui]")
        return 0
    try:
        if args == ["--check"]:
            return check()
        if args == ["--gui"]:
            return gui()
        if args and args[0] == "--apply" and set(args[1:]) <= {"--yes", "--allow-without-snapshot"}:
            return apply(assume_yes="--yes" in args, allow_without_snapshot="--allow-without-snapshot" in args)
        # The normal terminal command is an explicitly confirmed safe update.
        if not args:
            return apply(assume_yes=False, allow_without_snapshot=False)
        raise UpdateError(f"unknown option. Run {PROGRAM} --help")
    except UpdateError as exc:
        print(f"Dagric Update stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
