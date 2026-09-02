# Dagric Flow

Dagric Flow is Dagric OS's visual language: a restrained obsidian surface,
subtle material depth and one red **Pulse Ribbon** used as the unmistakable
brand signature. It is designed to feel premium without consuming CPU, GPU or
battery on the older computers Dagric targets.

## Shipped foundation

- **Obsidian Pulse** is a static 16:9 wallpaper at 1080p and 4K. The red ribbon
  lives in the lower-right, leaving the primary work area quiet and readable.
- **Obsidian Flow** is the first style in Dagric Appearance. It applies the
  Dagric dark scheme, Pulse Red accent, Obsidian Pulse wallpaper and sensible
  no-motion defaults.
- `flow-tokens.json` is the single, package-shipped source of the Flow palette,
  spacing, radius and motion rules. New QML and web surfaces should take values
  from this contract rather than introducing one-off colours.
- Fresh systems seed Obsidian Pulse and Dagric Dark, so the desktop, recovery
  and first-login visual direction agree from the beginning.

## Accessibility and performance rules

Pulse Red is an interaction colour, not body text on dark backgrounds. The
scheme uses Frost/Mist for sustained reading and keeps success, warning and
danger semantically distinct. The default artwork is rendered once as an image:
there is no animated wallpaper, shader, polling loop or persistent GPU work.
Reduced-motion users should receive fades rather than travel animations.

## Next implementation slices

The identity is intentionally layered on top of upstream KDE rather than
forking Plasma or KWin. The next independently testable slices are: a shared
Plymouth/SDDM lock screen using this artwork, a compact 40px Horizon Bar,
and a Home launcher that opens work, games and recent files without replacing
the application menu. Each must retain a stock fallback and remain optional.
