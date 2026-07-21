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
- [ ] Real wallpaper (render `branding/wallpaper/freehold-default.svg` to PNG,
      wire into Plasma defaults + SDDM login screen + GRUB/Plymouth boot splash)
- [ ] Plasma layout defaults tuned for Windows switchers (taskbar, launcher,
      tray, click behavior) via `config/includes.chroot/etc/skel/`
- [ ] Calamares branding module (slideshow, colors, product name)
- [ ] Flathub enabled out of the box in Discover
- [ ] Firefox policies file: no sponsored tiles, no Pocket, sane privacy defaults

## Phase 3 — Real-hardware validation
- [ ] Test matrix: 1 laptop + 1 desktop, Intel and AMD graphics, common Wi-Fi
- [ ] Full-disk-encryption install path verified
- [ ] Secure Boot behavior documented

## Phase 4 — Distribution infrastructure (only if it goes public)
- [ ] Private signed APT repo for `freehold-*` config packages
      (move the includes/hooks content into versioned .deb packages)
- [ ] CI pipeline: Git push → ISO build → automated VM boot test
- [ ] Release signing + checksums, download page, support docs

## Explicit non-goals (bloat guard)
Custom kernel, custom package manager, forked desktop environment, rolling
release, full Debian mirror. Debian does the heavy lifting; we maintain the
delta. The moment we violate this, we've become the thing we're against.
