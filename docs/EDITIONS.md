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
3 styles free / 6 on Pro, thirty-four Dagric-made wallpaper packs (twenty
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
  Thunderbird and Orca are deliberately **not** renamed: the brand is what the
  owner already searches for.
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
  a switcher. 94 pages, 844 KB, zero network calls. Search indexes the Windows
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

**Security baseline** (genuinely strong — free is lean, not insecure):
AppArmor mandatory access control enforced from boot, an expanded hardened
kernel (kexec disabled, BPF/perf locked down, network-spoof protections,
non-world-readable homes), firewalld, silent security updates, and Lynis
on-demand security auditing. Plus day-one functional support most switchers
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

**Launcher entries for the helpers.** All 27 `dagric-*` tools were audited and
13 gained a launcher entry. Where the edition line falls is mechanical, not a
marketing judgement:

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
`dagric-driver-offer` (hidden helpers), `dagric-snapshot-setup` (a one-shot root
task with nothing to open), and `dagric-gaming` (Proton-GE is an operation on an
existing Steam install, and ProtonUp-Qt is the GUI for the same job and *is*
surfaced). `dagric-gaming` does get a Hub row on both editions, since it only
downloads a free Proton build.

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
