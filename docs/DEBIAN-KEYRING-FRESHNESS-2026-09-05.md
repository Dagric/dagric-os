# Debian keyring freshness and archive-source provenance — 5 September 2026

## Concrete result

Authenticated newer keyring data improves, but does not finish, the exact DSC
signature review. Full strict rechecks of all **1,861** candidate DSCs now
include both June's packaged keys and August's authenticated canonical keys:

| Result | July 2025 packaged keys | June 2026 packaged keys | August 2026 canonical keys |
| --- | ---: | ---: | ---: |
| Valid cryptography plus nonexpired/nonrevoked selected key state | 1,266 | 1,538 | **1,570** |
| Expired key | 445 | 166 | 131 |
| Unavailable key | 143 | 131 | 134 |
| Revoked key | 4 | 23 | 23 |
| Strict cross-certification error | 3 | 3 | 3 |

The additional revoked cases are a reason to retain checks, not to approve old
warnings automatically. No signature, expiry, revocation or weak-digest policy
was relaxed. The three errors still involve SHA1 subkey cross-certification,
not SHA1 DSC message digests. Package-specific historical authorization remains
separate from mathematical signature validity.

## Authenticated package, not suite migration

Only keyring **data** was downloaded and privately extracted. Nothing was
installed; APT configuration, OS package sources, trust databases, services
and candidate images were unchanged. The security-availability audit still
compares the OS exclusively to its supported stable suites.

Fresh signed `sid/InRelease` evidence:

- Date: **5 September 2026 14:10:12 UTC**.
- Valid-Until: **12 September 2026 14:10:12 UTC**.
- InRelease SHA-256:
  `565ab14183f896764312d2bfa90e748f92c39d0a05f4128e162844f1613547da`.
- Packages SHA-256:
  `3446806f40a394deec3ec10725c9d59c14c9eacd16ca7d8cb87f146f45a6693d`.
- `debian-keyring 2026.06.27`, 33,813,856 bytes, package SHA-256:
  `7f2f3eb718818e09a8beb5b05b4d9eef5d766d8d1c5c128da834bbe371024507`.

`audit-dsc-signatures.py` now accepts explicit `--keyring-suite sid` for this
data-only use, while defaulting to trixie. It enforces exact origin/codename,
valid signature and index/package hashes, unexpired Valid-Until, no future Date,
and a signed sid Date no older than 48 hours. The complete verifier now has
**31 passing regression tests**, including the canonical-manifest chain.

The full recheck report at 18:55:34 UTC is
`/var/tmp/dagric-keyring-freshness.wTRo51/full-dsc-verification/dsc-signatures.private.json`,
SHA-256 `296db91ab8513ed7faeeeb6e70543198de326fd7cdec4273b172c39a659fef9e`.
Its complete download/signature proof starts at
`/var/tmp/dagric-keyring-freshness.wTRo51/authenticated-keyring-receipt.json`.

## More current canonical data is now authenticated

Debian's official workflow says its canonical active keyrings are served over
rsync, accompanied by a maintainer-signed `sha512sums.txt`. The archive package
can lag active membership and should not be treated as the live authority.
[Debian keyring workflow](https://keyring.debian.org/keyring-workflow.html).

Following that route, the **27 August 2026** canonical checksum manifest was
verified using the previously archive-authenticated June keyring. Its SHA512
signature belongs to John Sullivan, listed among Debian's keyring maintainers;
both signing-subkey and primary-key state passed the separate offline checks.
[Official package maintainer listing](https://packages.debian.org/sid/debian-keyring).

- Signing fingerprint: `AD3219669D1E8CF06CF90BC88D3628DB7EAFE30A`.
- Primary fingerprint: `A4626CBAFF376039D2D7554497BA9CE761A0963B`.
- Manifest SHA-256:
  `73367e3136e437a64124e56e5588907e3867e4a263fea5f23378af6ca71f2fa3`.

The four canonical developer, maintainer, role and non-uploading keyring files
were privately downloaded and their SHA512 digests matched that authenticated
manifest. No arbitrary keyserver data or Salsa UI verification label was trusted.
Their receipt and exact files are under
`/var/tmp/dagric-keyring-freshness.wTRo51/canonical-authenticated/`.

The canonical step is now completed in the standalone verifier. It independently
reverifies June's package signature/hash chain, inspects the bootstrap key state,
verifies the pinned maintainer's SHA512-signed August manifest, checks the exact
ten-name manifest allowlist and alias digests, and authenticates the four active
keyring files' bytes. The manifest signer and primary are checked again against
the authenticated canonical key state. Unknown signers, duplicate or unknown
filenames, changed files, stale/future signature times, expired/revoked signer
state, and incomplete signature success are refused. Manifest signatures must
be at most 31 days old. No network request is made during this canonical run.

Emeritus files appear in the official signed file set but are **not loaded** into
the verifier. Removed or historical keys remain unavailable rather than being
silently converted into active approval. The three additional unavailable cases
versus June are retained explicitly. The default packaged-key mode remains
available and still defaults to trixie.

The final canonical report, checked at `2026-09-05T19:02:45.478744+00:00`, is:

`/var/tmp/dagric-keyring-freshness.wTRo51/full-canonical-dsc-verification/dsc-signatures.private.json`

SHA-256: `5137f989e50ca6f5cb1400001b0f616e4d1350782739a0259221115cd47f2716`.
All 1,861 DSC identities, content digests and source-file checksum sets remained
bound. Positive results are labelled `cryptographically-valid-with-canonical-key-state`,
not packaged-key results. Expired, missing, revoked and cross-certification-error
cases remain distinct. No release or historical upload-authority clearance is
granted by a positive result.

To reproduce offline, use a fresh destination:

```sh
python3 tools/audit-dsc-signatures.py \
  --candidate out/private-source-candidate-20e24dd0-20260905 \
  --keyring-deb /var/tmp/dagric-keyring-freshness.wTRo51/debian-keyring.deb \
  --signed-index-dir /var/tmp/dagric-keyring-freshness.wTRo51/signed-index \
  --keyring-suite sid \
  --canonical-manifest /var/tmp/dagric-keyring-freshness.wTRo51/canonical-sha512sums.txt \
  --canonical-keyring-dir /var/tmp/dagric-keyring-freshness.wTRo51/canonical-authenticated \
  --output-dir /var/tmp/dagric-keyring-freshness.wTRo51/NEW-CANONICAL-AUDIT
```

Python compilation and `git diff --check` passed after the extension. The 31
offline tests include pinned signer, signer/primary expiry/revocation, stale and
future dates, duplicate signatures, exact filename allowlist, duplicate/missing
filenames, alias inconsistencies and changed keyring content. Prior June and
July reports remain unchanged as dated evidence, not silently rewritten.

## Independent signed archive-membership evidence

Separately, **1,815 of 1,861 exact DSC identities** and their source-file digest
sets matched current signature-bound Debian `Sources` indexes. Twelve indexes
from trixie, trixie-updates and trixie-security, across four components, totalled
10,892,448 compressed bytes. Their enclosing Release signatures and exact
index checksums were checked; no APT refresh or expiry override was used.

This includes 142 of the original 143 missing-key DSCs and all four originally
revoked-key cases. It proves that Debian's signed archive metadata names those
exact bytes; it does **not** change their individual signer verdicts or prove
absence of malicious code. Debian distinguishes archive authentication from
per-package signatures. [APT archive-authentication documentation](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html).

Receipt:
`/var/tmp/dagric-keyring-freshness.wTRo51/signed-source-membership/signed-source-membership.private.json`,
SHA-256 `4fc775fe1e00cc823e5f5c4b041fe7e0fe1973bb309454ccc1af53204c149306`.

The remaining **46 older source versions** need historical signed Sources
membership checks. Snapshot preserves date-specific archive views, making
that route feasible. Such evidence must retain the historical Date/Valid-Until
and be labelled archival membership, never current repository freshness.
[Debian Snapshot documentation](https://snapshot.debian.org/).

No historical Sources claim, public source delivery, rights approval, release
promotion, or complete-source clearance is asserted by this research.
