# Dagric social video narration batch

This batch supplies six short voice tracks for the Adobe social-video renders.
The language is intentionally factual and avoids absolute hardware or compatibility
claims.

| Track | Voice | Intended cut | Format |
| --- | --- | --- | --- |
| `windows10.wav` | David | Moving on from Windows 10 | 9:16, 15 seconds |
| `privacy.wav` | Zira | Privacy and control | 1:1, 15 seconds |
| `hardware.wav` | Zira | Check This PC | 9:16, 15 seconds |
| `install.wav` | David | Installation review | 16:9, 15 seconds |
| `looks.wav` | Zira | Desktop layouts | 1:1, 15 seconds |
| `free-vs-pro.wav` | David | Free versus Pro | 16:9, 12 seconds |

The matching `.txt` files are the approved narration copy. The `audio/` directory
contains uncompressed WAV masters so the dialogue can be remixed without generation
loss.

The accompanying non-dialogue Adobe batch contains:

- 15-second promo and looks cuts in 9:16
- A 20-second installer cut in 1:1
- Mixed 24-second montages in 16:9 and 9:16
- A mixed 30-second montage in 1:1
- A 5-second square teaser

## Optional ElevenLabs takes

`../elevenlabs_tts.py` creates an MP3 take from one approved `.txt` file and
an auditable JSON sidecar. It reads `ELEVENLABS_API_KEY` only from the current
process environment; it never reads a project `.env` file or writes the key to
disk. The binary output directory is already ignored by Git.

List the account's approved voices first, then choose a voice ID intentionally:

```powershell
cd promo
npm run tts:voices
npm run tts:eleven -- --text-file narration\windows10.txt --voice-id YOUR_VOICE_ID --output public\narration-batch\windows10.mp3
```

The JSON sidecar records the model, voice ID, voice settings, source text,
SHA-256, and synthetic-voice disclosure without recording credentials. Pair
the resulting narration only with the approved realtime-footage workflow in
`../CREATIVE-PIPELINE.md`; the older screenshot-driven social renderer is now
kept as a `legacy:*` command and is not approved for new output.

Keep the existing Kokoro path as the local/offline fallback. Do not claim that
synthetic narration is a human recording, and use a voice only when you have
the right to use it for the intended Dagric campaign.
