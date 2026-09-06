# Startup and setup motion polish

Source changes only: the existing ISO downloads and running guest do not yet
contain this pass. Rebuild and live visual acceptance remain required.

- Removed setup page, card and button zoom transforms so text remains at native
  scale instead of softening during transitions. Existing short fades remain.
- Choice cards use animated border/color feedback without moving neighboring UI.
- Added a 200 ms header progress line following the actual setup step count;
  it honors the wizard's existing reduced-motion preference.
- Splash retains its sharp SVG logo, adds a fine static outline, and removes
  unreachable entrance animation code. The one-time highlight remains.
- Added a splash reducedMotion property which stops the highlight and disables
  progress interpolation. This property is not yet wired to a persisted desktop
  preference; do not claim system-wide reduced-motion support from this change.
- No boot delay, external artwork, additional package or privileged command added.

Verification: 13 Qt tests passed, including Free/Pro 800x600, 1366x768 and
1920x1080 layout checks and reduced-motion progress. Three boot-presentation
tests and the flow/contrast check passed. The rendered Pro 800x600 text-size
confirmation screen was visually inspected: progress, controls and footer fit.
The host lacks the installed logo path, so its splash test exercises the text
fallback; the real-image SVG appearance still requires live verification.
