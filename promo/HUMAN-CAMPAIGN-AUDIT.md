# Dagric OS Human Campaign Audit

Audited: 2026-09-01 (America/Chicago)

## Verdict

The 12-video human campaign is approved for scheduling as a smaller, proof-led replacement set. It is materially stronger than the earlier high-volume batch because it leads with genuine Dagric OS and Docker Desktop interaction, varies the narration and calls to action, and names the limits of VM evidence.

## Deliverables

- 12 MP4 files: eight vertical and four landscape
- Eight distinct editorial concepts
- Six distinct narration voices
- Sidecar SRT captions for every MP4
- Persistent social strip: `@dagricosofficial`, Snapchat `@dagricos`, and `dagric.com`
- Varied end cards and calls to action

## Technical checks

| Check | Result |
| --- | --- |
| Video count | 12/12 |
| Container/video/audio | MP4, H.264, AAC |
| Audio | 12/12 stereo, 48 kHz |
| Silent-track scan | 0 failures |
| Duplicate SHA-256 hashes | 0 |
| Vertical frame | 1080 x 1920 |
| Landscape frame | 1920 x 1080 |
| Frame rate | 30 fps |
| Duration range | 20-42 seconds |
| Caption safe-area review | Pass |
| Black/missing-footage review | Pass; the detected final 2.7 seconds are the intentional dark social end card |

## Editorial and claims review

- The primary footage is genuine Dagric OS Pro live-ISO UI captured from the QEMU framebuffer.
- The Docker sequence uses genuine Docker Desktop state from the running `dagric-boottest` container.
- The videos do not claim that a VM proves Wi-Fi, graphics, suspend, printers, or other physical hardware compatibility.
- The hardware-check videos show the VM's negative findings rather than hiding them.
- The videos identify KDE Plasma and avoid presenting Dagric as a Windows clone.
- The strongest recurring proposition is: try the live USB and inspect evidence before installing.
- The voice tracks are locally synthesized with Kokoro-82M; platform synthetic-media disclosure should remain enabled where available.
- The sound bed is locally synthesized and uses no downloaded music, samples, or stock audio.

## Scheduling rule

Use these files to replace weaker future posts; do not stack them on top of the existing queue. Assign a different concept to each platform on a given day, rotate hooks and outro language, and keep each social account to two or three posts per day. Do not publish the same edit through Buffer, Later, and Publer on the same day.

## Rejected capture

The original accelerated-window capture of Docker Desktop rendered black and is not approved. It is retained in the campaign's rejected-captures folder for traceability and must not be scheduled.
