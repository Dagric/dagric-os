# Dagric OS changelog

## Unreleased — the first hour

Everything here ships on **both** editions. A switcher decides in the first
hour whether leaving Windows was a mistake, and the free edition has to win
that hour on its own.

- **Set Up Dagric** (`dagric-firstrun`) — a real six-step first-run wizard
  replacing the Firefox welcome tab: light/dark, accent, wallpaper, text size,
  taskbar layout, and your files from Windows. Steps the machine cannot act on
  are never shown. Every choice applies for real as you click it, and the
  escape hatch is an **Undo my changes** button rather than a nag when you
  close the window. Re-runnable from the launcher and the Hub.
- **The launcher now says what things do.** Files, Terminal, Photos, Document
  Viewer, Archive Manager, Text Editor, Music, Screenshot, Task Manager,
  Software Store, Saved Passwords, Videos, Scanner, Package Installer. The
  original names still find them when you search, and the rename is regenerated
  after every apt transaction so a KDE point release cannot quietly undo it.
  Firefox, LibreOffice, GIMP, Blender and the rest keep their own names.
- **Dagric Manual** (`dagric-manual`) — 94 offline pages, one per application
  and per Dagric tool: what it is, what it replaced on Windows, five things you
  will actually do, and the one thing that will surprise you. Search understands
  the Windows names, so *notepad* finds the text editor.
- **Text Size** (`dagric-display`) — 100% to 200% scaling with a 20-second undo
  that runs outside the dialog it protects, so it still fires if the dialog
  ends up off-screen. Plus a night light on fixed hours. Dagric also measures
  your screen at first login and picks a sensible size on its own.
- **Ctrl+Shift+Esc opens the Task Manager**, the same keys as Windows.
  (Ctrl+Esc, which older Dagric pages recommended, was never bound in Plasma 6.)
- **The "Plasma (X11)" login option now works.** It had always been listed and
  had never had a window manager behind it — pick it and you got a desktop with
  no title bars. `kwin-x11` now ships.
- **Six new wallpaper designs** — Contour, Mesh, Prism, Linen, Void (true black,
  for OLED) and Halftone, each with a logo-free cut. 34 packs in all. The six
  original designs are now generated from the same script as the rest, so the
  whole set is reproducible. New login-screen artwork, and twelve user avatars
  where there were none.
- **Faster, quieter boot and a machine that does not lock up when memory runs
  out**: zram on zstd, `earlyoom` so a 4 GB machine closes Firefox instead of
  freezing for minutes, BFQ on spinning disks only, journald capped at 200 MB,
  and `ldconfig` no longer rebuilding a correct cache on every boot. Installed
  systems now get real mount options (`noatime`, and `compress=zstd:1` on
  btrfs) — a Calamares config key that was being silently ignored meant every
  install to date mounted with a bare `defaults`.
- **The user guide answers questions now instead of being read once.** It opens
  with a table of **where everything went** — Start menu, File Explorer, Task
  Manager, Recycle Bin, fourteen rows — because that is the question ten years
  of habit actually arrives with. Then a **first-day checklist** that remembers
  which items you ticked, and a **search box that speaks Windows**: type
  *recycle bin*, *task manager* or *kein Ton* and you land on the right section.
  New **troubleshooting** section covering the eight things that really happen,
  symptom first, none of them needing the terminal — including the one almost
  no distro documents: a hibernating Windows keeps its drives locked, which is
  why your Windows drive sometimes will not open. All of it in German too.
- **The desktop is branded end to end now.** A Dagric **startup screen** fills
  the gap between signing in and the desktop appearing — it was stock Breeze,
  the last unbranded surface in a boot that is otherwise ours from the menu
  onward. The **terminal** gained Dagric colours, measured for contrast rather
  than picked by eye. And the guide, the manual and the welcome page **follow
  your light or dark choice** instead of being permanently dark, which was the
  one part of Dagric that ignored the wizard's very first question.
- **More Windows keys that just work.** <kbd>Win</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd>
  grabs a screen region, exactly as it does on Windows.
  <kbd>Win</kbd>+<kbd>V</kbd> opens clipboard history, which now survives a
  sign-out the way Windows' does. And **right-click → Create New** in Files
  offers a blank document, spreadsheet and presentation — the Explorer gesture
  with no equivalent until now.
- **Fixes worth naming.** The free edition was missing the package that creates
  your Documents, Downloads and Pictures folders, so a fresh free install had
  none of them. The guide claimed rolling back a bad update was a Pro feature;
  it is on every edition and always was. The boot menu's *(with screen reader)*
  entry shared its shortcut key with the entry above it, so the key always
  booted the wrong one. And console and SSH logins greeted you with Debian's
  warranty notice rather than anything of ours.

### Things that were quietly broken

Five audit passes went through the tree feature by feature, checking each
finding against a real build rather than trusting the source. These are the
ones that mattered, in the order an owner would care.

- **Pro machines all shared the same SSH host key.** The key pair was generated
  while the image was being built, so every Pro installation carried an
  identical one. A host key is the only thing that proves to a client it reached
  the computer it dialled, so sharing one removes that proof. Each machine now
  generates its own on first boot. *If you installed Pro before this release and
  have ever switched the SSH server on, the manual's SSH page has the three
  commands that replace them — it only ever mattered once you enabled it, and it
  ships off.*
- **Bringing your Windows passwords across recovered nothing.** The importer
  opened the wrong kind of Firefox key store — the format Firefox stopped using
  in 2018 — so it found no key, decrypted nothing, and reported that there were
  no saved logins. It reads the right store now.
- **The installer offered no disk-encryption option.** The guided install path
  never showed the *Encrypt system* checkbox, although the manual said it would.
  It is there now.
- **The NVIDIA driver could leave you at a black screen.** On a machine with
  Secure Boot on — the factory setting on most Windows laptops — the helper was
  unable to detect it, skipped the key-enrolment walkthrough, and told you to
  reboot. The driver then refused to load. The detection works now, and the
  enrolment steps appear when they are needed.
- **Snapshots were never cleaned up.** Every update added a pair and nothing
  removed them, so the disk filled until the system would have turned itself
  read-only. They are now counted against the limits that were always meant to
  govern them.
- **Sharing this computer's connection did nothing** on the free edition — the
  Wi-Fi hotspot came up but handed out no addresses.
- **Pro started a container service nobody asked for** at every boot, which also
  opened a network bridge and added firewall rules of its own. Docker is
  installed and now waits until you start it; the manual says how.
- **SSH was closed on one network profile but not the others**, including the
  *home* profile our own guide tells you to use.
- **Moving your files in another language** created English-named folders beside
  your real ones, so the files arrived where nothing on the system looked.
- Plus: audio no longer pops and clips the start of every sound on older
  machines; English punctuation stops borrowing shapes from the CJK fallback
  font; the boot menu's snapshot entries read as dates and descriptions instead
  of filesystem paths; the appearance gallery says something when it cannot
  start rather than nothing at all; and a `dagric-game-launch` option holds full
  performance and stops the screen dimming during controller-only games.

We also corrected two things we had claimed. AppArmor is described as *active*
rather than *enforced*, because Debian ships a large part of its profile set in
a mode that logs rather than blocks — most are enforced, roughly a third are
not, and `aa-status` shows you which. And the task manager shortcut is
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Esc</kbd>; one page still said
<kbd>Ctrl</kbd>+<kbd>Esc</kbd>, which was never bound.

## 1.0 "Foundation" — 2026-07-26

First release, free and Pro editions.

### Base
- Debian 13 "Trixie", KDE Plasma, Calamares installer
- Zero telemetry (none shipped), no ads, no accounts
- Firefox hardened by policy: telemetry, studies, Pocket and sponsored tiles
  off, tracking protection on, and **uBlock Origin** set up for you — Firefox
  downloads it from addons.mozilla.org the first time it runs, and it can be
  removed like any add-on
- Debloat: `--apt-recommends false` everywhere, every package hand-picked
- Hardened: firewall on, kernel sysctls, silent security updates,
  **no automatic reboots**, zram swap
- **EFI + BIOS installs** (grub-efi + shim Secure Boot chain and grub-pc-bin
  from one image), **btrfs default filesystem** (instant Timeshift snapshots;
  ext4 available), branded Plymouth boot splash
- Dagric Welcome first-run page + offline user guide
- **Dagric Hub** — one launcher entry gathering every owner tool (setup,
  drivers, Security Checkup, guide, and the Pro creator/gaming/AI helpers)
  in a single edition-aware window, plus searchable menu entries for each
- **Dagric Styles** (`dagric-style`) — one-click desktop moods: color scheme
  + accent + wallpaper + KWin effects together, all reversible via Reset.
  3 styles free, 6 on Pro; extensible by dropping `.style` files in
  `/usr/share/dagric/styles`
- **Dagric Looks** (`dagric-looks`) — switch the desktop layout (panel shape
  and position) to match what you came from. 3 layouts free, 7 on Pro
- **Migration Assistant** (`dagric-migrate`) — copies Documents/Pictures/
  Music/Videos/Desktop plus Chrome/Edge/Firefox bookmarks off the Windows
  partition, read-only, never writing to Windows
- **Snapshot recovery** on the default btrfs install: snapper takes an
  automatic snapshot before and after every apt transaction, and a vendored
  grub-btrfs generator lists them as a boot-menu submenu — a bad update is
  undone from GRUB instead of reinstalled. `dagric-snapshot-setup` wires it
  up on first boot of the installed system
- Accessibility now functional: Orca ships with its speech backend
  (espeak-ng), not mute
- Steam is a one-click consent install, never bundled (Hub entry and menu
  entry on Pro; the `dagric-get-steam` helper ships on every edition)
- Print-to-PDF, L2TP/IPsec VPN, and (Pro) Google Drive in Dolphin
- Pro gaming: Heroic (Epic/GOG/Amazon) and ProtonUp-Qt one-click helpers
- **Dagric logo throughout** (Zorin-style): branded boot-menu splash, desktop
  wallpaper and login background (D monogram + wordmark), the
  application-launcher button (first-login script, self-healing), the
  About-this-System page (`LOGO=` in os-release), and a full hicolor icon set
  (16–256 px + scalable SVG)
- Windows-switcher care: NTFS/exFAT drives, 7z, thumbnails, network browsing,
  laptop power profiles, double-click defaults

### Pro edition adds
- Creator suite: Chromium, Thunderbird, full LibreOffice, GIMP (PhotoGIMP
  layout), Krita, Inkscape, Blender, OBS Studio, Kdenlive
- Gaming/Windows apps: Wine 64+32-bit, Steam (Proton), gamemode, MangoHud,
  Proton-GE via `dagric-gaming`
- **Security Suite**: OpenSnitch per-application outbound firewall (ships in
  monitor mode, blocking is opt-in from the GUI) and USBGuard against
  BadUSB/USB-drop attacks — shipped masked, and armed only by
  `dagric-usb-protect` (Hub → USB protection), which first builds an
  allow-list from the devices already attached so enabling it can never
  deauthorize the owner's own keyboard or mouse
- Timeshift restore points (scheduled GUI on top of the snapper/grub-btrfs
  rollback every edition gets); Borg + Vorta + rclone backup
- KDE Connect phone integration (firewall preconfigured)
- Dev stack: Docker + Compose, Podman, Distrobox, build-essential, git,
  Python, SSH (server off by default)
- Papirus icon theme; owner-consent helpers: `dagric-drivers`,
  `dagric-get-resolve`, `dagric-ai`

### Known limitations
- Real-hardware validation pending (QEMU-tested: BIOS and UEFI)
- Update channel (repo.dagric.com) built but not yet hosted

### History
Named Dagric (dagr "day" + ric "ruler") 2026-07-21; earlier working titles
Freehold OS and Antithesis OS.
