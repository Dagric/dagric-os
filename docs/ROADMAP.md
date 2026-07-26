# Roadmap

## Phase 1 — Proof of concept  ← YOU ARE HERE
- [x] live-build source tree, reproducible from Git
- [x] Debloated KDE Plasma package set (no metapackage bloat, no recommends)
- [x] Zero-telemetry guarantee (nothing to disable — it isn't shipped)
- [x] Identity/branding hooks (`os-release`, issue, wallpaper placeholder)
- [x] Hardening baseline: firewall on, silent security updates, no auto-reboot,
      kernel sysctl hardening, zram
- [x] Calamares graphical installer on the live ISO
- [x] One-command build from Windows via Docker
- [x] First successful ISO build (`.\build.ps1`) — 2026-07-21, 1.8 GB hybrid ISO
- [x] Boot test in a VM — boots to full Plasma desktop (QEMU harness in `test\`)

## Phase 2 — Polish
- [x] Real wallpaper — rendered from SVG at build prep, set as Plasma default
      via look-and-feel hook (verified on booted desktop) + SDDM background
- [x] Boot menu splash (`config/bootloaders/splash.svg` — live-build renders it
      for both BIOS/isolinux and EFI/GRUB menus)
- [x] Plasma defaults for Windows switchers (double-click to open, no wobbly
      effects) via `etc/skel`
- [x] Calamares branding module — product name, colors, 3-slide ownership
      slideshow (`etc/calamares/branding/dagric/`); config verified in image
- [x] Flathub enabled out of the box in Discover (verified in image)
- [x] Firefox policies: telemetry/Pocket/studies/sponsored tiles off, tracking
      protection on, uBlock Origin installed via ExtensionSettings (fetched
      from AMO on first run; removable by the owner) (verified in image)
- [x] Calamares install run-through test — full install to a 20 GB virtual
      disk in the QEMU harness, then booted the INSTALLED system to the
      Plasma desktop (branded SDDM login included). Found and fixed three
      install blockers along the way: missing cracklib-runtime,
      squashfs-tools, and grub-pc. Test creds: user dagric.

## Phase 3 — Real-hardware validation
- [x] EFI install support — VERIFIED end to end in the UEFI (OVMF) harness:
      GPT + EFI System Partition + btrfs root install completes, and the
      installed system boots from its EFI partition through the Plymouth
      splash to the desktop. Fix chain: grub-efi-amd64-bin/-signed +
      shim-signed + efibootmgr + gdisk/parted + dosfstools (the killer:
      mkfs.vfat for the FAT32 ESP).
- [x] btrfs default install filesystem (Timeshift atomic snapshots) — verified
- [x] Plymouth branded boot splash — verified on installed system
- [ ] Test matrix: 1 laptop + 1 desktop, Intel and AMD graphics, common Wi-Fi
- [ ] Full-disk-encryption install path verified
- [ ] Secure Boot with enforcing firmware (shim-signed chain ships; test on
      real Secure Boot hardware)
- [x] Live session idle screen-lock disabled (live-config script; installed
      systems keep normal lock behavior)
- [x] Installer menu label renamed to "Install Dagric OS"
- [x] Locales generated (no more terminal locale warnings)
- [x] Windows-switcher hardware/format support: NTFS, exFAT, 7z, laptop
      power profiles, network browsing + thumbnails in Dolphin
- [x] Dagric Welcome: branded offline first-run page, opens once on
      first login (verified live)
- [x] Installed GRUB menu branded ("Dagric OS", background, 2s timeout)

## Phase 4 — Distribution infrastructure (only if it goes public)
- [ ] Private signed APT repo for `dagric-*` config packages
      (move the includes/hooks content into versioned .deb packages)
- [ ] CI pipeline: Git push → ISO build → automated VM boot test
- [ ] Release signing + checksums, download page, support docs

## Explicit non-goals (bloat guard)
Custom kernel, custom package manager, forked desktop environment, rolling
release, full Debian mirror. Debian does the heavy lifting; we maintain the
delta. The moment we violate this, we've become the thing we're against.
