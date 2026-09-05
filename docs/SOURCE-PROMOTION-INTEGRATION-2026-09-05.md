# Proposed source promotion integration — not implemented

Prerequisite update: the standalone private canonical lock producer/checker
`tools/source-candidate-lock.py` is implemented with 18 offline regressions.
Real creation and a fresh full-content validation both passed for the frozen
candidate: 1,862 exact sources and 6,010 unique DSC/content objects. The lock is
`out/private-source-candidate-20e24dd0-20260905/candidate-source-lock.private.json`,
SHA-256 `1d5c3384e7ae569332e9fa5c535c6536770a42598d83fc333841aa04a5c92419`.
It recomputes inputs/cache, keeps per-source filenames and shared-object aliases,
excludes report/index/self hash cycles, and refuses overwrite or any approval
claim. Source object records are embedded in this first private lock rather
than split into an externally referenced manifest. ISO hashes remain supplied
receipts, and it does not bind separate external build-receipt document hashes.
Those additional contracts and the shared promotion integration below remain
unimplemented; this lock is not accepted as a release authorization.

The remaining engineering design replaces the unconditional source hold in
`tools/install-generated-source-map.py` and `tools/check-commercial-release.py`.
It does **not** remove that hold, approve the candidate, change a public schema,
write release records, upload sources, or authorize distribution. The combined
contract and acceptance tests must be reviewed before implementation.

Private source-object verification is valuable evidence but cannot by itself
close this engineering work or establish complete corresponding-source duties.

## Existing controls and gaps

The current primary map binds every installed binary name/version to one source
identity. The new private tooling also checks immutable dpkg `Source` fields,
exact `Built-Using`/`Static-Built-Using` declarations, DSC identities/file sets,
and complete source-object sizes/hashes. The separate image binder independently
hashes both images and compares the extracted inventories. It correctly labels
the source commit as an external build receipt: these candidates have no
verified embedded commit marker.

The public source schema still represents only the primary map. The commercial
gate separately validates human Firefox, artwork, firmware and restricted-
package approvals, but has no qualified corresponding-source coverage/delivery
approval. Its final unconditional source hold is therefore still necessary.

Two existing interfaces cannot be reused unchanged:

- `check-commercial-release.py promotion` can currently be called without actual
  images when no upload authorization is requested. The release workflow's
  `publish` job uses that metadata-only form. It must not become a successful
  source promotion path after the unconditional hold is removed.
- A current private bundle receipt hashes its source-index input. Placing the
  receipt's hash inside that same source index creates a circular hash. No
  implementation may solve this by dropping a binding or trusting a mutable
  `status: complete` flag.

## 1. Non-circular immutable data contract

Introduce a separately versioned **candidate-source lock**, independent of the
public source index and all derived success reports. File names below are
proposed interfaces, not existing approved formats.

```text
immutable candidate inputs + exact object manifest
                       |
                 source-lock.json
                       |
              public source-index.json

Fresh verification reads these inputs and actual artifacts;
its report may hash them, but they never hash the report back.
```

`source-lock.json` must contain:

- A schema version, exact source commit and release identity.
- Exactly Free and Pro: ISO filename, byte size and SHA-256; package-manifest
  SHA-256; extracted dpkg-status SHA-256; and external build-receipt hashes.
- Exact primary-map and supplementary-record document names and hashes.
- Per-edition declared embedded-source records, including binary name,
  architecture, version, declaration field, and exact source name/version.
- The exact source-object manifest document name and hash.

The object manifest must enumerate **all** required DSC and archive objects,
not just sources absent from the primary map. Each object has its SHA-256,
positive size, original filename(s), source identity references, and pinned
upstream locator(s). Shared content can be stored once, but every source
identity's filename set must remain reconstructable. The Dagric archive is
included and pinned to the exact commit.

The lock must not contain a report hash, public-source-index hash, or its own
hash. Its digest belongs in consumers. Define one canonical JSON serialization
for semantic comparisons; keep original byte hashes for frozen input documents.
Reject duplicate members, unknown fields, duplicate/contradictory records,
extra editions and unreferenced supplementary identities.

The public source index may reference the lock, object manifest, primary map,
supplement and source-delivery manifest by immutable URL and SHA-256. It must
not reinterpret a primary-map pass as overall source clearance. Existing
`complete` records without the new required contract remain invalid for release.

## 2. Shared fresh source gate

Implement one reusable validator, provisionally
`tools/check-source-promotion.py`, called by every actual source installation or
commercial promotion path. It accepts input paths, actual artifacts and an
explicit delivery mode. **A detached passing report is not an input authority.**

Required inputs include both actual ISO files; both external source-commit
receipts; the lock; exact primary and supplemental records; the source object
cache; approved delivery manifest; and authenticated provenance inputs. At the
time of promotion the gate must:

1. Independently hash and extract both immutable images, checking edition,
   package manifests, dpkg status, source commit receipts and all lock bindings.
   The supplied source commit must not be called embedded or reproducible
   provenance when only an external receipt supports it.
2. Recompute exact primary identities and per-edition embedded declarations from
   the extracted bytes. Require one-to-one binary coverage and exact source
   versions, with no missing declarations or substitutions by newer versions.
3. Re-parse and hash every required DSC and source archive from the current
   cache. Compare all checksums, sizes, source identities and filename sets to
   the independently recomputed inventory and object manifest.
4. Recheck approved source-authenticity evidence. A parsed PGP armor block is
   not verification. Signer authority/keyring provenance and invalid, revoked,
   unknown or unsigned records need explicit handling. Any alternative signed
   repository-metadata chain must itself be cryptographically verified down to
   the exact source objects; do not turn an exception list into a force flag.
5. Verify the required delivery mode using actual retrieved object bytes and
   compare the exact delivered object set. A HEAD response, content length,
   object-count claim, R2 user metadata, or a previous report is not sufficient.
6. Check input identities again before producing a result. Changed inputs,
   symlinks/reparse points, partial reads and ambiguous JSON must fail closed.

Use bounded, resumable verification of completed objects and explicit download
budgets. Never execute or build downloaded source as part of this gate. Failure
must leave existing records/authorizations intact and create no new authorization.

## 3. Source delivery and retention contract

Separate two purposes so private staging does not pretend to be public delivery:

- **Private candidate staging:** the exact complete objects and metadata are
  available in the dedicated private candidate namespace and verified by full
  authenticated readback. This may support a private staging authorization,
  never a public-release authorization.
- **Public release:** before exposing binary downloads, all approved source
  delivery URLs must retrieve the exact corresponding objects without a secret,
  expiring URL, undisclosed account requirement or payment condition inconsistent
  with the reviewed source offer. Verify full object content, redirects and
  availability at the intended customer-facing endpoint.

A source-delivery manifest must bind the candidate lock, exact object identities,
delivery URLs and original filenames. It also identifies the retention policy,
responsible operator, source-request route and the qualified approval covering
that delivery method. A URL claiming to be permanent does not establish the
operator's retention obligations. The appropriate duration, written offers,
third-party-mirror reliance and additional build/install information must be
decided by the qualified reviewer for the actual licenses, not guessed by code.

If using Dagric-controlled object storage, use immutable candidate/content keys,
least-privilege credentials, no overwrite of older source objects, and readback
verification. Publish source objects before enabling their corresponding binary
downloads, while retaining all existing download holds. Do not expose private
candidate metadata, reviewer personal information, credentials or unsigned
binary candidates through the source endpoint.

Do not select paid storage, change retention/deletion settings, or make public
uploads merely to get a green test. Those are separate live actions requiring
the approved delivery plan and existing user authorization for that scope.

## 4. Qualified corresponding-source approval

Extend the protected human approval contract with a dedicated corresponding-
source section bound to the exact source lock and delivery-manifest hashes,
source commit and both image hashes. It must cover:

- Primary and declared embedded source coverage, plus investigation of relevant
  undeclared vendored/generated code and additional required build information.
- Applicable license obligations, notices, source availability/retention method,
  source offer/request route, and accepted authenticated-provenance dispositions.
- A named qualified human reviewer, review date, evidence and explicit decision.

Keep firmware, package rights, artwork and Mozilla decisions separate and retain
their existing exact-inventory/policy bindings. Generic user permission, a test
fixture, an engineering pass, or a synthesized reviewer name is not approval.
Physical Secure Boot, hardware, accessibility and multi-user evidence also remain
separate and mandatory before live distribution.

## 5. Concrete integration changes

| Component | Required change |
| --- | --- |
| New lock/object/delivery schemas | Strict versioned data contract with positive sizes, exact identities and no report/index hash cycle. |
| `site/manifest/source-index.schema.json` and `release.schema.json` | Distinguish primary metadata, privately verified content and qualified public source delivery; require the new lock/delivery bindings for complete release status. Preserve existing holds. |
| `tools/audit-site.py` | Validate new references and exact public record consistency; do not treat an offline website check as live availability or legal approval. |
| `tools/install-generated-source-map.py` | Replace the legacy primary-only operation with new staged-record preparation using the shared gate. No automatic distribution enabling, unrelated hold removal, or in-place partial record updates. |
| `tools/check-commercial-release.py` | Invoke the shared fresh gate; require both actual ISO/provenance pairs for every promotion; validate qualified source approval; bind source lock, object manifest and delivery evidence in versioned authorizations. |
| `tools/release.sh` | Supply complete artifacts/inputs at sign, stage and publish boundaries; preserve clean tagged source checks, locale checks and human/physical gates. |
| `.github/workflows/release.yml` | Supply source inputs to both jobs. The publish job must retrieve actual private candidate images/content or delegate promotion to the local full-artifact gate; metadata-only promotion cannot pass. |
| `tools/upload-to-r2.sh` and `promote-r2-release.sh` | Verify the extended authorization and exact source availability/readback before applicable writes; preserve private staging, physical validation, fixed signing fingerprint, held public origins and signature-last ordering. |

Avoid requiring public availability before private source staging, which would
create an operational dependency cycle. Use distinct, non-interchangeable
`private-staging` and `public-release` authorization scopes. Private staging
cannot clear the public source hold. Public record preparation should write a
new complete candidate directory and validate it before any later atomic
installation; do not independently overwrite release and source-index files.

## 6. Acceptance fixtures before replacing the hold

Reuse the current 17 embedded-source tests, source-bundle tests, image-binding
tests and commercial/physical regression tests. The old commercial fixtures
use fake ISO text and DSC URLs/hashes; they correctly test earlier validators
but must **not** become the positive full-source fixture by mocking out the new
gate or adding `complete: true`.

Add a positive isolated end-to-end fixture with tiny actual ISO/SquashFS images
for both editions, different package/status inventories, an epoch/binary rebuild,
a dependency present only in `Built-Using`, another only in `Static-Built-Using`,
two source versions, a shared archive, and a commit-pinned Dagric source object.
Use tiny real hash-bound DSC/archive bytes and isolated test-only signing keys
and transport fixtures. Unit-test synthetic human attestations only inside the
fixture; they must never enter production records or be called actual approvals.

Positive acceptance must prove the shared gate actually executes all content,
image, source, delivery and approval checks, then writes only a new correctly
scoped authorization. Tests for live distribution must include the physical
gate and signature checks, not merely a source-only pass.

Mandatory negative cases include:

- Primary-only mapping; detached passing inventory; absent, extra, stale or
  wrong-version embedded sources; and both declaration fields independently.
- Wrong edition, changed ISO, status or manifest; changed external source
  receipt/commit; missing either actual ISO; and mutation during verification.
- Poisoned/truncated/missing content, wrong DSC identity/size/file set, duplicate
  JSON members, source filename traversal and unsafe redirects.
- Invalid/missing signer authority and unauthenticated exception claims.
- Source-lock or delivery-manifest substitution; public 404/private-only access,
  missing delivered objects, correct HEAD with incorrect GET bytes, redirects to
  expiring/credentialed URLs, and mismatched retained object identities.
- Missing or wrong-candidate qualified source approval; unchanged failures for
  Firefox, firmware, restricted packages, artwork, localization and physical
  evidence; proprietary client payloads still rejected.
- Attempt to use private-staging authority for public promotion; staged metadata
  without actual artifacts; public writes before the corresponding gates.
- Every failure leaves existing records and previous authorizations unchanged,
  produces no new authorization and makes zero publish/upload calls. Existing
  output paths and symlink/reparse destinations are refused.

## Implementation sequence and risk boundary

1. Review the independent lock, exact source manifest, delivery modes and human
   approval contract together. No existing hold changes at this step.
2. Implement/test the shared verifier and staged-record preparation with positive
   and negative fixtures. Existing production gates remain blocked.
3. Wire schemas, public-record validation, both workflow jobs, manual staging
   and live promotion paths. Review actual-artifact, approval and write ordering.
4. Only after all paths and failure fixtures pass, replace the unconditional
   source hold with the shared verifier. A candidate still fails normally until
   real source, delivery, qualified-human and physical requirements are satisfied.

This is a multi-component release-boundary change, not a one-line hold removal.
The immediate private byte/signature/image audits reduce the missing evidence;
they do not make this proposed integration implemented or legally approved.
