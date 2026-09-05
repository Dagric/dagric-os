# Website finishing audit — 5 September 2026

## Implemented

- Homepage, Features, Windows switching, installation, FAQ, Pro, download and proof pages now distinguish the held release from historical test results. Removed immediate-download promises from the main calls to action and the claim that a Debian support date automatically covers all Dagric software.
- Kept the original release manifest, source hashes, sales/download hold and existing policy rights intact. The August 2026 proof matrix is explicitly historical; a new build needs its own evidence.
- Installation steps now lead with verification and backup, explain USB/disk erasure, stop when the expected alongside-install option is unavailable, and distinguish signature verification from a matching checksum. The Mac checksum command is now correct.
- Site Finder handles natural questions, Wi-Fi variants, migration/transfer terms, app names and partial words. It includes an explicit empty state, clear action, screen-reader result announcements and a no-JavaScript topic directory.
- Mobile navigation touch targets no longer overlap. The sticky-header offset follows its actual height. Navigation exposes the current page. The website follows the system light/dark preference until the visitor chooses a theme, and autoplay pauses for reduced-motion users.
- Fixed narrow-screen overflow from release hashes and the legal company name. Corrected the homepage's three-item trust strip from a five-column grid.
- The brand gate now requires a release-status action and visible hold notice for held releases and rejects premature download calls to action. Brand metadata matches the current action.

## Verification

- `python tools/check-brand.py`: passed.
- `python tools/audit-site.py`: all 30 pages passed structural, link, metadata, structured-data and media checks.
- Node syntax checks for `site/assets/search.js` and `site/assets/theme.js`: passed.
- Chromium browser run: 30 pages at 320, 390, 768 and 1440 pixels (120 page/viewport checks); zero document overflow and zero page-script errors after repairs.
- Search: “Will my Wi-Fi work?”, “move my files”, “How do I back up?”, “apps” and “release proof” return relevant topics. An unknown query shows the helpful empty state; clearing restores all 14 topics. With JavaScript disabled all 14 remain available.
- Light-system/reduced-motion browser: light theme selected; zero autoplay attributes and video paused.
- Held-release regression using in-memory file substitutions: the current homepage passes; changing its action back to an immediate download or removing the hold notice is rejected.
- Mobile homepage visually inspected in Chromium.

## Live audit and source references

Before these local changes, https://dagric.com/ still offered “Try Dagric OS Free,” purchase-delivery language, blanket Secure Boot wording, and inherited support into 2030 despite the release hold. Local changes require deployment before these findings are resolved in production.

- Debian 13 dates and scope: https://www.debian.org/releases/trixie/ and https://wiki.debian.org/LTS
- Windows 10 options: https://www.microsoft.com/en-us/windows/extended-security-updates

The website does not prove physical hardware compatibility, accessibility usability, multi-user security, firmware/artwork rights or final release provenance. Existing evidence and remaining limitations stay visible. No deployment or public account mutation was performed by this website workstream.

## Deployment verification by the coordinating agent

Firebase Hosting deployment to project `dagric-os` completed on September 5,
2026, before 16:30 UTC. It uploaded the 106 hosting files only; no release
artifact, Worker, payment link or R2 policy was promoted. The coordinating agent
checked the design and a migration query in the in-app browser, then verified
the same two relevant search results on live `https://dagric.com/search`.
The release hold remains visible and enforced.
