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
| Debian non-free firmware and CPU microcode | Not open source; redistributed under each package's applicable terms for hardware support. Exact notices remain under `/usr/share/doc/<package>/copyright`. |
| `firmware-b43-installer`, `firmware-b43legacy-installer`, and `b43-fwcutter` | The published 1.0 manifests include Debian `contrib` installers/tools that can retrieve separately licensed Broadcom firmware. Future builds disable live-build's automatic firmware scan and do not select these packages. Before any 1.0 distribution resumes, review and inventory both the installer packages and every retrieved firmware file; a binary package manifest alone is insufficient. |
| `libfishcamp1t64` and `libsbig4t64` | The published 1.0 manifests include these Debian `non-free/libs` astronomy-camera libraries, which contain prebuilt vendor binaries. Preserve and review their exact package notices and embedded payload conditions; see Debian's [libfishcamp copyright record](https://metadata.ftp-master.debian.org/changelogs/non-free/libf/libfishcamp/libfishcamp_1.2%2B20220607003151-3_copyright) and [libsbig copyright record](https://metadata.ftp-master.debian.org/changelogs/non-free/libs/libsbig/libsbig_4.9.9-7_copyright). Future candidates must include them only if the artifact-derived non-free inventory and human approval expressly cover them. |
| `firmware-nvidia-graphics`, `firmware-nvidia-tesla-535-gsp` | Proprietary NVIDIA firmware is bundled from Debian `non-free-firmware`; the proprietary NVIDIA kernel/display driver is not bundled. Preserve the package notices and review the current [NVIDIA license](https://www.nvidia.com/en-us/drivers/nvidia-license/linux/) for every release. |
| Firefox ESR | MPL-covered software with separate Mozilla trademark rules. Dagric modifications and branded redistribution require policy review. |
| Google Widevine | Proprietary; not included on the ISO and may be downloaded by Firefox when DRM playback is used. |
| Steam | Valve proprietary software; not bundled. A clearly labeled, user-initiated helper asks Debian's `steam-installer` package to obtain Steam under Valve's terms. |
| `steam-devices` | Open-source Debian package included in the published 1.0 images but removed from future base images. It contains Valve-origin Expat-licensed udev rules, not the proprietary client. The informed Steam helper may install it for advanced controller features; Debian warns that its broad device and `/dev/uinput` permissions are unsuitable where local users may be malicious. |
| Heroic Games Launcher | GPL-3.0 open-source software; not bundled. A user-initiated helper installs the upstream Flathub package for the current user. |
| GOG, Epic Games, and Amazon Games services | No proprietary store clients or game content from these services are bundled. Their names identify account libraries that an owner may choose to access through Heroic or Lutris, subject to each provider's terms. |
| Lutris, Wine, Winetricks, and DXVK | Open-source Debian packages included in Pro; community installers and dependency tools may retrieve separately licensed software. Their package licenses and notices remain under `/usr/share/doc/<package>/copyright`. |
| Bottles and ProtonUp-Qt | Open-source optional applications installed only after owner confirmation from their upstream Flathub packages. They are not bundled. |
| GE-Proton | Open-source optional compatibility tool obtained from its sole official GitHub project with digest verification. GE-Proton is not affiliated with Valve's Proton project. |
| NVIDIA proprietary driver and DaVinci Resolve | Proprietary applications; not bundled. Dagric only provides user-initiated installation guidance or helpers. This row does not describe the separately bundled NVIDIA firmware listed above. |

## Optional applications

Applications installed later by the owner—from Debian, Flathub, a vendor, or a
Dagric helper—remain governed by their own licenses and terms. Their availability
does not mean they are bundled with or endorsed by Dagric OS.

Third-party names are used only to describe compatibility or an owner-selected
integration. IMPRESSIONSDIRECT360 LLC and Dagric OS are not affiliated with,
sponsored by, or endorsed by Valve, GOG, Epic Games, Amazon, Heroic Games
Launcher, Lutris, or their respective owners.

## Source requests

Release package manifests and source-availability instructions are published at
https://dagric.com/licenses. Source requests may be submitted through
https://dagric.com/contact.

This file should be checked against the actual Free and Pro package manifests
before every release and updated whenever a vendored component changes.
