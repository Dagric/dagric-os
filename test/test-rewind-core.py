#!/usr/bin/env python3
"""Unit tests for the unprivileged Dagric Rewind data model."""

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "config/includes.chroot/usr/lib/dagric/rewind_core.py"
SPEC = importlib.util.spec_from_file_location("rewind_core", MODULE)
rewind = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(rewind)


class SnapperJsonTests(unittest.TestCase):
    def test_accepts_nested_and_top_level_layouts(self):
        nested = {
            "root": {
                "config": "root",
                "snapshots": [
                    {"number": 2, "type": "pre", "date": "2026-09-01", "description": "before"},
                    {"number": "3", "type": "post", "date": "2026-09-01", "description": "after"},
                ],
            }
        }
        self.assertEqual([2, 3], [row["number"] for row in rewind.normalize_snapper_json(nested)])
        self.assertEqual(1, len(rewind.normalize_snapper_json([
            {"number": 7, "type": "single", "description": "checkpoint"}
        ])))

    def test_rejects_unrelated_numbers_and_deduplicates(self):
        value = {
            "metadata": {"number": 99},
            "snapshots": [
                {"number": 4, "date": "old", "description": "old"},
                {"number": 4, "date": "new", "description": "new"},
                {"number": "not-a-number", "type": "single", "date": "bad"},
            ],
        }
        rows = rewind.normalize_snapper_json(value)
        self.assertEqual([4], [row["number"] for row in rows])
        self.assertEqual("new", rows[0]["description"])


class StatusSummaryTests(unittest.TestCase):
    def test_summarizes_without_reading_contents(self):
        summary = rewind.parse_snapper_status([
            "+..... /etc/dagric/new.conf",
            "c..... /usr/bin/example",
            "-..... /boot/old-kernel",
            ".p.... /var/lib/dpkg/status",
            "c..... /home/alex/.config/example",
            "c..... /var/log/journal/noise",
            "c..... /tmp/noise",
            "+..... /var/lib/dagric/rewind/current.json",
            "c..... /var/lib/timekpr/work/alex.time",
            "c..... /boot/grub/grub-btrfs.cfg",
        ])
        self.assertEqual(5, summary["total"])
        self.assertEqual(1, summary["added"])
        self.assertEqual(3, summary["modified"])
        self.assertEqual(1, summary["deleted"])
        self.assertEqual(5, summary["ignoredNoise"])
        categories = {row["name"]: row["count"] for row in summary["categories"]}
        self.assertEqual(2, categories["Software"])
        self.assertEqual(1, categories["Settings"])
        self.assertEqual(1, categories["Boot"])
        self.assertEqual(1, categories["Other"])
        self.assertNotIn("contents", summary)

    def test_caps_the_visible_path_list(self):
        summary = rewind.parse_snapper_status(
            [f"c..... /etc/example-{number}" for number in range(6)], path_limit=2
        )
        self.assertEqual(6, summary["total"])
        self.assertEqual(2, len(summary["paths"]))
        self.assertTrue(summary["truncated"])

    def test_dpkg_is_software_not_generic_var(self):
        self.assertEqual("Software", rewind.category_for("/var/lib/dpkg/status"))
        self.assertEqual("System state", rewind.category_for("/var/lib/random-seed"))


class PublicDataTests(unittest.TestCase):
    def test_snapshot_output_is_bounded(self):
        row = rewind.public_snapshot({
            "number": "12",
            "type": "post",
            "pre-number": "11",
            "date": "2026-09-01T10:00:00Z",
            "description": "x" * 500,
            "read-only": True,
            "secret": "never expose this",
        })
        self.assertEqual(12, row["number"])
        self.assertEqual(11, row["preNumber"])
        self.assertLessEqual(len(row["description"]), 160)
        self.assertNotIn("secret", row)

    def test_only_exact_dagric_apt_pairs_become_automatic_sessions(self):
        rows = [
            {"number": 10, "type": "pre", "date": "2026-09-01T10:00:00Z", "description": "apt (pre)"},
            {"number": 11, "type": "post", "pre-number": 10, "date": "2026-09-01T10:02:00Z", "description": "apt (post)"},
            {"number": 20, "type": "pre", "date": "2026-09-01T11:00:00Z", "description": "not apt"},
            {"number": 21, "type": "post", "pre-number": 20, "date": "2026-09-01T11:02:00Z", "description": "apt (post)"},
            {"number": 31, "type": "post", "pre-number": 30, "date": "2026-09-01T12:00:00Z", "description": "apt (post)"},
        ]
        sessions = rewind.automatic_apt_sessions(rows)
        self.assertEqual(1, len(sessions))
        self.assertEqual((10, 11), (sessions[0]["pre"], sessions[0]["post"]))
        self.assertTrue(rewind.is_automatic_apt_pair(rows, 10, 11))
        self.assertFalse(rewind.is_automatic_apt_pair(rows, 20, 21))


if __name__ == "__main__":
    unittest.main()
