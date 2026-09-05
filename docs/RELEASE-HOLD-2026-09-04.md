# Dagric OS release hold — 2026-09-04

## Status

Dagric OS 1.0 Free and Pro binary delivery and new Pro sales remain held. The
repository now contains a release-exact one-to-one corresponding-source map for
all 1,810 Free and 2,537 Pro binary entries, and all five release locales are
mechanically complete. The live site may still expose the earlier hold-only
deployment until the new source is reviewed and deployed. This document records
an engineering hold, not a legal conclusion.

## Implemented in this repository

- The download page has no direct public ISO or Stripe checkout URL and explains
  the temporary corresponding-source hold.
- The Pro page and home page route purchase calls to release status instead of
  bypassing the hold.
- The post-purchase page provides contact/support and preserves cancellation or
  refund-remedy language instead of constructing a private download URL.
- The download Worker returns `503` before Stripe, KV, or R2 access unless the
  deployment explicitly sets `DISTRIBUTION_ENABLED` to `"true"`.
- Structured-data offers report `OutOfStock` and do not advertise a download URL.
- Repository checks fail if checkout/direct ISO links or available structured
  offers return while distribution is held, independently of source-map status.
- Dagric's Firefox enterprise policy was removed from the image and update
  package; the gate now requires candidate-bound human review of the exact
  `unmodified-distribution-reviewed` disposition.
- The publication path now rejects missing or stale human physical evidence for
  Secure Boot, install/reboot/login, hardware, accessibility, multi-user and
  OpenSnitch testing across the required hardware matrix.

## Operations still required on the live services

These are external account actions; a local source edit alone does not complete
them. Live state was rechecked on 4 September 2026 after the emergency hold
deployment:

1. **Completed:** deployed the reviewed static site. `/download` and `/pro`
   disclose the hold and contain no ISO or Stripe link; `/thanks-pro` contains
   neither delivery route.
2. **Completed:** deployed `infra/gate-worker.js` with
   `DISTRIBUTION_ENABLED="false"`; the live root returns HTTP 503 before Stripe,
   KV, or R2 access.
3. **Completed:** deactivated the live $39 Dagric OS Pro Stripe Payment Link
   (`plink_1TwRxZ6lZx4VOIr3IATmC1Ak`) on 4 September 2026 at 7:46 PM CDT.
   Stripe reports the link as `Deactivated`, offers only an `Activate` action,
   and its checkout preview reports that the link is no longer active.
4. **Completed:** disabled the `dagric-downloads` R2 development URL without
   deleting the retained release artifact; the former Free ISO URL returns HTTP
   401.
5. **Partly completed:** direct probes pass against the old Free origin, Pro
   gate, `/download`, `/pro`, `/thanks-pro`, and the hold-only source
   index. Authenticated Wrangler reports that the Free bucket's r2.dev URL is
   disabled and no custom domain is attached. The formal
   `tools/check-release-hold.sh` API proof still requires the protected
   `R2_ACCOUNT_ID` and `CLOUDFLARE_R2_AUDIT_TOKEN` environment values; configure
   those in the release environment, then re-run it and a signed-out browser
   drill.
6. **Ongoing requirement:** keep support, cancellation, and applicable refund remedies available to
   existing customers throughout the hold.

The emergency static-site deployment used the current audited working tree to
close a live distribution exposure. It was not produced from a clean release
commit, so it is a hold-only deployment and must not be treated as a release or
promotion artifact.

## Private candidate staging prepared

On 4 September 2026, the dedicated Cloudflare R2 bucket
`dagric-release-staging-private` was created in the ENAM location. Its r2.dev
URL is disabled, no custom domain is attached, and the GitHub repository's
`R2_STAGING_BUCKET` Actions secret now names it. The bucket is empty and no
candidate was uploaded. The separate, read-only
`CLOUDFLARE_R2_AUDIT_TOKEN` Actions secret is still required before the
workflow can prove those privacy settings through Cloudflare's API.

Do not mark any operation above complete without evidence from the live service.

## Resume criteria

Binary delivery and new sales may resume only after all of the following pass for
the exact candidate artifacts:

- release tag, source commit, image filename, byte count, and SHA-256 are bound;
- each Free and Pro binary maps exactly once to its exact corresponding source
  (**complete in the current repository for the recorded 1.0 manifests**);
- every `contrib`, `non-free`, and `non-free-firmware` component and every
  downloader/installer payload is inventoried, notice-reviewed, and covered by
  a human approval record;
- Debian's unmodified Firefox ESR disposition is approved by a qualified human
  and bound to the exact candidate (the prior Dagric policy is already removed);
- all Dagric gaming-helper artwork hashes have human IP approval;
- package, source, security, boot, install, accessibility, and upgrade gates pass;
- the protected physical-evidence gate passes for the exact Free and Pro hashes;
- the website, Worker flag, Stripe link, and R2 access are switched together and
  verified after deployment.

Qualified counsel should review the release packet and the delivery method before
the hold is lifted. Automated checks reduce omissions; they cannot guarantee that
the distribution creates no legal risk.
