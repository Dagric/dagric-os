# Mozilla distribution review packet

Status: action required before treating the modified Firefox-branded build as
cleared for commercial distribution.

## Why this review exists

Dagric OS redistributes Debian's `firefox-esr` package and supplies an
enterprise policy file. Mozilla's distribution policy says changes to default
settings, bookmarks, extensions, installer content, and similar behavior make a
distribution modified for trademark-policy purposes. Open-source rights in
Firefox code do not by themselves grant rights to Mozilla's marks.

Official policies:

- https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/
- https://www.mozilla.org/en-US/foundation/trademarks/policy/
- https://www.mozilla.org/en-US/about/legal/firefox/

## Dagric configuration to disclose

Source file:
`config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json`

The current policy:

- disables Firefox telemetry and studies;
- disables Pocket and sponsored Firefox Home content;
- disables extension and feature recommendations;
- skips onboarding and removes default bookmarks;
- enables tracking protection for cryptomining and fingerprinting;
- enables DNS over HTTPS with fallback;
- allows encrypted-media extensions, without locking the setting;
- prevents default-browser prompts and clears first-run/update pages; and
- offers normal first-run installation of uBlock Origin from Mozilla Add-ons.

Dagric does not modify Firefox source code in this repository, but the shipped
policy changes the branded browser's defaults and first-run experience.

## Permission request draft

Subject: Firefox ESR distribution permission request for Dagric OS

> Impressions Direct 360 LLC develops Dagric OS, an independently branded
> Debian 13 derivative. We redistribute Debian's Firefox ESR binary package and
> do not alter Firefox source code or executable binaries. Dagric supplies the
> enterprise-policy configuration summarized and linked below, primarily to
> disable telemetry, studies, sponsored content, and recommendations and to
> offer uBlock Origin from addons.mozilla.org. We identify Firefox as a
> third-party product, do not imply Mozilla sponsorship, and preserve all
> applicable notices. Please confirm whether this redistribution may retain the
> Firefox name and artwork and identify any changes or attribution you require.
>
> Product: https://dagric.com/
>
> Source: https://github.com/Dagric/dagric-os
>
> Policies: [link to the exact tagged policies.json for the release]
>
> Legal/contact identity: Impressions Direct 360 LLC, operating as Dagric

Attach the exact released policy file and a screenshot of Firefox's first-run
state. Do not describe permission as granted until Mozilla replies in writing.

## Release decision record

Complete one of these before release:

- [ ] Written Mozilla permission received and archived with the release record.
- [ ] Firefox policy changes removed and the resulting distribution reviewed
      against Mozilla's current unmodified-distribution requirements.
- [ ] An appropriately unbranded browser package adopted after technical,
      update-security, and legal review.

Record the decision, date, reviewer, relevant version/tag, and stored evidence
here or in the release manifest.
