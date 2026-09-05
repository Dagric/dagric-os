# Upstream open-source projects for Dagric OS

A curated catalog of projects that can improve Dagric, honestly categorized by
**how** they'd be integrated and whether they're already covered. We integrate
upstreams — we don't fork or copy their code into this repo. Every item lists
its license; anything GPL/MIT/Apache is safe to ship or link per its terms.

## Already covered (KDE-native — don't duplicate)

Dagric is KDE Plasma, so several "must-have" GNOME tools from generic
Debian-hardening guides are already answered by a native equivalent:

| Generic suggestion | Dagric already ships | 
|---|---|
| Albert / Rofi launcher | **KRunner** (Alt+F2 / Meta) |
| GSConnect (phone sync) | **KDE Connect** (Pro) |
| GNOME Software | **Plasma Discover** + Flatpak |
| GUFW firewall GUI | **plasma-firewall** (firewalld) |
| GNOME Tweaks | **System Settings** (Plasma KCMs) |
| Stacer / cleaning | **BleachBit** (Pro) + Sweeper |
| PipeWire audio | **PipeWire** (both editions) |

## Now added from Debian (this session)

Free: sane-airscan + avahi (driverless network scan), va-driver-all (GPU video
decode), gdebi (.deb double-click), fwupd, VPN plugins, codecs, MS-Office
metric fonts, fprintd, thermald, orca, plocate.
Pro: **mesa-vulkan-drivers** (critical — Proton/DXVK need Vulkan), lutris,
goverlay, nala + bat + zoxide (modern shell), fonts-noto-cjk, gvfs-backends,
ttf-mscorefonts-installer (via hook, EULA preseeded).

## Worth integrating next — from GitHub (not in Debian)

These are the high-value upstreams that aren't Debian-packaged. Ship as Flatpak
(via the preconfigured Flathub) or as an owner-consent helper mirroring the
`dagric-get-resolve` pattern — never bundled if the license or size argues
against it.

| Project | What it adds | License | How | Tier |
|---|---|---|---|---|
| **Antynea/grub-btrfs** | "Boot into previous snapshot" entries in GRUB — the factory-reset safety net | GPL-3.0 | vendor + snapper config | free (recovery) |
| **DavidoTek/ProtonUp-Qt** | GUI to install/manage GE-Proton & Wine-GE | GPL-3.0 | Flatpak | both (optional) |
| **Heroic-Games-Launcher** | Independent launcher for Epic Games Store, GOG and Amazon Games accounts | GPL-3.0 | Flatpak / consent-helper | both (optional) |
| **linuxmint/webapp-manager** | Turn Office365/Netflix/Canva URLs into desktop apps | GPL-3.0 | vendor (.deb build) | free |
| **Calamares OEM mode** | True out-of-box-experience: ship frozen, customer sets up on first boot | GPL | Calamares config (already have Calamares) | both |

## New — things to build ourselves (our IP, no upstream needed)

- **"Finish setting up this PC" welcome action** — buttons on the Dagric Welcome
  page that pkexec the codec/driver/printer helpers, so the invisible
  `dagric-*` CLIs become a one-click discoverable flow. (Highest-leverage UX.)
- **First-boot NVIDIA offer** — a Plasma notification wrapping `dagric-drivers`.
- **Factory-reset** — a recovery entry that re-images to stock (pairs with
  grub-btrfs snapshots or a small recovery partition).
- **dagric-get-heroic / dagric-get-protonup** — consent-helpers like
  `dagric-get-resolve` for the Flatpak-only gaming tools.

## Deliberately NOT integrating

- **Catppuccin / Nord theming** — Dagric has its own brand identity; a third
  aesthetic would dilute it. (Users can install via Discover if they want.)
- **oh-my-zsh / fish as default shell** — bash + the bat/zoxide/nala additions
  give the modern feel without changing the default login shell (which can
  surprise scripts). Offer, don't impose.
- **ttf-ms-win10** (extracting real Windows fonts) — legally dubious;
  ttf-mscorefonts-installer (official, EULA'd) + Carlito/Caladea cover it.
