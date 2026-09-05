# Commercial release hard gate

Dagric's normal quality/build workflows may report unresolved legal work as a
warning. The commercial `release.yml` workflow does not: it stops before any
candidate ISO, manifest, GitHub release or live-site record is uploaded unless
the built artifacts, release localization and a qualified human review all
match. Public promotion additionally requires exact, human-reviewed physical
qualification evidence.

This is an engineering control, not legal advice and not a promise that a
release cannot create legal risk.

## Release identity uses two commits

A Git commit cannot contain its own hash. Therefore a release record cannot
truthfully name the same commit that contains that record.

1. The **build-source commit** contains every OS, build-script, policy, notice,
   artwork and checker change. This is the commit recorded by
   `site/manifest/release.json.source.commit` and embedded in the build
   provenance sidecars.
2. Reproducible candidate builds produce the Free/Pro ISO hashes and exact
   `filesystem.packages` inventories. Complete the exact binary-to-source map
   for those inventories.
3. A later **release-record commit** may change only the release JSON, source
   index, package manifests and a release-note document. Put the `v*` release
   tag on this later commit.

The workflow proves that the build-source commit exists, is an ancestor of the
tag, and that no build-affecting file changed between the two. It then checks
out and builds the recorded source commit—not the metadata commit.

The release tag's major version must match the product version. A `v1.x` tag may
describe Dagric OS `1.0`, but a `v2.x` tag cannot silently reuse `1.0` filenames,
hashes or source records.

## Required GitHub environment

Create a protected GitHub Environment named `commercial-release` and configure
qualified human required reviewers. Add environment secrets named
`COMMERCIAL_RELEASE_APPROVAL_JSON` and `PHYSICAL_RELEASE_EVIDENCE_JSON`.

Environment approval by itself is not treated as legal clearance. The JSON is
also checked against the exact release tag, build-source commit, Firefox
configuration hash or verified absence, complete ordered game-art policy/hash
set, and every firmware/microcode
package resolved into both candidate ISOs. A generic engineering review, AI
output, missing evidence, `pending` value, stale hash, omitted asset, or omitted
firmware downloader blocks the release.

Do not commit the completed approval JSON. Preserve it in the company's legal
record system and put that system's HTTPS evidence references in the record.
The workflow publishes only its SHA-256 fingerprint.

## Prepare the review scope

After extracting both candidate package manifests, create a fail-closed review
template:

```bash
python3 tools/check-commercial-release.py approval-template \
  --candidate-commit "$BUILD_SOURCE_COMMIT" \
  --release-tag "$RELEASE_TAG" \
  --free-manifest out/dagric-os-1.0.packages \
  --pro-manifest out/dagric-os-pro-1.0.packages \
  --free-package-sections out/PACKAGE_SECTIONS-free.tsv \
  --pro-package-sections out/PACKAGE_SECTIONS-pro.tsv \
  --candidate-source-root candidate-source \
  --firefox-policy candidate-source/config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json \
  --game-policy candidate-source/config/includes.chroot/usr/share/dagric/policy/game-integrations.json \
  --output out/approval.pending.json
```

The generated file deliberately contains `pending-human-review`, false
attestations and blank reviewer/evidence fields. It cannot pass the gate. It
does contain the exact, mechanically derived review scope:

- current Firefox configuration hash, or `absent` when the candidate injects no
  Dagric Firefox policy;
- every asset and SHA-256 listed by
  `game-integrations.json.artworkClearance.assets`, in policy order;
- every resolved package whose binary name contains `firmware` or `microcode`,
  separately for Free and Pro; and
- the subset such as `firmware-b43-installer` and
  `firmware-b43legacy-installer` that downloads/installs another payload and
  needs explicit reviewer attention.
- every resolved package whose authoritative dpkg Section is `contrib/*`,
  `non-free/*`, or `non-free-firmware/*`, including names with no obvious clue
  such as `libfishcamp1t64` and `libsbig4t64`; these are classified for review,
  not automatically banned, because some packages in those sections are FOSS.

The qualified reviewer must examine the evidence and change the record to the
accepted `dagric-commercial-legal-approval-v1` decisions. The gate requires:

- `decision: "approved"`, `scope: "commercial-distribution"`, and
  `reviewed_by_human: true`;
- an exact candidate commit and tag plus a real UTC approval timestamp;
- the human reviewer's name and a legal/IP/trademark role;
- a documented Firefox disposition consistent with the candidate: the current
  no-policy build requires `unmodified-distribution-reviewed`; a modified
  configuration requires written permission or a reviewed unbranded build;
- approved game-art/IP review bound to the complete policy and asset set;
- review of game-platform terms, third-party notices, NVIDIA redistribution,
  the complete firmware/microcode inventories, and the complete resolved
  contrib/non-free/non-free-firmware Section inventories; and
- non-placeholder HTTPS evidence links for each legal decision.

## Artifact and promotion behavior

For each built edition the release workflow extracts
`/live/filesystem.packages` from the immutable ISO. Before its first R2 upload,
it requires all of the following:

- provenance equals the recorded build-source commit;
- ISO filename, byte size and SHA-256 equal both release records;
- package-manifest bytes, package count and SHA-256 equal both release records;
- the complete source map is a one-to-one match for the actual binary package
  names and versions;
- no proprietary storefront package is present, including `steam-installer`,
  `steamcmd`, Steam client/library payloads, GOG Galaxy, Epic Games Launcher,
  Amazon Games or other listed vendor clients; and
- the exact human approval and firmware review scope match; and
- `de`, `es`, `fr`, `it` and `pt_BR` exactly match `po/dagric.pot`, with zero
  fuzzy and zero untranslated active messages.

The localization rule is deliberately release-only. Development and quality
jobs may report partial work without preventing ordinary test images. A
commercial artifact fails because `msgfmt` omits fuzzy translations and empty
translations fall back to English. Run `python3 tools/check-release-locales.py`
to see the exact per-locale counts.

`PACKAGE_SECTIONS-free.tsv` and `PACKAGE_SECTIONS-pro.tsv` are generated from
the built chroot's dpkg database, not inferred from package names or the host's
APT cache. The gate requires each section record to match the ISO package
manifest one-to-one. That prevents a newly resolved non-free dependency from
falling outside the legal review merely because its name looks like a normal
library.

The promotion job downloads both staged package manifests and checksum
sidecars, repeats the combined gate, then validates the protected physical
evidence before staging release records. It creates a **draft** GitHub release.
It does not publish a public release or move
R2 staging objects to live keys because the checksum signature must be made
offline with the protected release key.

Every staged key is isolated under
`staging/<release-tag>/<build-source-commit>/` in a **dedicated private bucket**.
Set the protected `R2_STAGING_BUCKET` secret to a bucket other than
`dagric-downloads` and `dagric-pro`, disable its r2.dev URL, and attach no
custom domain. `CLOUDFLARE_R2_AUDIT_TOKEN` needs Workers R2 Storage Read so the
workflow can verify both conditions through Cloudflare's domain APIs before
every candidate upload. A prefix inside `dagric-downloads` is not staging:
that bucket is public and the tag/commit prefix is guessable.

Before creating the draft, the
workflow checks each remote ISO's byte size and its upload-time SHA-256,
source-commit and release-tag metadata against the release record. Concurrent
or retried release runs therefore cannot silently assemble one candidate from
another run's shared staging keys.

The commercial gate emits
`out/release-gate/COMMERCIAL-RELEASE-AUTHORIZATION.json`. It contains hashes and
identities, never the confidential approval JSON. It is not a bearer token:
the staging and promotion helpers re-run the gate over the current files and
must reproduce it exactly.

## Physical qualification gate

Generate the pending packet only after the release record contains the exact
candidate artifact hashes:

```bash
python3 tools/check-physical-release.py template \
  --candidate-commit "$BUILD_SOURCE_COMMIT" \
  --release-tag "$RELEASE_TAG" \
  --output out/physical-release.pending.json
```

The template is deliberately non-passing. A human test lead must run and link
evidence for physical BIOS, UEFI and Secure Boot paths; Free and Pro install,
reboot and login; display acceleration, Ethernet, Wi-Fi, audio, Bluetooth and
suspend/resume; keyboard-only, audible Orca, 200% text, reduced-motion, X11 and
Wayland checks; multi-user home/Polkit/family-control isolation; and Pro
OpenSnitch socket, key and non-admin boundaries. The matrix must cover Intel and
AMD processors and Intel, AMD and NVIDIA graphics without recording serial
numbers, MAC addresses, IP addresses or usernames.

Store the completed JSON as the protected `PHYSICAL_RELEASE_EVIDENCE_JSON`
environment secret. `tools/check-physical-release.py check` binds it to the
exact source commit, tag, Free/Pro filenames, byte sizes and SHA-256 values. The
workflow and manual live-promotion path publish only its SHA-256 fingerprint and
bind that fingerprint into the live-promotion receipt. VM results cannot satisfy
this gate.

The manual path is intentionally split:

1. `tools/release.sh sign` repeats the gate and creates the offline signature.
2. `tools/upload-to-r2.sh <file>` accepts only an exact allowlist, derives the
   bucket and candidate key, and can write only under the isolated staging
   prefix in `DAGRIC_STAGING_BUCKET`. It rejects either live bucket and uses the
   Cloudflare API to prove the staging bucket has no public domain. It has no
   caller-supplied bucket or live-key mode. Stage both ISOs, `SHA256SUMS`,
   `SHA256SUMS.sig`, and the authorization JSON.
3. `DAGRIC_PROMOTE_TO_LIVE=YES tools/promote-r2-release.sh` repeats the full
   commercial and physical gates, verifies the signing-key fingerprint and every staged byte, then moves
   only the exact Free/Pro and checksum objects to their fixed live keys. The
   detached signature is moved last and every live byte is read back. Only then
   does it write the exact, local `R2-LIVE-PROMOTION.json` receipt. The command
   runs `tools/check-release-hold.sh` before the first live write and after
   readback: the public download page must show the hold, the Pro Worker must
   return 503, and every Free origin listed in
   `infra/release-public-origins.txt` must be unavailable. Keep that hold in
   place through the matching site deployment. The hold check also queries
   Cloudflare's authoritative r2.dev and custom-domain settings for the live
   Free bucket and rejects any enabled public domain. Then re-enable delivery
   as a separate reviewed operation and run `tools/verify-published.sh`.
4. `tools/release.sh publish` repeats the gate and requires that receipt to
   match the current authorization, ISO identities, checksums and signature
   before changing the site. A new `sign` run deletes any older receipt.

All commands require `DAGRIC_RELEASE_TAG` and
`COMMERCIAL_RELEASE_APPROVAL_JSON`; live promotion and publication additionally
require `PHYSICAL_RELEASE_EVIDENCE_JSON`. The R2 steps additionally require
`DAGRIC_STAGING_BUCKET`, `CLOUDFLARE_R2_AUDIT_TOKEN`, and the environment-only
R2 credentials. Do not use raw `aws`, `rclone`, dashboard, or public-root upload
commands as a substitute for this sequence.

## Current state

The exact Free/Pro binary-to-source map is complete, all five required PO
catalogs have zero fuzzy and zero untranslated active messages, and the injected
Firefox policy has been removed. Distribution remains held because no qualified
human legal/trademark/package-rights/artwork approval or candidate-bound physical
qualification exists, and the dirty development tree has not yet become an
immutable build-source commit with matching new ISO hashes. Do not invent either
approval or weaken the physical gate merely to make CI green.
