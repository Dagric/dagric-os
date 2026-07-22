# Dagric OS — full test report

Session 2026-07-21. Method: hands-on VM test of the Pro edition (live) in the
QEMU harness, ISO-filesystem inspection, and two source-review passes
(bug hunt + commercial-gap analysis).

## What was verified working

- Boots to live desktop (BIOS + UEFI, both editions) with Dagric wallpaper
- Branded "Install Dagric OS" desktop icon + Calamares (D logo, verified on screen)
- Welcome page auto-opens on first login; offline user guide linked
- Ctrl+Esc system monitor (confirmed by user on real hardware)
- Full UEFI install + EFI boot + Plymouth splash (earlier session)
- Pro suite binaries present in image: chromium, thunderbird, libreoffice,
  gimp (PhotoGIMP skel lands in GIMP/3.0 — correct for Trixie), krita, inkscape,
  blender, obs-studio, kdenlive, wine(+wine32), steam-installer, gamemode,
  mangohud, timeshift, distrobox, docker.io, podman, kdeconnect, vorta, rclone,
  papirus-icon-theme
- firewalld kdeconnect service present; wallpaper `Image=Dagric` set correctly

## Review findings — triaged against the real image

FALSE POSITIVES (static analysis wrong; verified fine in the built image):
- Wallpaper "sed no-op on Plasma 6": defaults file reads `Image=Dagric` — works.
- PhotoGIMP GIMP-version mismatch: skel is in `GIMP/3.0`, matches Trixie — works.
- KDE Connect firewall service missing: `kdeconnect.xml` exists — works.

REAL — fixed this session:
- `build.sh` native path had no edition gating and didn't chmod the
  includes.chroot helpers → mis-branded, bloated, broken-helper native builds.
  Now mirrors container-build.sh (edition arg, /etc/dagric-edition, chmod).
- SDDM login theme relied on Debian defaulting to breeze (works today, fragile).
  Added `/etc/sddm.conf.d/10-dagric.conf` with `Current=breeze`.
- `dagric-gaming` wrote Proton-GE into `~/.steam/root` (a symlink Steam owns).
  Now uses `~/.local/share/Steam/compatibilitytools.d` and checks Steam ran.

DEFERRED (defensive, not current bugs): Calamares rebrand filename-fragility
(works today); doc copy about Timeshift rsync-vs-btrfs (cosmetic).

## Gap analysis — commercial holes fixed this session

The free edition had day-one FUNCTIONAL holes (read as "broken", not "lean").
All added to free (necessity, not suite):
- Scanners: sane-utils + skanlite (print-only was a refund trigger)
- Printing breadth: cups-filters, printer-driver-gutenprint, ipp-usb
- Firmware updates: fwupd (Discover already integrates it)
- VPN import: network-manager-openvpn + openconnect (privacy pitch needs it)
- Codecs: libavcodec-extra + gstreamer plugins (good/bad/ugly/libav/vaapi)
- Firefox EME enabled → Netflix/Spotify-web work day one
- MS-Office font fidelity: fonts-crosextra-carlito + caladea
- Laptop hardware: fprintd + libpam-fprintd (fingerprint), thermald
- Accessibility: orca (legal procurement requirement in EU/US markets)
- plocate (fast search)

Pro completeness (kept as the step-up):
- Gaming: lutris + goverlay (Steam-only felt half-finished)
- Full international text: fonts-noto-cjk (~200 MB, kept in Pro to keep free lean)

## Still backlog (bigger, future)

- Welcome-page "Finish setting up this PC" one-click (codecs/drivers/printer)
- First-boot GUI NVIDIA driver offer wrapping dagric-drivers
- Free rollback: snapper + grub-btrfs (Timeshift GUI stays the Pro step-up)
- Secure Boot MOK enrollment UX for the driver helper
- Heroic (Epic/GOG) + ProtonUp-Qt as consent-helpers/Flatpak
- Verify/surface Calamares LUKS full-disk-encryption
