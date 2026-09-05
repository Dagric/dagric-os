#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare an offline source-delivery plan against BOTH actual candidate images.

Rehashes the current cache and extracts the actual image inventories. The result
is a private immutable transfer plan, NOT upload authority or proof of delivery,
source authenticity, complete license coverage, or release readiness. It accepts
no detached passing audit report and performs no network requests or uploads.
"""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


lock = module("distribution_lock", "source-candidate-lock.py")
images = module("distribution_images", "check-source-bundle-images.py")
require = lock.require


def delivery_plan(document, digest, image_rows):
    objects = []
    for row in document["objects"]:
        names = sorted(lock.safe_filename(name) for name in row["filenames"])
        objects.append({"sha256": row["sha256"], "size_bytes": row["size_bytes"],
                        "original_filenames": names,
                        "candidate_object_key": "source-objects/sha256/" + row["sha256"]})
    return {
        "format": "dagric-private-source-distribution-plan-v1",
        "private": True,
        "release_approved": False,
        "upload_authorized": False,
        "public_delivery_verified": False,
        "source_authenticity_verified": False,
        "corresponding_source_complete": False,
        "source_commit_from_external_receipt": document["source_commit"],
        "candidate_source_lock_sha256": digest,
        "actual_image_bindings": image_rows,
        "objects": objects,
        "sources": document["sources"],
        "total_unique_object_bytes": sum(row["size_bytes"] for row in objects),
        "remaining_requirements": [
            "Authenticated provenance for every exact source object.",
            "Reviewed source coverage, notices, build instructions and retention/delivery terms.",
            "Approved destination plus full-byte authenticated readback for private staging.",
            "Public source delivery and full-byte anonymous readback before binary distribution.",
            "Separate release, rights, localization, security and physical validation gates.",
        ],
    }


def prepare(args):
    lock.bundle.regular(args.output)
    require(not args.output.exists(), "output must be a new private plan path")
    document, digest = lock.bundle.read_json(args.lock)
    lock.lock_shape(document)
    require(lock.bundle.read(args.lock) == lock.canonical(document), "source lock must be canonical")
    binding = {
        "iso_size_bytes_from_supplied_index": {e: r["iso_size_bytes"] for e, r in document["editions"].items()},
        "iso_sha256_from_supplied_receipts": {e: r["iso_sha256_from_supplied_receipts"] for e,r in document["editions"].items()},
        "package_manifest_sha256": {e: r["package_manifest_sha256"] for e,r in document["editions"].items()},
        "dpkg_status_sha256": {e: r["dpkg_status_sha256"] for e,r in document["editions"].items()},
    }
    rows = []
    with tempfile.TemporaryDirectory(prefix="dagric-source-distribution-") as work:
        for edition in ("free", "pro"):
            scratch = Path(work) / edition
            scratch.mkdir(mode=0o700)
            path = getattr(args, edition + "_iso").absolute()
            rows.append(images.verify_edition(edition, path, binding, scratch))
            print(f"source-distribution: actual {edition} image and extracted inventory verified", flush=True)
    # Revalidate all primary/embedded identities and source bytes AFTER image
    # extraction. A substituted/missing cache object cannot use an old receipt.
    verified = lock.verify_lock(args.lock, args)
    require(lock.canonical(verified) == lock.canonical(document), "lock changed during image validation")
    for row in rows:
        require(images.file_digest(Path(row["iso"])) == row["sha256"], "image changed during full source validation")
    result = delivery_plan(verified, digest, rows)
    lock.write_new(args.output, result)
    return result


def main(argv=None):
    parser = lock.parser()
    parser.description = __doc__
    parser.add_argument("--free-iso", type=Path, required=True)
    parser.add_argument("--pro-iso", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(args.mode == "create" and args.lock is not None and args.output is not None,
                "use create with --lock and a new --output")
        result = prepare(args)
        print(f"source-distribution: private plan created: {len(result['sources'])} exact sources, {len(result['objects'])} unique objects")
        print("source-distribution: no upload, public records, rights approvals or release authorization changed")
        return 0
    except (lock.Error, images.Error, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"source-distribution: BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
