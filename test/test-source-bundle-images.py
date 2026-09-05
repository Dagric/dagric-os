#!/usr/bin/env python3
"""Offline image-binding regression fixtures; no QEMU, mounts or downloads."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_images", ROOT / "tools/check-source-bundle-images.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.iso = self.root / "candidate.iso"
        self.iso.write_bytes(b"isolated fake image bytes")
        self.payloads = (b"package 1.0\n", b"Package: package\nStatus: install ok installed\n", b"free\n")
        self.inputs = {"iso_sha256_from_supplied_receipts": {"free": audit.file_digest(self.iso)},
                       "iso_size_bytes_from_supplied_index": {"free": self.iso.stat().st_size},
                       "package_manifest_sha256": {"free": audit.sha256(self.payloads[0])},
                       "dpkg_status_sha256": {"free": audit.sha256(self.payloads[1])}}

    def verify(self, extractor=None):
        return audit.verify_edition("free", self.iso, self.inputs, self.root,
                                    extractor or (lambda iso, scratch: self.payloads))

    def test_matching_image_and_both_inventories_pass(self):
        result = self.verify()
        self.assertTrue(result["unchanged_during_inspection"])
        self.assertEqual(result["embedded_edition"], "free")

    def test_wrong_image_digest_rejected_before_extraction(self):
        self.inputs["iso_sha256_from_supplied_receipts"]["free"] = "0" * 64
        with self.assertRaisesRegex(audit.Error, "actual ISO SHA-256 differs"):
            self.verify(lambda *args: self.fail("must not extract mismatched image"))

    def test_wrong_size_rejected(self):
        self.inputs["iso_size_bytes_from_supplied_index"]["free"] += 1
        with self.assertRaisesRegex(audit.Error, "byte count"):
            self.verify()

    def test_wrong_edition_rejected(self):
        self.payloads = (*self.payloads[:2], b"pro\n")
        with self.assertRaisesRegex(audit.Error, "edition marker"):
            self.verify()

    def test_stale_manifest_and_status_each_rejected(self):
        for key in ("package_manifest_sha256", "dpkg_status_sha256"):
            with self.subTest(key=key):
                original = self.inputs[key]["free"]
                self.inputs[key]["free"] = "0" * 64
                with self.assertRaises(audit.Error):
                    self.verify()
                self.inputs[key]["free"] = original

    def test_image_changed_during_extraction_rejected(self):
        def mutate(*args):
            self.iso.write_bytes(b"x" * self.iso.stat().st_size)
            return self.payloads
        with self.assertRaisesRegex(audit.Error, "changed during"):
            self.verify(mutate)

    def test_missing_or_unrecognized_bundle_rejected(self):
        for report in ({}, {"format": "dagric-private-source-bundle-audit-v1", "release_approved": True}):
            with self.assertRaises(audit.Error):
                audit.validate_report(report)

    def test_extraction_failure_cannot_return_a_pass(self):
        def failed(*args):
            raise OSError("fixture extraction failed")
        with self.assertRaises(OSError):
            self.verify(failed)

    def main_fixture(self):
        inputs = {key: {"free": value["free"], "pro": value["free"]} for key, value in self.inputs.items()}
        inputs.update({key: "a" * 64 for key in ("primary_map_sha256", "supplement_sha256", "source_index_sha256")})
        report = {"format": "dagric-private-source-bundle-audit-v1", "private": True,
                  "release_approved": False, "source_commit": "b" * 40, "inputs": inputs, "status": "incomplete"}
        source = self.root / "bundle.json"
        source.write_text(json.dumps(report))
        output = self.root / "new-receipt.json"
        args = ["--bundle-report", str(source), "--free-iso", str(self.iso), "--pro-iso", str(self.iso), "--output", str(output)]
        return source, output, args

    def test_pro_failure_leaves_no_success_output(self):
        source, output, args = self.main_fixture()
        with mock.patch.object(audit, "verify_edition", side_effect=[{"edition": "free"}, audit.Error("Pro mismatch")]):
            self.assertEqual(audit.main(args), 1)
        self.assertFalse(output.exists())

    def test_report_mutation_leaves_no_success_output(self):
        source, output, args = self.main_fixture()
        def mutate(edition, *unused):
            source.write_text("{}")
            return {"edition": edition}
        with mock.patch.object(audit, "verify_edition", side_effect=mutate):
            self.assertEqual(audit.main(args), 1)
        self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        source, output, args = self.main_fixture()
        output.write_bytes(b"prior receipt")
        with mock.patch.object(audit, "verify_edition") as verifier:
            self.assertEqual(audit.main(args), 1)
            verifier.assert_not_called()
        self.assertEqual(output.read_bytes(), b"prior receipt")

    def test_passing_binding_never_upgrades_incomplete_source_or_release(self):
        source, output, args = self.main_fixture()
        with mock.patch.object(audit, "verify_edition", side_effect=lambda edition, *unused: {"edition": edition}):
            self.assertEqual(audit.main(args), 0)
        report = json.loads(output.read_text())
        self.assertTrue(report["image_inventory_binding_verified"])
        self.assertFalse(report["release_approved"])
        self.assertFalse(report["corresponding_source_complete"])
        self.assertEqual(report["bundle_status_not_reassessed"], "incomplete")

    def test_streaming_extractor_rejects_oversized_stdout_before_producer_finishes(self):
        marker = self.root / "producer-finished"
        program = ("import pathlib,sys\n"
                   "for _ in range(1024):\n"
                   " sys.stdout.buffer.write(b'x' * 65536); sys.stdout.buffer.flush()\n"
                   "pathlib.Path(sys.argv[1]).write_text('must not finish')\n")
        with self.assertRaisesRegex(audit.Error, "stdout exceeds 128 byte limit"):
            audit.command([sys.executable, "-c", program, str(marker)], max_bytes=128, timeout=5)
        self.assertFalse(marker.exists())

    def test_streaming_extractor_bounds_stderr_too(self):
        marker = self.root / "error-producer-finished"
        program = ("import pathlib,sys\n"
                   "for _ in range(1024):\n"
                   " sys.stderr.buffer.write(b'x' * 65536); sys.stderr.buffer.flush()\n"
                   "pathlib.Path(sys.argv[1]).write_text('must not finish')\n")
        with mock.patch.object(audit, "COMMAND_ERROR_LIMIT", 128):
            with self.assertRaisesRegex(audit.Error, "stderr exceeds 128 byte limit"):
                audit.command([sys.executable, "-c", program, str(marker)], max_bytes=128, timeout=5)
        self.assertFalse(marker.exists())

    def test_streaming_command_exact_limit_success_and_failed_exit(self):
        self.assertEqual(audit.command([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 128)"],
                                      max_bytes=128, timeout=5), b"x" * 128)
        with self.assertRaisesRegex(audit.Error, r"failed \(3\): fixture extraction failed"):
            audit.command([sys.executable, "-c", "import sys; sys.stderr.write('fixture extraction failed'); sys.exit(3)"],
                          max_bytes=128, timeout=5)

    def test_streaming_command_timeout_terminates_process(self):
        for program in ("import time; time.sleep(30)",
                        "import os,time; os.close(1); os.close(2); time.sleep(30)"):
            with self.subTest(program=program), self.assertRaises(subprocess.TimeoutExpired):
                audit.command([sys.executable, "-c", program], max_bytes=128, timeout=0.1)

    def test_oversized_manifest_rejected_before_reading_it(self):
        path = self.root / "filesystem.packages"
        path.write_bytes(b"x" * 9)
        with mock.patch.object(Path, "open", side_effect=AssertionError("oversized inventory must not be opened")):
            with self.assertRaisesRegex(audit.Error, "oversized package inventory"):
                audit.read_inventory(path, 8)
        path.write_bytes(b"x" * 8)
        self.assertEqual(audit.read_inventory(path, 8), b"x" * 8)
        path.write_bytes(b"")
        with self.assertRaisesRegex(audit.Error, "empty/oversized"):
            audit.read_inventory(path, 8)

    def test_extraction_routes_explicit_limits_and_invalid_manifest_stops_early(self):
        calls = []
        def extractor(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[0] == "xorriso":
                Path(argv[-1]).write_bytes(self.payloads[0] if argv[-2].endswith(".packages") else b"fixture squashfs")
                return b""
            return self.payloads[1] if argv[-1] == "var/lib/dpkg/status" else self.payloads[2]
        with mock.patch.object(audit, "command", side_effect=extractor):
            self.assertEqual(audit.extract_image(self.iso, self.root), self.payloads)
        self.assertEqual(calls[2][1], {"max_bytes": audit.STATUS_LIMIT})
        self.assertEqual(calls[3][1], {"max_bytes": audit.EDITION_LIMIT})
        calls.clear()
        with mock.patch.object(audit, "MANIFEST_LIMIT", 1), mock.patch.object(audit, "command", side_effect=extractor):
            with self.assertRaisesRegex(audit.Error, "oversized package inventory"):
                audit.extract_image(self.iso, self.root)
        self.assertEqual(len(calls), 1)

    def test_oversized_stream_cannot_write_binding_receipt(self):
        source, output, args = self.main_fixture()
        def oversized(*unused):
            return audit.command([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 129)"],
                                 max_bytes=128, timeout=5)
        with mock.patch.object(audit, "verify_edition", side_effect=oversized):
            self.assertEqual(audit.main(args), 1)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
