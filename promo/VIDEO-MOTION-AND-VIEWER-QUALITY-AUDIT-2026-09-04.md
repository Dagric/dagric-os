# Dagric video motion and viewer-quality audit

Audited: 2026-09-04

## Release decision

Do not upload the current 124-video caption-free set yet. All 124 exports contain editor-added continuous crop movement, not just natural motion inside Dagric. The current automated reports passed this because they only tested whether pixels changed; they did not distinguish useful UI activity from artificial camera drift.

The named video, `1-minute-open-coast-hub-youtube.mp4`, has one encoded video stream and no subtitle stream, so it does not have the older two-video-layer defect. It does have the visible shake, weak pacing, a claim/action mismatch, and public-facing text the brief says not to show.

## Named video: 1-minute-open-coast-hub-youtube.mp4

Path: `C:\Users\1248n\Downloads\Dagric OS Videos\Duration Ladder\caption-free-v4\youtube\1-minute-open-coast-hub-youtube.mp4`

### Critical findings

1. **The whole screen is deliberately moved for the entire minute.** The renderer crops at `x = 41 + 41 sin(0.42t)` and `y = 25 + 25 cos(0.37t)`. That moves the desktop up to 82 pixels horizontally and 50 pixels vertically, reversing direction about every 7.5 to 8.5 seconds. Because crop positions are rounded to pixels, a mostly static desktop appears to creep, pause, and jump by a pixel. This is the shake the viewer sees.

2. **The opening says “one click,” but the footage shows a terminal command.** At roughly 0:00-0:09, the viewer sees `dagric-style --apply open-coast`. The spoken promise and visible proof do not match.

3. **The middle is visually under-explained.** Around 0:10-0:18 the video is mostly an empty wallpaper. Around 0:20-0:60 it stays on one long Dagric Hub list while the selection moves down. The existing audit found only two scene cuts in the full minute.

4. **The footage exposes wording the public brief excludes.** At approximately 0:55 the Hub visibly shows `Windows in a VM`.

5. **Narration is too sparse for a one-minute product explanation.** It contains 105 words (105 WPM), about 39.87 seconds of speech, and 20.13 seconds without narration. The gaps are about 6.96 seconds, 6.19 seconds, and a 6.48-second tail after the last spoken line.

6. **There is a short near-freeze.** An independent FFmpeg pass found 0.87 seconds of near-identical frames from approximately 0:25.57 to 0:26.43. The older audit used a looser threshold and reported zero freezes.

### What passes

- 1920x1080, 30 fps, H.264/AAC.
- One encoded video stream and one audio stream.
- No subtitle stream or burned captions detected.
- No black-frame event detected.
- Audio level is technically healthy: -15.9 LUFS integrated and -1.5 dB true peak, with no clipping detected.
- The `Check This PC` desktop icon is already a computer-style illustration rather than the Dagric logo.

### Voice conclusion

The audio level passes, but the storytelling pace does not. The narration uses Kokoro Heart at 1.12x, yet the finished script averages only 105 WPM because of the long gaps. Naturalness is still unverified: every quality report has manual voice review incomplete, so the current files cannot honestly be certified as human-sounding.

## Current 124-video set

Scope:

- 100 files in `Realtime Replacement Batch\batch-01`
- 24 files in `Duration Ladder\caption-free-v4`

| Viewer-facing problem | Affected files | Severity |
|---|---:|---|
| Continuous editor-added crop drift | 124 / 124 | Critical |
| Landscape recording reduced to a 675px-high strip on a 1920px vertical canvas | 118 / 124 | Critical |
| Source footage accelerated between 1.85x and 3.0x | 48 / 124 | High |
| Narration below 120 WPM | 72 / 124 | High |
| Narration above 165 WPM | 24 / 124 | High |
| Freeze of at least one second in existing quality metrics | 13 / 124 | High |
| Manual visual/listening review not passed | 124 / 124 | Release blocker |

### Why the vertical versions look weak

The 100 replacement videos and the 18 vertical duration-ladder videos place a 1080x675 desktop strip at y=300 on a 1080x1920 canvas. Product footage therefore uses only 35.2% of the frame height. The rest is largely a flat color field. This makes menus, settings, and terminal text too small to read on a phone and makes the videos feel empty even when the desktop is moving.

The intro label is outside the product footage and fades by three seconds, which follows the stated banner timing rule. The larger problem is the layout itself: it sacrifices almost two thirds of the mobile frame.

### Accelerated footage

Twelve replacement concepts, exported to four platforms each, speed the captured desktop to 1.85x-3.0x. The worst is `dagric-hub-in-motion` at 3.0x. Fast source playback combines with the artificial crop movement, making pointer movement and menu changes harder to follow.

### Narration pacing

The replacement set has large pacing swings:

- 48 files are slow at 105-112 WPM.
- 24 files are fast at 165.18-178 WPM.
- Only 28 files land in the 120-165 WPM review band.

All 24 duration-ladder exports are slow at 90.4-112 WPM. Their unvoiced share grows with duration:

| Edition | WPM | Time without narration | Share without narration | Silent/ambient tail |
|---|---:|---:|---:|---:|
| 15 seconds | 112.0 | 5.55s | 37.0% | 5.20s |
| 30 seconds | 106.0 | 10.25s | 34.2% | 5.00s |
| 1 minute | 105.0 | 20.13s | 33.5% | 6.48s |
| 5 minutes | 95.8 | 129.93s | 43.3% | 15.69s |
| 10 minutes | 90.4 | 283.33s | 47.2% | 40.48s |
| 15 minutes | 92.4 | 428.53s | 47.6% | 21.46s |

### Files with freezes of at least one second

Replacement batch:

- `44-complete-opening-minute-instagram-vertical.mp4` — 1.60s
- `35-desktop-arrives-fifteen-instagram-vertical.mp4` — 1.60s, 10.7% of the video
- `35-desktop-arrives-fifteen-youtube-shorts-vertical.mp4` — 1.60s, 10.7% of the video
- `34-layout-and-app-choice-thirty-snapchat-vertical.mp4` — 1.53s

Duration ladder:

- Instagram, TikTok, and Snapchat versions of `5-minute-first-run-to-night-orbit` — 1.57s each
- Instagram, TikTok, and Snapchat versions of `10-minute-freedom-and-tools` — 2.53s each
- Instagram, TikTok, and Snapchat versions of `15-minute-complete-live-tour` — 2.53s each

The long-form YouTube versions did not cross the old one-second freeze threshold, but they still use the same continuous moving crop.

## Legacy videos still on disk

### 00-real-dagric-showcase-vertical.mp4

This older 45-second file should remain retired. It has one encoded video stream, but the opening visually nests busy website/video content inside a permanent promo frame, producing the “two videos at once” impression. It also keeps a large header and proof footer on screen for the full video, reduces the desktop to a small window, and has an `.srt` caption sidecar. It conflicts with the current no-captions, no-permanent-banner, single-focus brief.

### Enhanced Masters and Platform-Native Campaign

- 74 `Enhanced Masters` were built with karaoke captions, a visible `AI VOICE` label, a permanent border/progress rail/audio meter, and another sine-wave camera drift.
- 296 `Platform-Native Campaign` files were derived from those enhanced files and add a second moving crop. Their motion can compound the first drift.

These 370 files are legacy and should not be returned to the upload queue.

## Required correction standard before upload

1. Lock the screen recording to a fixed crop for the full shot. No sine/cosine crop motion, zoom drift, simulated handheld movement, or one-pixel oscillation.
2. For vertical posts, use intentional close-up edits of the active window or control, not a full landscape desktop inside a 35%-height strip.
3. Keep product footage at 1.0x unless a clearly marked, short time-lapse is necessary. Do not speed normal UI interaction above 1.25x.
4. Match every spoken claim to the exact action on screen. A terminal command cannot prove “one click.”
5. Remove public-facing `VM`, `ISO`, test-environment, and capture-infrastructure wording from both narration and visible screens selected for marketing.
6. Target roughly 135-160 WPM, with no unexplained gap longer than two seconds and no dead tail longer than one second.
7. Require a full-speed human review of motion, comprehension, voice naturalness, and visual focus. Structural checks alone cannot mark a video publish-ready.
8. Add a negative motion gate: reject full-frame editor movement when the OS itself is stationary. Do not count artificial movement as an attention-hook pass.

## Evidence

- `promo/assemble-duration-ladder-videos.py`: moving vertical crop at line 171 and moving landscape crop at line 182.
- `promo/assemble-caption-free-replacement-batch.py`: moving crop at line 743.
- `promo/enhance-social-videos.py`: moving crop and permanent overlay stack at lines 245-267.
- `promo/make-platform-native-variants.py`: additional moving crop at lines 203-204.
- `C:\Users\1248n\Downloads\Dagric OS Videos\Attention Audit\two-second-attention-audit.json`: previous 124-file test counted motion as a pass but did not classify its source.
- `C:\Users\1248n\Downloads\Dagric OS Videos\Realtime Replacement Batch\batch-01\batch-quality-audit.json`: freeze, loudness, WPM, and manual-review status for 100 files.
- `C:\Users\1248n\Downloads\Dagric OS Videos\Duration Ladder\caption-free-v4\duration-ladder-quality-audit.json`: freeze, loudness, WPM, and manual-review status for 24 files.

No video files were changed during this audit.
