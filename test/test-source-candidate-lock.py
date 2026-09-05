#!/usr/bin/env python3
"""Offline canonical source-lock regressions using tiny exact source fixtures."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_lock", ROOT / "tools/source-candidate-lock.py")
lock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lock)
spec = importlib.util.spec_from_file_location("source_lock_fixtures", ROOT / "test/test-source-bundle.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class SourceLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.args, self.record, self.dsc, self.body = fixtures.candidate(self.root)
        self.args.cache, self.args.workers = self.root / "cache", 2
        self.args.cache.mkdir()
        for payload in (self.dsc, self.body):
            self.cache_path(payload).write_bytes(payload)
        index = json.loads(self.args.index.read_text())
        for row in index["release"]["artifacts"]:
            row["filename"] = row["edition"] + ".iso"
        self.args.index.write_text(json.dumps(index))
        self.output = self.root / "lock.json"

    def cache_path(self, payload):
        return self.args.cache / (fixtures.digest(payload) + ".blob")

    def create(self):
        document = lock.source_lock(self.args)
        lock.write_new(self.output, document)
        return document

    def cli(self, mode="create"):
        args = [mode, "--map", str(self.args.map_path), "--supplement", str(self.args.supplement), "--index", str(self.args.index),
                "--dagric-commit", self.args.dagric_commit, "--cache", str(self.args.cache), "--workers", "2"]
        for edition in ("free", "pro"):
            for field in ("status", "manifest", "iso_sha256"):
                args += [f"--{edition}-{field.replace('_', '-')}", str(getattr(self.args, f"{edition}_{field}"))]
        return args + (["--output", str(self.output)] if mode == "create" else ["--lock", str(self.output)])

    def test_create_and_check_deterministic_candidate_binding(self):
        document = self.create()
        self.assertEqual(lock.verify_lock(self.output, self.args), document)
        self.assertEqual(self.output.read_bytes(), lock.canonical(lock.source_lock(self.args)))
        self.assertEqual(document["source_commit"], fixtures.COMMIT)
        for edition in ("free", "pro"):
            row = document["editions"][edition]
            self.assertEqual(row["iso_sha256_from_supplied_receipts"], fixtures.ISO[edition])
            self.assertEqual(row["iso_size_bytes"], 1024)
            self.assertEqual(row["dpkg_status_sha256"], fixtures.digest(getattr(self.args, f"{edition}_status").read_bytes()))
            self.assertEqual(row["package_manifest_sha256"], fixtures.digest(getattr(self.args, f"{edition}_manifest").read_bytes()))
        self.assertEqual(len(document["sources"]), 1)
        self.assertEqual(len(document["objects"]), 2)

    def test_all_approval_claims_stay_false(self):
        document = self.create()
        self.assertTrue(document["private"])
        for field in lock.FALSE_FIELDS:
            self.assertIs(document[field], False)
            changed = copy.deepcopy(document)
            changed[field] = True
            with self.subTest(field=field), self.assertRaisesRegex(lock.Error, "cannot claim"):
                lock.lock_shape(changed)

    def test_no_index_report_self_hash_cycle_or_volatile_timestamp(self):
        before = lock.canonical(lock.source_lock(self.args))
        for forbidden in (b'"source_index_sha256"', b'"bundle_report_sha256"', b'"self_sha256"', b'"generated_utc"'):
            self.assertNotIn(forbidden, before)
        # An index may now safely reference this lock. Only the immutable
        # candidate identity, not the containing index's hash, enters the lock.
        index = json.loads(self.args.index.read_text())
        index["proposed_source_lock_sha256"] = fixtures.digest(before)
        index["status"] = "still-private"
        self.args.index.write_text(json.dumps(index))
        self.assertEqual(before, lock.canonical(lock.source_lock(self.args)))

    def test_complete_flags_in_input_index_are_not_release_authority(self):
        index = json.loads(self.args.index.read_text())
        index.update(status="complete", release_approved=True, corresponding_source_complete=True)
        self.args.index.write_text(json.dumps(index))
        document = lock.source_lock(self.args)
        for field in lock.FALSE_FIELDS:
            self.assertIs(document[field], False)

    def test_complete_cache_is_mandatory_not_detached_success(self):
        self.cache_path(self.body).unlink()
        index = json.loads(self.args.index.read_text())
        index["source_bundle_status"] = "exact-declared-source-objects-verified"
        self.args.index.write_text(json.dumps(index))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lock.main(self.cli()), 1)
        self.assertFalse(self.output.exists())

    def test_poisoned_cache_fails_without_output_or_repair(self):
        self.cache_path(self.body).write_bytes(b"changed")
        with self.assertRaisesRegex(lock.Error, "complete exact source-cache"):
            lock.source_lock(self.args)
        self.assertEqual(self.cache_path(self.body).read_bytes(), b"changed")
        self.assertFalse(self.output.exists())

    def test_changed_index_commit_and_iso_receipt_are_rejected(self):
        for key, value in (("dagric_commit", "b" * 40), ("free_iso_sha256", "0" * 64)):
            args = copy.copy(self.args)
            setattr(args, key, value)
            with self.subTest(key=key), self.assertRaises(lock.Error):
                lock.source_lock(args)

    def test_unsafe_artifact_name_is_rejected_before_content_audit(self):
        index = json.loads(self.args.index.read_text())
        index["release"]["artifacts"][0]["filename"] = "../free.iso"
        self.args.index.write_text(json.dumps(index))
        with patch.object(lock.bundle, "audit", side_effect=AssertionError("must not hash cache")), self.assertRaisesRegex(lock.Error, "artifact filename"):
            lock.source_lock(self.args)

    def test_mutated_lock_identity_objects_and_unknown_members_rejected(self):
        original = self.create()
        for mutate in (lambda d: d["editions"]["free"].update(iso_size_bytes=1025),
                       lambda d: d["objects"].pop(), lambda d: d["sources"][0].update(source_version="2.0-1"),
                       lambda d: d.update(report_sha256="f" * 64)):
            changed = copy.deepcopy(original)
            mutate(changed)
            self.output.write_bytes(lock.canonical(changed))
            with self.subTest(changed=changed), self.assertRaises(lock.Error):
                lock.verify_lock(self.output, self.args)

    def test_noncanonical_and_duplicate_json_rejected(self):
        original = self.create()
        self.output.write_text(json.dumps(original, indent=2))
        with self.assertRaisesRegex(lock.Error, "not canonical"):
            lock.verify_lock(self.output, self.args)
        self.output.write_text('{"format":"one","format":"two"}')
        with self.assertRaisesRegex(lock.Error, "duplicate JSON"):
            lock.verify_lock(self.output, self.args)

    def test_offline_only_never_creates_network_request(self):
        with patch.object(lock.bundle.ObjectCache, "network_chunk", side_effect=AssertionError("network forbidden")):
            self.create()
        self.assertEqual({p.name for p in self.args.cache.iterdir()}, {self.cache_path(self.body).name, self.cache_path(self.dsc).name})

    def test_source_input_mutation_during_verification_rejected(self):
        real_audit = lock.bundle.audit
        def altered(*args):
            report = real_audit(*args)
            self.args.pro_status.write_bytes(self.args.pro_status.read_bytes() + b"\n")
            return report
        with patch.object(lock.bundle, "audit", side_effect=altered), self.assertRaisesRegex(lock.Error, "changed during"):
            lock.source_lock(self.args)

    def test_existing_output_refused_before_expensive_validation(self):
        self.output.write_bytes(b"existing receipt")
        before = {p.name for p in self.root.iterdir()}
        with patch.object(lock, "source_lock", side_effect=AssertionError("must not audit")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lock.main(self.cli()), 1)
        self.assertEqual(self.output.read_bytes(), b"existing receipt")
        self.assertEqual({p.name for p in self.root.iterdir()}, before)

    def test_publication_failure_leaves_no_partial_or_temporary_lock(self):
        document = lock.source_lock(self.args)
        with patch.object(lock.os, "link", side_effect=OSError("fixture publish failed")), self.assertRaises(OSError):
            lock.write_new(self.output, document)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".source-lock-*")))

    def test_destination_race_never_overwrites_other_receipt(self):
        document = lock.source_lock(self.args)
        original_link = lock.os.link
        def compete(source, destination):
            self.output.write_bytes(b"other process receipt")
            return original_link(source, destination)
        with patch.object(lock.os, "link", side_effect=compete), self.assertRaises(OSError):
            lock.write_new(self.output, document)
        self.assertEqual(self.output.read_bytes(), b"other process receipt")
        self.assertFalse(list(self.root.glob(".source-lock-*")))

    def test_cli_check_is_read_only_and_mode_arguments_do_not_mix(self):
        self.create()
        before = self.output.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lock.main(self.cli("check")), 0)
        self.assertEqual(self.output.read_bytes(), before)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lock.main(self.cli("check") + ["--output", str(self.root / "bad.json")]), 1)
        self.assertFalse((self.root / "bad.json").exists())

    def test_declared_embedded_sources_and_shared_content_retained(self):
        extra, dsc, body = fixtures.source("embedded", "2:1.0-1", self.body)
        supplement = json.loads(self.args.supplement.read_text())
        supplement["entries"] = [extra]
        self.args.supplement.write_text(json.dumps(supplement))
        self.cache_path(dsc).write_bytes(dsc)
        for edition, field in (("free", "Built-Using"), ("pro", "Static-Built-Using")):
            path = getattr(self.args, f"{edition}_status")
            path.write_bytes(path.read_bytes().rstrip() + f"\n{field}: embedded (= 2:1.0-1)\n\n".encode())
        document = self.create()
        self.assertEqual(len(document["sources"]), 2)
        self.assertEqual(len(document["objects"]), 3)  # two DSCs + one shared tar
        for edition, field in (("free", "Built-Using"), ("pro", "Static-Built-Using")):
            row = document["editions"][edition]["declared_embedded_sources"][0]
            self.assertEqual(row["field"], field)
            self.assertEqual(row["source_version"], "2:1.0-1")
            self.assertEqual(row["binary_architecture"], "amd64")
        shared = next(row for row in document["objects"] if row["sha256"] == fixtures.digest(self.body))
        self.assertEqual(len(shared["filenames"]), 2)
        self.assertEqual(len(shared["upstream_urls"]), 2)

    def test_symlink_destination_and_cache_rejected(self):
        outside = self.root / "outside.json"
        outside.write_bytes(b"outside")
        try:
            self.output.symlink_to(outside)
        except OSError:
            self.skipTest("symlink permission unavailable")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lock.main(self.cli()), 1)
        self.assertEqual(outside.read_bytes(), b"outside")


if __name__ == "__main__":
    unittest.main()
