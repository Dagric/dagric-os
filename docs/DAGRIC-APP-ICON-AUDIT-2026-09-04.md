# Dagric OS app icon audit — 2026-09-04

## Outcome

All 32 Dagric launchers that previously reused `dagric-logo` now have distinct artwork derived from the launcher's `Name` and `Comment`. Dagric Picks has its own original icon too, replacing the Discover icon that made two different applications look like the same Software Store. The remaining launchers that already reference a suitable custom or system icon remain unchanged.

Each new master is a transparent PNG in `branding/icons/apps`. `tools/build-app-icons.py` exports standard hicolor theme sizes: 16, 22, 24, 32, 48, 64, 128, 256, and 512 pixels.

## Visual mapping

| Launcher | Icon metaphor |
|---|---|
| Local AI | neural chip, private shield, offline cloud |
| Appearance | monitor, wallpaper cards, color palette |
| Blueprint | system diagram, checklist, gear |
| Text Size | monitor, magnifier, readable text bars, night moon |
| Graphics Drivers | GPU, gear, download arrow |
| Set Up Dagric | welcoming desktop doorway and setup wand |
| Gaming Setup | generic game window, settings gear and performance gauge |
| Bottles | isolated bottle compartments and download arrow |
| Cryptomator | locked encrypted folder vault |
| Heroic | independent multi-library cabinet, abstract cover tiles and connection spark |
| Joplin | locked notebook and device sync |
| LocalSend | laptop-to-phone local transfer |
| ONLYOFFICE | writer, grid and presentation documents |
| ProtonUp-Qt | compatibility gear, verified particle core and update arrows |
| DaVinci Resolve | editing timeline, color wheel and download arrow |
| Steam | generic game-tile library, install arrow and verification shield |
| Upscayl | soft-to-sharp image enlargement and local AI chip |
| Variety | rotating wallpaper fan and clock |
| User Guide | handbook with update, Wi-Fi, printer and shortcut symbols |
| Dagric Hub | central hub linked to setup, security, guide and creator tools |
| Dagric Picks | layered application cards, trusted selection checks and one restrained focus sparkle |
| Life Support | lifesaver protecting storage health and recovery tools |
| Dagric Looks | selectable desktop layouts |
| Dagric Manual | reference book of app tiles |
| Migrate from Windows | secure old-to-new computer transfer |
| Restore Migration Notes | checklist restored from an archive box |
| Dagric Rewind | rewind ring, gear and restore-point clock |
| Finish Setup | toolbox, graphics, printer and completion check |
| Dagric Styles | prism/wand transforming desktop colors and effects |
| Support Mode | privacy-shielded diagnostics and redacted identity |
| USB Protection | unknown USB stopped by shield and lock |
| Windows in a Virtual Machine | nested desktop isolated behind glass and shield |

Third-party installer artwork uses original functional metaphors rather than copied vendor marks.

## Gaming-artwork clearance record

- Current hash-pinned masters:
  - `dagric-gaming-source.png`: `6b7edf9f688a1438bc38ac88ab1005f22741f838c72f780ba4ca8eb2e300ca46`
  - `dagric-get-steam-source.png`: `19cde985cd6d9668d588f28c5258bac6e717a99aeb3a63479cef7798aa94600d`
  - `dagric-get-heroic-source.png`: `e2a7c838ceba423954eb1ab54c83a5840036bb0f1c979a81df825bcec94516bb`
  - `dagric-get-protonup-source.png`: `ff9c27e08bd6a0f5b1d68fd001e98ed60b7179be7261ed0bcfd07f90fb165d39`
- Preliminary engineering review: 2026-09-04
- Finding: the four current masters use generic library, setup, compatibility,
  and performance metaphors with no controller silhouette, platform shape set,
  recognizable game cover, or third-party logo.
- The policy records and bans all four rejected or retired predecessor hashes;
  every hicolor/family export and the review contact sheet was rebuilt.
- This is a preliminary visual-similarity screen, not a legal opinion. A human
  IP/trademark reviewer must approve the exact current hash before commercial
  release. The policy checker prevents an unreviewed asset change from silently
  replacing this master.

## Validation contract

- No Dagric launcher may use `Icon=dagric-logo` as a generic fallback.
- Every custom Dagric icon name must resolve to a 512-pixel shipped icon.
- Every generated source must be square RGBA with usable transparency.
- The generated contact sheet must make neighboring icons distinguishable at menu scale.
- Its sidecar manifest must hash every current source and the sheet itself, so a
  stale review image cannot survive a source-icon rebuild.
