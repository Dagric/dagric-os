# Private full source object audit

`tools/audit-source-bundle.py` moves beyond recording tarball hashes: it can
retrieve and stream-verify every exact primary and declared embedded source
object. It does not publish, promote, extract, execute, sign, or approve a release.

## Actual offline candidate check

The first offline run used the existing private candidate inventories and cache
for source commit `20e24dd04ea3de802531be5139f9f36fe96a1490`. It established:

- 1,862 exact source identities: 1,861 Debian identities and one Dagric commit.
- All 1,861 cached Debian DSC bodies match the candidate SHA-256, exact
  `Source`/`Version`, complete `Checksums-Sha256` filename set, and recorded hashes.
  Their positive byte sizes are now inventoried as well.
- Each primary Debian source identity agrees with the immutable dpkg `Source`
  field, including epoch and binary-only rebuild versions. Manifest identities,
  both edition hashes, source-index identity, and supplementary declarations are
  checked together, rather than trusting a detached successful inventory.
- 4,149 distinct source content objects after digest deduplication. The existing
  267,784,299-byte Dagric source archive was rehashed and imported. The remaining
  4,148 Debian objects total 11,158,962,052 bytes and were **not downloaded by the
  offline pass**. Shared archives are counted once.

The ignored receipt is
`out/private-source-candidate-20e24dd0-20260905/full-source-plan.private.json`.
It reports `status: incomplete`, no release approval, and zero network bytes.
The initial receipt's `known_content_bytes` counted Debian sizes before the
Dagric cache import; subsequent receipts include measured imported sizes too.

## Completed private download and fresh offline verification

The later bounded download completed with **4,149/4,149 content objects and
1,861 DSC files verified, zero missing objects and zero failures**. The source
content totals **11,426,746,351 bytes**, including Dagric's exact commit archive.
Including DSCs, the 6,010 content-addressed cache files total 11,431,922,649 bytes.

A separate offline run rehashed all completed objects with the final downloader
code and used zero network bytes. Its receipt is
`out/private-source-candidate-20e24dd0-20260905/full-source-final-offline.private.json`,
generated 5 September 2026 at 18:55:30 UTC, SHA-256
`950f71ce3fa480a260e8d59a9b36dafeb5644ddd5babd6e7886c0358c4f47237`.
The prior successful download receipt is retained as
`full-source-download-retry.private.json`, SHA-256
`4505eff9b91e0f22da2deb6c8fab42dcb6f2c0e86633146847512d9e36fd2190`.
The initial interrupted download did not produce a passing report; complete
verified objects were preserved and reused, not partial transfer prefixes.

`tools/check-source-bundle-images.py` separately rehashed both original images,
extracted each actual edition marker, package manifest and dpkg status, matched
them to the final offline report, and rechecked both image hashes afterward.
Both passed. Receipt:
`/var/tmp/dagric-source-bundle-image-binding-final-20260905.json`.
It does not invent an embedded build-commit marker, reproducibility proof,
signature approval or public source delivery. Its extraction streams and
diagnostics are bounded before buffering; 19 regression tests cover oversized
producers, timeouts, mutations and failure without a success receipt.

This closes the private exact-declared-object availability gap only. The source
promotion hold is unchanged. See `SOURCE-PROMOTION-INTEGRATION-2026-09-05.md`
for the separate lock, authenticity, delivery and release-gate integration work.

## Run modes

Use the existing frozen candidate inputs. Always select a **new** output path.
Default mode is offline and never opens a network connection. A populated cache
is rehashed on every run; an absent archive appears as a missing object. The
optional legacy cache is read-only and each imported object is rehashed.

```sh
python3 tools/audit-source-bundle.py \
  --map out/private-source-candidate-20e24dd0-20260905/exact-source-map.private.json \
  --index out/private-source-candidate-20e24dd0-20260905/source-index.private.json \
  --supplement out/private-source-candidate-20e24dd0-20260905/embedded-source-supplement.private.json \
  --dagric-commit 20e24dd04ea3de802531be5139f9f36fe96a1490 \
  --free-status out/private-source-candidate-20e24dd0-20260905/manifests/free-dpkg-status \
  --pro-status out/private-source-candidate-20e24dd0-20260905/manifests/pro-dpkg-status \
  --free-manifest out/private-source-candidate-20e24dd0-20260905/manifests/free.packages \
  --pro-manifest out/private-source-candidate-20e24dd0-20260905/manifests/pro.packages \
  --free-iso-sha256 0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc \
  --pro-iso-sha256 69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa \
  --cache out/private-source-candidate-20e24dd0-20260905/full-source-cache \
  --legacy-snapshot-cache out/private-source-candidate-20e24dd0-20260905/snapshot-cache \
  --workers 4 \
  --output out/private-source-candidate-20e24dd0-20260905/full-source-next.private.json
```

After checking local free disk space, append `--download --max-download-bytes
12000000000` to permit at most that many streamed response-body bytes in the run.
There are at most eight workers (default four), with bounded per-request timeouts.
Failed reads conservatively charge their complete reserved byte allowance;
reports distinguish measured response-body bytes from uncertain charges.
Redirect response bodies are closed without an unbounded read outside that
budget. This ceiling does not measure HTTP headers or total wire traffic.
This is a transfer ceiling, not a disk-space reservation or a promise of success.
All required archives must verify for exit 0. Exit 1 means an incomplete receipt;
exit 2 means rejected inputs/options or another preflight failure.

Downloads only use timestamp-pinned official Snapshot URLs and the exact Dagric
GitHub commit archive. Redirects cannot downgrade HTTPS, cross to unrelated
origins, add credentials/query strings, or change the Dagric commit. No shell
commands or archive contents are executed. Completed digest-named objects are
atomically cached. Interrupted temporary objects are removed; rerunning skips
only complete objects that pass a fresh size/hash check. Partial HTTP transfers
are not resumed. A corrupted existing cache object fails rather than being
silently replaced. New reports are exclusive-create; existing evidence is never
overwritten. Symlinks, Windows reparse points and hard-linked inputs are refused.

## What remains separate

The source bundle report binds hashes of the actual supplied maps, source index,
package manifests and immutable dpkg status files, plus the source commit and
supplied ISO receipt hashes/sizes. It does **not** independently extract or hash
the ISO files. The separate image-binding check must establish that provenance.

Verified object bytes are not equivalent to verified OpenPGP signer authority:
the DSC clearsign wrapper is parsed, not cryptographically approved. Authentic
signatures, undeclared vendored-code review, full corresponding-source duties,
source retention/delivery, package/firmware/artwork rights, and physical/security
release evidence remain separate. All reports retain `release_approved: false`,
`corresponding_source_complete: false`, `openpgp_signatures_verified: false` and
`public_delivery_verified: false` even when every source object is present.

## Regression evidence

`python3 test/test-source-bundle.py`: 30 tests pass in Debian WSL, including
symlink rejection, failed-read budget accounting and all five redirect status
codes without unbounded body drains. Tests cover candidate/edition/hash
binding, exact dpkg source identities, missing and extra declarations, poisoned
caches, invalid DSC checksums/sizes/identities, malicious URLs and redirects,
transfer limits across workers, HTTP corruption, offline inventory, resumed
verified caches, zero archive fetching after metadata failure, and no report
overwrite. The existing 17 embedded-source regressions also pass unchanged.

A separate 163-byte live retrieval probe successfully followed Snapshot's
official `/file/<SHA-1>/<original-filename>` redirect and checked the exact
`libisofs_1.5.6.pl01.orig.tar.gz.asc` content SHA-256 and size. This verifies the
download path only; retrieving a signature file does not verify its signature.
