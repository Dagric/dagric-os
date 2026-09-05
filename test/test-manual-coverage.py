#!/usr/bin/env python3
"""Regression cases for the documentation failure found in the Pro build."""

import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "manual_coverage", ROOT / "tools/check-manual-coverage.py"
)
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


class ManualCoverageTests(unittest.TestCase):
    def setUp(self):
        self.index = (coverage.MANUAL / "index.html").read_text(encoding="utf-8")

    def test_current_sidebar_matches_actual_cards(self):
        self.assertEqual(coverage.check_group_counts(self.index), [])

    def test_rejects_original_dagric_sidebar_regression(self):
        broken = (
            '<a data-goto="g-dagric">Tools<span class="count">26</span></a>\n'
            '<section id="g-dagric">'
            + '<a class="card" href="tool.html">Tool</a>' * 27
            + '</section>'
        )
        self.assertTrue(any(
            "g-dagric: says 26; section contains 27 cards" in error
            for error in coverage.check_group_counts(broken)
        ))

    def test_balanced_group_errors_fail_even_when_total_is_unchanged(self):
        broken = (
            '<a data-goto="g-files">Files<span class="count">1</span></a>\n'
            '<a data-goto="g-photos">Photos<span class="count">3</span></a>\n'
            '<section id="g-files">'
            + '<a class="card" href="file.html">File</a>' * 2
            + '</section><section id="g-photos">'
            + '<a class="card" href="photo.html">Photo</a>' * 2
            + '</section>'
        )
        errors = coverage.check_group_counts(broken)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("g-files" in error for error in errors))
        self.assertTrue(any("g-photos" in error for error in errors))

    def test_missing_sidebar_group_is_reported(self):
        broken = self.index.replace('data-goto="g-dagric"', "", 1)
        self.assertIn(
            "manual section g-dagric: sidebar count is missing",
            coverage.check_group_counts(broken),
        )

    def test_sidebar_cannot_point_at_missing_section(self):
        broken = self.index.replace('id="g-dagric"', 'id="removed"', 1)
        self.assertIn(
            "manual sidebar g-dagric: section is missing",
            coverage.check_group_counts(broken),
        )

    def test_newly_installed_launchers_have_real_help(self):
        routes, errors = coverage.read_map(coverage.MAP)
        self.assertEqual(errors, [])
        for desktop in (
            "fcitx5-configtool.desktop",
            "org.fcitx.Fcitx5.desktop",
            "guvcview.desktop",
            "timekpr-admin-su.desktop",
            "timekpr-admin.desktop",
        ):
            with self.subTest(desktop=desktop):
                self.assertIn(desktop, routes)
                page = routes[desktop]
                content = (coverage.MANUAL / page).read_text(encoding="utf-8")
                self.assertIn(f'class="card" href="{page}"', self.index)
                self.assertIn("<h2>", content)
                self.assertEqual(content.count('<li><span class="t">'), 5)

    def test_restore_notes_routes_to_findable_migration_help(self):
        routes, errors = coverage.read_map(coverage.MAP)
        self.assertEqual(errors, [])
        self.assertEqual(
            routes.get("dagric-restore-assistant.desktop"),
            "tool-dagric-migrate.html",
        )
        card = re.search(
            r'<a class="card" href="tool-dagric-migrate.html"[^>]*data-s="([^"]+)"',
            self.index,
        )
        self.assertIsNotNone(card)
        self.assertIn("restore migration notes", card.group(1))
        help_text = (coverage.MANUAL / "tool-dagric-migrate.html").read_text(
            encoding="utf-8"
        )
        for filename in ("Dagric-Migration-State-Pack.json", "Dagric-Migration-Notes.html"):
            self.assertIn(filename, help_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
