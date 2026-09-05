#!/usr/bin/env python3
"""Offline regressions: DSC signature evidence must not become blanket trust."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dsc_audit", ROOT / "tools/audit-dsc-signatures.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
FPR = "A" * 40
SUB = "B" * 40
STATUS = f"[GNUPG:] VALIDSIG {SUB} 2020-01-01 100 0 4 0 1 8 01 {FPR}\n"


class DscSignatureTests(unittest.TestCase):
    def setUp(self):
        self.keys = {
            FPR: {"validity": "-", "created": 1, "expires": 0, "role": "debian-keyring"},
            SUB: {"validity": "-", "created": 2, "expires": 0, "role": "debian-keyring"},
        }

    def category(self, status=STATUS, code=0):
        return AUDIT.classify(code, status, self.keys, 1000)[0]

    def test_known_signature_is_only_packaged_key_evidence(self):
        self.assertEqual(self.category(), "cryptographically-valid-with-packaged-key-state")

    def test_no_validsig_is_not_success(self):
        self.assertEqual(self.category("[GNUPG:] GOODSIG somekey Somebody\n"), "verification-error")

    def test_failed_process_with_validsig_is_not_success(self):
        self.assertEqual(self.category(code=2), "verification-error")

    def test_bad_signature_overrides_valid_signature(self):
        self.assertEqual(self.category(STATUS + "[GNUPG:] BADSIG x y\n"), "bad-signature")

    def test_missing_key_retained(self):
        self.assertEqual(self.category("[GNUPG:] NO_PUBKEY DEADBEEF\n", 2), "unavailable-key")

    def test_primary_key_expiry_is_checked_despite_gpgv_success(self):
        self.keys[FPR]["expires"] = 200
        self.assertEqual(self.category(), "expired-key")

    def test_subkey_expiry_is_checked(self):
        self.keys[SUB]["validity"] = "e"
        self.assertEqual(self.category(), "expired-key")

    def test_revocation_is_checked_despite_gpgv_success(self):
        self.keys[FPR]["validity"] = "r"
        self.assertEqual(self.category(), "revoked-key")

    def test_signature_expiration(self):
        status = STATUS.replace("100 0 4", "100 500 4")
        self.assertEqual(self.category(status), "expired-signature")

    def test_nonuploading_key_is_not_upload_authority(self):
        self.keys[FPR]["role"] = "debian-nonupload"
        self.assertEqual(self.category(), "non-uploading-key")

    def test_missing_key_state_not_accepted(self):
        del self.keys[SUB]
        self.assertEqual(self.category(), "key-state-unavailable")

    def test_future_signature_not_accepted(self):
        self.assertEqual(self.category(STATUS.replace("100 0 4", "2000 0 4")), "future-signature")

    def test_signature_before_key_not_accepted(self):
        self.keys[SUB]["created"] = 300
        self.assertEqual(self.category(), "signature-before-key")

    def test_truncated_validsig_rejected(self):
        with self.assertRaises(ValueError):
            self.category("[GNUPG:] VALIDSIG x\n")

    def test_key_metadata_binds_primary_and_subkey(self):
        lines = ["pub:-:4096:1:KEY:1:2000::-:::scSC:", f"fpr:::::::::{FPR}:",
                 "sub:r:4096:1:SUB:2:500::-:::s:", f"fpr:::::::::{SUB}:"]
        keys = AUDIT.parse_keys("\n".join(lines), "debian-maintainers")
        self.assertEqual(keys[SUB]["primary_fingerprint"], FPR)
        self.assertEqual(keys[SUB]["validity"], "r")
        self.assertEqual(keys[FPR]["expires"], 2000)

    def test_url_addressed_cache_not_confused_with_content_digest(self):
        record = {"integrity": {"dsc_sha256": "c" * 64}, "locator": {"dsc_url": "https://snapshot.debian.org/example.dsc"}}
        with tempfile.TemporaryDirectory() as temp:
            path = AUDIT.cached_dsc_path(Path(temp), record)
        self.assertEqual(path.name, AUDIT.sha(record["locator"]["dsc_url"].encode()) + ".bin")
        self.assertNotEqual(path.name, "c" * 64 + ".bin")

    def test_sid_data_requires_fresh_unexpired_exact_signed_suite(self):
        now = datetime(2026, 9, 5, 20, tzinfo=timezone.utc)
        release = {"Origin": "Debian", "Codename": "sid", "Date": "Sat, 05 Sep 2026 14:10:12 UTC",
                   "Valid-Until": "Sat, 12 Sep 2026 14:10:12 UTC", "SHA256": "\n" + "a" * 64 + " 4 main/binary-amd64/Packages.xz"}
        self.assertEqual(AUDIT.validate_keyring_release(release, "sid", now)["date"], release["Date"])
        with self.assertRaises(ValueError):
            AUDIT.validate_keyring_release(release, "trixie", now)
        release["Date"] = "Tue, 01 Sep 2026 14:10:12 UTC"
        with self.assertRaises(ValueError):
            AUDIT.validate_keyring_release(release, "sid", now)

    def test_sid_data_does_not_skip_missing_or_expired_valid_until(self):
        now = datetime(2026, 9, 5, 20, tzinfo=timezone.utc)
        release = {"Origin": "Debian", "Codename": "sid", "Date": "Sat, 05 Sep 2026 14:10:12 UTC", "SHA256": ""}
        with self.assertRaises(ValueError):
            AUDIT.validate_keyring_release(release, "sid", now)
        release["Valid-Until"] = "Sat, 05 Sep 2026 19:00:00 UTC"
        with self.assertRaises(ValueError):
            AUDIT.validate_keyring_release(release, "sid", now)

    def canonical_fixture(self):
        now = 1788614547
        status = (f"[GNUPG:] VALIDSIG {AUDIT.CANONICAL_SIGNER} 2026-09-05 {now - 60} 0 4 0 1 10 01 "
                  f"{AUDIT.CANONICAL_PRIMARY}\n")
        keys = {fingerprint: {"validity": "-", "created": 1, "expires": 0, "role": "debian-keyring"}
                for fingerprint in (AUDIT.CANONICAL_SIGNER, AUDIT.CANONICAL_PRIMARY)}
        return status, keys, now

    def canonical_file_list(self):
        return "\n".join("a" * 128 + f"  keyrings/{role}.{extension}"
                         for role in (*AUDIT.CANONICAL_ROLES, "emeritus-keyring")
                         for extension in ("gpg", "pgp"))

    def test_canonical_pinned_signer_accepted(self):
        status, keys, now = self.canonical_fixture()
        self.assertEqual(AUDIT.validate_canonical_signer(0, status, keys, now)["fingerprint"], AUDIT.CANONICAL_SIGNER)

    def test_canonical_unknown_signer_rejected_even_when_key_is_present(self):
        status, keys, now = self.canonical_fixture()
        keys["C" * 40] = dict(keys[AUDIT.CANONICAL_SIGNER])
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status.replace(AUDIT.CANONICAL_SIGNER, "C" * 40), keys, now)

    def test_canonical_stale_manifest_rejected(self):
        status, keys, now = self.canonical_fixture()
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status, keys, now + 32 * 86400)

    def test_canonical_future_manifest_rejected(self):
        status, keys, now = self.canonical_fixture()
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status, keys, now - 120)

    def test_canonical_revoked_primary_rejected(self):
        status, keys, now = self.canonical_fixture()
        keys[AUDIT.CANONICAL_PRIMARY]["validity"] = "r"
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status, keys, now)

    def test_canonical_expired_signing_key_rejected(self):
        status, keys, now = self.canonical_fixture()
        keys[AUDIT.CANONICAL_SIGNER]["expires"] = now - 1
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status, keys, now)

    def test_canonical_multiple_manifest_signatures_rejected(self):
        status, keys, now = self.canonical_fixture()
        with self.assertRaises(ValueError):
            AUDIT.validate_canonical_signer(0, status + status, keys, now)

    def test_canonical_manifest_exact_allowlist(self):
        entries = AUDIT.canonical_manifest_entries(self.canonical_file_list())
        self.assertEqual(len(entries), 10)

    def test_canonical_unknown_filename_rejected(self):
        with self.assertRaises(ValueError):
            AUDIT.canonical_manifest_entries(self.canonical_file_list() + "\n" + "a" * 128 + "  ../injected.pgp")

    def test_canonical_duplicate_filename_rejected(self):
        lines = self.canonical_file_list()
        with self.assertRaises(ValueError):
            AUDIT.canonical_manifest_entries(lines + "\n" + lines.splitlines()[0])

    def test_canonical_missing_filename_rejected(self):
        with self.assertRaises(ValueError):
            AUDIT.canonical_manifest_entries("\n".join(self.canonical_file_list().splitlines()[:-1]))

    def test_canonical_different_alias_digest_rejected(self):
        with self.assertRaises(ValueError):
            AUDIT.canonical_manifest_entries(self.canonical_file_list().replace("a" * 128, "b" * 128, 1))

    def test_canonical_changed_blob_rejected(self):
        digest = AUDIT.hashlib.sha512(b"good").hexdigest()
        AUDIT.canonical_blob(b"good", digest)
        with self.assertRaises(ValueError):
            AUDIT.canonical_blob(b"changed", digest)


if __name__ == "__main__":
    unittest.main()
