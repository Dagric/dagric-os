# Dagric OS changelog

## 1.0 "Foundation" — 2026-07-21

First release, free and Pro editions.

### Base
- Debian 13 "Trixie", KDE Plasma, Calamares installer
- Zero telemetry (none shipped), no ads, no accounts
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
- Timeshift restore points; Borg + Vorta + rclone backup
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
