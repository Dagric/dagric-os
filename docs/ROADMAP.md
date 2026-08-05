# Roadmap

## Phase 1 — Proof of concept  ← YOU ARE HERE
- [x] live-build source tree, reproducible from Git
- [x] Debloated KDE Plasma package set (no metapackage bloat, no recommends)
- [x] Zero-telemetry guarantee (nothing to disable — it isn't shipped)
- [x] Identity/branding hooks (`os-release`, issue, wallpaper placeholder)
- [x] Hardening baseline: firewall on, silent security updates, no auto-reboot,
      kernel sysctl hardening, zram
- [x] Calamares graphical installer on the live ISO
- [x] One-command build from Windows via Docker
- [x] First successful ISO build (`.\build.ps1`) — 2026-07-21, 1.8 GB hybrid ISO
- [x] Boot test in a VM — boots to full Plasma desktop (QEMU harness in `test\`)

## Phase 2 — Polish
- [x] Real wallpaper — rendered from SVG at build prep, set as Plasma default
      via look-and-feel hook (verified on booted desktop) + SDDM background
- [x] Boot menu splash (`config/bootloaders/splash.svg` — live-build renders it
      for both BIOS/isolinux and EFI/GRUB menus)
- [x] **Boot experience overhaul** — the whole chain from firmware to login,
      designed and then measured rather than assumed. A real GRUB theme on
      UEFI (`usr/share/dagric/boot/grub-theme/`) with a visible selection and
      a "Starting Dagric OS in 6s" countdown; the same design on BIOS in what
      `vesamenu` can express (`config/bootloaders/isolinux/stdmenu.cfg`), at
      1024x768 instead of the 640x480 live-build hard-codes; both titles
      suppressed because they printed through the wordmark; a 10-second
      timeout on both paths, which used to be *wait forever*. Plymouth now
      loads the bootloader's own `background.png` and finds the artwork's
      decorative rule in the pixels at build time to place its progress fill.
      `gfxterm` keeps drawing the branded art through the squashfs load, which
      removes the black rectangle that used to sit there for ~19 s. Verified
      by booting throwaway GRUB ISOs under OVMF at 1920x1080, 1280x800 and
      1024x768 and opening every screenshot; the accessible "(with screen
      reader)" entry is regression-checked against a reconstructed pre-hook
      tree on both firmware paths.
- [x] **Dagric's own SDDM theme** (`usr/share/sddm/themes/dagric/`) — replaces
      Breeze-with-our-wallpaper. Imports `QtQuick` and nothing else, so no KDE
      QML module can be renamed upstream and take the login screen with it.
      Breeze stays configured as the documented rescue path with the same art.
      `branding/sddm/render-login.sh` renders its states (users / caps / failed
      / no-users / layouts) under Xvfb so they can be reviewed without a
      twenty-minute reboot.
- [x] **Boot time: 69 s → 56 s to the Plasma wallpaper** (QEMU/OVMF, cold
      cache, median of 3-6 runs; BIOS 61 s → 49 s). Two causes, both silent:
      the initramfs was gzip because `zstd` was only a dropped *Recommends*,
      and live-build defaults the squashfs to xz when
      `--chroot-squashfs-compression-type` is unset. Fixed in
      `system.list.chroot`, `auto/config` and
      `0260-boot-speed.hook.chroot`. These are QEMU numbers on an SSD: both
      phases are I/O- and decompression-bound, so the gain on the USB-2 sticks
      and 5400 rpm disks this OS targets should be **larger**, not smaller —
      but that is reasoning, not a measurement.
- [x] Plasma defaults for Windows switchers (double-click to open, no wobbly
      effects) via `etc/skel`
- [x] Calamares branding module — product name, colors, 3-slide ownership
      slideshow (`etc/calamares/branding/dagric/`); config verified in image
- [x] Flathub enabled out of the box in Discover (verified in image)
- [x] Firefox policies: telemetry/Pocket/studies/sponsored tiles off, tracking
      protection on, uBlock Origin installed via ExtensionSettings (fetched
      from AMO on first run; removable by the owner) (verified in image)
- [x] Calamares install run-through test — full install to a 20 GB virtual
      disk in the QEMU harness, then booted the INSTALLED system to the
      Plasma desktop (branded SDDM login included). Found and fixed three
      install blockers along the way: missing cracklib-runtime,
      squashfs-tools, and grub-pc. Test creds: user dagric.
- [ ] **A Dagric Plasma startup screen** (`etc/xdg/ksplashrc` + a look-and-feel
      package). This is the largest unbranded stretch left in the boot and it
      is not a black gap — it is **~16 seconds of KDE's Breeze splash**, a
      white KDE logo and "Plasma made by KDE" on pure black, because
      `/etc/xdg/ksplashrc` does not exist in the image and Plasma falls back.
      It is also the cheapest of the remaining items, because something *is*
      already drawing: it needs the same `#0e1826 → #05080d` ground and the
      mark at the same height, not new machinery.
- [ ] **The ~9-second black window between Plymouth and the Plasma splash.**
      Measured, and **not** fixed — recorded here so nobody reports it as done.
      Two independent arrangements were tried (`After=display-manager.service`
      on `plymouth-quit`, worth exactly 1 s because `sddm.service` is
      `Type=simple` and goes active the instant it is exec'd; and SDDM on tty1
      the way Fedora arranges GDM, worth nothing at all). It is the display
      server taking the VT with nothing yet drawing, and Plymouth cannot cover
      it — the framebuffer is cleared at that moment regardless of ordering or
      which VT. `plymouth quit --retain-splash` *is* shipped and does fix the
      related bug: plain `plymouth quit` restored the text console and dumped
      stale pre-boot text on screen for the whole gap. The levers that would
      close the gap itself are SDDM's and Plasma's, not Plymouth's.
- [ ] Align Plymouth's mark with GRUB's. The base gradient is byte-identical
      between the two now, so the colour is continuous, but Plymouth's mark
      sits at 38% of screen height and the bootloader's wordmark block sits
      higher — so the logo still moves once, between the menu and the splash.
- [ ] Boot-theme assets for HiDPI. Everything in the GRUB theme is a fixed
      pixel size because GRUB cannot scale a font — it renders pre-generated
      `.pf2` bitmaps. That is why `gfxmode` is capped at 1920x1080 rather than
      set to bare `auto`: `auto` would keep the firmware's own mode and remove
      a mode change, but on a 4K laptop it produces a menu a quarter of the
      screen wide in unreadable type. A HiDPI font set would let `auto` win.

## Phase 3 — Real-hardware validation
- [x] EFI install support — VERIFIED end to end in the UEFI (OVMF) harness:
      GPT + EFI System Partition + btrfs root install completes, and the
      installed system boots from its EFI partition through the Plymouth
      splash to the desktop. Fix chain: grub-efi-amd64-bin/-signed +
      shim-signed + efibootmgr + gdisk/parted + dosfstools (the killer:
      mkfs.vfat for the FAT32 ESP).
- [x] btrfs default install filesystem (Timeshift atomic snapshots) — verified
- [x] Plymouth branded boot splash — verified on installed system
- [ ] Test matrix: 1 laptop + 1 desktop, Intel and AMD graphics, common Wi-Fi
- [ ] **One real login on real hardware (or an installed VM) before shipping
      the new SDDM theme.** Three things could not be exercised in
      `--test-mode`: PAM's `informationMessage` text (expired password, locked
      account), the Restart / Shut down buttons against real logind
      (`sddm.canReboot`/`canPowerOff` are false in test mode, so they were only
      driven through stubs), and multi-monitor. On multi-monitor the greeter
      logs "Adding view for screen <rect>" per screen and this theme
      deliberately ignores `screenModel` and fills its view — so the form will
      most likely appear on **every** monitor rather than only the primary.
      Sixty seconds on a dual-head machine settles it.
- [ ] Boot timings on real media. Everything measured so far is QEMU/KVM with
      the ISO on an SSD, which models a fast USB 3 stick and not the USB 2
      sticks and 5400 rpm disks this OS targets. In particular the ~13 MB/s
      GRUB initrd read rate is an OVMF figure; real firmware varies widely and
      is often worse.
- [ ] Full-disk-encryption install path verified
- [ ] Secure Boot with enforcing firmware (shim-signed chain ships; test on
      real Secure Boot hardware)
- [x] Live session idle screen-lock disabled (live-config script; installed
      systems keep normal lock behavior)
- [x] Installer menu label renamed to "Install Dagric OS"
- [x] Locales generated (no more terminal locale warnings)
- [x] Windows-switcher hardware/format support: NTFS, exFAT, 7z, laptop
      power profiles, network browsing + thumbnails in Dolphin
- [x] Dagric Welcome: branded offline page describing what Dagric is and the
      promises it makes (verified live). It is **no longer** the first-run
      experience — see Phase 5 — but it is kept and is now reachable from the
      wizard's last screen, the Hub and the launcher.
- [x] Installed GRUB menu branded ("Dagric OS", background, 2s timeout)

## Phase 4 — Distribution infrastructure (only if it goes public)
- [ ] Private signed APT repo for `dagric-*` config packages
      (move the includes/hooks content into versioned .deb packages)
- [ ] CI pipeline: Git push → ISO build → automated VM boot test
- [ ] Release signing + checksums, download page, support docs

## Phase 5 — The first hour, and the day after
Everything here ships on both editions. The bet: the free edition wins on the
first hour, and nobody pays for a step-up they never found.

- [x] **Set Up Dagric** (`dagric-firstrun`) — a real six-step first-run wizard
      replacing the Firefox welcome tab: light/dark, accent, wallpaper, text
      size, taskbar layout, and bringing files over from Windows. Steps the
      machine cannot act on are never shown. Every choice applies live, and a
      header **Undo my changes** button restores what the owner started with.
      Re-runnable from the launcher and the Hub.
- [x] **Plain-English app names** (`dagric-app-names`) — the launcher says
      Files, Terminal, Photos, Document Viewer, Task Manager. Regenerated into
      `/usr/local/share/applications` after every apt transaction, so the
      rename survives KDE point releases instead of silently reverting. The
      upstream names stay in `Keywords=` and remain searchable.
- [x] **Dagric Manual** (`dagric-manual`) — 94 offline pages, one per
      application and per `dagric-*` tool, searchable by the Windows name.
- [x] **Text Size** (`dagric-display`) — 100%–200% scaling with a 20-second
      undo that runs in the shell rather than in the dialog it protects, plus a
      night light on fixed hours. First-login auto-scale corrects the two
      panels KWin 6.3.6 gets wrong.
- [x] Working X11 rescue session — `plasmax11.desktop` had always been offered
      at the login screen with no `kwin_x11` behind it.
- [x] **Check This PC** (`dagric-hardware-check`) — a read-only, unprivileged,
      offline hardware report run from the live USB *before* the install: Wi-Fi
      chip named in plain words and whether its firmware is on the disc, GPU
      and bound driver, Secure Boot state parsed out of the EFI variable
      properly, per-drive layout and a plain-English BitLocker block, RAM/CPU
      against a stated minimum, UEFI vs legacy BIOS. Never prompts for a
      password; mounts and unlocks nothing. On the live desktop next to
      *Install Dagric OS*; in the launcher and the Hub afterwards.
- [x] The Hub gained **Check this PC**, **Accessibility** and the **user
      guide** (which had no entry anywhere but the wizard's last screen), and
      is fully translated. 31 rows free / 34 Pro.
- [ ] File-content search: Baloo is a decision still owed (see EDITIONS.md)
- [ ] One pass of all of the above on real hardware, not a stubbed harness

## Phase 6 — Accessibility, and languages
Both are procurement gates in the markets this OS is aimed at, and both are
free-edition features. Everything below ships on both editions.

- [x] **A screen reader that speaks** — `orca` + `speech-dispatcher-espeak-ng`,
      with `0530-accessibility.hook.chroot` re-checking the whole chain on the
      built image and failing the build if a link is missing.
- [x] **Menu entries for it.** Debian's `orca` package ships no `.desktop` file
      at all, so searching the launcher for "screen reader" or "narrator"
      returned nothing on a stock build. Two entries now exist, with Windows
      vocabulary in `Keywords=`.
- [x] **Meta+Alt+S** bound explicitly in skel (KGlobalAccel's defaults are
      compiled enums and could not be confirmed — so it is asserted, not
      assumed).
- [x] **High Contrast style + colour scheme**, authored and measured: 160 pairs,
      worst 7.22:1, re-measured at build time against a 7:1 bar. Free, and
      carrying no `EDITION=` line on purpose.
- [x] **Accessible boot entry on the live ISO** (`dagric.a11y=1`) — the one
      place a blind owner can get in unaided, because the live session autologs
      in. Built by copying the normal live entry so it cannot drift from it.
- [x] **Both QML tools made readable and keyboard-operable** — roles, names,
      states, roving focus in the grids, a focus ring that survives being drawn
      on a photograph, runtime-derived text contrast, and text-size scaling.
      Found by running them, not reading them: reversed tab order on every
      screen, Return doing nothing on any button, 2.56:1 white-on-blue in light
      mode, and a 20-second auto-revert that was a WCAG 2.2.1 Level A failure.
- [x] **The offline HTML audited and fixed** — skip links on all 95 manual
      pages (the manual had none), named landmarks, a real label on the search
      box, an off switch for the bare `/` shortcut, and 97 colour pairs
      measured across three stylesheets with zero failures.
- [x] **An Accessibility section in the shipped guide** (EN 301 549 12.1.1),
      which claims only what is installed and states what does not work.
- [x] **Five languages for the shell tools and launcher entries** (de, fr, es,
      pt_BR, it) on a committed gettext catalogue, with build-time drift gates.
      The user guide and the welcome page ship in all six.
- [x] **The live-locale defect fixed** — `0150-locales.hook.chroot` used to
      clobber `/etc/locale.gen`, so both mechanisms that give an owner a
      non-English system silently failed.
- [ ] **Hear it.** Nothing above has been through a live AT-SPI tree — WSL has
      no accessibility D-Bus. Owed before any accessibility claim is made
      commercially: `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 accerciser` against both
      QML tools on the built image, and one pass with Orca and the mouse
      unplugged. Confirm Meta+Alt+S actually fires.
- [ ] **Native review of the translations.** They are machine-generated and every
      `.po` header carries `X-Dagric-Review-Status: second-model-reviewed;
      back-translation-verified; no-native-speaker-pass` — reviewed by a second
      model and checked by blind back-translation, which is not the same thing
      as read by a native speaker, and is why this item is still open. No language may be advertised
      until at least the tier-one strings are cleared — see EDITIONS.md.
- [ ] **Repaint the two default colour schemes.** `DagricLight` and
      `DagricDark` inherit Breeze accents that fail 4.5:1 in several places
      (WCAG 1.4.3). A deliberate brand decision, not a bug fix to slip in.
- [ ] **A manual page for Check This PC.** The manual has a page per app and
      this tool has none — the one tool a prospective buyer runs first.
- [ ] **Publish a minimum specification.** `dagric-hardware-check` asserts one
      (3500 MB RAM, 25 GB disk) that nothing the project publishes states, so a
      customer can be told "below the minimum" by a number they cannot find.
- [ ] **Translate the QML chrome and `dagric-hardware-check`'s output.** Both
      are still English inside an otherwise translated product. The QML needs
      `qsTr()` plus `lupdate`/`lrelease`; note both files are called `main.qml`
      and would share the translation context "main".
- [ ] **The login screen's ~10 strings.** "Other user", "Restart", "Shut down",
      "Caps Lock is on" and the rest of `usr/share/sddm/themes/dagric/Main.qml`
      are English. The clock and the long date are the exception and are
      already correct in every locale — they come out of Qt's own locale rather
      than a format string. `metadata.desktop` deliberately omits
      `TranslationsDirectory` rather than advertise a directory that does not
      exist; that key goes in at the same time as the `.qm` files.
      Watch for the trap that cost a render here: `Qt.formatTime(d,
      Locale.ShortFormat)` **silently ignores the locale in every locale** —
      that overload takes a `Qt::DateFormat`, and `Locale.ShortFormat == 1 ==
      Qt.ISODate`. Use `Date.toLocaleTimeString`/`toLocaleDateString`.
- Not achievable, recorded so it is not re-attempted: **the login screen cannot
  host a screen reader** (SDDM publishes no AT-SPI bus its Qt greeter joins),
  and **slow keys do not exist on the Wayland session** (no KWin plugin;
  `kaccess`'s XKB path reaches XWayland only). Section 508 502.4(B) must be
  reported as *Does Not Support*.

## Explicit non-goals (bloat guard)
Custom kernel, custom package manager, forked desktop environment, rolling
release, full Debian mirror. Debian does the heavy lifting; we maintain the
delta. The moment we violate this, we've become the thing we're against.
