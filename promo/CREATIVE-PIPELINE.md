# Dagric Realtime Video Pipeline

The approved Dagric video path uses continuous, real product footage only.
Still screenshots, slideshow animation, image-to-video generation, and generated
replacement UI are excluded from every publishable master.

```
Running Dagric live ISO / VM
          │ continuous framebuffer recording
          ▼
Raw video-only capture ──► clip selection / factual review
          │
          ├─ ElevenLabs narration (selected licensed voice)
          └─ local Kokoro narration (offline fallback)
          │
          ▼
Realtime edit + text/captions ──► technical/provenance audit
          │
          ▼
Creative Cloud speech cleanup / platform reframe / human review
```

## Non-negotiable visual rule

Every product visual must originate in a continuous screen recording of a
running Dagric session. Do not place text, captions, banners, borders, badges,
or calls to action over the moving product footage. A brief opening title may
use otherwise empty letterbox space and must disappear within three seconds.
Do not use:

- PNG/JPEG screenshots as scenes or backgrounds;
- Ken Burns, parallax, or zoom effects applied to still images;
- Higgsfield image-to-video or any model-generated Dagric interface;
- repeated snapshots presented as a recording;
- stock desktop footage presented as Dagric.

Higgsfield may analyze or help rank uploaded real video clips, but generated
visual frames are outside the approved path.

## 1. Capture continuously

`capture-real-vm.py` now runs a continuous 20 fps encoder alongside an
asynchronous VNC framebuffer-update stream. It no longer refreshes once per
second and uses a still screenshot as a scene. Static UI can naturally produce
identical adjacent video frames, as it does in any screen recorder. Each
recording receives a `.capture.json`
receipt bound to the video by SHA-256; the editor refuses legacy footage that
does not have a valid receipt.

Example:

```powershell
cd promo
npm run capture:realtime -- fresh-onboarding "C:\Users\1248n\Downloads\Dagric OS Videos\Real VM Footage\raw-realtime\01-real-onboarding.mp4"
```

Available scenarios include onboarding, everyday desktop use, hardware check,
settings, Dagric Hub, appearance/layouts, and the live Dagric website. Capture
all seven required source files before rebuilding a delivery. Dagric Hub and
the hardware report deliberately use separate recording sessions.

| Scenario | Required output in `Real VM Footage\raw-realtime` |
| --- | --- |
| `fresh-onboarding` | `01-real-onboarding.mp4` |
| `hub` | `02-real-dagric-hub.mp4` |
| `fresh-hardware` | `03-real-hardware-check.mp4` |
| `appearance` | `04-real-appearance-and-layouts.mp4` |
| `everyday` | `05-real-everyday-desktop.mp4` |
| `settings` | `06-real-settings-accessibility-connect.mp4` |
| `website` | `07-real-firefox-dagric-site.mp4` |

The former `raw-highres` directory is treated as legacy evidence. New captures
go into `raw-realtime`, so the approved renderer cannot accidentally reuse the
older snapshot-sampled recordings.

## 2. Record narration separately

The picture source remains continuous video regardless of narration provider.
Use `elevenlabs_tts.py` for a deliberately selected ElevenLabs voice, or the
installed Kokoro model for an offline/repeatable take. Keep the approved source
text, generated audio, and JSON sidecar together. Never store an API key in the
repository.

## 3. Build only from moving sources

```powershell
npm run render:realtime
npm run audit:realtime
```

`assemble-real-vm-footage.py` rejects a visual source unless it is a video file
with a decodable video stream, enough duration for the requested cut, and a
valid continuous-capture receipt. Its manifest records the exact source file,
source time range, receipt path, empty snapshot input list, and
`generatedVisuals: false` for every output. Both aspect-ratio templates permit
exactly one visible product-video layer; a blurred, cropped, delayed, or second
copy of the Dagric screen is forbidden.

The older screenshot-driven Remotion compositions remain source history only;
their commands are explicitly named `legacy:*` and are not part of this
pipeline. There are no approved `still` package commands.

## 4. Audit the source, not just the final overlay

The realtime audit maps each final file back to its underlying source video and
samples both at one frame per second. At least 40 percent of the sampled frames
must be visually distinct. It independently verifies that every capture receipt
matches the source video's SHA-256. It also rejects missing manifest provenance,
non-video sources, snapshot input entries, generated visuals, missing captions,
bad formats, clipped/silent audio, duplicate deliveries, and any manifest that
does not declare exactly one visible product-video layer.

## 5. Finish without covering or replacing the footage

Creative Cloud may organize footage, enhance the narration, resize/reframe the
continuous video, and support the final human review. It must not cover the
Dagric interface with persistent graphics or substitute a generated or still
Dagric interface. Describe the recording publicly as `live footage`; do not use
internal capture terms such as `VM`, `virtual machine`, or `ISO` in titles or
narration. Technical provenance belongs in the private audit receipt. Keep the footage
manifest, audit report, audio manifest, captions, and final MP4 together.

## Release gate

Before posting:

1. Run `npm run audit:realtime` and require a full pass.
2. Watch the complete final file and confirm the UI is continuously moving.
3. Verify every factual claim against the current Dagric source or live session.
4. Confirm narration rights and add synthetic-media disclosure when required.
5. Treat VM footage as software-workflow proof only; hardware claims still need
   a live USB test on the actual computer.
