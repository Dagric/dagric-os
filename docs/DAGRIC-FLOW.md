# Dagric Design Language (DDL) and Dagric Flow

The Dagric Design Language (DDL) is the internal contract that keeps boot,
login, desktop, setup, recovery and first-party tools recognizable as one
product. Dagric Flow is its default product-experience theme: a restrained obsidian
surface, subtle material depth and one red **Pulse Ribbon** used as that theme's
signature. It is designed to feel premium without consuming CPU, GPU or battery
on the older computers Dagric targets. Pulse Red does not replace the master
Dagric palette; the blue-to-mint mark, product name, and public action hierarchy
remain stable while desktop themes are free to change accent and wallpaper.

## Shipped foundation

- **Obsidian Pulse** is a static 16:9 wallpaper at 1080p and 4K. The red ribbon
  lives in the lower-right, leaving the primary work area quiet and readable.
- **Obsidian Flow** is the first style in Dagric Appearance. It applies the
  Dagric dark scheme, Pulse Red accent, Obsidian Pulse wallpaper and sensible
  no-motion defaults.
- `flow-tokens.json` is the single, package-shipped source of the DDL palette,
  spacing, radius, typography, surface and motion rules. Its filename remains
  stable for compatibility. New QML and web surfaces should take values
  from this contract rather than introducing one-off colours.
- Fresh systems seed Obsidian Pulse and Dagric Dark, so the desktop, recovery
  and first-login visual direction agree from the beginning.

## Accessibility and performance rules

Pulse Red is an interaction colour, not body text on dark backgrounds. The
scheme uses Frost/Mist for sustained reading and keeps success, warning and
danger semantically distinct. The default artwork is rendered once as an image:
there is no animated wallpaper, shader, polling loop or persistent GPU work.
Reduced-motion users should receive fades rather than travel animations.

## Current implementation boundary

The identity is intentionally layered on upstream KDE rather than forking
Plasma or KWin. Boot artwork, SDDM, first-run, Appearance, Rewind, the 46px
primary panel and the Centered layout now share the DDL contract. The ordinary
shell still uses upstream Plasma components. The next independently testable
slices are a full Dagric look-and-feel package, a categorized Dagric Settings
front end, a Dagric Machine dashboard, and then a signature launcher and quick
controls. Each slice must retain an upstream fallback and pass a real-session
boot test before becoming the default.
