# Dagric social replacement deployment — 2026-09-04

## Completed cleanup

| Service | Old media/posts removed | Verified remaining state |
| --- | ---: | --- |
| Later | 26 old videos and 1 legacy draft | 44 videos; all grouped as uploaded Today; no legacy draft remains |
| Publer | 11 old videos | Media Library empty |
| Buffer | 191 scheduled posts and 4 drafts | YouTube queue 0; TikTok queue 0; Instagram queue 0; drafts 0 |

The deletions above were performed through the signed-in service interfaces and are not recoverable through those interfaces.

## Replacement batch

- Root: `C:\Users\1248n\Downloads\Dagric OS Videos\Realtime Replacement Batch\batch-01`
- Deliverables: 44 MP4 files (11 stories × TikTok, Instagram, YouTube Shorts, and Snapchat)
- Automated audit: 44 pass, 0 fail
- Continuous Dagric footage: required
- Snapshot inputs: forbidden
- Simultaneous product-video layers: exactly one
- Captions/subtitle streams/sidecars: forbidden
- Intro label: optional, confined to unused letterbox space, maximum three seconds
- Platform-specific persistent banners: forbidden
- Human voice-naturalness review: pending

## Deployment state

- Later: all 44 replacement files uploaded to the Media Library; none newly scheduled or published.
- Publer: replacement upload blocked because the in-app file chooser did not return a file-selection event. The Free plan also deletes unused library media after seven days.
- Buffer: replacement posts not created because the required end-to-end voice listening review is still pending. All legacy queues and drafts are clear.

## Next publish gate

1. Listen to every unique narration master in full and record pass/revise results.
2. Re-render any rejected narration with a lighter, faster, more natural voice.
3. Upload only the platform-specific files assigned to each scheduler.
4. Create multiple distinct posts per day without duplicate cross-scheduler ownership.
5. Stop immediately before the final external scheduling/publishing confirmation.
