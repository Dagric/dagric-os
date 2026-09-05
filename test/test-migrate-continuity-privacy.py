#!/usr/bin/env python3
"""Privacy regression tests for opt-in Steam continuity migration."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config/includes.chroot/usr/share/dagric/migrate-continuity.py"
SPEC = importlib.util.spec_from_file_location("dagric_migrate_continuity", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def put(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


class SteamContinuityPrivacyTests(unittest.TestCase):
    def make_windows_profile(self, root: Path) -> tuple[Path, Path]:
        profile = root / "Users" / "Alice"
        steam = root / "Program Files (x86)" / "Steam"

        put(profile / "Saved Games" / "OpenGame" / "slot1.sav", "generic-save")
        put(profile / "Saved Games" / "OpenGame" / "account-token.json", "generic-token")
        put(profile / "Documents" / "My Games" / "Puzzle" / "progress.dat", "document-save")

        remote = steam / "userdata" / "123456" / "999" / "remote"
        put(remote / "campaign" / "save.bin", "steam-cloud-save")
        put(remote / "campaign" / "chapter-1" / "save2.bin", "nested-steam-cloud-save")
        put(remote / "session_token.dat", "steam-session-token")
        put(remote / "webcache" / "cache.bin", "steam-web-cache")
        put(remote / "client.key", "steam-private-key")

        screenshots = steam / "userdata" / "123456" / "760" / "remote" / "999" / "screenshots"
        put(screenshots / "match-01.jpg", "screenshot")
        put(screenshots / "screenshots.vdf", "screenshot-metadata")
        put(screenshots / "session-preview.png", "session-named-image")

        layouts = (
            steam
            / "steamapps"
            / "common"
            / "Steam Controller Configs"
            / "123456"
            / "config"
            / "999"
        )
        put(layouts / "my-layout.vdf", "controller-layout")
        put(layouts / "alternate.json", "controller-layout-json")
        put(layouts / "auth-layout.vdf", "controller-auth")
        put(layouts / "preview.png", "controller-preview")

        # These are deliberately outside every copy source, even though they
        # sit beside allowlisted user content in a normal Steam installation.
        put(steam / "config" / "loginusers.vdf", "steam-login-users")
        put(steam / "config" / "config.vdf", "steam-client-config")
        put(steam / "userdata" / "123456" / "config" / "localconfig.vdf", "steam-local-config")
        put(steam / "htmlcache" / "Cookies", "steam-cookie-store")
        put(
            steam / "steamapps" / "appmanifest_999.acf",
            '"AppState"\n{\n"appid" "999"\n"name" "Private Game Library Entry"\n"installdir" "PrivateGame"\n}',
        )
        return profile, steam

    def test_steam_reinstall_is_routed_through_consent_helper(self) -> None:
        plan = MODULE.APP_REPLACEMENTS["steam"]
        self.assertEqual(plan["install_hint"], "dagric-get-steam")
        self.assertEqual(plan["source_key"], "dagric")
        self.assertNotIn("apt install", plan["install_hint"])

    def test_gaming_sources_are_specific_user_content_leaves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile, steam = self.make_windows_profile(Path(directory))
            rows = MODULE.source_groups("gaming", str(profile))
            sources = {Path(source).resolve() for _, source in rows}

            self.assertIn((steam / "userdata" / "123456" / "999" / "remote").resolve(), sources)
            self.assertIn(
                (steam / "userdata" / "123456" / "760" / "remote" / "999" / "screenshots").resolve(),
                sources,
            )
            self.assertIn(
                (
                    steam
                    / "steamapps"
                    / "common"
                    / "Steam Controller Configs"
                    / "123456"
                    / "config"
                    / "999"
                ).resolve(),
                sources,
            )
            self.assertNotIn((steam / "userdata").resolve(), sources)
            self.assertNotIn((steam / "userdata" / "123456").resolve(), sources)
            self.assertNotIn((steam / "config").resolve(), sources)
            self.assertTrue(all(path.name.casefold() not in {"userdata", "config", "htmlcache"} for path in sources))

    def test_copy_keeps_allowlisted_material_and_filters_sensitive_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile, _ = self.make_windows_profile(root)
            output = root / "output"

            results = []
            for index, (label, source) in enumerate(MODULE.source_groups("gaming", str(profile)), 1):
                results.append(
                    MODULE.copy_source("gaming", label, source, str(output / ("source-%02d" % index)))
                )

            copied_contents = {
                item.read_text(encoding="utf-8")
                for item in output.rglob("*")
                if item.is_file()
            }
            self.assertTrue(
                {"generic-save", "document-save", "steam-cloud-save", "nested-steam-cloud-save", "screenshot", "controller-layout", "controller-layout-json"}
                <= copied_contents
            )
            self.assertTrue(
                {
                    "generic-token",
                    "steam-session-token",
                    "steam-web-cache",
                    "steam-private-key",
                    "screenshot-metadata",
                    "session-named-image",
                    "controller-auth",
                    "controller-preview",
                    "steam-login-users",
                    "steam-client-config",
                    "steam-local-config",
                    "steam-cookie-store",
                }.isdisjoint(copied_contents)
            )
            self.assertGreater(sum(item["filtered_paths"] for item in results), 0)
            if os.name != "nt":
                for item in output.rglob("*"):
                    expected = 0o600 if item.is_file() else 0o700
                    self.assertEqual(stat.S_IMODE(item.stat().st_mode), expected, str(item))

    def test_unknown_gaming_source_label_cannot_bypass_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = put(root / "Steam" / "config" / "harmless-name.vdf", "unsafe-root")
            result = MODULE.copy_source("gaming", "Steam config", str(source), str(root / "output"))
            self.assertEqual(result["status"], "filtered")
            self.assertEqual(result["copied_files"], 0)
            self.assertFalse((root / "output").exists())

    def test_library_manifest_cannot_escape_the_windows_volume(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            external = Path(external_directory)
            profile, steam = self.make_windows_profile(root)
            external_remote = external / "userdata" / "777" / "4242" / "remote"
            put(external_remote / "outside.bin", "outside-volume")
            vdf_path = str(external).replace("\\", "\\\\")
            put(
                steam / "steamapps" / "libraryfolders.vdf",
                '"libraryfolders"\n{\n"1"\n{\n"path" "%s"\n}\n}' % vdf_path,
            )

            inventory = MODULE.steam_inventory(str(profile))
            sources = {Path(source).resolve() for _, source in MODULE.source_groups("gaming", str(profile))}
            self.assertNotIn(str(external), inventory["libraries"])
            self.assertNotIn(external_remote.resolve(), sources)

    def test_cli_report_describes_filtered_v3_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile, steam = self.make_windows_profile(root)
            output = root / "output"
            subprocess.run(
                [sys.executable, str(SOURCE), str(profile), str(output), "--copy", "gaming"],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads((output / MODULE.OUT_JSON).read_text(encoding="utf-8"))
            self.assertEqual(report["version"], 3)
            self.assertIn("best effort", report["privacy"])
            self.assertIn("tokens", report["privacy"])
            copy_sources = {Path(item["source"]).resolve() for item in report["copies"]["gaming"]}
            self.assertNotIn((steam / "userdata").resolve(), copy_sources)
            self.assertNotIn((steam / "config").resolve(), copy_sources)
            steam_plan = next(item["dagric_plan"] for item in report["apps"] if item["name"] == "Steam")
            self.assertEqual(steam_plan["install_hint"], "dagric-get-steam")

    def test_cli_does_not_inventory_steam_when_gaming_is_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile, _ = self.make_windows_profile(root)
            output = root / "output"
            subprocess.run(
                [sys.executable, str(SOURCE), str(profile), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads((output / MODULE.OUT_JSON).read_text(encoding="utf-8"))
            self.assertFalse(report["gaming"]["selected"])
            self.assertEqual(report["gaming"]["steam_libraries"], [])
            self.assertEqual(report["gaming"]["steam_games"], [])


if __name__ == "__main__":
    unittest.main()
