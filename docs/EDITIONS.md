# Dagric OS editions

One source tree, two products. The free edition builds adoption and trust;
Pro is the paid step-up with the full creator/developer suite and, later,
support contracts.

```
.\build.ps1                  →  dagric-os-1.0-amd64.iso        (free)
.\build.ps1 -Edition pro     →  dagric-os-pro-1.0-amd64.iso    (Pro)
```

Mechanics: `config/package-lists/pro-*.list.chroot` only exist in Pro
builds; the `0600-pro-edition` hook applies Pro-only config (it reads
`/etc/dagric-edition`, which the build writes). Everything else —
branding, security baseline, debloat rules, installer — is IDENTICAL.
Free is never a crippled Pro; Pro is never a different OS.

## Dagric OS (free)

Everything already shipped: debloated KDE Plasma, zero telemetry,
silent updates that never force a reboot, Firefox (telemetry/Pocket/studies
off, tracking protection on, and the uBlock Origin ad blocker, which Firefox
fetches from addons.mozilla.org on first launch and the owner can remove like
any add-on), LibreOffice essentials
(Writer/Calc/Impress), Elisa music library, Flathub, NTFS/exFAT,
Dagric Welcome, branded installer, **Dagric Styles** (`dagric-style` —
one-click desktop moods: color scheme + accent + wallpaper + KWin effects,
4 styles free / 7 on Pro — **High Contrast** is deliberately one of the free
four and carries no `EDITION=` line at all, because a person who cannot read
the screen is not an upsell — thirty-four Dagric-made wallpaper packs (twenty
designs, fourteen of them also in a logo-free "Clean" cut), all reversible
via Reset; complements Dagric Looks which handles panel layouts),
**Dagric Appearance** (`dagric-appearance` — the same styles and layouts as
a picture gallery: clicking one applies it on the spot but saves nothing
until the owner picks Keep, and an unanswered or unreadable change reverts
itself after twenty seconds, so nothing the owner tries can strand them),
and the **Migration Assistant**
(`dagric-migrate` — copies Documents/Pictures/Music/Videos/Desktop and
Chrome/Edge/Firefox bookmarks over from the Windows partition, read-only,
never touching Windows). Drive-health watching too: plasma-disks warns
before a failing disk dies, and the Security Checkup reports SMART status.

### The first hour (free, and not a Pro teaser)

Every item below ships on **both** editions. Some of them are edition-*aware* —
the wizard shows a Pro badge and the Pro-only layouts, the manual badges Pro
software — but none of them is gated. A switcher decides in the first hour
whether this was a mistake, and the free edition has to win that hour on its
own.

- **The boot, end to end** — the first ninety seconds of the product, and until
  recently the least designed part of it. Both firmware paths now carry the
  brand and the edition, and the chain from power-on to the login screen was
  measured frame by frame rather than assumed.
  **The menu.** UEFI gets a real GRUB theme
  (`usr/share/dagric/boot/grub-theme/`): translucent panel, a brand-blue
  selection pill, and a countdown that reads *"Starting Dagric OS in 6s"*
  instead of GRUB's *"The highlighted entry will be executed automatically
  in 3s."* Legacy BIOS gets the same design in what `vesamenu` can express —
  same art, same navy, same blue, same wording — at 1024x768 rather than the
  640x480 live-build hard-codes. Both menus name the edition on every entry
  and wait **10 seconds**; both used to wait *forever*, which is the worst
  possible default for someone who does not know Enter is required and will
  conclude the machine has hung. Neither shows a top-level title any more: it
  printed straight through the wordmark on the art, on both paths, unnoticed.
  The accessible **(with screen reader)** entry survives all of this and is
  regression-checked on both paths.
  **The handoff.** The moment GRUB left the menu it used to punch a black
  rectangle through the splash and leave it there for the entire ~19-second
  squashfs load. `gfxterm` now draws the same branded picture the menu was
  drawing, so the mark stays up. Plymouth then loads *that same PNG* rather
  than a colour-matched imitation, and pins its progress fill to the
  decorative rule in the artwork — measured out of the image at build time,
  not hard-coded, because the rule moved once mid-development and nothing
  except a screenshot noticed. Nothing fades in and nothing pulses: if the
  previous frame already showed the mark, fading it in makes the screen
  visibly empty and refill.
  **The login screen** is now Dagric's own SDDM theme, not Breeze with our
  wallpaper pushed into six configurable keys. It imports `QtQuick` and
  nothing else — no Kirigami, no `org.kde.plasma.*` — so there is no KDE QML
  module left that can be renamed upstream and take the login screen with it.
  Breeze remains configured as the documented rescue path, carrying the same
  art.
  **Three kernel flags** ride every entry, each for a measured reason.
  `plymouth.ignore-serial-consoles` is the one that matters: any machine whose
  firmware advertises a serial console — business desktops with AMT, anything
  with serial redirection, every VPS — was getting **no splash at all**, black
  from the GRUB handoff to the KDE startup screen. `vt.global_cursor_default=0`
  removes a blinking console cursor from the VT handoff.
  `loglevel=3` is the honest odd one out: `quiet` is only loglevel 4, so kernel
  errors and warnings still print over the splash. Nothing printed in QEMU,
  which has no real hardware to complain about.
  **What is not fixed, stated plainly.** There is still a ~9-second black
  window between Plymouth and the Plasma startup screen. It was measured, two
  independent arrangements were tried against it, and neither moved it: it is
  the display server taking the VT with nothing yet drawing, and Plymouth
  cannot cover it because the framebuffer is cleared at that moment regardless
  of ordering. Plasma's own startup screen is also still KDE's Breeze — a
  white KDE logo on pure black for about sixteen seconds, which is the largest
  unbranded stretch left in the sequence. Both are named in the roadmap.
- **Check This PC** (`dagric-hardware-check`) — the first *tool* here, and one
  that runs before the install rather than after. A read-only, unprivileged, offline hardware report
  that answers the question the live USB otherwise leaves hanging: will the
  Wi-Fi work, is the disk BitLocker'd, is Secure Boot going to be a problem,
  is there room. It names the Wi-Fi chip in plain words and says whether its
  firmware is on the disc (Broadcom `b43`/`wl` are not, and cannot be, so those
  owners are told to plan for a cable) — and it decides "broken" from sysfs, a
  driver bound with no `net/` directory, rather than from firmware errors in
  the kernel log, because `iwlwifi` logs a failure for every API version above
  the one that exists on cards that work perfectly. It never prompts for a
  password (`kernel.dmesg_restrict=1` means the log needs root, so it tries
  `sudo -n` and *says* it skipped the probe rather than claiming a clean bill),
  it mounts and unlocks nothing, and it writes exactly one file — the report,
  to a path the owner picked. Its report is also the support artifact: "run
  Check This PC and send me the report".
  In the **live session** it is on the desktop next to *Install Dagric OS*
  (`usr/lib/live/config/2010-dagric-hwcheck-icon`), because a tool found after
  the install is worth nothing. On an **installed** system it stays in the
  launcher and the Hub, worded as the diagnostic it becomes.
  It asserts a minimum specification — 3500 MB RAM (7000 comfortable), 25 GB
  disk (60 comfortable), from `/usr/share/dagric/hwcheck/minimums`. **Nothing
  the project publishes states one yet.** The RAM floor is 3500 and not 4096
  on purpose: a genuine 4 GB machine reports ~3.8 GB after firmware
  reservation, and a round 4096 would fail every real 4 GB laptop.
- **Set Up Dagric** (`dagric-firstrun`) — a six-step first-run wizard shown
  once at first login and re-runnable from the launcher or Hub → *Get started*.
  Welcome → appearance (light/dark, 9 accents, every wallpaper as a real
  thumbnail) → text size → taskbar layout → your files from Windows → finish.
  Steps the machine cannot act on are never shown: no migration step without a
  Windows partition, none in the live session. Every choice applies for real as
  it is clicked, and the escape hatch is a header **Undo my changes** button
  rather than a nag on close. This replaced the seven-line Firefox welcome tab,
  which looked exactly like the OEM landing page switchers are trained to shut.
- **Plain-English app names** (`dagric-app-names`) — the launcher says
  **Files**, **Terminal**, **Photos**, **Document Viewer**, **Archive
  Manager**, **Text Editor**, **Music**, **Screenshot**, **Task Manager**,
  **Software Store**, **Saved Passwords**, **Videos**, **Scanner**, **Package
  Installer**. *Support needs to know this*: the menu no longer says Dolphin.
  The original names are all still in `Keywords=` and still find the app, and
  each entry's second line names it (`Files / File manager (Dolphin)`), which
  agrees with the title bar — no `.desktop` file can change what Dolphin calls
  its own window. Firefox, LibreOffice, GIMP, Blender, Krita, Inkscape, OBS,
  Thunderbird and Blender are deliberately **not** renamed: the brand is what
  the owner already searches for. *Orca used to be listed here and that was
  wrong in a way worth recording*: Debian's `orca` package ships **no**
  `.desktop` file at all (checked with `dpkg-deb -c` on 48.1-1+deb13u2 — it
  contains `/usr/bin/orca`, `/usr/bin/orca-dm-wrapper` and a GNOME-only
  autostart entry with `NoDisplay=true`). There was nothing in the menu to
  rename, and nothing to find: searching for *orca*, *screen reader*,
  *narrator* or *blind* returned nothing whatsoever. `0530-accessibility` now
  installs the entry, called **Screen Reader**, with `orca` in its `Keywords=`.
  Mechanically this is a regenerator writing complete copies into
  `/usr/local/share/applications`, re-run by an apt `Post-Invoke-Success` hook.
  dpkg never writes to `/usr/local`, so the rename survives KDE point releases;
  everything except the three changed keys is re-derived from upstream, so
  `Exec=`/`MimeType=`/Desktop Actions never freeze. Only the English
  translations are overridden — a German install keeps its German names, which
  is a market decision, not a technical limit.
- **Dagric Manual** (`dagric-manual`) — an offline, searchable handbook with a
  page for every application and every `dagric-*` tool: what it is, what it
  replaces on Windows, five common tasks, and the one thing that will surprise
  a switcher. 94 pages, 892 KB, zero network calls. Search indexes the Windows
  name, so *notepad* finds the Text Editor and *task manager* finds System
  Monitor. Pro-only applications are documented on the free edition too, badged
  PRO and carrying a plain note that they are not installed here — a free owner
  should be able to see exactly what Pro adds rather than learning it from a
  sales page. The front page has a one-click filter that hides them (94 → 57).
  Install-on-request apps (Joplin, ONLYOFFICE, Bottles, LocalSend, Cryptomator,
  Heroic, ProtonUp-Qt, Upscayl, Steam, Resolve, Ollama, Variety) carry an
  ADD-ON badge and **no** PRO badge, because they install from Flathub on any
  edition.
- **Text Size** (`dagric-display`) — make everything on screen bigger, 100% to
  200%, with a night light that warms the screen from 8pm to 7am. Two safety
  properties worth naming: sizes that would not leave 800×600 logical pixels
  are never offered, and the 20-second undo countdown runs in the *shell*, not
  in the dialog it is protecting — so it still fires if the dialog lands
  off-screen or is unclickable at the new size. Dagric also measures the panel
  from EDID at first login and corrects the two cases KWin 6.3.6 gets wrong
  (a 15.6" 1080p laptop and a 27" 1440p monitor both land on a blurry 1.15;
  a 14" 2880×1800 OLED lands on 1.95 instead of a pixel-exact 2.0).
  Wayland only — see *Sessions* below.
- **Ctrl+Shift+Esc opens the Task Manager**, because the app is now called that
  and a rename without the muscle memory is half a promise
  (`etc/skel/.config/kglobalshortcutsrc`). KDE's own Meta+Esc still works.
  Note for anyone editing docs: **Ctrl+Esc is not bound in Plasma 6** — it was
  ksysguard's "Show System Activity" and that action no longer exists. Older
  Dagric pages claimed it and were wrong.
- **Twelve user avatars** and an SDDM default face. There were none; a brand-new
  machine landed on a stock grey silhouette.

**Sessions.** SDDM offers "Plasma (Wayland)" and "Plasma (X11)". The X11 entry
ships from `plasma-workspace` unconditionally, but `kwin-x11` is only a
*Recommends alternative* and this build passes `--apt-recommends false` — so
until now picking it gave a desktop with **no window manager**. `kwin-x11` is
now in `desktop.list.chroot` (1.7 MB) so the rescue option works, which matters
most for the owner whose Wayland session is already misbehaving on an older
NVIDIA card. `dagric-display` remains Wayland-only by design (KWin owns
per-screen scale there, and that is the only thing that makes a live undo timer
possible); on X11 it says so and opens the System Settings page instead, and
the setup wizard falls back to inline 100/125/150 buttons.
`0520-display-defaults` removes the X11 session entry if `kwin-x11` is ever
dropped again, so the broken state cannot come back silently.

**Snapshot recovery** (free, on the default btrfs install): snapper takes an
automatic snapshot before and after every apt transaction, and grub-btrfs
exposes them as a submenu in the boot menu — so a bad update is undone from
GRUB instead of reinstalled. `dagric-snapshot-setup` configures it on first
boot of the installed system. This is what the Welcome page's rollback
promise rests on; Pro adds Timeshift's scheduled GUI on top of it.

### Accessibility (free, and never gated)

A screen reader is a procurement requirement in much of the EU (EN 301 549)
and the US (Section 508). More to the point: a person who cannot read the
screen is not an upsell, so **nothing in this section is Pro-only**, including
the High Contrast style.

What ships and works:

- **A screen reader that actually speaks.** `orca` plus
  `speech-dispatcher-espeak-ng`. `0530-accessibility.hook.chroot` re-checks the
  whole chain on the built image every build — reader, voice module, audio
  plugin, module config, AT-SPI bus — and **fails the build** if a link is
  missing. Only one of the pinned lines is load-bearing:
  `speech-dispatcher-espeak-ng` is a *Recommends* and `--apt-recommends false`
  drops it; `speech-dispatcher` and `speech-dispatcher-audio-plugins` are hard
  Depends and were never at risk. (`desktop.list.chroot` now says so.)
- **Two menu entries that did not exist**: **Screen Reader** and
  **Accessibility** (`systemsettings kcm_access`), both with heavy `Keywords=`
  aimed at Windows vocabulary — *narrator*, *ease of access*, *magnifier*,
  *large cursor*. Plasma's own `kcm_access.desktop` is `NoDisplay=true`, which
  is correct for a KCM and means the menu had no answer for someone typing
  "sticky keys". The Hub gained a matching **Accessibility** row.
- **Meta+Alt+S toggles the reader**, written explicitly into
  `etc/skel/.config/kglobalshortcutsrc` rather than assumed. It could not be
  confirmed that Plasma binds it by default — `kaccess` contains the action
  name but KGlobalAccel's defaults are compiled Qt enums — so it is asserted.
- **A High Contrast style**, authored rather than borrowed. 160 colour pairs
  measured against both `BackgroundNormal` *and* `BackgroundAlternate`, worst
  7.22:1; the build hook re-measures and fails below 7:1. It forces a flat
  black wallpaper, because desktop icon labels are drawn straight onto the
  wallpaper and a photograph under them has no contrast ratio you can state.
- **A 32px pointer by default**, matching Windows 10's. 24 reads as "smaller
  than my old computer" to the audience this OS is sold to. One line in
  `kcminputrc` if anyone disagrees.
- **An accessible boot entry on the live ISO** — *"… (with screen reader)"*,
  directly under the default, adding `dagric.a11y=1`. This is the one place a
  blind person can get in unaided, because the live session autologs in.
  `0950-boot-branding.hook.binary` builds it by *copying* the normal live entry
  so it cannot drift from it; `/usr/lib/dagric/a11y-live` reads the flag.
- **The two QML tools** (the setup wizard and the appearance gallery) are
  screen-reader-readable and fully keyboard-operable — roles, names and states
  on every control, arrow-key roving focus inside the wallpaper and layout
  grids so twenty wallpapers are not twenty tab stops, a two-tone focus ring
  that survives being drawn over a photograph, and every hard-coded pixel size
  scaled off the real application font. Four things were found by running them
  rather than by reading them: the tab order ran footer → header → page on
  every screen (WCAG 2.4.3), Return did nothing on any button (Qt Quick's
  Button takes Space only), light mode shipped white-on-blue at **2.56:1** for
  the Next button while dark mode passed comfortably, and the gallery's
  20-second auto-revert was a WCAG 2.2.1 Level A timing failure — it now has a
  **More time** button, unlimited, plus spoken warnings at 10s and 5s.
- **The offline HTML** (95 manual pages, the guide, the welcome page): skip
  links on every page — the manual had none (WCAG 2.4.1, Level A) — accessible
  names on all 94 unnamed `<nav>`s, a real `<label>` on the search box, and 97
  colour pairs measured across three stylesheets with **0** failures. The bare
  `/` search shortcut now has a visible off switch (WCAG 2.1.4). The guide
  gained an Accessibility section in both languages, because EN 301 549 clause
  12.1.1 requires shipped documentation to describe these features and nothing
  did.

What does **not** work, stated plainly because a VPAT that rounds these up is
worse than no VPAT:

- **The login screen cannot read itself aloud.** SDDM has no way to publish an
  AT-SPI bus its Qt greeter would join — `libQt6Gui` reads
  `AT_SPI_BUS_ADDRESS` (the env var) and never `AT_SPI_BUS` (the X root-window
  property), so the usual `Xsetup` + `at-spi-bus-launcher` recipe produces a
  bus the greeter never joins and a reader announcing an empty screen. There is
  no `GreeterEnvironment` in sddm 0.21.0. The whole dead end is written into
  `/etc/sddm.conf.d/20-accessibility.conf` so nobody loses a day on it again.
  The workarounds are the live ISO's accessible boot entry, and autologin.
- **Slow keys do not exist on the Wayland session.** Sticky, bounce and mouse
  keys are KWin plugins; there is no `SlowKeysPlugin`, and `kaccess` applies
  slow keys via `XkbSetControls`, which only reaches XWayland. Any VPAT/ACR
  must say **Does Not Support** for Section 508 502.4(B) — do not let this get
  rounded up because `kaccess` still contains the string.
- **`DagricLight` and `DagricDark` fail 4.5:1 in several places** — they
  inherit Breeze's own accent colours (`ForegroundActive` 2.43:1 on Button,
  `ForegroundNeutral` 2.14:1 on Header). This is a real WCAG 1.4.3 exposure and
  it is a deliberate open decision, not an oversight: repainting the brand from
  an accessibility hook would have been the wrong call to make by ambush.
- **None of this has been heard.** Everything above is verified by declared
  properties, measured pixels, real key injection and build-time assertions.
  The live AT-SPI tree has *not* been exercised — WSL has no accessibility
  D-Bus. Before any accessibility claim is made commercially, one pass on the
  built image with `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 accerciser`, and one
  pass with Orca and the mouse unplugged, is owed.

### Languages

The shell tools and the launcher entries speak **German, French, Spanish,
Brazilian Portuguese and Italian** — 310 messages per language, compiled to
`.mo` catalogues that ship in the image (280 KB total; `msgfmt` is a build-host
tool and has no business on a desktop ISO, so compilation happens here and the
output is committed like the wallpapers). `0150-locales.hook.chroot` fails the
build if a catalogue is missing.

Coverage is honest rather than uniform:

| | |
|---|---|
| Every `dagric-*` shell tool, the Hub, the launcher entries | de, fr, es, pt_BR, it |
| Style / layout / wallpaper-pack names (they cross into the QML as data) | de, fr, es, pt_BR, it |
| Welcome page, user guide | **German only** |
| The setup wizard's and gallery's own chrome (QML strings) | English |
| `dagric-hardware-check`'s output | English |
| The 94-page manual | **English, deliberately and permanently** |

The manual is not a gap that will be closed. Its entire value is that the
search index knows the *English* Windows names — type *notepad*, get the Text
Editor. A German index would have to carry German keywords across 94 cards or
a German owner typing "Editor" finds nothing, and a page that looks translated
but answers in English is worse than one that never claimed to be. It says so,
in German, at the top of the page, and links back to the German guide.

> **THE TRANSLATIONS ARE MACHINE-GENERATED AND HAVE NOT BEEN READ BY A NATIVE
> SPEAKER.** Every `.po` header records this (`Last-Translator`, `X-Generator`,
> `X-Dagric-Review-Status: unreviewed`) and names the tier-one strings that
> must be reviewed first: all of `dagric-migrate`, all of `dagric-usb-protect`,
> the Secure Boot notice in `dagric-drivers`, the Steam and Resolve licence
> paragraphs, and the translated affirmative in `y yes`. **Do not list
> Deutsch / Français / Español / Português / Italiano on the download page, in
> the shop, or in a language picker until those have been cleared.** Shipping
> unreviewed translation is a defect; advertising it is a promise that cannot
> be kept. If one is to ship deliberately, say so in the language itself —
> *"Deutsch (Beta — Übersetzung noch nicht geprüft)"* — which turns a defect
> into a recruitment ad for community translators.

A real defect was found and fixed on the way here: `0150-locales.hook.chroot`
did `echo "en_US.UTF-8 UTF-8" > /etc/locale.gen`, destroying the 509-line
commented template. Both mechanisms that give an owner a non-English system —
live-config's `locales=` boot parameter and Calamares' `rewrite_locale_gen()` —
work by *uncommenting* a line in that template, so both silently failed:
picking German in the installer set `LANG=de_DE.UTF-8` pointing at a locale
that was never generated, which is C fallback plus the exact locale warnings
the hook existed to prevent, with all 219 language directories of KDE and
Debian translation already on the disk ignored.

**Security baseline** (genuinely strong — free is lean, not insecure):
AppArmor mandatory access control active from boot — Debian's mature profiles
enforced, the wider apparmor-profiles set in complain mode per upstream (about a
third of the total; see the AppArmor manual page and 0300-hardening's counter) —
an expanded hardened kernel (kexec disabled, BPF/perf locked down, network-spoof
protections, non-world-readable homes), firewalld, silent security updates, and
Lynis on-demand security auditing. Plus day-one functional support most switchers
need: scanners, printer breadth, firmware updates (fwupd), VPN import, media
codecs + Netflix/Spotify (EME), MS-Office-metric fonts, fingerprint login,
GPU video decode, `.deb` double-click, and a screen reader.
Pro adds *proactive* monitoring on top (the Security Suite) — free is not
crippled, Pro is a clear step up.

## Dagric OS Pro — everything above, plus

**Creator suite**
| | |
|---|---|
| Browsers | Chromium alongside Firefox ESR |
| Email/calendar | Thunderbird |
| Office | The complete LibreOffice suite |
| Image | GIMP (with PhotoGIMP layout), Krita, Inkscape |
| 3D | Blender |
| Video | OBS Studio (recording/streaming) + Kdenlive (editing) |
| Backup | Borg + Vorta GUI (local/encrypted) + rclone (70+ cloud providers) |
| Mobile | KDE Connect — Android/iOS notifications, files, clipboard, remote input (firewall ports preconfigured) |
| Look | Papirus icon theme, Pro identity |

**Gaming & Windows apps**
| | |
|---|---|
| Windows apps | Wine (64- and 32-bit) + winetricks — run classic .exe software; Bottles via one-click consent install |
| Windows itself | "Windows in a window" — KVM/QEMU + virt-manager preinstalled with UEFI (OVMF) and software TPM (swtpm) for Windows 11 guests; `dagric-vm` enables it with consent. Windows is never bundled — the helper points to Microsoft's official ISO download |
| Games | Steam via one-click consent install (`dagric-get-steam` — NEVER bundled); 32-bit Vulkan prepped; `dagric-gaming` adds community Proton-GE on request |
| Performance | gamemode governor + MangoHud FPS overlay |

**Stability**
| | |
|---|---|
| System restore | Timeshift — adds user-scheduled restore points and an rsync mode for manual ext4 installs, on top of the snapper/grub-btrfs pre-update rollback every edition gets |

**Security Suite** (the Pro step-up; free keeps a strong baseline — see below)
| | |
|---|---|
| App firewall | OpenSnitch — per-application outbound control; ships in monitor mode, blocking opt-in from the GUI |
| USB control | USBGuard — block BadUSB / USB-drop attacks. Ships masked; `dagric-usb-protect` (Hub → USB Protection) generates an allow-list from the devices currently attached and only then arms the daemon, so enabling it can never deauthorize the owner's own keyboard/mouse. Same tool disarms it. |

**Developer toolchain**
| | |
|---|---|
| Containers | Docker (+ compose) and Podman preinstalled |
| Any-distro shells | Distrobox — Ubuntu/Fedora/Arch userlands in a terminal with full host integration |
| Toolchain | build-essential, git, Python (pip + venv) |
| SSH | client ready; server installed but OFF until enabled |

**Owner-consent helpers (never auto-run)**
- `sudo dagric-drivers` — detects NVIDIA hardware, installs the
  proprietary driver from Debian non-free on request
- `dagric-get-resolve` — guided official DaVinci Resolve install
  (Blackmagic's license forbids preinstalling it; no honest OS can)
- `dagric-ai` — one-command local LLM setup (Ollama); models run
  entirely on the machine, nothing leaves it
- `dagric-vm` — enables the VM stack (groups + service) with consent
- `dagric-get-joplin` — local-first Markdown notes (OneNote/Notion
  alternative, offline, optional E2E-encrypted sync)
- `dagric-get-onlyoffice` — MS-Office-style ribbon suite with the best
  open-source .docx/.xlsx/.pptx fidelity, alongside LibreOffice

**Launcher entries for the helpers.** `config/includes.chroot/usr/bin` holds 33
`dagric-*` tools plus one sourced library (`dagric-i18n.sh`, which every tool
reads its language from and which is not a command). 27 of them ship a launcher
entry; `0530-accessibility.hook.chroot` writes two more at build time (**Screen
Reader**, **Accessibility**), so the menu carries 29. Where the edition line
falls is mechanical, not a marketing judgement:

> A helper that only **fetches a free app** — from Flathub, from Debian, or
> from the vendor — ships on **both** editions. A helper that drives software
> **only Pro installs** ships on Pro.

By that test exactly two are Pro: `dagric-vm` (needs the KVM/QEMU/virt-manager
stack) and `dagric-usb-protect` (needs USBGuard). Both would be dead buttons on
free. The other eleven — Steam, Heroic, ProtonUp-Qt, Bottles, ONLYOFFICE,
Joplin, LocalSend, Cryptomator, Upscayl, DaVinci Resolve and Ollama — are on
both editions, and appear in the Hub under **Add more apps**.

All fourteen were briefly Pro-only. That build shipped a free edition whose own
manual documented Steam, Bottles, Heroic and Resolve and then offered no way to
reach any of them — the exact "free feels broken" failure this project forbids
— and the thing being gated was a script that runs `apt install steam`. Steam
is free software; charging $39 for the convenience of installing it protected
no revenue and made the gate look petty to precisely the people most likely to
notice. Pro's value is that the creator and gaming stacks arrive **already
installed and tuned** (Wine, gamemode, MangoHud, the full creator suite, the VM
stack, the Security Suite), not that free owners are forbidden to download
things.

The two genuinely Pro entries carry `X-Dagric-Edition=pro` and are **deleted** —
not hidden — from free images by `0510-app-names.hook.chroot`, for the same
reason the Pro looks and styles are: a flag the owner can edit out is not a gate.
Deliberately given no *launcher* entry: `dagric-brand-launcher` and
`dagric-driver-offer` (hidden helpers) and `dagric-snapshot-setup` (a one-shot
root task with nothing to open). `dagric-gaming` is **not** one of them, though
this paragraph used to say it was: `dagric-gaming.desktop` shipped all along and
carried `X-Dagric-Edition=pro`, so Pro got a *Gaming Setup* entry this document
said did not exist, and free — whose manual page for the helper is marked
available and tells the owner to open *launcher → Gaming Setup* — got none. The
flag is removed. The launcher entry and the Hub row now both ship on **both**
editions, since it only downloads a free Proton build. `dagric-hub` itself and
`dagric-app-names` are the other two without one — the Hub has an entry, the
regenerator is an apt hook. `dagric-guide` is a *wrapper*, not a new tool:
`dagric-guide.desktop`'s `Exec=` used to hardcode the English
`guide/index.html`, and a `.desktop` Exec is a fixed string, so once
`guide/de/index.html` existed a German entry could only ever open English text.
Its `Name=` was a second half of the same bug and is fixed with it: it read
*Welcome Guide*, the Hub's name for the welcome page, and now reads *User
Guide*, matching the Hub row, the setup wizard's card and the document's own
title in all six languages.

**The Hub** (`dagric-hub`) now draws **31 rows on free, 34 on Pro**, in four
sections plus Pro's fifth. Three of them are new: **Check this PC**,
**Accessibility**, and the **user guide** — which had no Hub row at all while
two other rows were labelled "Welcome guide" and "App manual" and the launcher
carried a third entry called "Welcome Guide" that opened a different document
again. The three are now spelled out: *Welcome page — what Dagric promises*
(`welcome/`), *User guide — your first week* (`guide/`), *App manual*
(`manual/`). Every row goes through gettext; every **tag** stays literal,
because kdialog hands the tag back and a translated tag is a row that silently
does nothing.

## Pro roadmap (engineering ahead of promises)

These are real projects, not checkbox features — listed here so the
pitch never outruns the product:

- **Immutable core / atomic updates with rollback** — requires moving to
  an image-based update model (ostree/ABroot-style). Large but doable.
  (The btrfs-default + snapper/grub-btrfs rollback groundwork already
  ships; this is the step beyond it.)
- **umu-launcher** — containerized Proton for non-Steam .exe files;
  not yet packaged in Debian, revisit when it lands (or vendor it).
- **LocalAI** — OpenAI-compatible self-hosted engine (LLM + Whisper +
  image gen) as an alternative backend for `dagric-ai`.
- **Fleet management dashboard** — builds on the signed APT repo
  (`docs/REPOSITORY.md`); needs a server-side product.
- **Compliance profiles** (disk-encryption enforcement, audit logging,
  centralized policy) — enterprise tier.
- **10-year LTS + 24/7 SLA support** — a staffing commitment, priced per
  seat (Red Hat/Canonical model).
- **OEM preinstall partnerships** — after real-hardware validation.

## Facts worth writing down

Things that have cost a research pass at least once. Written here so they never
cost another.

- **The ISO shipped a gzip initramfs that nobody chose, and nothing was
  misconfigured.** `/etc/initramfs-tools/initramfs.conf` says `COMPRESS=zstd` —
  Debian's own Trixie default — and it had never once taken effect.
  `mkinitramfs` falls back with `W: No zstd in $PATH, using gzip` and then
  exits 0, so the exit status says nothing and the warning lands in a
  fifteen-minute build log. `zstd` was absent because `initramfs-tools-core`
  only *Recommends* it and `auto/config` sets `--apt-recommends false`. Two
  correct decisions cancelling each other, silently: 161 MB of gzip where
  140 MB of zstd was asked for. `zstd` is now pinned in
  `system.list.chroot` and `0260-boot-speed.hook.chroot` greps for that exact
  warning string, because the size alone cannot prove it.
- **live-build defaults the squashfs to `-comp xz` when you do not say
  otherwise** — the `# Set squashfs compression type or default to xz` branch
  in `/usr/lib/live/build/binary_rootfs`. So every file read during session
  startup paid an xz block decompression. Measured power-on to Plasma
  wallpaper under QEMU/OVMF, cold cache, medians of 3-6 runs: **69 s** shipped,
  63 s with a zstd squashfs, **56 s** with zstd squashfs *and* zstd initrd. The
  build step also gets **faster** (75 s vs 122 s). The ISO grows ~4%;
  `--chroot-squashfs-compression-level 19` buys 17 MB of that back for ~82 s
  more build time and costs nothing at boot, because zstd's decompression rate
  is essentially independent of the level it was compressed at. Note there is
  **no** `lb config` flag for the squashfs block size — only
  `--chroot-squashfs-compression-type` and `--chroot-squashfs-compression-level`
  exist; a 256K block would have to be smuggled through `MKSQUASHFS_OPTIONS`,
  which is undocumented passthrough and is deliberately not done.
- **systemd's boot is not where this OS's boot time goes.** Its own accounting
  on the shipped image: `Startup finished in 3.99s (kernel) + 8.24s (userspace)
  = 12.23s` — of a 69-second boot. The critical chain to `sddm.service`, read
  off a `kmsg`-on-serial log, is live-config (2.7 s) → firewalld (2.1 s) →
  network-pre → NetworkManager → network.target → systemd-user-sessions →
  sddm, and nothing else on it is over a second. Both of those costs are things
  the product sells. The time is in GRUB reading a 161 MB initrd at ~13 MB/s
  and in the Plasma session drawing itself. **Do not go unit-hunting here.**
- **GRUB's PNG decoder is narrower than ImageMagick's writer, and it fails
  silently.** A 16-bit or sub-byte-palette PNG draws as rainbow moiré, or as
  nothing at all, with no error anywhere. `magick` picks both encodings on its
  own — 16-bit whenever it composites with alpha, palette whenever an image has
  few colours, which is exactly what a flat-filled 9-slice tile is. Every PNG
  in the boot theme is forced to 8-bit RGBA non-interlaced and the IHDR is
  re-read afterwards; `build.sh` hard-fails on any PNG under
  `config/includes.chroot` deeper than 8-bit (`od -An -tu1 -j24 -N1 f.png`).
- **`gfxterm`'s `background_image` can only stretch — there is no crop mode**,
  unlike the theme's own `desktop-image-scale-method: "crop"`. That is why the
  load screen is the branded 1920x1080 art stretched: exact at 16:9, ~11%
  narrow at 1280x800, visibly oval at 1024x768. Rendered under OVMF at all
  three and looked at before choosing. The unbranded `terminal.png` is still
  generated for anyone whose fleet is mostly 4:3; swapping the filename in
  `0950-boot-branding.hook.binary` is the whole change.
- **`/etc/calamares/modules/fstab.conf`'s `mountOptions:` and
  `ssdExtraMountOptions:` are dead config** for this Calamares version. The
  fstab module reads its option strings out of global storage
  (`mountOptionsList`) and its own schema is `additionalProperties: false`,
  allowing only `crypttabOptions` and `tmpOptions`. The real source is the
  **mount** module, `modules/mount.conf` — which shipped with no `mountOptions`
  block at all, so `if mount_options is None: return "defaults"` fired and every
  Dagric install mounted root with a bare `defaults`, not even `noatime`.
  `0250-performance.hook.chroot` now appends a proper block there
  (`noatime` everywhere, `compress=zstd:1` on btrfs, ESP restated as
  `defaults`, no `discard` because `fstrim.timer` is already enabled).
- **File-content search is a decision still owed.** Baloo currently indexes
  file *contents* by default. The urgent case is `dagric-migrate`: it copies
  the owner's whole Windows Documents/Pictures/Videos into the new home right
  after install, which starts a multi-hour full-content index on a spinning
  disk during the exact window the owner is forming their opinion. The fix is
  **not** to ship `Indexing-Enabled=false` on its own — that drops Dolphin to
  filename-only search, which is a feature removal, not a leaning-out. It needs
  to ship together with a Hub toggle ("Search inside my files"), and ideally
  with `dagric-migrate` offering to switch indexing on *after* the copy
  finishes. Do not remove the `baloo6` package: Dolphin and Plasma pull in
  `libkf6baloo6` and `qml6-module-org-kde-baloo`.
- **Akonadi is not installed** on either edition (verified against
  `filesystem.packages`), and Pro's Thunderbird does not use it. Nobody needs
  to "fix" this.
- **`systemd-oomd` is a separate, uninstalled package in Debian** — it is not
  bundled with systemd 257 the way upstream discussion implies. `earlyoom` is
  what Dagric ships for the low-RAM livelock, configured by
  `0250-performance.hook.chroot`.
- **Annotating a Qt `TabButton` deletes it from the accessibility tree.** Adding
  so much as `Accessible.description` to a `TabButton` makes it report
  `Accessible.ignored == true` shortly after layout — later than both
  `Component.onCompleted` and `Qt.callLater`, so an imperative reset does not
  survive either. A *bare* `TabBar` reads `false` on every button. The
  appearance gallery's tabs are therefore deliberately un-annotated, with a
  20-line comment saying so. Plain `Button`s and `Rectangle`s are unaffected
  (checked at a late read), which is why the wizard's button descriptions are
  safe. If someone "improves" the tabs, the tabs vanish for screen-reader users
  and nothing else changes.
- **`--bootappend-live` is every entry's kernel command line.** Anything that is
  meant to be a *choice* cannot go there. `dagric.a11y=1` is on one copied menu
  entry built by `0950-boot-branding.hook.binary`; in `auto/config` it would
  start a screen reader talking on every machine that boots the stick.
- **Package names that look right and are not**: `qt6-speech-speechd` does not
  exist (`qt6-speech-speechd-plugin` does, 6.8.2-2, and nothing needs it — Orca
  does not). The Breeze cursor directory is `breeze_cursors`, not `Breeze`, and
  a wrong `Inherits=` falls back to the 1987 X core cursor rather than erroring.
  `~/.config/plasma-workspace/env/` no longer exists as a mechanism — grep of
  the whole plasma-workspace 6.3.6 package finds no reference to that path.
- **`includes.chroot` lands BEFORE hooks**, not after. `lb chroot` runs
  `chroot_includes_after_packages` (line 51) then `chroot_hooks` (line 52).
  A comment in `0800-snapshot-recovery.hook.chroot` used to claim the reverse
  and a hand-made wants-symlink was written to work around a constraint that
  does not exist.

## Pricing sketch

| Tier | Price | Gets |
|---|---|---|
| Dagric OS | free | The full OS. No account, no strings. |
| Dagric Pro | one-time or per-seat | Creator + dev suite preconfigured, priority updates |
| Dagric Enterprise | per seat/year | Fleet dashboard, compliance, SLAs (future) |
