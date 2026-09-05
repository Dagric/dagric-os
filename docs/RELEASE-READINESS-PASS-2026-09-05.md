# Release-readiness continuation — 5 September 2026

**Dagric OS is not release-ready.** This pass closes concrete engineering and
evidence gaps while retaining all distribution and paid-release holds. A green
developer test suite or private source download is not overall acceptance.

## Frozen candidate identity

Both actual images remain built from
`20e24dd04ea3de802531be5139f9f36fe96a1490`. The audit/tooling changes in this
pass do not alter those images or relabel them as built from a newer commit.

| Edition | Bytes | SHA-256 |
| --- | ---: | --- |
| Free | 1,999,503,360 | `0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc` |
| Pro | 3,901,456,384 | `69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa` |

## Verified progress

- All 1,862 exact primary/declared source identities have their private content:
  1,861 DSC files and 4,149 unique source-content objects, 11,426,746,351 content
  bytes. A fresh offline full-cache rehash passed with zero missing objects or
  failures. See `SOURCE-BUNDLE-AUDIT-2026-09-05.md` for hashes and receipts.
- Both actual images were independently hashed, extracted and matched to that
  final source audit's package/status inputs, then rehashed to detect mutation.
  No candidate code was executed by that inspection.
- Downloader regression fixes prevent failed reads and redirect-body draining
  from bypassing the explicit transfer budget. Bounded extraction prevents an
  oversized inventory or diagnostic stream from being fully buffered first.
- The installed-system audit now rejects live boots and non-root invocation,
  requires all four Dagric packages, preserves dpkg/systemd command failures,
  narrowly validates the intended Free/Pro packaging differences, and checks
  runtime and systemd trigger state separately from service enablement.
  Fifteen offline regressions pass; this is **not** a successful installed run.
- The security auditor includes exact `Built-Using` and `Static-Built-Using`
  versions with binary/architecture attribution. Both editions' underlying
  kernel is `linux 6.12.107-1`; the Free packaging-source name no longer hides
  that dependency from the audit. Declared and primary findings stay separate
  because they overlap and are not counts of demonstrated exploitable flaws.
- A canonical private source-lock prerequisite is implemented. It recomputes
  exact input and complete cache bindings offline rather than trusting a prior
  success flag. The shared promotion, authenticity, delivery and human-approval
  integration described in `SOURCE-PROMOTION-INTEGRATION-2026-09-05.md` is still
  separate work; the unconditional hold has not been removed.

The actual canonical lock was created and independently checked by rehashing
the complete cache again. It is stored as
`out/private-source-candidate-20e24dd0-20260905/candidate-source-lock.private.json`,
SHA-256 `1d5c3384e7ae569332e9fa5c535c6536770a42598d83fc333841aa04a5c92419`.
It is an integration prerequisite, not the complete proposed release schema.

The final stable security collection is
`out/private-candidate-security-20260905-release-check/candidate-security-audit.json`,
SHA-256 `3e6c9458a2aab6b0a5f3d391f5aae99d0d276603222626df759cf8e4aed7da62`.
All three repository signatures and 24 package indexes verified. Zero newer
stable binaries were available; known priority findings remain. Twenty-eight
regressions cover exact dependency/architecture attribution and invalid tracker
versions without false clearance. See `CANDIDATE-SECURITY-REAUDIT-2026-09-05.md`.

The final offline OpenPGP run uses Debian's authenticated 27 August canonical
keyring, chained through a signed-index-verified package and a pinned official
maintainer's signed SHA512 manifest. Of 1,861 exact DSCs: **1,570** have positive
canonical-key-state signature evidence; **131 expired**, **134 unavailable**,
**23 revoked** and **three strict cross-certification-error** cases remain.
No weaker signature option, key import or OS suite change was used. Separately,
signed current Debian Sources indexes name 1,815 exact DSC/file-digest sets;
46 historical versions need archival proof. These are provenance observations,
not approval of the remaining signer or legal questions.

Final canonical evidence:
`/var/tmp/dagric-keyring-freshness.wTRo51/full-canonical-dsc-verification/dsc-signatures.private.json`,
SHA-256 `5137f989e50ca6f5cb1400001b0f616e4d1350782739a0259221115cd47f2716`.
See `DEBIAN-KEYRING-FRESHNESS-2026-09-05.md` for dated comparisons and proof.

The real miniature-image integration tests exercise the complete source-content
audit, actual ISO/SquashFS extraction and canonical lock create/check chain.
The positive path uses genuine archive and image bytes, not mocked extraction;
negative cases retain prior evidence and create no new success receipt. These
isolated fixtures remain separate from installed-system or physical acceptance.

Final aggregate verification: `wsl -d Debian sh tools/audit-all.sh --source-only`
completed successfully with **all 50 selected developer gates passing**. The
seven new/expanded audit suites contain 146 passing regression cases: installed
audit 15, candidate security 28, source bundle 30, canonical lock 18, DSC
signatures 31, image binding 19 and real-image integration 5. Native image tools
were available, so the five integration cases actually ran rather than skipped.
The 30-page website check, production JavaScript dependency audit, 140 shell
entry points and all localization checks also passed in that aggregate run.
These are local results, not GitHub hosted checks or release acceptance.

Only reviewed changes from this pass are being saved in one local commit on
`codex/release-safety`. No release tag, signed distribution, cloud deployment
or Git push is part of this continuation. Private images, source-cache data,
keyring evidence and prior failed attempts are preserved outside tracked files.

## Live read-only release-environment recheck

The GitHub repository secret-name listing still lacks
`CLOUDFLARE_R2_AUDIT_TOKEN`; no secret values were retrieved or printed. Existing
R2 storage/staging secret names do not substitute for the required least-privilege
read-only Cloudflare API token.

The latest pushed source run, `33983133474` for `bcd0ba1`, failed before its
runner started. Its current annotation still says the account is locked due to
a billing issue. This confirms the hosted-check blocker on the latest pushed
revision, not just the older run cited in the finishing pass. Billing settings
were not changed. [GitHub run](https://github.com/Dagric/dagric-os/actions/runs/33983133474).

The separate connected `Workers Builds: dagric-os` check also reports failure;
its cause was not diagnosed in this pass. A failed build check is not evidence
that the previously deployed Firebase website is down. No Cloudflare build,
deployment or public release was triggered by this local continuation.

## Actual installer state and required handoff

The Dagric Lab skill's native WSL backend was used for isolated live installer
inspection. Run `e36e5e1382ec4e548919c179fa00d488` uses the exact Pro image above
and the dedicated blank 64 GiB disk:

`/var/tmp/dagric-native-lab/runs/e36e5e1382ec4e548919c179fa00d488/test-disk.raw`.

There is no network interface, host filesystem share or clipboard attachment.
This run is legacy BIOS, not UEFI or physical Secure Boot evidence. The viewer
is `http://localhost:6081/vnc.html`.

Calamares reached Users after verifying American English, America/Chicago,
US keyboard and the sole unpartitioned `/dev/vda` disk. The pending guided plan
uses Btrfs with no swap; the encryption option is visible but not selected.
Only the nonsecret fixture account name `dagricqa` was entered. Both password
fields remain for the user to fill; automatic login is unchecked.
**No partitions were created and installation was not started.**

The user was asked to enter a temporary password twice in the lab, click Next
and stop at Summary, without sharing the password in chat. Continue only after
that handoff and a fresh inspection of the exact disk/summary. Do not automate
around the credential entry boundary. This audit does not claim encryption,
reboot, recovery, OpenSnitch installed enforcement or multi-user acceptance.

## Remaining release requirements

1. Complete real installations and reboots for both editions, then application,
   update, backup/restore, recovery, printing and security-boundary acceptance.
   Include encryption and UEFI paths; a BIOS live desktop is not equivalent.
2. Complete source promotion schema/shared-gate integration using actual images
   and current complete source objects at every promotion boundary. Authenticate
   provenance, review undeclared/vendor coverage and establish approved source
   delivery and retention. Private object hashes alone do not fulfill this.
3. Resolve or explicitly substantiate current upstream security findings. No
   stable-package updates available is not a vulnerability-clear result; disabled
   startup does not protect later use of a vulnerable container runtime/browser.
4. Obtain qualified-human firmware/package redistribution, artwork, Mozilla
   policy and complete corresponding-source approvals. Do not fabricate reviewer
   decisions or infer them from general user permission.
5. Gather physical Secure Boot/hardware, accessibility and multi-user security
   evidence. Neither offline fixtures nor virtualized boot can replace it.
6. Restore GitHub hosted checks after the account-owner/billing-admin issue and
   provide the least-privilege read-only R2 audit secret through the authorized
   live credential workflow. Do not call local tests a hosted CI pass.
7. Keep the release checkout coherent and reviewed. Separate the unchanged
   frozen image build identity from later audit, website and release-tool commits.

The earlier completed locale syntax/coverage checks remain valid: five catalogs
with 670 translated entries each, zero fuzzy/untranslated. Native-speaker and
accessible real-use review remain separate. The earlier website deployment and
release disclosure work is recorded in `WEBSITE-FINISHING-2026-09-05.md`.

No Stripe, Cloudflare/R2 policy, sale, contest submission, social publishing or
public distribution was changed by this continuation. Marketing completion
conditions remain in force; do not advertise the OS as finished or certified.
