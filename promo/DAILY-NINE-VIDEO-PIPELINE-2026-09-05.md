# Dagric daily nine-video pipeline

Verified: 2026-09-05

Timezone: America/Chicago

## Outcome

- Nine new platform-specific portrait videos were rendered from receipt-backed continuous Dagric OS recordings of the newest named build.
- All nine pass the automated Dagric `social-ui` quality gate.
- None is marked publish-ready or scheduled yet because full-speed human motion review and human listening review are still pending.
- The recurring task now wakes every day at 12:30 AM Central to continue production and fill verified empty YouTube, Instagram, and TikTok slots.
- Existing queued posts were preserved. No public post was deleted, replaced, or duplicated.

## Permanent daily target

Each platform receives one distinct post in every slot:

| Central time | YouTube Shorts | Instagram Reels | TikTok |
|---|---|---|---|
| 8:15 AM | one video | one video | one video |
| 1:30 PM | one video | one video | one video |
| 6:00 PM | one video | one video | one video |

That is nine platform posts per day. A video or caption must not repeat on the same account. Existing queued posts own their current platform/time slot; the daily task fills only the missing platform slots.

## Starter batch

| # | Planned platform | Planned time | Video | Length | WPM | LUFS | Longest freeze | Automated gate |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | YouTube Shorts | Sep 6, 8:15 AM | Choose a desktop that fits | 15.0s | 156.0 | -16.0 | 2.90s | Pass |
| 2 | Instagram Reels | Sep 6, 8:15 AM | A clean desktop that opens up | 16.0s | 150.0 | -16.1 | 3.00s | Pass |
| 3 | TikTok | Sep 6, 8:15 AM | Find owner tools fast | 15.0s | 148.0 | -15.9 | 3.10s | Pass |
| 4 | YouTube Shorts | Sep 6, 1:30 PM | Check the computer first | 18.0s | 143.33 | -16.1 | 3.90s | Pass |
| 5 | TikTok | Sep 6, 1:30 PM | Files stay familiar | 15.0s | 140.0 | -16.1 | 3.00s | Pass |
| 6 | Instagram Reels | Sep 6, 6:00 PM | Accessibility before decoration | 16.0s | 150.0 | -16.2 | 3.40s | Pass |
| 7 | TikTok | Sep 6, 6:00 PM | Sound, Bluetooth, and phone | 16.0s | 146.25 | -16.2 | 3.10s | Pass |
| 8 | YouTube Shorts | Sep 7, 8:15 AM | Open the web from the desktop | 15.0s | 168.0 | -16.2 | 3.00s | Pass |
| 9 | Instagram Reels | Sep 7, 8:15 AM | Optional apps stay optional | 15.0s | 160.0 | -16.2 | 2.83s | Pass |

The existing Sep 6 Instagram 1:30 PM and YouTube 6:00 PM posts complete those two slots. The next production batch must begin with the missing Sep 7 TikTok 8:15 AM video, then fill every remaining Sep 7 platform slot.

## Technical and editorial gate

Every final file is 1080x1920, 30 fps, H.264/AAC, with exactly one video stream and one audio stream. The files contain no subtitle streams, caption sidecars, still-image inputs, split screen, picture-in-picture, persistent banners, editor camera drift, or simultaneous product-video layers. The source plays at normal speed. Portrait framing uses fixed 450x800 close-ups and hard cuts around actual interface actions.

The palette rotates through Open Horizon, Open Coast, Night Orbit, and Wild Meadow. Public scripts avoid test-environment wording. Synthetic narration remains disclosed in production metadata and must be disclosed through platform controls where available.

Automated checks are necessary but not sufficient. Publishing remains blocked until a person watches each final video at normal speed and confirms all five manual fields: single visual focus, transition flow, natural voice, clear questions/statements, and no caption overlay.

## Recording blocker

Docker Desktop 4.84 currently crashes while opening the stale reparse point at `C:\Users\1248n\AppData\Local\Docker\run\dockerInference`. Windows returns error 1920 and will not release or remove the socket after Docker stops. A Windows restart is required before a brand-new live recording can be captured. This starter batch therefore uses the existing September 4 continuous recordings, whose capture receipts match the newest named Dagric Pro build hash `94923d86b69523852980e2b08bc8ba3d2929433da3c67beaefde481585c73b3b`.

## Evidence

- Renderer: `promo/assemble-daily-nine-starter.py`
- Batch root: `C:\Users\1248n\Downloads\Dagric OS Videos\Daily 9\starter-01`
- Manifest: `C:\Users\1248n\Downloads\Dagric OS Videos\Daily 9\starter-01\daily-nine-starter-manifest.json`
- Per-video audit: next to each MP4 as `.quality-audit.json`
- Per-video visual evidence: next to each MP4 as `.quality-contact-sheet.jpg`
- Manual-review template: next to each MP4 as `.manual-review.json`
- Rejected browser-price version: `C:\Users\1248n\Downloads\Dagric OS Videos\Daily 9\starter-01\rejected\browser-price-exposure`

The rejected browser-price artifacts were moved, not deleted, so they remain recoverable and cannot be confused with the approved manifest set.
