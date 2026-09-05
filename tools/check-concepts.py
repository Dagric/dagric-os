#!/usr/bin/env python3
"""Validate that every declared Dagric product concept has executable wiring.

This is intentionally a source-contract check, not a claim that hardware or a
fresh install has been tested.  It catches the quieter failure mode where a
feature is advertised but its command, launcher, package, policy, or recovery
half silently disappears from the image definition.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
INCLUDE = ROOT / "config/includes.chroot"
LISTS = ROOT / "config/package-lists"


@dataclass(frozen=True)
class Requirement:
    path: str
    tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class Concept:
    name: str
    requirements: tuple[Requirement, ...]


def req(path: str, *tokens: str) -> Requirement:
    return Requirement(path, tokens)


CONCEPTS = (
    Concept("Build and reproducibility", (
        req("build.sh", "check-source.py", "check-package-names.sh"),
        req("docker/container-build.sh", "check-source.py", "EDITION"),
        req(".github/workflows/build-iso.yml"),
        req(".github/workflows/quality.yml"),
    )),
    Concept("Offline graphical installer", (
        req("config/package-lists/installer.list.chroot", "calamares", "grub-efi-amd64-signed", "shim-signed", "cryptsetup"),
        req("config/includes.chroot/usr/share/calamares/helpers/calamares-bootloader-config", "Dagric OS", "grub-efi-amd64-signed"),
        req("config/includes.chroot/etc/calamares/modules/packages.conf", "try_remove"),
        req("config/hooks/normal/0330-calamares-helper.hook.chroot", "calamares-bootloader-config"),
    )),
    Concept("BIOS, UEFI, and Secure Boot", (
        req("config/package-lists/installer.list.chroot", "grub-pc-bin", "grub-efi-amd64-bin", "shim-signed"),
        req("config/includes.chroot/usr/bin/dagric-efi-fallback", "shimx64.efi", "grubx64.efi"),
        req("tools/check-secureboot.sh"),
        req("test/boot-test.ps1"),
    )),
    Concept("Desktop, branding, and first run", (
        req("config/includes.chroot/usr/bin/dagric-firstrun"),
        req("config/includes.chroot/usr/bin/dagric-appearance"),
        req("config/includes.chroot/usr/bin/dagric-hub"),
        req("config/hooks/normal/0500-desktop-defaults.hook.chroot"),
        req("config/includes.chroot/usr/share/sddm/themes/dagric/Main.qml"),
        req("tools/check-flow.py", "DagricObsidianPulse", "contrast"),
    )),
    Concept("Performance and boot tuning", (
        req("config/hooks/normal/0250-performance.hook.chroot"),
        req("config/hooks/normal/0260-boot-speed.hook.chroot"),
        req("config/hooks/normal/0990-boot-cache.hook.chroot"),
        req("config/includes.chroot/usr/lib/dagric/pipeline.py", "bounded-launch-prefetch", "background_warming"),
        req("config/includes.chroot/usr/lib/dagric/twin.py", "bounded-launch-prefetch-v1", "QUARANTINE_SECONDS"),
        req("docs/DAGRIC-TWIN.md", "Performance Contract", "5%"),
        req("config/includes.chroot/etc/systemd/system/dagric-pipeline.timer", "OnUnitActiveSec=6h"),
        req("tools/check-pipeline.sh"),
        req("test/test-twin.py"),
        req("config/includes.chroot/etc/gamemode.ini"),
        req("config/includes.chroot/usr/share/dagric/budgets/services.json", "cpu_percent_max", "measured", "provisional"),
        req("test/boot-test.ps1"),
    )),
    Concept("Accessibility", (
        req("config/package-lists/desktop.list.chroot", "orca", "speech-dispatcher-espeak-ng"),
        req("config/hooks/normal/0530-accessibility.hook.chroot", "orca"),
        req("config/includes.chroot/usr/share/applications/dagric-screen-reader.desktop"),
        req("site/accessibility.html"),
    )),
    Concept("Localization", (
        req("po/de.po"), req("po/es.po"), req("po/fr.po"), req("po/it.po"), req("po/pt_BR.po"),
        req("tools/i18n-desktop.py"),
        req("config/hooks/normal/0150-locales.hook.chroot"),
    )),
    Concept("Apps, search, and offline manual", (
        req("config/includes.chroot/usr/bin/dagric-app-names"),
        req("config/includes.chroot/usr/bin/dagric-store", "Popular", "Windows replacements", "Flathub", "Debian"),
        req("config/includes.chroot/usr/share/applications/dagric-software-store.desktop", "Name=Dagric Picks", "Icon=dagric-picks", "Exec=/usr/bin/dagric-store"),
        req("config/includes.chroot/etc/skel/.config/kglobalshortcutsrc", "[krunner]", "run_command=Meta+Space"),
        req("config/includes.chroot/usr/bin/dagric-manual"),
        req("config/includes.chroot/usr/share/dagric/manual/index.html"),
        req("config/hooks/normal/0340-offline-docs.hook.chroot"),
    )),
    Concept("Hardware and driver guidance", (
        req("config/includes.chroot/usr/bin/dagric-hardware-check"),
        req("config/includes.chroot/usr/bin/dagric-support", "trust.py"),
        req("config/includes.chroot/usr/lib/dagric/trust.py", "hardware_passport", "lab_rating"),
        req("config/includes.chroot/usr/bin/dagric-drivers", "mokutil"),
        req("config/package-lists/firmware.list.chroot"),
        req("config/package-lists/installer.list.chroot", "mokutil"),
    )),
    Concept("Windows migration", (
        req("config/includes.chroot/usr/bin/dagric-migrate", "rsync", "--ignore-existing", "migrate-state-pack.py"),
        req("config/package-lists/system.list.chroot", "ntfs-3g", "exfatprogs", "rsync"),
        req("config/includes.chroot/usr/share/applications/dagric-migrate.desktop"),
        req("config/includes.chroot/usr/share/dagric/migrate-browser.py", "Windows-browser-context.json"),
        req("config/includes.chroot/usr/share/dagric/migrate-state-pack.py", "Dagric-Migration-State-Pack.json"),
        req("config/includes.chroot/usr/bin/dagric-restore-assistant", "--apply-kde"),
        req("config/includes.chroot/usr/share/applications/dagric-restore-assistant.desktop"),
    )),
    Concept("Steam and Linux gaming", (
        req("config/includes.chroot/usr/bin/dagric-get-steam", "steam-installer", "mesa-vulkan-drivers:i386"),
        req("config/includes.chroot/usr/bin/dagric-gaming", "Proton"),
        req("config/package-lists/pro-gaming.list.chroot", "gamemode", "mangohud", "lutris", "dxvk-wine64"),
        req("config/hooks/normal/0600-pro-edition.hook.chroot", "dpkg --add-architecture i386", "wine32:i386", "dxvk-wine32:i386"),
    )),
    Concept("Windows applications", (
        req("config/package-lists/pro-gaming.list.chroot", "wine", "wine-binfmt", "winetricks"),
        req("config/includes.chroot/usr/bin/dagric-get-bottles", "com.usebottles.bottles"),
        req("config/includes.chroot/usr/share/dagric/manual/app-wine.html"),
    )),
    Concept("Security and privacy", (
        req("config/package-lists/system.list.chroot", "firewalld", "apparmor", "apparmor-utils"),
        req("config/package-lists/pro-security.list.chroot", "opensnitch", "usbguard"),
        req("config/hooks/normal/0300-hardening.hook.chroot"),
        req("config/includes.chroot/usr/bin/dagric-security-checkup"),
        req("config/package-lists/apps.list.chroot", "firefox-esr"),
    )),
    Concept("Updates and package delivery", (
        req("packages/build-repo.sh"),
        req("packages/stage-packages.sh"),
        req("config/includes.chroot/etc/apt/sources.list.d/dagric.list"),
        req("config/includes.chroot/usr/bin/dagric-upgrade"),
        req(".github/workflows/release.yml"),
    )),
    Concept("Rewind snapshots and recovery", (
        req("config/includes.chroot/usr/bin/dagric-rewind"),
        req("config/includes.chroot/usr/lib/dagric/rewind-ctl", "MIN_SNAPSHOT_FREE_BYTES", "flock"),
        req("config/includes.chroot/usr/lib/dagric/rewind_core.py"),
        req("config/includes.chroot/usr/share/polkit-1/actions/org.dagric.rewind.policy"),
        req("config/hooks/normal/0800-snapshot-recovery.hook.chroot"),
        req("test/test-rewind-core.py"), req("test/test-rewind-controller.py"),
    )),
    Concept("Family controls", (
        req("config/includes.chroot/usr/bin/dagric-family"),
        req("config/includes.chroot/usr/lib/dagric/family-apply"),
        req("config/includes.chroot/usr/share/polkit-1/actions/com.dagric.family.policy"),
        req("config/includes.chroot/usr/share/applications/dagric-family.desktop"),
    )),
    Concept("Family Pack staging safety", (
        req("site/family.html", "currently offered", "not available for purchase or delivery"),
        req("infra/gate-worker.js", "REPLACE_ME_family_pack_price_id_from_stripe"),
        req("firebase.json", "family.html"),
        req("tools/check-site.sh", "PLACEHOLDER"),
    )),
    Concept("Windows virtual machine", (
        req("config/package-lists/pro-vm.list.chroot", "virt-manager", "qemu-system-x86", "ovmf", "swtpm"),
        req("config/includes.chroot/usr/bin/dagric-vm"),
        req("config/includes.chroot/usr/share/applications/dagric-vm.desktop"),
    )),
    Concept("Backups and storage", (
        req("config/package-lists/system.list.chroot", "kup-backup", "smartmontools"),
        req("config/package-lists/pro-apps.list.chroot", "borgbackup", "vorta"),
        req("config/includes.chroot/usr/share/dagric/manual/app-kup.html"),
        req("config/includes.chroot/usr/share/dagric/manual/app-vorta.html"),
        req("config/includes.chroot/usr/lib/dagric/trust.py", "restore points are not reported as backups"),
    )),
    Concept("Trust loop and privacy-safe support", (
        req("config/includes.chroot/usr/lib/dagric/trust.py", "privacy_errors", "support_manifest", "O_EXCL"),
        req("config/includes.chroot/usr/bin/dagric-support"),
        req("config/includes.chroot/usr/share/applications/dagric-support.desktop"),
        req("test/test-trust.py"),
        req("tools/check-trust.sh"),
        req("docs/DAGRIC-TRUST-LOOP.md", "Recent-request audit", "Release truth"),
    )),
    Concept("Blueprint, Black Box, and Life Support foundations", (
        req("config/includes.chroot/usr/lib/dagric/foundations.py", "BLUEPRINT_SCHEMA", "BLACKBOX_MAX_EVENTS", "apply_available", "automatic_changes_applied"),
        req("config/includes.chroot/usr/bin/dagric-blueprint", "foundations.py"),
        req("config/includes.chroot/usr/bin/dagric-blackbox", "foundations.py"),
        req("config/includes.chroot/usr/bin/dagric-life-support", "foundations.py"),
        req("config/includes.chroot/etc/systemd/system/dagric-blackbox.service", "MemoryMax=64M", "CPUQuota=5%", "ProtectSystem=strict"),
        req("config/includes.chroot/etc/systemd/system/dagric-blackbox.timer", "OnUnitActiveSec=5m", "Persistent=false"),
        req("config/includes.chroot/usr/share/dagric/budgets/services.json", "network", "none"),
        req("test/test-foundations.py", "hidden_payloads", "retention_and_ring_cap", "read_only"),
        req("tools/check-foundations.sh"),
        req("docs/DAGRIC-FOUNDATIONS.md", "Transactional roots", "Release boundary"),
    )),
    Concept("Website and release delivery", (
        req("site/index.html"), req("site/features.html"), req("site/download.html"),
        req("infra/gate-worker.js"), req("tools/check-site.sh"),
        req("tools/release.sh"), req("tools/write-release-proof.py"),
    )),
)


def evaluate(concept: Concept) -> list[str]:
    failures: list[str] = []
    for requirement in concept.requirements:
        path = ROOT / requirement.path
        if not path.is_file():
            failures.append(f"missing {requirement.path}")
            continue
        if not requirement.tokens:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            failures.append(f"cannot read {requirement.path}: {exc}")
            continue
        for token in requirement.tokens:
            if token not in content:
                failures.append(f"{requirement.path} lacks {token!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args()
    results = []
    for concept in CONCEPTS:
        failures = evaluate(concept)
        results.append({"concept": concept.name, "implemented": not failures, "failures": failures})
    passed = sum(item["implemented"] for item in results)
    if args.json:
        print(json.dumps({"passed": passed, "total": len(results), "concepts": results}, indent=2))
    else:
        for item in results:
            state = "PASS" if item["implemented"] else "FAIL"
            print(f"[{state}] {item['concept']}")
            for failure in item["failures"]:
                print(f"       {failure}")
        print(f"concept-check: {passed}/{len(results)} implementation contracts passed")
        print("note: hardware, installation, performance, and commercial validation are separate audit gates")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
