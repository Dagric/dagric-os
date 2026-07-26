# Dagric OS changelog

## 1.0 "Foundation" — 2026-07-26

First release, free and Pro editions.

### Base
- Debian 13 "Trixie", KDE Plasma, Calamares installer
- Zero telemetry (none shipped), no ads, no accounts
- Firefox hardened by policy: telemetry, studies, Pocket and sponsored tiles
  off, tracking protection on, and **uBlock Origin** set up for you — Firefox
  downloads it from addons.mozilla.org the first time it runs, and it can be
  removed like any add-on
- Debloat: `--apt-recommends false` everywhere, every package hand-picked
- Hardened: firewall on, kernel sysctls, silent security updates,
  **no automatic reboots**, zram swap
- **EFI + BIOS installs** (grub-efi + shim Secure Boot chain and grub-pc-bin
  from one image), **btrfs default filesystem** (instant Timeshift snapshots;
  ext4 available), branded Plymouth boot splash
- Dagric Welcome first-run page + offline user guide
- **Dagric Hub** — one launcher entry gathering every owner tool (setup,
  drivers, Security Checkup, guide, and the Pro creator/gaming/AI helpers)
  in a single edition-aware window, plus searchable menu entries for each
- **Dagric Styles** (`dagric-style`) — one-click desktop moods: color scheme
  + accent + wallpaper + KWin effects together, all reversible via Reset.
  3 styles free, 6 on Pro; extensible by dropping `.style` files in
  `/usr/share/dagric/styles`
- **Dagric Looks** (`dagric-looks`) — switch the desktop layout (panel shape
  and position) to match what you came from. 3 layouts free, 7 on Pro
- **Migration Assistant** (`dagric-migrate`) — copies Documents/Pictures/
  Music/Videos/Desktop plus Chrome/Edge/Firefox bookmarks off the Windows
  partition, read-only, never writing to Windows
- **Snapshot recovery** on the default btrfs install: snapper takes an
  automatic snapshot before and after every apt transaction, and a vendored
  grub-btrfs generator lists them as a boot-menu submenu — a bad update is
  undone from GRUB instead of reinstalled. `dagric-snapshot-setup` wires it
  up on first boot of the installed system
- Accessibility now functional: Orca ships with its speech backend
  (espeak-ng), not mute
- Steam is a one-click consent install, never bundled (Hub entry and menu
  entry on Pro; the `dagric-get-steam` helper ships on every edition)
- Print-to-PDF, L2TP/IPsec VPN, and (Pro) Google Drive in Dolphin
- Pro gaming: Heroic (Epic/GOG/Amazon) and ProtonUp-Qt one-click helpers
- **Dagric logo throughout** (Zorin-style): branded boot-menu splash, desktop
  wallpaper and login background (D monogram + wordmark), the
  application-launcher button (first-login script, self-healing), the
  About-this-System page (`LOGO=` in os-release), and a full hicolor icon set
  (16–256 px + scalable SVG)
- Windows-switcher care: NTFS/exFAT drives, 7z, thumbnails, network browsing,
  laptop power profiles, double-click defaults

### Pro edition adds
- Creator suite: Chromium, Thunderbird, full LibreOffice, GIMP (PhotoGIMP
  layout), Krita, Inkscape, Blender, OBS Studio, Kdenlive
- Gaming/Windows apps: Wine 64+32-bit, Steam (Proton), gamemode, MangoHud,
  Proton-GE via `dagric-gaming`
- **Security Suite**: OpenSnitch per-application outbound firewall (ships in
  monitor mode, blocking is opt-in from the GUI) and USBGuard against
  BadUSB/USB-drop attacks — shipped masked, and armed only by
  `dagric-usb-protect` (Hub → USB protection), which first builds an
  allow-list from the devices already attached so enabling it can never
  deauthorize the owner's own keyboard or mouse
- Timeshift restore points (scheduled GUI on top of the snapper/grub-btrfs
  rollback every edition gets); Borg + Vorta + rclone backup
- KDE Connect phone integration (firewall preconfigured)
- Dev stack: Docker + Compose, Podman, Distrobox, build-essential, git,
  Python, SSH (server off by default)
- Papirus icon theme; owner-consent helpers: `dagric-drivers`,
  `dagric-get-resolve`, `dagric-ai`

### Known limitations
- Real-hardware validation pending (QEMU-tested: BIOS and UEFI)
- Update channel (repo.dagric.com) built but not yet hosted

### History
Named Dagric (dagr "day" + ric "ruler") 2026-07-21; earlier working titles
Freehold OS and Antithesis OS.
