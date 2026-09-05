#!/usr/bin/env python3
"""Release gate for Dagric's optional game-platform legal boundary."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / "config/includes.chroot"
POLICY = INC / "usr/share/dagric/policy/game-integrations.json"
PROPRIETARY_CLIENT_PACKAGES = {
    "steam",
    "steam-installer",
    "steam-launcher",
    "steamcmd",
    "gog-galaxy",
    "epic-games-launcher",
    "amazon-games",
}


def forbidden_client_package(name: str) -> bool:
    return name in PROPRIETARY_CLIENT_PACKAGES or name.startswith("steam-libs")
EXPECTED_GAME_ART = {
    "branding/icons/apps/dagric-gaming-source.png":
        "6b7edf9f688a1438bc38ac88ab1005f22741f838c72f780ba4ca8eb2e300ca46",
    "branding/icons/apps/dagric-get-steam-source.png":
        "19cde985cd6d9668d588f28c5258bac6e717a99aeb3a63479cef7798aa94600d",
    "branding/icons/apps/dagric-get-heroic-source.png":
        "e2a7c838ceba423954eb1ab54c83a5840036bb0f1c979a81df825bcec94516bb",
    "branding/icons/apps/dagric-get-protonup-source.png":
        "ff9c27e08bd6a0f5b1d68fd001e98ed60b7179be7261ed0bcfd07f90fb165d39",
}
BLOCKED_GAMING_ART_SHA256 = {
    "003537ef93a993b2965a8c6597ff34182596123bbdfdb7ebefe5ce9115969eb2",
    "a27e9d6bc8ef4fc0053210fc10ed3f97d8a96d249de82c7abf41585776a9ce9f",
    "30bcc921ec1cb4508258d8d11f849b39e6e752225e2c265c3f1bfe9fec24f295",
    "21eb1891ac9ea65ca50638e2a3915368dee2a1bea1788727e43e89812a6e70c8",
}


def normalized_package_name(raw_line: str) -> str | None:
    """Return a Debian binary package name from a list or resolved manifest."""
    line = raw_line.split("#", 1)[0].strip()
    if not line:
        return None
    name = line.split(maxsplit=1)[0].lower().rstrip("+-")
    return name.split(":", 1)[0]


def package_names() -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    inputs = sorted((ROOT / "config/package-lists").glob("*.list.chroot"))
    inputs += sorted((ROOT / "site/manifest").glob("*.packages"))
    for package_list in inputs:
        for raw_line in package_list.read_text(encoding="utf-8").splitlines():
            name = normalized_package_name(raw_line)
            if not name:
                continue
            found.setdefault(name, []).append(package_list)
    return found


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def forbid_tokens(path: Path, tokens: tuple[str, ...], failures: list[str]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in tokens:
        if token.casefold() in text.casefold():
            failures.append(f"{path.relative_to(ROOT)} contains prohibited text: {token}")


def integration_map(policy: object) -> dict[str, dict[str, object]]:
    if not isinstance(policy, dict) or not isinstance(policy.get("integrations"), list):
        return {}
    return {
        item["id"]: item
        for item in policy["integrations"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def require_tokens(path: Path, tokens: tuple[str, ...], failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"Missing required file: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in tokens:
        if token.casefold() not in text.casefold():
            failures.append(f"{path.relative_to(ROOT)} lacks required text: {token}")


def main() -> int:
    failures: list[str] = []
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"game-platform-policy: cannot read policy: {error}", file=sys.stderr)
        return 1

    if policy.get("schemaVersion") != 1:
        failures.append("game integration policy must use schemaVersion 1")
    rules = policy.get("releaseRules", {})
    expected_false = (
        "proprietaryStoreClientsBundled",
        "officialThirdPartyLogosInDagricArtwork",
        "compatibilityGuaranteed",
    )
    for key in expected_false:
        if rules.get(key) is not False:
            failures.append(f"releaseRules.{key} must be false")
    if rules.get("optionalInstallRequiresOwnerAction") is not True:
        failures.append("releaseRules.optionalInstallRequiresOwnerAction must be true")
    if rules.get("thirdPartyTermsMustBeCurrentAtRelease") is not True:
        failures.append("releaseRules.thirdPartyTermsMustBeCurrentAtRelease must be true")

    clearance = policy.get("artworkClearance", {})
    if not isinstance(clearance, dict):
        failures.append("artworkClearance must be an object")
    else:
        records = clearance.get("assets", [])
        recorded = {
            item.get("asset"): item.get("sha256")
            for item in records
            if isinstance(item, dict)
        } if isinstance(records, list) else {}
        if set(recorded) != set(EXPECTED_GAME_ART):
            failures.append("artwork clearance must cover every game-related Dagric master")
        for relative_asset, expected_hash in EXPECTED_GAME_ART.items():
            artwork = ROOT / relative_asset
            if not artwork.is_file():
                failures.append(f"missing cleared artwork: {relative_asset}")
                continue
            actual_hash = sha256(artwork)
            if actual_hash in BLOCKED_GAMING_ART_SHA256:
                failures.append(f"rejected or retired game artwork has returned: {relative_asset}")
            if actual_hash != expected_hash:
                failures.append(
                    f"{relative_asset} changed without a new visual-clearance record: {actual_hash}"
                )
            if recorded.get(relative_asset) != actual_hash:
                failures.append(f"artwork clearance hash does not match {relative_asset}")
        retired = clearance.get("rejectedOrRetiredPredecessorSha256", [])
        if set(retired) != BLOCKED_GAMING_ART_SHA256:
            failures.append("artwork clearance does not record every rejected/retired predecessor")
        if clearance.get("reviewedOn") != "2026-09-04":
            failures.append("artwork clearance review date is missing or unexpected")
        if clearance.get("reviewedBy") != "Dagric release engineering":
            failures.append("artwork clearance must name the neutral internal review role")
        if clearance.get("humanLegalReviewRequiredBeforeCommercialRelease") is not True:
            failures.append("artwork clearance must preserve the human legal-review requirement")

    integrations = integration_map(policy)
    for required_id in (
        "steam",
        "steam-devices",
        "heroic",
        "gog",
        "epic-games-store",
        "amazon-games",
        "lutris",
        "bottles",
        "protonup-qt",
        "ge-proton",
        "wine-winetricks-dxvk",
        "nvidia-firmware",
        "nvidia-driver",
    ):
        if required_id not in integrations:
            failures.append(f"missing required integration record: {required_id}")

    packages = package_names()
    for package in sorted(name for name in packages if forbidden_client_package(name)):
        locations = ", ".join(str(path.relative_to(ROOT)) for path in packages[package])
        failures.append(f"proprietary client {package!r} is listed for image inclusion in {locations}")

    expected_helpers = {
        "steam": (False, "/usr/bin/dagric-get-steam", "steam-installer"),
        "heroic": (False, "/usr/bin/dagric-get-heroic", "com.heroicgameslauncher.hgl"),
        "bottles": (False, "/usr/bin/dagric-get-bottles", "com.usebottles.bottles"),
        "protonup-qt": (False, "/usr/bin/dagric-get-protonup", "net.davidotek.pupgui2"),
    }
    for integration_id, (bundled, helper, identifier) in expected_helpers.items():
        record = integrations.get(integration_id, {})
        if record.get("bundledApplication") is not bundled:
            failures.append(f"{integration_id}.bundledApplication must be {bundled}")
        if record.get("usesOfficialPlatformLogo") is not False:
            failures.append(f"{integration_id}.usesOfficialPlatformLogo must be false")
        if record.get("compatibilityGuaranteed") is not False:
            failures.append(f"{integration_id}.compatibilityGuaranteed must be false")
        delivery = record.get("delivery", {})
        if not isinstance(delivery, dict):
            failures.append(f"{integration_id}.delivery must be an object")
            continue
        if delivery.get("helper") != helper or delivery.get("identifier") != identifier:
            failures.append(f"{integration_id} delivery helper or identifier drifted from policy")
        helper_path = INC / helper.lstrip("/")
        require_tokens(helper_path, (identifier, "[y/N]", "No changes made."), failures)

    steam = integrations.get("steam", {})
    steam_delivery = steam.get("delivery", {}) if isinstance(steam, dict) else {}
    if not isinstance(steam_delivery, dict) or steam_delivery.get("repositoryComponent") != "contrib":
        failures.append("steam delivery must identify Debian's contrib component")
    steam_helper = INC / "usr/bin/dagric-get-steam"
    require_tokens(
        steam_helper,
        (
            "proprietary game store and launcher",
            "https://store.steampowered.com/subscriber_agreement/",
            "Debian's installer",
        ),
        failures,
    )

    lutris = integrations.get("lutris", {})
    if lutris.get("bundledApplication") is not True or "pro" not in lutris.get("bundledEditions", []):
        failures.append("Lutris policy must identify the Pro image inclusion")
    if "lutris" not in packages:
        failures.append("Lutris policy says it is bundled, but no image package list contains lutris")

    steam_devices = integrations.get("steam-devices", {})
    if steam_devices.get("containsProprietarySteamClient") is not False:
        failures.append("steam-devices must be distinguished from the proprietary client")
    if steam_devices.get("bundledApplication") is not False:
        failures.append("steam-devices must stay out of future base images")
    declared_lists = sorted((ROOT / "config/package-lists").glob("*.list.chroot"))
    for package_list in declared_lists:
        declared = {
            normalized_package_name(line)
            for line in package_list.read_text(encoding="utf-8").splitlines()
        }
        if "steam-devices" in declared:
            failures.append(f"steam-devices remains in base image list {package_list.relative_to(ROOT)}")
    require_tokens(
        steam_helper,
        ("steam-devices", "/dev/uinput", "untrusted local users"),
        failures,
    )

    ge_proton = integrations.get("ge-proton", {})
    ge_delivery = ge_proton.get("delivery", {}) if isinstance(ge_proton, dict) else {}
    if not isinstance(ge_delivery, dict) or ge_delivery.get("mode") != (
        "owner-initiated-official-github-release-with-sha256-verification"
    ):
        failures.append("GE-Proton policy must record owner-initiated SHA-256 verification")
    require_tokens(
        INC / "usr/bin/dagric-gaming",
        ("sha256:[0-9a-f]{64}", "sha256sum", "[y/N]"),
        failures,
    )

    for service_id in ("gog", "epic-games-store", "amazon-games"):
        service = integrations.get(service_id, {})
        if service.get("bundledApplication") is not False:
            failures.append(f"{service_id} must not be represented as bundled")
        if service.get("usesOfficialPlatformLogo") is not False:
            failures.append(f"{service_id} must require original generic artwork")
        if not str(service.get("terms", "")).startswith("https://"):
            failures.append(f"{service_id} must record a current terms URL")

    nvidia_firmware = integrations.get("nvidia-firmware", {})
    if nvidia_firmware.get("bundledApplication") is not True:
        failures.append("NVIDIA firmware must be disclosed as bundled")
    for package in ("firmware-nvidia-graphics", "firmware-nvidia-tesla-535-gsp"):
        if package not in packages:
            failures.append(f"published manifests do not disclose bundled {package}")

    store = INC / "usr/bin/dagric-store"
    require_tokens(store, ("dagric-get-steam", "dagric-get-heroic", "dagric-get-protonup", "not affiliated"), failures)
    if store.is_file() and re.search(
        r"(?:sudo\s+)?apt(?:-get)?\s+install(?:\s+-\S+)*\s+steam(?:\s|[\"'])",
        store.read_text(encoding="utf-8", errors="replace"),
        re.IGNORECASE,
    ):
        failures.append("Dagric Store bypasses the Steam consent helper with a direct apt command")

    first_run = INC / "usr/bin/dagric-firstrun"
    first_run_qml = INC / "usr/share/dagric/firstrun/main.qml"
    first_run_tokens = (
        "Some choices are third-party or proprietary; none is required.",
        "Optional proprietary Valve client; vendor terms apply.",
        "/usr/bin/dagric-get-steam || true",
    )
    require_tokens(first_run, first_run_tokens, failures)
    require_tokens(first_run_qml, first_run_tokens[:2], failures)
    if first_run.is_file() and re.search(
        r"\|\s*/usr/bin/dagric-get-", first_run.read_text(encoding="utf-8"), re.IGNORECASE
    ):
        failures.append("first-run pre-answers an optional installer confirmation")

    migration = INC / "usr/share/dagric/migrate-continuity.py"
    require_tokens(migration, ("dagric-get-steam",), failures)
    if migration.is_file() and re.search(
        r"(?:sudo\s+)?apt(?:-get)?\s+install(?:\s+-\S+)*\s+steam(?:\s|[\"'])",
        migration.read_text(encoding="utf-8", errors="replace"),
        re.IGNORECASE,
    ):
        failures.append("migration advice bypasses the Steam disclosure helper")

    banned_claims = (
        "All of it is free software",
        "Steam is free software",
    )
    claim_surfaces = (
        first_run,
        first_run_qml,
        ROOT / "po/dagric-data-strings.sh",
        ROOT / "po/dagric.pot",
        ROOT / "po/de.po",
        ROOT / "po/es.po",
        ROOT / "po/fr.po",
        ROOT / "po/it.po",
        ROOT / "po/pt_BR.po",
        ROOT / "docs/EDITIONS.md",
        INC / "usr/bin/dagric-hub",
    )
    for path in claim_surfaces:
        forbid_tokens(path, banned_claims, failures)

    manual_root = INC / "usr/share/dagric/manual"
    manuals = {
        "app-steam.html": ("not bundled", "compatibility", "not affiliated"),
        "app-heroic.html": ("provider's current terms", "compatibility varies", "independent"),
        "app-lutris.html": ("review their source", "not a security sandbox", "not affiliated"),
    }
    for filename, tokens in manuals.items():
        require_tokens(manual_root / filename, tokens, failures)

    banned_manual_claims = (
        "nobody may redistribute it",
        "all work under Lutris",
        "claim the free Epic game every week",
        "most of your library will simply work",
    )
    for path in (manual_root / name for name in manuals):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
        for claim in banned_manual_claims:
            if claim.casefold() in text:
                failures.append(f"{path.relative_to(ROOT)} contains banned guarantee/legal claim: {claim}")

    require_tokens(
        ROOT / "THIRD-PARTY-NOTICES.md",
        (
            "Steam",
            "steam-devices",
            "Heroic Games Launcher",
            "GOG",
            "Epic Games",
            "Amazon Games",
            "Bottles",
            "ProtonUp-Qt",
            "GE-Proton",
            "firmware-nvidia-graphics",
            "not affiliated",
        ),
        failures,
    )
    require_tokens(
        ROOT / "LICENSES.md",
        (
            "firmware-nvidia-graphics",
            "firmware-nvidia-tesla-535-gsp",
            "NVIDIA firmware packages",
            "steam-devices",
        ),
        failures,
    )
    require_tokens(
        INC / "usr/bin/dagric-drivers",
        ("https://www.nvidia.com/en-us/drivers/nvidia-license/linux/", "[y/N]"),
        failures,
    )
    require_tokens(
        ROOT / "TRADEMARKS.md",
        ("Steam", "Valve", "GOG GALAXY", "Epic Games", "generic"),
        failures,
    )

    if failures:
        print("game-platform-policy: FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(
        "game-platform-policy: proprietary clients excluded; interactive consent, "
        "hash-pinned preliminary artwork review, notices, and compatibility boundaries passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
