# Dagric duration ladder

This campaign uses one continuous, real Dagric VM recording as its visual source. It does not use screenshots, still-image stand-ins, picture-in-picture, a second video layer, burned captions, or subtitle tracks.

## Source of truth

- Capture: `C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\long-form-v3\00-dagric-15-minute-live-showcase-v3.mp4`
- Duration: 900 seconds
- Canvas: 1280 × 800 at 20 fps
- ISO: `out/dagric-os-pro-1.0-amd64.iso`
- ISO SHA-256: `A57CCCBE666765232B4578DF7D4F7FE99E5EC8487A58D572C0C485EEC978BEF3`
- Visual sequence: Open Horizon → Night Orbit → Wild Meadow → Open Coast
- Feature sequence: first run → Hub → hardware check → Files → Settings → Terminal → Software Store → website → Hub → hardware check → website

## Deliverables

| Runtime | Editorial focus | Live-source window | Narration pace |
| --- | --- | ---: | ---: |
| 15 seconds | Fast profile-change hook | 230–245 s | 1.16× |
| 30 seconds | Wild Meadow and Files | 437–467 s | 1.14× |
| 1 minute | Open Coast and Dagric Hub | 676–736 s | 1.12× |
| 5 minutes | First run through Night Orbit | 0–300 s | 1.09× |
| 10 minutes | Tools, proof, and multiple looks | 230–830 s | 1.07× |
| 15 minutes | Complete live tour | 0–900 s | 1.06× |

The narration is generated locally with Kokoro Heart. It is deliberately spaced so the viewer can read the interface. Synthetic-voice disclosure remains in production metadata, and final voice naturalness requires a human listening review.

## Quality gates

Every finished file must have exactly one video stream, one clear audio stream, no subtitle streams, no caption sidecars, stable frame cadence, no extended black frames, and an exact target duration. A contact-sheet review and a full listening review are required before publishing. Source-mode audits never mark a file publish-ready.

Long readable UI holds can trigger the conservative freeze detector even when the capture is functioning correctly. That warning must be reported rather than suppressed; shorter edits should favor active feature windows.

## Publishing

The closing narration asks viewers to follow Dagric OS and visit `dagric.com`. Uploading or replacing posts in Publer, Later, Buffer, YouTube, or any other public channel remains a separate action-time approval step.
