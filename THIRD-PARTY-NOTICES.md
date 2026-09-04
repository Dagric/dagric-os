# Third-party notices

Dagric OS is a Debian derivative assembled from independently licensed
components. This overview is a navigation aid, not a substitute for the exact
notices installed with each package.

## Debian packages

The base operating system, KDE Plasma desktop, and applications installed from
Debian retain their upstream licenses. Exact package versions are published in
the release manifests. On an installed system, the authoritative Debian
copyright and license notice for each package is located at:

    /usr/share/doc/<package>/copyright

Corresponding Debian source is available from:

- https://snapshot.debian.org/
- https://sources.debian.org/

Common licenses in the distribution include GPL-2.0-or-later,
GPL-3.0-or-later, LGPL, MPL-2.0, Apache-2.0, MIT, BSD, and ISC.

## Material components requiring special attention

| Component | Treatment |
| --- | --- |
| Dagric-authored scripts, hooks, QML, and configuration | GPL-3.0-or-later; see `LICENSE` and file SPDX headers. |
| Dagric-authored branding and wallpapers | CC-BY-SA-4.0 for copyright; Dagric marks remain subject to `TRADEMARKS.md`. |
| KDE Breeze-derived color schemes | LGPL-2.0-or-later; retain upstream notices. |
| grub-btrfs | GPL-3.0; vendored release and notice must remain pinned and included. |
| Smart Video Wallpaper Reborn | GPL-2.0-or-later; no user video content is bundled. |
| PhotoGIMP configuration | Retains its upstream open-source terms and notices. |
| Debian non-free firmware and CPU microcode | Not open source; redistributed under each package's applicable terms for hardware support. |
| Firefox ESR | MPL-covered software with separate Mozilla trademark rules. Dagric modifications and branded redistribution require policy review. |
| Google Widevine | Proprietary; not included on the ISO and may be downloaded by Firefox when DRM playback is used. |
| Steam, NVIDIA proprietary driver, DaVinci Resolve | Proprietary; not bundled. Dagric only provides user-initiated installation guidance or helpers. |

## Optional applications

Applications installed later by the owner—from Debian, Flathub, a vendor, or a
Dagric helper—remain governed by their own licenses and terms. Their availability
does not mean they are bundled with or endorsed by Dagric OS.

## Source requests

Release package manifests and source-availability instructions are published at
https://dagric.com/licenses. Source requests may be submitted through
https://dagric.com/contact.

This file should be checked against the actual Free and Pro package manifests
before every release and updated whenever a vendored component changes.
