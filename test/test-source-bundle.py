#!/usr/bin/env python3
"""Offline source bundle boundary tests; source bytes are tiny mocked fixtures."""

import argparse
import contextlib
import copy
import hashlib
import http.client
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_bundle", ROOT / "tools/audit-source-bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
COMMIT = "a" * 40
ISO = {"free": "e" * 64, "pro": "f" * 64}
BASE = "https://snapshot.debian.org/archive/debian/20260901T010203Z/pool/main/d/demo/"


def digest(body):
    return hashlib.sha256(body).hexdigest()


def source(name="demo", version="1.0-1", body=b"exact source tar bytes"):
    filename = f"{name}_1.0.orig.tar.xz"
    dsc = (f"Format: 3.0 (quilt)\nSource: {name}\nVersion: {version}\nChecksums-Sha256:\n {digest(body)} {len(body)} {filename}\n").encode()
    base = BASE.replace("/d/demo/", f"/{name[0]}/{name}/")
    record = {"source_name": name, "source_version": version, "origin": "debian",
              "locator": {"dsc_url": base + f"{name}_{version.split(':')[-1]}.dsc",
                          "debian_archive_url": "https://snapshot.debian.org/archive/debian/20260901T010203Z/"},
              "integrity": {"dsc_sha256": digest(dsc), "source_files": [{"filename": filename, "url": base + filename, "sha256": digest(body)}]}}
    return record, dsc, body


def candidate(folder):
    record, dsc, body = source()
    manifest = b"demo\t1.0-1\n"
    status = b"Package: demo\nStatus: install ok installed\nArchitecture: amd64\nVersion: 1.0-1\n\n"
    primary = {"format": "dagric-exact-binary-source-map-v1", "generated_utc": "2026-09-05T00:00:00Z", "editions": {
        edition: {"binary_package_manifest": f"{edition}.packages", "binary_package_manifest_sha256": digest(manifest),
                  "entries": [{"binary_name": "demo", "binary_version": "1.0-1", **copy.deepcopy(record)}]} for edition in ("free", "pro")}}
    index = {"release": {"source_commit": COMMIT, "artifacts": [
        {"edition": edition, "sha256": ISO[edition], "bytes": 1024, "binary_package_manifest": f"{edition}.packages", "binary_package_manifest_sha256": digest(manifest)} for edition in ("free", "pro")]}}
    supplement = {"format": "dagric-embedded-source-supplement-v1", "source_commit": COMMIT, "entries": []}
    args = argparse.Namespace(map_path=folder / "map.json", index=folder / "index.json", supplement=folder / "supplement.json", dagric_commit=COMMIT)
    for edition in ("free", "pro"):
        for kind, content in (("manifest", manifest), ("status", status)):
            path = folder / f"{edition}.{kind}"
            path.write_bytes(content)
            setattr(args, f"{edition}_{kind}", path)
        setattr(args, f"{edition}_iso_sha256", ISO[edition])
    for path, document in ((args.map_path, primary), (args.index, index), (args.supplement, supplement)):
        path.write_text(json.dumps(document), encoding="utf-8")
    return args, record, dsc, body


class Response(io.BytesIO):
    def __init__(self, body, url, headers=None, status=200):
        super().__init__(body)
        self.url, self.headers, self.status = url, headers or {}, status

    def geturl(self):
        return self.url


class Opener:
    def __init__(self, body, headers=None, status=200):
        self.body, self.headers, self.status, self.calls = body, headers, status, 0

    def open(self, request, **kwargs):
        self.calls += 1
        return Response(self.body, request.full_url, self.headers, self.status)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def obj(self, body=b"source"):
        return {"kind": "debian-source", "filename": "demo_1.0.orig.tar.xz", "url": BASE + "demo_1.0.orig.tar.xz", "sha256": digest(body), "size_bytes": len(body)}

    def test_dsc_exact_content_size(self):
        record, dsc, body = source(version="2:1.0-1")
        rows = bundle.verify_dsc(dsc, record)
        self.assertEqual(rows[0]["size_bytes"], len(body))
        self.assertEqual(rows[0]["sha256"], digest(body))

    def test_clearsigned_dsc_is_parsed_not_signature_approved(self):
        record, dsc, _body = source()
        signed = b"-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\n" + dsc + b"-----BEGIN PGP SIGNATURE-----\nfixture-not-valid-crypto\n-----END PGP SIGNATURE-----\n"
        record["integrity"]["dsc_sha256"] = digest(signed)
        self.assertEqual(len(bundle.verify_dsc(signed, record)), 1)

    def test_dsc_wrong_bytes_identity_missing_extra_and_duplicate_files(self):
        record, dsc, body = source()
        row = dsc.split(b"Checksums-Sha256:\n")[1]
        mutations = (dsc + b" ", dsc.replace(b"Source: demo", b"Source: other"), dsc.replace(b"Version: 1.0-1", b"Version: 1.0-2"),
                     dsc.replace(b"Checksums-Sha256", b"Checksums-Sha1"), dsc + row,
                     dsc + row.replace(b"demo_", b"extra_"), dsc.replace(str(len(body)).encode() + b" demo_", b"-1 demo_"),
                     dsc.replace(b"demo_1.0.orig", b"../demo_1.0.orig"), dsc + b"Source: demo\n")
        for index, payload in enumerate(mutations):
            changed = copy.deepcopy(record)
            if index:
                changed["integrity"]["dsc_sha256"] = digest(payload)
            with self.subTest(index=index), self.assertRaises(bundle.Error):
                bundle.verify_dsc(payload, changed)

    def test_dsc_wrong_source_digest(self):
        record, dsc, _body = source()
        record["integrity"]["source_files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(bundle.Error, "digest mismatch"):
            bundle.verify_dsc(dsc, record)

    def test_candidate_binds_every_supplied_input(self):
        args, _record, _dsc, _body = candidate(self.folder)
        sources, binding, inventory = bundle.candidate_inputs(args)
        self.assertEqual(set(sources), {("demo", "1.0-1")})
        self.assertEqual(binding["iso_sha256_from_supplied_receipts"], ISO)
        self.assertEqual(binding["dpkg_status_sha256"]["free"], digest(args.free_status.read_bytes()))
        self.assertEqual(binding["package_manifest_sha256"]["free"], digest(args.free_manifest.read_bytes()))
        self.assertEqual(binding["source_index_sha256"], digest(args.index.read_bytes()))
        self.assertFalse(inventory["release_approved"])

    def test_stale_commit_wrong_iso_and_changed_manifest_rejected(self):
        args, *_ = candidate(self.folder)
        for key, value in (("dagric_commit", "b" * 40), ("free_iso_sha256", "0" * 64)):
            altered = copy.copy(args)
            setattr(altered, key, value)
            with self.subTest(key=key), self.assertRaises(bundle.Error):
                bundle.candidate_inputs(altered)
        args.free_manifest.write_bytes(b"demo\t2.0-1\n")
        with self.assertRaisesRegex(bundle.Error, "manifest digest mismatch"):
            bundle.candidate_inputs(args)

    def test_map_source_must_match_status_source_field(self):
        args, *_ = candidate(self.folder)
        args.free_status.write_bytes(args.free_status.read_bytes().replace(b"Version: 1.0-1", b"Version: 1.0-1\nSource: other (2.0-1)"))
        with self.assertRaisesRegex(bundle.Error, "disagrees with immutable dpkg Source"):
            bundle.candidate_inputs(args)

    def test_installed_epoch_binnmu_source_version_is_exact(self):
        args, *_ = candidate(self.folder)
        primary = json.loads(args.map_path.read_text())
        record, _dsc, _body = source(version="2:1.0-1")
        for edition in primary["editions"].values():
            edition["entries"] = [{"binary_name": "demo", "binary_version": "2:1.0-1+b1", **record}]
        body = b"Package: demo\nStatus: install ok installed\nArchitecture: amd64\nVersion: 2:1.0-1+b1\nSource: demo (2:1.0-1)\n\n"
        bundle.verify_primary_status({"free": body, "pro": body}, primary, COMMIT)
        with self.assertRaises(bundle.Error):
            bundle.verify_primary_status({"free": body.replace(b"Source: demo (2:1.0-1)", b"Source: demo (2:1.0-2)"), "pro": body}, primary, COMMIT)

    def test_missing_declared_supplement_and_extra_supplement_rejected(self):
        args, *_ = candidate(self.folder)
        args.free_status.write_bytes(args.free_status.read_bytes().rstrip() + b"\nBuilt-Using: missing (= 1.0-1)\n\n")
        with self.assertRaisesRegex(bundle.Error, "missing exact declared"):
            bundle.candidate_inputs(args)
        args, *_ = candidate(self.folder)
        supplement = json.loads(args.supplement.read_text())
        supplement["entries"] = [source("unused")[0]]
        args.supplement.write_text(json.dumps(supplement))
        with self.assertRaisesRegex(bundle.Error, "undeclared extraneous"):
            bundle.candidate_inputs(args)

    def test_duplicate_json_and_wrong_edition_rejected(self):
        args, *_ = candidate(self.folder)
        args.index.write_text('{"release": {}, "release": {}}')
        with self.assertRaisesRegex(bundle.Error, "duplicate JSON"):
            bundle.candidate_inputs(args)
        args, *_ = candidate(self.folder)
        index = json.loads(args.index.read_text())
        index["release"]["artifacts"][1]["edition"] = "free"
        args.index.write_text(json.dumps(index))
        with self.assertRaisesRegex(bundle.Error, "one artifact per edition"):
            bundle.candidate_inputs(args)

    def test_offline_plan_never_opens_network_and_lists_missing(self):
        args, record, dsc, body = candidate(self.folder)
        sources, binding, inventory = bundle.candidate_inputs(args)
        opener = Opener(body)
        cache = bundle.ObjectCache(self.folder / "cache", opener=opener)
        cache.path(digest(dsc)).write_bytes(dsc)
        report = bundle.audit(sources, binding, inventory, cache, 2)
        self.assertEqual(opener.calls, 0)
        self.assertEqual(report["content_objects_missing"], 1)
        self.assertEqual(report["known_content_bytes"], len(body))
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["release_approved"])

    def test_verified_offline_report_never_claims_signature_or_delivery(self):
        args, record, dsc, body = candidate(self.folder)
        sources, binding, inventory = bundle.candidate_inputs(args)
        cache = bundle.ObjectCache(self.folder / "cache")
        for payload in (dsc, body):
            cache.path(digest(payload)).write_bytes(payload)
        report = bundle.audit(sources, binding, inventory, cache, 2)
        self.assertEqual(report["status"], "exact-declared-source-objects-verified")
        for key in ("release_approved", "corresponding_source_complete", "openpgp_signatures_verified", "public_delivery_verified"):
            self.assertFalse(report[key])

    def test_download_success_and_verified_resume_no_second_request(self):
        body = b"source"
        opener = Opener(body, {"Content-Length": str(len(body))})
        cache = bundle.ObjectCache(self.folder / "cache", download=True, budget=100, opener=opener)
        first = cache.get(self.obj(body))
        second = cache.get(self.obj(body))
        self.assertEqual(first["state"], "verified-download")
        self.assertEqual(second["state"], "verified-cache")
        self.assertEqual(opener.calls, 1)
        self.assertEqual(cache.transferred, len(body))
        self.assertFalse(list(cache.root.glob(".download-*")))

    def test_bad_existing_cache_is_not_redownloaded_or_overwritten(self):
        opener = Opener(b"source")
        cache = bundle.ObjectCache(self.folder / "cache", download=True, budget=100, opener=opener)
        path = cache.path(self.obj()["sha256"])
        path.write_bytes(b"bad")
        with self.assertRaisesRegex(bundle.Error, "cached object SHA-256 mismatch"):
            cache.get(self.obj())
        self.assertEqual(path.read_bytes(), b"bad")
        self.assertEqual(opener.calls, 0)

    def test_corrupt_truncated_oversize_encoded_and_http_error_not_cached(self):
        for index, (body, headers, status) in enumerate(((b"wrong!", {}, 200), (b"sourc", {}, 200), (b"sourceextra", {}, 200),
                (b"source", {"Content-Encoding": "gzip"}, 200), (b"source", {"Content-Length": "7"}, 200), (b"source", {}, 206))):
            cache = bundle.ObjectCache(self.folder / f"cache-{index}", download=True, budget=100, opener=Opener(body, headers, status))
            with self.subTest(index=index), self.assertRaises(bundle.Error):
                cache.get(self.obj())
            self.assertEqual(list(cache.root.iterdir()), [])

    def test_budget_exhaustion_no_partial_object(self):
        cache = bundle.ObjectCache(self.folder / "cache", download=True, budget=2, opener=Opener(b"source"))
        with self.assertRaisesRegex(bundle.Error, "budget exhausted"):
            cache.get(self.obj())
        self.assertEqual(list(cache.root.iterdir()), [])
        self.assertEqual(cache.transferred, 2)

    def test_parallel_budget_reservations_never_exceed_limit(self):
        from concurrent.futures import ThreadPoolExecutor
        cache = bundle.ObjectCache(self.folder / "cache", download=True, budget=7)
        def consume():
            count = 0
            try:
                stream = io.BytesIO(b"1234567")
                while True:
                    chunk = cache.network_chunk(stream, 3)
                    if not chunk:
                        return count
                    count += len(chunk)
            except bundle.Error:
                return count
        with ThreadPoolExecutor(max_workers=4) as pool:
            counts = list(pool.map(lambda _n: consume(), range(4)))
        self.assertEqual(sum(counts), 7)
        self.assertEqual(cache.transferred, 7)
        self.assertEqual(cache.reserved, 0)

    def test_failed_reads_consume_full_reservation_without_claiming_measured_bytes(self):
        for index, error in enumerate((http.client.IncompleteRead(b"xx"), TimeoutError("fixture timeout"))):
            cache = bundle.ObjectCache(self.folder / f"failed-cache-{index}", download=True, budget=4)
            class BrokenRead:
                calls = 0
                def read(self, amount):
                    self.calls += 1
                    raise error
            stream = BrokenRead()
            with self.assertRaises(type(error)):
                cache.network_chunk(stream, 4)
            self.assertEqual(cache.transferred, 0)
            self.assertEqual(cache.failed_read_budget_charges, 4)
            self.assertEqual(cache.reserved, 0)
            with self.assertRaisesRegex(bundle.Error, "budget exhausted"):
                cache.network_chunk(stream, 4)
            self.assertEqual(stream.calls, 1)

    def test_real_chunked_partial_exception_consumes_budget_even_when_partial_is_empty(self):
        # The standard-library HTTP reader may lose partial-byte information
        # while propagating a truncated chunk. Counting only exc.partial is
        # therefore insufficient to preserve the explicit transfer budget.
        class Socket:
            def makefile(self, *args):
                return io.BytesIO(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n4\r\nxx")
        stream = http.client.HTTPResponse(Socket())
        stream.begin()
        cache = bundle.ObjectCache(self.folder / "chunked-cache", download=True, budget=4)
        with self.assertRaises(http.client.IncompleteRead):
            cache.network_chunk(stream, 4)
        self.assertEqual(cache.transferred, 0)
        self.assertEqual(cache.failed_read_budget_charges, 4)
        self.assertEqual(cache.reserved, 0)
        with self.assertRaisesRegex(bundle.Error, "budget exhausted"):
            cache.network_chunk(io.BytesIO(b"more"), 4)

    def test_failed_download_report_separates_observed_bytes_from_budget_charge(self):
        args, record, dsc, body = candidate(self.folder)
        sources, binding, inventory = bundle.candidate_inputs(args)
        class BrokenResponse(Response):
            def read(self, amount):
                raise http.client.IncompleteRead(b"xx")
        class BrokenOpener:
            def open(self, request, **kwargs):
                return BrokenResponse(b"", request.full_url)
        cache = bundle.ObjectCache(self.folder / "report-cache", download=True, budget=100, opener=BrokenOpener())
        cache.path(digest(dsc)).write_bytes(dsc)
        report = bundle.audit(sources, binding, inventory, cache, 1)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["network_bytes_transferred"], 0)
        self.assertEqual(report["network_failed_read_budget_charges"], len(body) + 1)
        self.assertEqual(report["network_budget_bytes_charged"], len(body) + 1)
        self.assertEqual(report["network_budget_bytes_limit"], 100)
        self.assertEqual(report["content_objects_verified"], 0)
        self.assertEqual(len(report["failures"]), 1)
        self.assertFalse(cache.path(digest(body)).exists())
        self.assertFalse(list(cache.root.glob(".download-*")))

    def test_cache_exact_size_and_oversized_dsc_rejected_before_read(self):
        cache = bundle.ObjectCache(self.folder / "cache")
        obj = self.obj()
        cache.path(obj["sha256"]).write_bytes(b"source")
        with self.assertRaisesRegex(bundle.Error, "size limit"):
            cache.get({**obj, "size_bytes": 5})
        with patch.object(bundle, "DSC_LIMIT", 2), self.assertRaisesRegex(bundle.Error, "size limit"):
            cache.get({**obj, "kind": "dsc", "size_bytes": None})

    def test_metadata_failure_prevents_archive_downloads(self):
        args, record, _dsc, body = candidate(self.folder)
        sources, binding, inventory = bundle.candidate_inputs(args)
        opener = Opener(body)
        cache = bundle.ObjectCache(self.folder / "cache", download=True, budget=100, opener=opener)
        report = bundle.audit(sources, binding, inventory, cache, 2)
        self.assertEqual(opener.calls, 1)  # only the failed DSC retrieval
        self.assertEqual(len(report["failures"]), 1)
        self.assertEqual(report["content_objects_verified"], 0)

    def test_legacy_cache_import_is_hash_checked(self):
        legacy = self.folder / "legacy"
        (legacy / "dsc").mkdir(parents=True)
        record, dsc, _body = source()
        url = record["locator"]["dsc_url"]
        (legacy / "dsc" / (digest(url.encode()) + ".bin")).write_bytes(dsc)
        cache = bundle.ObjectCache(self.folder / "cache", legacy=legacy)
        obj = {"kind": "dsc", "url": url, "sha256": digest(dsc)}
        self.assertEqual(cache.get(obj, "dsc")["state"], "verified-import")
        self.assertEqual(cache.path(digest(dsc)).read_bytes(), dsc)

    def test_path_traversal_and_unsafe_download_urls(self):
        for url in ("http://snapshot.debian.org/file/" + "a" * 40, BASE + "../secret", BASE.replace("snapshot.debian.org", "user@snapshot.debian.org") + "source.tar",
                    "https://localhost/source", BASE + "source.tar?token=value", "https://github.com/Other/repo/archive/" + COMMIT + ".tar.gz"):
            with self.subTest(url=url), self.assertRaises(bundle.Error):
                bundle.allowed_url(url)
        with self.assertRaises(bundle.Error):
            bundle.ObjectCache(self.folder / "cache").path("../escape")

    def test_redirect_policy_blocks_external_origin_and_changed_commit(self):
        redirect = bundle.SafeRedirect()
        original = Request(BASE + "demo.dsc")
        with self.assertRaises(bundle.Error):
            redirect.redirect_request(original, None, 302, "Found", {}, "https://example.com/source")
        original = Request(f"https://github.com/Dagric/dagric-os/archive/{COMMIT}.tar.gz")
        with self.assertRaisesRegex(bundle.Error, "changed source commit"):
            redirect.redirect_request(original, None, 302, "Found", {}, "https://codeload.github.com/Dagric/dagric-os/tar.gz/" + "b" * 40)

    def test_snapshot_content_address_redirect_preserves_exact_filename(self):
        redirect = bundle.SafeRedirect()
        original = Request(BASE + "demo_1.0%2Bpatch.orig.tar.xz")
        target = "https://snapshot.debian.org/file/" + "c" * 40 + "/demo_1.0%2Bpatch.orig.tar.xz"
        redirected = redirect.redirect_request(original, None, 302, "Found", {}, target)
        self.assertEqual(redirected.full_url, target)
        for altered in (target.replace("demo_", "other_"), target.replace("/demo_", "/../demo_"), target + "/extra",
                        target.replace("snapshot.debian.org", "snapshot.debian.org.example")):
            with self.subTest(altered=altered), self.assertRaises(bundle.Error):
                redirect.redirect_request(original, None, 302, "Found", {}, altered)

    def test_full_redirect_handlers_never_drain_unbudgeted_response_bodies(self):
        class RedirectBody(io.BytesIO):
            def read(self, *args, **kwargs):
                raise AssertionError("redirect body must not be read outside the transfer budget")
        class Parent:
            def open(self, request, **kwargs):
                self.request, self.options = request, kwargs
                return "redirected-without-network"
        target = "https://snapshot.debian.org/file/" + "c" * 40 + "/demo.dsc"
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                redirect = bundle.SafeRedirect()
                redirect.parent = Parent()
                request = Request(BASE + "demo.dsc")
                request.timeout = 7
                response = RedirectBody(b"unbounded irrelevant redirect body")
                result = getattr(redirect, f"http_error_{code}")(
                    request, response, code, "Redirect", {"location": target})
                self.assertEqual(result, "redirected-without-network")
                self.assertTrue(response.closed)
                self.assertEqual(redirect.parent.request.full_url, target)
                self.assertEqual(redirect.parent.options, {"timeout": 7})

    def test_no_drain_redirect_retains_method_identity_and_loop_restrictions(self):
        class RedirectBody(io.BytesIO):
            def read(self, *args, **kwargs):
                raise AssertionError("redirect body must not be consumed")
        class Parent:
            def open(self, request, **kwargs):
                return request
        redirect = bundle.SafeRedirect()
        redirect.parent = Parent()
        target = "https://snapshot.debian.org/file/" + "c" * 40 + "/demo.dsc"
        request = Request(BASE + "demo.dsc", data=b"post-body", headers={"Content-Type": "text/plain"})
        request.timeout = 7
        # Preserve stdlib's POST-to-GET conversion for 303, without changing
        # its refusal to replay a POST automatically for 307/308.
        redirected = redirect.http_error_303(request, RedirectBody(), 303, "See Other", {"location": target})
        self.assertEqual(redirected.get_method(), "GET")
        self.assertIsNone(redirected.data)
        self.assertFalse(redirected.has_header("Content-Type"))
        for code in (307, 308):
            response = RedirectBody()
            with self.assertRaises(HTTPError):
                getattr(redirect, f"http_error_{code}")(request, response, code, "Redirect", {"location": target})
            self.assertTrue(response.closed)
        request = Request(BASE + "demo.dsc")
        request.timeout = 7
        request.redirect_dict = {target: redirect.max_repeats}
        with self.assertRaises(HTTPError):
            redirect.http_error_302(request, RedirectBody(), 302, "Redirect", {"location": target})
        request = Request(BASE + "demo.dsc")
        request.timeout = 7
        for bad_target in (target.replace("demo.dsc", "other.dsc"), "https://example.com/demo.dsc"):
            response = RedirectBody()
            with self.assertRaises(bundle.Error):
                redirect.http_error_302(request, response, 302, "Redirect", {"location": bad_target})
            self.assertTrue(response.closed)

    def test_symlink_cache_input_is_refused(self):
        target = self.folder / "outside"
        target.write_bytes(b"source")
        cache = bundle.ObjectCache(self.folder / "cache")
        try:
            cache.path(self.obj()["sha256"]).symlink_to(target)
        except OSError:
            self.skipTest("symlink permission unavailable")
        with self.assertRaisesRegex(bundle.Error, "linked path"):
            cache.get(self.obj())

    def test_cli_existing_output_is_never_overwritten(self):
        args, *_ = candidate(self.folder)
        output = self.folder / "receipt.json"
        output.write_text("keep")
        argv = ["--map", str(args.map_path), "--index", str(args.index), "--supplement", str(args.supplement),
                "--dagric-commit", COMMIT, "--cache", str(self.folder / "cache"), "--output", str(output)]
        for edition in ("free", "pro"):
            for field in ("status", "manifest", "iso_sha256"):
                argv += [f"--{edition}-{field.replace('_', '-')}", str(getattr(args, f"{edition}_{field}"))]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bundle.main(argv), 2)
        self.assertEqual(output.read_text(), "keep")
        self.assertFalse((self.folder / "cache").exists())


if __name__ == "__main__":
    unittest.main()
