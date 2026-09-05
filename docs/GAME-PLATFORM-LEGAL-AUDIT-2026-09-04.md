# Dagric OS game-platform rights audit — 2026-09-04

This is an engineering and release-risk audit, not a legal opinion.
IMPRESSIONSDIRECT360 LLC should have qualified counsel review the distribution before a
commercial release or any campaign that uses third-party logos.

## Current distribution result after remediation

- Dagric OS does not list the Steam client, GOG GALAXY, Epic Games Launcher, or
  Amazon Games client for inclusion in its ISO package lists.
- Steam is offered only through a clearly labeled, user-initiated helper. The
  helper invokes Debian's `steam-installer`; Dagric does not carry the Valve
  client in its source tree or image package list.
- Heroic Games Launcher is not bundled. A user-initiated helper installs the
  upstream GPL-3.0 Flathub application for the current user.
- GOG, Epic Games, and Amazon Games are referenced descriptively as account
  libraries that Heroic supports. Dagric does not include their games, store
  content, credentials, or proprietary clients.
- Lutris, Wine, and DXVK are included in Pro from Debian and retain the package
  notices installed under `/usr/share/doc/<package>/copyright`.
- The former PlayStation-like Gaming Setup master and three controller-led helper
  masters were rejected or retired and replaced. Four current masters are
  hash-pinned and use generic library, setup, compatibility, and performance
  symbols with no controller silhouette or platform mark. Human IP review of
  every exact current hash remains required before commercial release.
- The published 1.0 images bundle Debian's open-source `steam-devices` rules.
  Current release source removes them from future base images: the informed
  Steam helper installs them only after owner consent because Debian warns that
  their broad device and `/dev/uinput` access weakens multi-user isolation.
- NVIDIA binary firmware is bundled from Debian `non-free-firmware`; NVIDIA's
  proprietary kernel/display driver remains an explicit owner-initiated option.

## Controls added

- `TRADEMARKS.md` now identifies the relevant third-party marks, limits their
  use to compatibility and integration descriptions, and disclaims affiliation,
  sponsorship, and endorsement.
- `THIRD-PARTY-NOTICES.md`, the website license page, and the website terms now
  explain what is bundled, what is installed later, and whose terms govern it.
- The Steam helper no longer makes the overbroad claim that Valve's license
  forbids everyone from bundling Steam. It states the narrower, verifiable fact
  that Dagric does not redistribute the client and the owner obtains it under
  Valve's terms.
- First-run no longer calls Steam or the other optional installers with a piped
  yes. Each helper opens interactively and asks before changing the machine;
  the Steam card now identifies the proprietary Valve client and vendor terms.
- `tools/check-game-platform-policy.py` hash-pins all four game-related masters,
  bans their rejected/retired predecessors and false free-software copy, audits
  package lists and published manifests, and checks the first-run/helper
  execution boundary.
  It runs alongside `tools/check-release-rights.py` in all release workflows.

## Rules for releases and marketing

1. Keep proprietary game-store clients and game content out of the ISO unless
   written redistribution permission has been obtained and reviewed.
2. Keep every proprietary install explicit and owner initiated. Show the source
   and governing terms before installation.
3. Use platform names only to explain compatibility. Do not use third-party
   logos in Dagric branding, helper icons, ads, thumbnails, or badges without
   permission that covers that exact use.
4. Do not imply partnership, certification, sponsorship, or endorsement.
5. Retain Debian/upstream copyright files and publish the exact package manifest
   for every release.
6. Re-run both `python tools/check-release-rights.py` and
   `python tools/check-game-platform-policy.py` against every release candidate.
7. Re-review this audit whenever a helper, package source, icon, store name, or
   marketing claim changes.

## Official policies reviewed

- Valve Steam Subscriber Agreement: <https://store.steampowered.com/subscriber_agreement/>
- Valve Steam branding guidelines: <https://partner.steamgames.com/doc/marketing/branding>
- GOG brand and visual guidelines: <https://www.gog.com/pressroom/wp-content/uploads/2025/06/GOG-Brand-Visual-Guidelines.pdf>
- Epic Games intellectual-property FAQ: <https://legal.epicgames.com/epicgames/intellectual-property-faq>
- Amazon trademark guidelines: <https://developer.amazon.com/en/support/legal/tuabg>
- Heroic Games Launcher source and GPL-3.0 license: <https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher>
- Lutris source and GPL-3.0 license: <https://github.com/lutris/lutris>

## Remaining legal-review items

- Counsel should confirm the exact hash-pinned Gaming artwork, final installer
  flow, screenshots, advertising, source-delivery path, and distribution
  territories against each current provider policy.
- Any future use of official platform logos requires a separate permission and
  brand-guideline review; the current generic icons should remain the default.
- Mozilla's separate distribution/trademark review remains open and is outside
  this game-platform audit.
