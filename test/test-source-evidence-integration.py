#!/usr/bin/env python3
"""Offline evidence chain with tiny real ISO, SquashFS, DSC and tar.xz bytes.

No network, mounts, guest execution, private candidates or real source caches.
Native Debian tools are required; missing tools produce an explicit test skip.
The unsigned DSC fixtures are content evidence, never legal/signature approval.
"""

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_integration_fixtures", ROOT / "test/test-source-bundle.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
TOOLS = ("xorriso", "mksquashfs", "unsquashfs")
MISSING = [name for name in TOOLS if shutil.which(name) is None]
SUPPORTED = os.name == "posix" and not MISSING
SKIP_REASON = "requires native Debian/POSIX image tools: " + (", ".join(MISSING) if MISSING else "POSIX process pipes")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def source_tar(name):
    output = io.BytesIO()
    contents = (f"Exact isolated {name} source fixture. No code is executed.\n").encode()
    with tarfile.open(fileobj=output, mode="w:xz", format=tarfile.USTAR_FORMAT) as archive:
        info = tarfile.TarInfo(f"{name}-1.0/README")
        info.size, info.mtime, info.mode = len(contents), 0, 0o644
        archive.addfile(info, io.BytesIO(contents))
    payload = output.getvalue()
    # Confirm these are actual readable compressed archive bytes, not a dummy
    # byte string accepted solely because its digest happened to match.
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz") as archive:
        if archive.extractfile(f"{name}-1.0/README").read() != contents:
            raise AssertionError("fixture source archive was not readable")
    return payload


@unittest.skipUnless(SUPPORTED, SKIP_REASON)
class SourceEvidenceIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dagric-source-integration-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.args, _old_record, _old_dsc, _old_archive = fixtures.candidate(self.root)
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.primary, primary_dsc, primary_tar = fixtures.source(body=source_tar("demo"))
        self.embedded, embedded_dsc, embedded_tar = fixtures.source("embedded", "2:1.0-1", source_tar("embedded"))
        for payload in (primary_dsc, primary_tar, embedded_dsc, embedded_tar):
            (self.cache / (digest(payload) + ".blob")).write_bytes(payload)
        self.archive = self.cache / (digest(embedded_tar) + ".blob")
        supplement = {"format": "dagric-embedded-source-supplement-v1", "source_commit": fixtures.COMMIT, "entries": [self.embedded]}
        self.args.supplement.write_text(json.dumps(supplement), encoding="utf-8")

        primary_map = json.loads(self.args.map_path.read_text())
        index = json.loads(self.args.index.read_text())
        self.isos, self.statuses, self.manifests = {}, {}, {}
        for edition in ("free", "pro"):
            declaration = "Built-Using" if edition == "free" else "Static-Built-Using"
            status = ("Package: demo\nStatus: install ok installed\nArchitecture: amd64\nVersion: 1.0-1\n"
                      f"{declaration}: embedded (= 2:1.0-1)\n\n").encode()
            manifest = b"demo\t1.0-1\n"
            entries = [{"binary_name": "demo", "binary_version": "1.0-1", **copy.deepcopy(self.primary)}]
            if edition == "pro":
                status += b"Package: demo-extra\nStatus: install ok installed\nArchitecture: amd64\nVersion: 1.0-1\nSource: demo (1.0-1)\n\n"
                manifest += b"demo-extra\t1.0-1\n"
                entries.append({"binary_name": "demo-extra", "binary_version": "1.0-1", **copy.deepcopy(self.primary)})
            getattr(self.args, f"{edition}_status").write_bytes(status)
            getattr(self.args, f"{edition}_manifest").write_bytes(manifest)
            self.statuses[edition], self.manifests[edition] = status, manifest

            guest = self.root / f"{edition}-root"
            (guest / "var/lib/dpkg").mkdir(parents=True)
            (guest / "etc").mkdir()
            (guest / "var/lib/dpkg/status").write_bytes(status)
            (guest / "etc/dagric-edition").write_bytes((edition + "\n").encode())
            iso_tree = self.root / f"{edition}-iso-tree"
            (iso_tree / "live").mkdir(parents=True)
            (iso_tree / "live/filesystem.packages").write_bytes(manifest)
            self.native(["mksquashfs", str(guest), str(iso_tree / "live/filesystem.squashfs"),
                         "-noappend", "-all-root", "-processors", "1", "-comp", "gzip", "-no-progress"])
            iso = self.root / f"{edition}.iso"
            self.native(["xorriso", "-as", "mkisofs", "-quiet", "-R", "-J", "-V", f"DAGRIC_{edition.upper()}_TEST",
                         "-o", str(iso), str(iso_tree)])
            self.isos[edition] = iso
            iso_bytes = iso.read_bytes()
            setattr(self.args, f"{edition}_iso_sha256", digest(iso_bytes))
            row = next(item for item in index["release"]["artifacts"] if item["edition"] == edition)
            row.update(filename=iso.name, bytes=len(iso_bytes), sha256=digest(iso_bytes), binary_package_manifest_sha256=digest(manifest))
            primary_map["editions"][edition].update(binary_package_manifest_sha256=digest(manifest), entries=entries)
        self.args.index.write_text(json.dumps(index), encoding="utf-8")
        self.args.map_path.write_text(json.dumps(primary_map), encoding="utf-8")
        self.bundle_report = self.root / "bundle.json"
        self.binding_report = self.root / "image-binding.json"
        self.lock_path = self.root / "lock.json"

    def native(self, command):
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        return result

    def common_args(self):
        args = ["--map", str(self.args.map_path), "--index", str(self.args.index), "--supplement", str(self.args.supplement),
                "--dagric-commit", fixtures.COMMIT, "--cache", str(self.cache), "--workers", "2"]
        for edition in ("free", "pro"):
            for field in ("status", "manifest", "iso_sha256"):
                args += [f"--{edition}-{field.replace('_', '-')}", str(getattr(self.args, f"{edition}_{field}"))]
        return args

    def tool(self, filename, args, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / filename), *args], cwd=self.root,
                                capture_output=True, text=True, timeout=45, check=False)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def source_audit(self, expected=0):
        return self.tool("audit-source-bundle.py", self.common_args() + ["--output", str(self.bundle_report)], expected)

    def image_binding(self, *, free=None, pro=None, output=None, expected=0):
        return self.tool("check-source-bundle-images.py", ["--bundle-report", str(self.bundle_report),
                         "--free-iso", str(free or self.isos["free"]), "--pro-iso", str(pro or self.isos["pro"]),
                         "--output", str(output or self.binding_report)], expected)

    def source_lock(self, mode="create", expected=0):
        option = "--output" if mode == "create" else "--lock"
        return self.tool("source-candidate-lock.py", [mode, *self.common_args(), option, str(self.lock_path)], expected)

    def test_complete_real_byte_extraction_to_canonical_lock_chain(self):
        self.source_audit()
        self.image_binding()
        self.source_lock()
        original = self.lock_path.read_bytes()
        self.source_lock("check")
        self.assertEqual(self.lock_path.read_bytes(), original)
        source = json.loads(self.bundle_report.read_text())
        images = json.loads(self.binding_report.read_text())
        canonical = json.loads(original)
        self.assertEqual(source["status"], "exact-declared-source-objects-verified")
        self.assertEqual(source["source_identity_count"], 2)
        self.assertEqual(source["dsc_objects_verified"], 2)
        self.assertEqual(source["content_objects_verified"], 2)
        self.assertEqual(source["network_bytes_transferred"], 0)
        self.assertTrue(images["image_inventory_binding_verified"])
        self.assertEqual(images["bundle_report_sha256"], digest(self.bundle_report.read_bytes()))
        self.assertEqual(len(canonical["objects"]), 4)
        for row in images["editions"]:
            edition = row["edition"]
            self.assertEqual(row["embedded_edition"], edition)
            self.assertEqual(row["sha256"], digest(self.isos[edition].read_bytes()))
            self.assertEqual(row["package_manifest_sha256"], digest(self.manifests[edition]))
            self.assertEqual(row["dpkg_status_sha256"], digest(self.statuses[edition]))
            self.assertEqual(canonical["editions"][edition]["dpkg_status_sha256"], row["dpkg_status_sha256"])
        self.assertNotEqual(images["editions"][0]["dpkg_status_sha256"], images["editions"][1]["dpkg_status_sha256"])
        self.assertEqual(canonical["editions"]["free"]["declared_embedded_sources"][0]["field"], "Built-Using")
        self.assertEqual(canonical["editions"]["pro"]["declared_embedded_sources"][0]["field"], "Static-Built-Using")
        for document in (source, images, canonical):
            self.assertTrue(document["private"])
            self.assertFalse(document["release_approved"])
            self.assertFalse(document["corresponding_source_complete"])
        self.assertFalse(source["openpgp_signatures_verified"])
        self.assertFalse(canonical["source_authenticity_verified"])
        self.assertFalse(canonical["independent_image_extraction_verified"])
        self.assertFalse(canonical["public_delivery_verified"])

    def test_swapped_real_image_fails_without_binding_or_lock(self):
        self.source_audit()
        result = self.image_binding(free=self.isos["pro"], expected=1)
        self.assertIn("BLOCKED", result.stderr)
        self.assertFalse(self.binding_report.exists())
        self.assertFalse(self.lock_path.exists())

    def test_mutated_image_does_not_replace_previous_or_write_new_binding(self):
        self.source_audit()
        self.image_binding()
        original = self.binding_report.read_bytes()
        # Keep length identical: this must fail the real byte hash, not merely
        # the recorded size. Only this disposable test fixture is modified.
        payload = bytearray(self.isos["pro"].read_bytes())
        payload[0] ^= 1
        self.isos["pro"].write_bytes(payload)
        new_output = self.root / "changed-image-binding.json"
        result = self.image_binding(output=new_output, expected=1)
        self.assertIn("actual ISO SHA-256 differs", result.stderr)
        self.assertFalse(new_output.exists())
        self.assertEqual(self.binding_report.read_bytes(), original)

    def test_substituted_status_inventory_is_rejected_by_actual_extraction(self):
        # Still a valid dpkg inventory with identical package/source identities,
        # but it is not the exact inventory contained in the Pro ISO.
        path = self.args.pro_status
        path.write_bytes(path.read_bytes() + b"\n")
        self.source_audit()
        result = self.image_binding(expected=1)
        self.assertIn("immutable dpkg status differs", result.stderr)
        self.assertFalse(self.binding_report.exists())
        self.assertFalse(self.lock_path.exists())

    def test_missing_source_cannot_create_successful_source_lock(self):
        self.archive.unlink()  # disposable tiny fixture object only
        self.source_audit(expected=1)
        incomplete = json.loads(self.bundle_report.read_text())
        self.assertEqual(incomplete["status"], "incomplete")
        self.assertEqual(incomplete["content_objects_missing"], 1)
        self.assertFalse(incomplete["release_approved"])
        result = self.source_lock(expected=1)
        self.assertIn("complete exact source-cache verification is required", result.stderr)
        self.assertFalse(self.lock_path.exists())
        self.assertFalse(self.binding_report.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
