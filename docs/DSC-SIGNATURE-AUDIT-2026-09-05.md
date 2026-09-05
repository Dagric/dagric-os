# Exact-source DSC signature audit — 5 September 2026

Historical keyring scope: the results below use the July 2025 packaged keyring.
The newer authenticated canonical-keyring run is recorded in
`DEBIAN-KEYRING-FRESHNESS-2026-09-05.md`: 1,570 positive canonical-key-state
results, 131 expired, 134 unavailable, 23 revoked and three strict verification
errors. The older receipts remain unchanged; neither collection clears release.

## Outcome

All **1,861 exact Debian DSC files** named by the completed candidate's primary
and declared embedded-source maps were checked. Their SHA-256 digests,
Source/Version identities and source-file digest sets matched the candidate
metadata. OpenPGP authentication is **not completely cleared**.

| Result category | DSC files | Interpretation |
| --- | ---: | --- |
| Cryptographically valid with packaged, nonexpired/nonrevoked key state | 1,266 | Positive signature evidence against this specific keyring snapshot, not current or historical per-package upload authority |
| Expired key in packaged key metadata | 445 | Mathematical signatures verify, but expiry needs current/historical key-state review |
| Signer unavailable in packaged keyrings | 143 | Signature could not be authenticated using the allowed keys |
| Revoked key in packaged key metadata | 4 | Mathematical signatures verify, but known revocation blocks a clean signer verdict |
| Verification error | 3 | Strict GnuPG rejected signing-subkey cross-certification involving SHA1 |
| Unsigned / bad mathematical signature / digest or identity mismatch | 0 / 0 / 0 | None observed in this exact collection; not evidence that other source obligations are complete |

**No release approval, source-promotion override or public upload occurred.**
The 445 expired-key and four revoked-key entries are not counted among the
1,266 clean packaged-key-state results. Expiration today does not by itself
prove that a historical signature was invalid when made. Likewise, a revoked
key does not by itself establish that these archived source packages were
malicious. Resolving those questions requires authoritative key history and
an explicit trust-policy review, not suppressing warnings.

## Exact candidate binding

The candidate source commit remains
`20e24dd04ea3de802531be5139f9f36fe96a1490`:

- Free image SHA-256:
  `0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc`.
- Pro image SHA-256:
  `69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa`.

The standalone verifier reuses `audit-source-bundle.py`'s strict candidate
input binding: exact manifests/dpkg source identities, source-index image
receipts, primary map and declared Built-Using/Static-Built-Using supplement.
It reads only DSC identities needed by these maps; unrelated legacy cache
objects are not treated as candidate evidence. No original image was changed
or independently rehashed by this signature tool.

Each selected DSC is rehashed and checked against its exact source identity
and file checksum set. Verification uses a private copy of those exact bytes.
After successful OpenPGP verification, the authenticated cleartext's source
identity and file digests are checked again. A valid signature on different
control data cannot satisfy the candidate binding.

## Keyring provenance and limits

The host initially had Debian archive signing keyrings but no developer or
maintainer keyring. `apt-get download debian-keyring=2025.07.26` downloaded
the official package into a newly created private directory. **It was not
installed.** No APT lists were refreshed and no host services were changed.

Before extraction, the verifier repeated the Debian `InRelease` signature,
origin/codename/date and main-amd64 Packages checksum checks against the
previously collected stable repository evidence. It matched the downloaded
package's size and SHA-256 to that signed index:

- Package: `debian-keyring_2025.07.26_all.deb`.
- Bytes: `33,751,188`.
- SHA-256: `b201fc5165cb91c0a8712c9a0fa8dded15729cb25cbe9d5e743986ec9b1256fb`.
- Signed Packages SHA-256:
  `3ab4e811cf4f3e5a335d382c58cc19d85f1abe7a4ef4689160ca1f637fa0e9b3`.
- InRelease SHA-256:
  `98b25b5cd185c59d34aa6e4c3e9b5b8f01bbe9d104fe2dcfbcd30dc0a14a59ed`.

Only after that authentication did `dpkg-deb --extract` unpack data into the
private audit directory. No package maintainer script was run. The developer,
maintainer, role and non-uploading keyring files are individually hash-recorded
in the result. Non-uploading key membership would receive a separate category,
not upload-authority approval.

Debian explicitly warns that the packaged keyring may lag current authoritative
keyring updates. Thus this **July 2025 keyring does not establish September 2026
revocation or expiry-extension freshness**, even though its package bytes are
authenticated. No arbitrary keyserver fetch, automatic key import, owner-trust
change or unverified replacement keyring was used. [Debian keyring package](https://packages.debian.org/trixie/debian-keyring).

GnuPG's documentation states that `gpgv` does not check expired or revoked
keys. Accordingly, this audit supplements signature verification with offline
`gpg --show-keys` fingerprint, primary/subkey expiry and revocation metadata
inspection. Both signing subkeys and their primary keys are checked. The raw
key metadata is preserved, including legacy display UIDs whose byte encoding
is not UTF-8; decisions use strict fingerprints and numeric fields, not those
display names. [GnuPG gpgv documentation](https://www.gnupg.org/documentation/manuals/gnupg/gpgv.html).

## Exceptions needing review

The four revoked-key cases are:

- `hyphen 2.8.8-7`.
- `libexecs 1.4-2`.
- `libsoxr 0.1.3-4`.
- `libudfread 1.1.2-1`.

All four refer to signing subkey
`8B7868786C33E5C64C4D0A480816B9E18C762BAD`, primary fingerprint
`66AE2B4AFCCF3F52DA184D184B043FCDB9444540`, as recorded in the packaged key
metadata. This is a public signing-key identifier, not a credential. Revocation
reason/timing and original archive acceptance have not been adjudicated here.

The three verification errors are:

- `setuptools 78.1.1-0.1`.
- `uchardet 0.0.8-1`.
- `virt-manager 1:5.0.0-5+deb13u1`.

Their logs say signing-subkey cross-certification is invalid under the strict
SHA1 rejection setting. The **DSC message signatures themselves specify SHA512**;
calling them SHA1-signed DSCs would be inaccurate. Neither weak-digest acceptance
nor an ignore-time-conflict flag was used to make these pass. Raw GnuPG error
and status logs are available per exact DSC digest.

The report contains all 143 unavailable-key cases and all 445 expired-key cases,
with exact source identities and full available signature fingerprints. A
missing key is an authentication gap, not proof of a forged package.

## Reproduce and inspect

The new tool is offline: download the official package separately and supply
the collected signed index directory. The destination must be fresh.

```sh
python3 tools/audit-dsc-signatures.py \
  --candidate out/private-source-candidate-20e24dd0-20260905 \
  --keyring-deb /var/tmp/dagric-dsc-signature-audit.KHRnZ3/debian-keyring_2025.07.26_all.deb \
  --signed-index-dir out/private-candidate-security-20260905-multiarch/trixie \
  --output-dir /var/tmp/dagric-dsc-signature-audit.KHRnZ3/NEW-VERIFICATION
python3 test/test-dsc-signatures.py
```

All **16 offline regression tests passed**, covering missing/bad/incomplete
signature status, nonzero verification exit status, primary/subkey expiry,
revocation, signature expiry, missing key state, non-uploading keys, future and
pre-key timestamps, full fingerprint bindings and URL-vs-content cache keys.
Python compilation and `git diff --check` passed.

The final complete run is:

`/var/tmp/dagric-dsc-signature-audit.KHRnZ3/verification-3/`

- `dsc-signatures.private.json`, reference time
  `2026-09-05T18:44:16.569221+00:00`, SHA-256
  `854a51975f062cdfcce940335e2f92a32df6335eabf628c4b5f952cd299f1196`.
- Authenticated package copy, keyring data, key metadata, signed-index proof,
  and per-DSC private copies, verified plaintext and GnuPG logs.

Earlier `verification` and `verification-2` directories are retained as failed
tooling attempts, not passing evidence: a legacy UID decoding issue and a
URL-addressed-versus-content-addressed cache-path mismatch were corrected.
The final fresh run had no digest/identity/cache-binding error.

This work does not prove every source file is privately present, publicly
delivered or legally sufficient; the full-source object audit owns that separate
check. Dagric's Git archive is not a Debian DSC, and undeclared embedded code,
firmware/package rights, historical upload authority and qualified-human
release approvals remain outside this signature collection.
