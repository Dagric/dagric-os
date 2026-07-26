# Licensing and third-party software

Dagric OS is a Debian derivative. This document explains what's in it, under
what terms, and how the proprietary pieces are handled. It is informational,
not legal advice — get a software/IP attorney to review before commercial sale.

## The operating system itself

Dagric OS is built with Debian's `live-build` from Debian 13 "Trixie". The vast
majority of the system — the Linux kernel, KDE Plasma, and the thousands of
packages it draws in — is free/open-source software under licenses such as
**GPL-2.0/3.0, LGPL, MIT, Apache-2.0, BSD, ISC, and MPL**.

**GPL source availability:** for the copyleft components, the corresponding
source is available from Debian's archives (https://sources.debian.org) and the
Dagric build configuration is published in full at the project's public
repository. Distributing Dagric therefore satisfies the GPL's source-offer
obligation by pointing recipients to those sources.

Everything the Dagric project itself adds (branding assets, the `dagric-*`
helper scripts, hooks, the welcome page, and configuration packages) is part of
this repository and is offered under the project's own terms.

## Base system: 100% open source

Every package Dagric preinstalls in the base system and the Pro suite is
OSI-approved open source. We deliberately do **not** ship any package whose
contents are proprietary. Notably, `ttf-mscorefonts-installer` (which downloads
Microsoft's proprietary fonts) was removed in favor of the open, metric-
compatible Carlito, Caladea, and Liberation fonts.

## Proprietary software — never bundled, always user-initiated

Two pieces of proprietary software can end up on a Dagric machine. In both
cases the actual proprietary code is **not** contained in the Dagric ISO or in
this repository — it is downloaded and installed by the user, who accepts the
vendor's own license at that time.

### Steam (Valve)

- Dagric does **not** preinstall Steam, or `steam-installer`, or any part of
  either. Neither ships in the free or the Pro ISO.
- The `dagric-get-steam` helper installs `steam-installer` — a small
  **bootstrapper**, which itself contains no Steam client code — from Debian's
  official repository, only when the user chooses to.
- That bootstrapper then downloads Steam from Valve, and the user accepts
  Valve's **Steam Subscriber Agreement** at that point.
- This is the same mechanism Debian, Ubuntu, Linux Mint, Pop!_OS, and Valve's
  own SteamOS use. Steam and the Steam logo are trademarks of Valve
  Corporation; Dagric is not affiliated with or endorsed by Valve.

### NVIDIA proprietary driver

- Dagric does **not** preinstall the NVIDIA driver.
- The `sudo dagric-drivers` helper installs `nvidia-driver` from **Debian's**
  official non-free repository, only when the user chooses to. NVIDIA and its
  logos are trademarks of NVIDIA Corporation; Dagric is not affiliated with or
  endorsed by NVIDIA.

### Other user-initiated proprietary options

The `dagric-get-resolve` helper guides the user through downloading DaVinci
Resolve from Blackmagic Design (its license forbids redistribution, so Dagric
never bundles it). Flatpak apps the user installs from Flathub carry their own
licenses.

## Trademarks

"Dagric" and the Dagric logo are marks of DGR Operations. Debian is a
trademark of Software in the Public Interest, Inc.; Dagric is based on Debian
but is not a Debian product and is not endorsed by the Debian project
(`ID_LIKE=debian`, own name and branding, per Debian's derivative guidelines).
All other product names, logos, and brands are property of their respective
owners and are used for identification only.
