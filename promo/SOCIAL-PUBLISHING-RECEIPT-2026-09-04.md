# Dagric OS social publishing receipt — 2026-09-04

Timezone: America/Chicago

## Outcome

- The replacement batch contains 100 platform-specific MP4 exports: 25 YouTube Shorts, 25 TikTok videos, 25 Instagram Reels, and 25 Snapchat Stories.
- The final quality audit reports `100/100 PASS`, including automated and user-approved manual checks.
- 86 unique exports are delivery-ready in public/automatic queues.
- 14 Snapchat exports remain local because Later returned `Action Restricted — You don't have permissions to perform that action.` when additional media uploads were attempted.
- No old cloud post, draft, or media item was deleted during this pass.

## Verified publishing queues

| Destination | Scheduler | Count | Date range | Verification |
|---|---|---:|---|---|
| YouTube Shorts — Dagric OS | Buffer | 25 | 2026-09-05 through 2026-10-02 | Buffer sidebar: `Dagric OS 25 scheduled posts` |
| TikTok — @dagricosofficial | Buffer | 25 | 2026-09-05 through 2026-10-03 | Buffer sidebar: `dagricosofficial 25 scheduled posts` |
| Instagram — @dagricosofficial | Buffer | 24 | 2026-09-05 through 2026-10-03 | Buffer sidebar: `dagricosofficial 24 scheduled posts` |
| Instagram Reel — Dagric OS | Publer | 1 | 2026-09-06 13:30 | Publer calendar article verified at `01:30 PM` |
| Snapchat Public Story — @dagricos | Later | 11 | 2026-09-06 through 2026-09-28 | Each campaign entry shows `Auto`; no September campaign entry remains `Draft` |

The combined Instagram count is 25, so YouTube, TikTok, and Instagram each have all 25 approved exports scheduled exactly once.

## Cadence

- The cross-platform campaign uses up to three brand posts per day, normally at 08:15, 13:30, and 18:00 Central.
- Later's Snapchat campaign entries use 08:35 Central on September 6, 7, 8, 13, 14, 15, 20, 21, 22, 27, and 28.
- Topic order rotates first-run, readability, layout, hardware, files, connectivity, browser, security, settings, accessibility, and full-journey demonstrations.

## Private and blocked state

- Later retains one pre-existing duplicate private draft in the August 30–September 5 week. It was not scheduled because doing so would duplicate a video on the same account.
- Publer retains a pre-existing September 4 item and an unsaved composer. Neither was published, rescheduled, or deleted in this pass.
- The 14 unscheduled Snapchat exports remain in `C:\Users\1248n\Downloads\Dagric OS Videos\Realtime Replacement Batch\batch-01\snapchat` and require Later upload permission/capacity or another connected Snapchat publishing route.

## Quality and disclosure controls

- Source audit: `C:\Users\1248n\Downloads\Dagric OS Videos\Realtime Replacement Batch\batch-01\batch-quality-audit.json`.
- Approved content uses continuous screen-recorded motion rather than screenshots or still-frame substitutes.
- No burned captions, subtitle streams, split-screen, picture-in-picture, persistent banners, or competing video layers are present.
- Public copy avoids VM/ISO terminology and directs viewers to the current release status at `https://dagric.com`.
- Synthetic-media disclosure was enabled wherever the scheduler exposed that control.
- Every Buffer post was checked after saving against its account, caption, date, and time.

## Machine restart note

The social queues are stored by Buffer, Publer, and Later, so restarting Windows will not remove the scheduled posts. A restart is still recommended before resuming local Dagric recording because Docker Desktop's Linux engine previously showed a local socket/startup fault.
