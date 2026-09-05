# Licensing and third-party software

Dagric OS is a Debian derivative. This document explains what's in it, under
what terms, and how the proprietary pieces are handled. It is informational,
not legal advice — get a software/IP attorney to review before commercial sale.

## The operating system itself

Dagric OS is built with Debian's `live-build` from Debian 13 "Trixie". The vast
majority of the system — the Linux kernel, KDE Plasma, and the thousands of
packages it draws in — is free/open-source software under licenses such as
**GPL-2.0/3.0, LGPL, MIT, Apache-2.0, BSD, ISC, and MPL**.

**Source availability for release 1.0:** the download and post-checkout pages
link beside each binary delivery to
<https://dagric.com/licenses#corresponding-source>. That page pins Dagric's
exact source commit, both binary package inventories, notices and an interim
machine-readable source index. The package inventories are exact binary lists;
they are **not** by themselves corresponding source and do not yet map every
binary to its Debian `Source` field, exact source version, `.dsc`, source-file
hashes and build-time snapshot. The site states this limitation, honors
release-specific source requests at no charge for network delivery, and pauses
binary delivery and new sales until a generated exact source map and the
required human approvals are published.

The request route is an additional support channel. It is not treated as a
substitute for making release-exact corresponding source available beside a
network-delivered binary.

For everything the Dagric project itself adds, the shipped file *is* the source:
the `dagric-*` helpers, hooks and wizard are shell, Python and QML installed in
clear text on every machine, each carrying its SPDX header. The one exception is
the compiled message catalogues under `/usr/share/locale/*/LC_MESSAGES/`, whose
corresponding source is the `.po` files in `po/`.

This repository is public at https://github.com/Dagric/dagric-os and publishes
Dagric's build configuration and modifications. The release-pinned index and
request route at https://dagric.com/licenses complement the repository and must
be maintained for the periods required by each applicable license. Release tags,
binary manifests and the generated source map must identify the source that
actually corresponds to each distributed image; a moving branch or generic
archive link is not an acceptable substitute.

The repository-level licensing map is in `LICENSE-POLICY.md`; the canonical
GPLv3 text is in `LICENSE` and `COPYING`; detailed third-party
coverage is in `THIRD-PARTY-NOTICES.md`. The terms on the installed Dagric layer
are also stated where every Debian tool looks for
them: `/usr/share/doc/<package>/copyright` in each of the four `dagric-*`
packages. The helper scripts, hooks and wizard are **GPL-3.0-or-later**; the
branding assets (wallpapers, logo, SDDM and splash artwork) are
**CC-BY-SA-4.0**. The Dagric name, the D monogram and the logo are trade marks
and are not licensed by either — see `TRADEMARKS.md` and Trademarks below.

## Base system: open source, with disclosed hardware-enablement exceptions

Every **application** Dagric preinstalls, in the base system and in the Pro
suite, is DFSG-free software under its Debian package terms. We deliberately do
**not** ship any application whose contents are proprietary. This statement is
about preinstalled applications, not the separately disclosed firmware,
microcode, installer packages, or non-free hardware libraries below. Notably,
`ttf-mscorefonts-installer` (which downloads Microsoft's proprietary fonts) was
removed in favor of the open, metric-compatible Carlito, Caladea, and Liberation
fonts.

Dagric's hardware-enablement layer includes components that are **not** open
source. The package names below are the firmware and CPU-microcode set Dagric
selects directly for future builds, not an exhaustive inventory of every binary
package resolved by Debian:

```
firmware-linux-nonfree   firmware-misc-nonfree   firmware-realtek
firmware-iwlwifi         firmware-atheros        firmware-brcm80211
firmware-sof-signed      intel-microcode         amd64-microcode
firmware-nvidia-graphics firmware-nvidia-tesla-535-gsp
```

The exact resolved inventory is generated from each candidate image's package
manifest and is a required input to the commercial-release legal gate. The
published 1.0 manifests contain additional live-build-resolved hardware
components: Broadcom firmware installers and the non-free `libfishcamp1t64` and
`libsbig4t64` astronomy-camera libraries. Those two libraries contain prebuilt
vendor binaries. The current build source disables live-build's automatic
firmware scan, so future candidates are limited to the explicit list above plus
normal dependencies; the finished artifact is still checked rather than trusted.
Release 1.0 remains blocked from renewed promotion until its exact payload and
corresponding notices have been reviewed.

Firmware packages contain or install binary blobs that load onto hardware such
as Wi-Fi, audio, CPU and GPU devices — not ordinary desktop applications. They are here
for the same reason Debian puts firmware on its official installer media: some
real hardware will not work without it. None of these blobs is OSI-approved.
Each package's exact governing notice must be preserved at
`/usr/share/doc/<package>/copyright` and audited in every release image. A
package-level manifest alone is not enough for downloader/installer packages or
prebuilt vendor libraries: their retrieved or embedded files and separate
licences must also be inventoried.

The two NVIDIA firmware packages above are bundled for hardware enablement from
Debian's `non-free-firmware` component. They are distinct from NVIDIA's
proprietary kernel/display driver, which Dagric does not bundle. The current
[NVIDIA driver and firmware license](https://www.nvidia.com/en-us/drivers/nvidia-license/linux/)
permits distribution for use with qualifying open-source operating-system
kernels only under its stated conditions, including unmodified binaries and
providing the agreement to recipients. Release engineering must verify the
actual package notices and current license rather than relying on this summary.

This section previously claimed the base system was "100% open source". That was
inaccurate, and it is corrected here rather than quietly narrowed: if you want a
machine carrying no non-free firmware at all, remove those packages after
installation. The system boots and runs without them; some of your hardware will
stop working.

## Optional proprietary software — not bundled by Dagric

Dagric includes open-source compatibility tools, but some optional applications
and services are proprietary. The Dagric ISO and repository do **not** contain
the proprietary clients named below. Installation is initiated by the owner and
the third party's current terms govern the resulting software, account and
content. This describes Dagric's release policy; it is not a substitute for
legal advice or for reviewing the current vendor terms before a release.

### Steam (Valve)

- Dagric does **not** preinstall or redistribute the Steam client or Debian's
  `steam-installer` package. Neither is listed for inclusion in the free or Pro
  image.
- `dagric-get-steam` explains the boundary, asks for an explicit yes/no choice,
  and then requests Debian's `steam-installer` package from Debian's `contrib`
  component. Installation and use remain subject to Valve's current terms.
- Dagric uses original generic gaming/performance artwork for its helper, not
  Valve's Steam logo. Steam and related marks belong to Valve Corporation;
  Dagric is not affiliated with or endorsed by Valve.
- Release references: [Debian's package record](https://packages.debian.org/stable/steam-installer)
  and the [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/).

### Heroic, GOG, Epic Games and Amazon Games

- Heroic Games Launcher is open-source software and is **not** preinstalled.
  `dagric-get-heroic` offers a user-initiated per-user installation from
  Flathub (`com.heroicgameslauncher.hgl`).
- Heroic can connect to third-party game services. Dagric does not bundle GOG
  GALAXY, Epic Games Launcher, Amazon Games or those services' game content.
  Account access, purchases, entitlements, downloads and offers remain subject
  to each provider's current terms.
- The names are used descriptively. Dagric is not affiliated with or endorsed
  by Heroic, GOG, Epic Games or Amazon.
- Release references: [Heroic source and GPL-3.0 license](https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher)
  and its [Flathub manifest](https://github.com/flathub/com.heroicgameslauncher.hgl/blob/master/com.heroicgameslauncher.hgl.yml).

### Lutris, Wine, Proton and compatibility tools

- Dagric Pro includes the open-source Lutris and Wine packages from Debian,
  plus open-source compatibility and performance components listed in the
  package manifests. Those tools are not the third-party game clients or games
  they may help an owner install or launch.
- The published 1.0 images include Debian's open-source `steam-devices` package;
  it contains Valve-origin udev rules under the Expat license, not the
  proprietary Steam client. Current release source removes it from the base
  image. Future images install it only through the informed Steam helper because
  Debian warns that its broad device and `/dev/uinput` permissions trade
  local-user isolation for controller functionality.
- Bottles, ProtonUp-Qt and GE-Proton are optional owner-initiated tools. Dagric
  does not bundle populated Wine/Bottles prefixes or third-party runtimes they
  may retrieve. GE-Proton is an independent project and is not affiliated with
  Valve's Proton project.
- Community installers and compatibility recipes can change and may retrieve
  separately licensed software. Owners should review the source and vendor
  terms before running them. Dagric makes no title-by-title compatibility
  guarantee.

### NVIDIA proprietary driver

- Dagric does **not** preinstall the NVIDIA driver.
- Dagric **does** bundle the separately licensed NVIDIA firmware packages named
  in the firmware section above; firmware and a kernel/display driver are not
  the same component.
- The `sudo dagric-drivers` helper installs `nvidia-driver` from **Debian's**
  official non-free repository, only when the user chooses to. NVIDIA and its
  logos are trademarks of NVIDIA Corporation; Dagric is not affiliated with or
  endorsed by NVIDIA. The helper displays the current NVIDIA license URL before
  asking for confirmation.

### Other user-initiated proprietary options

The `dagric-get-resolve` helper guides the owner to Blackmagic Design's official
download flow; Dagric does not bundle DaVinci Resolve. Flatpak applications the
owner installs carry their own licenses and may also depend on separately
licensed online services.

## Trademarks

"Dagric" and the Dagric logo are marks of IMPRESSIONSDIRECT360 LLC. Debian is a
trademark of Software in the Public Interest, Inc.; Dagric is based on Debian
but is not a Debian product and is not endorsed by the Debian project
(`ID_LIKE=debian`, own name and branding, per Debian's derivative guidelines).
All other product names, logos, and brands are property of their respective
owners and are used only to identify compatibility or an optional service. Such
references do not imply sponsorship, certification, affiliation or endorsement.
Dagric-owned surfaces should use original generic helper artwork unless written
permission or an applicable brand policy clearly authorizes an official mark.
