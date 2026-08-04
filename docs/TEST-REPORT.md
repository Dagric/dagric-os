# Dagric OS — full test report

Session 2026-07-21. Method: hands-on VM test of the Pro edition (live) in the
QEMU harness, ISO-filesystem inspection, and two source-review passes over the
tree (bug hunt + commercial-gap analysis).

## What was verified working

- Boots to live desktop (BIOS + UEFI, both editions) with Dagric wallpaper
- Branded "Install Dagric OS" desktop icon + Calamares (D logo, verified on screen)
- Welcome page auto-opens on first login; offline user guide linked
- Ctrl+Shift+Esc system monitor (confirmed by user on real hardware; this line
  said Ctrl+Esc, which was never bound in Plasma 6 — see docs/EDITIONS.md)
- Full UEFI install + EFI boot + Plymouth splash (earlier session)
- Pro suite binaries present in image (re-verified against the shipped Pro ISO
  2026-07-26): chromium, thunderbird, libreoffice, gimp (PhotoGIMP skel lands in
  GIMP/3.0 — correct for Trixie), krita, inkscape, blender, obs-studio, kdenlive,
  audacity, keepassxc, wine(+wine32), lutris, gamemode, mangohud, goverlay,
  timeshift, distrobox, docker.io, podman, kdeconnect, vorta, rclone,
  papirus-icon-theme
  - **No Steam package ships in either edition, by design.** `steam-installer`
    was bundled in the 2026-07-21 build this report originally covered; it was
    removed in `e3e3eb8` (2026-07-25). Steam is now reachable only through the
    `dagric-get-steam` consent helper, per the never-bundled mandate in
    docs/EDITIONS.md. Verified: no `Package: *steam*` stanza in the dpkg status
    of either ISO; `/usr/bin` carries only `dagric-get-steam`.
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
- Full international text: fonts-noto-cjk (89 MB installed per Debian, kept in Pro to keep free lean)

## Backlog features — DELIVERED + VERIFIED (2026-07-22)

Built the top of the backlog and tested it on a real free-edition
UEFI + btrfs install:

- **Snapshot recovery (free)** — VERIFIED end to end. On the installed btrfs
  system: root is btrfs, `grub-btrfsd` active, first-boot `dagric-snapshot-setup`
  ran, the apt pre/post snapshot hook is in `/etc/apt/apt.conf.d/`, and
  `snapper -c root list` shows the automatic "Dagric baseline (first boot)"
  snapshot. grub-btrfs (GPL-3.0) vendored from pinned upstream v4.14.
  Caught + fixed a real bug: the first-boot service wasn't enabled because
  `systemctl enable` in a hook runs before includes.chroot units are copied —
  now enabled via a direct wants-symlink.
- **Finish Setup** (dagric-setup) — launcher app for graphics/HP-printer drivers.
- **First-login NVIDIA offer** (dagric-driver-offer) — GUI offer, autostart.
- **Security Checkup** (dagric-security-checkup) — Lynis audit + hardening score.
- Free-edition install run-through: full UEFI+btrfs install completes and boots;
  the newer free packages (scanner, fwupd, AppArmor, VPN, snapper) don't break it.

## Still backlog (bigger, future)

- Full break-an-update-and-roll-back-from-GRUB cycle on real hardware (the pieces
  are verified wired; the end-to-end rollback is a real-HW test)
- Secure Boot MOK enrollment UX for the driver helper
- Heroic (Epic/GOG) + ProtonUp-Qt as consent-helpers/Flatpak
- Verify/surface Calamares LUKS full-disk-encryption
- OEM first-boot (Calamares OEM mode) + plasma-welcome re-theme
