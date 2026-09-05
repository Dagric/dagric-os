# Dagric Design Language implementation plan — 2026-09-04

This plan turns the finished-product brief into independently releasable work.
Its purpose is to make Dagric recognizable during ordinary use—not only at boot
or in first-party dialogs—without forking Plasma, weakening accessibility, or
claiming work that has not been built and tested.

## Status rules

- **Existing foundation** means the capability was already present before this
  remediation. Some items have prior candidate-ISO or hardware evidence, but
  their evidence must still be refreshed for the next release candidate.
- **Completed in this remediation** means the current source tree has the
  change. These changes are **not a released product claim** until a new Free
  and Pro ISO is built and passes the gates in this document.
- **Next phase** means planned work only. It must not appear on the website,
  screenshots, comparison tables, or sales copy as a shipped feature.

## Product contract

Dagric Design Language (DDL) is the system-wide contract for color, type,
spacing, shape, motion, icons, sounds, language, and reversible interactions.
Dagric Flow is the default visual theme built with that contract.

The intended identity is graphite and soft-black surfaces, warm readable text,
controlled crimson for state and progress, restrained blur, 8–14 px radii, and
short purposeful motion. The blue-to-mint Dagric mark remains the master logo;
crimson is the default desktop accent, not a reason to recolor every surface.
User-selected accents and layouts remain first-class choices.

The product must stay familiar, fast, and repairable. It must not clone Windows
or macOS, expose an assistant in every surface, add decorative animation, hide
advanced Plasma controls, or substitute branding for working system behavior.

## 1. Existing foundation before this remediation

The repository already provides a meaningful product layer:

- Branded Plymouth boot, login splash, custom SDDM theme, Calamares branding,
  and a clean default desktop path. Advanced boot remains available when an
  owner needs diagnostic messages.
- Dagric Appearance with visual choices, style/layout previews, state capture,
  Keep/Revert, and automatic timeout recovery for risky visual changes.
- Seven layout choices, multiple wallpaper collections at 1080p and 4K, three
  Dagric icon-style families, user avatars, Dagric color schemes, and a branded
  application launcher icon.
- A substantial first-run experience, friendly application names and launcher
  shortcuts, an offline guide, localized strings, and accessibility shortcuts.
- Dagric Rewind and snapshot plumbing, update and security helpers, hardware
  checks, gaming helpers, GameMode integration, and a themed installer.
- Upstream KDE/Plasma remains underneath as a supported fallback instead of an
  unmaintainable desktop fork.

The limitation is equally important: the everyday shell is still largely
upstream Plasma. Dagric does not yet own a complete desktop theme, lock screen,
launcher, quick-control panel, Settings front end, Machine dashboard, sound
theme, cursor, or opinionated Dolphin profile. Several existing first-party
tools are large shell/dialog flows rather than one coherent application family.

## 2. Completed in this remediation

The current working tree establishes a safer, more consistent baseline:

- The shipped `flow-tokens.json` contract is now DDL schema version 2. It names
  the palette, 8/10/12/14 px radii, Noto typography, 44 px minimum touch target,
  46 px primary panel, 150/180/240 ms motion targets, reduced-motion behavior,
  surface rules, plain-language rules, and third-party artwork boundaries.
- Crimson continuity now reaches first-run, Appearance, Rewind, the login
  splash, Plymouth progress, and Calamares selection state while preserving the
  official blue-to-mint logo.
- Classic's primary panel and Duo's lower panel use the 46 px DDL target.
  The previously exposed “Eleven” layout is now presented as “Centered”; its
  internal identifier is retained for compatibility.
- `Meta+Space` invokes KRunner while retaining KDE's `Alt+Space` and `Alt+F2`
  shortcuts. This delivers the taught search chord without pretending that a
  custom Dagric Search interface already exists.
- The second application-catalog entry is now “Dagric Picks,” with original
  generic artwork and a curated-guide description, so it is not confused with
  Discover's actual “Software Store.”
- Game-platform integration copy and policy now distinguish bundled open-source
  compatibility tools from owner-requested proprietary services. Storefront
  clients are not represented as bundled Dagric software, helper artwork must
  be original unless use of a mark is authorized, and compatibility is not
  guaranteed.
- Source gates now validate the DDL contract and visual continuity. The game
  platform policy gate checks package boundaries, installer consent, notices,
  disallowed claims, and the approved generic Gaming artwork.

This remediation is source-complete only. It still needs fresh ISO, VM,
installed-system, physical-hardware, and live-footage evidence before release.

## 3. Next safe implementation phases

Each phase must be shippable by itself. A new surface starts opt-in, keeps an
upstream escape route, and becomes the default only after the phase gates pass.

### Phase 0 — freeze and baseline the candidate

Before adding another shell component:

1. Build Free and Pro images from one identified commit.
2. Save checksums, package manifests, source-gate results, and the exact DDL
   token version beside the artifacts.
3. Boot the current design through live session and installed session; record
   the known gaps rather than fixing them opportunistically during testing.
4. Capture one continuous reference run from power-on through desktop, plus
   Appearance apply/revert and recovery entry.

**Acceptance:** both images build reproducibly enough to produce the expected
edition contents; no failed mandatory source gate; boot/install evidence is
attached to the candidate; all remediation items above can be observed or
inspected in that exact image.

### Phase 1 — own the everyday shell foundation

Create a package-owned `org.dagric.desktop` look-and-feel package and a Dagric
Plasma desktop theme. Move shell visuals out of build-time Breeze patching and
into explicit, removable Dagric packages. Cover panel backgrounds, menus,
tooltips, task indicators, dialogs, OSDs, notifications, calendar surfaces,
and the transition from splash to desktop. Keep Plasma and KWin APIs as the
implementation boundary; do not fork either project.

The first release of this phase should use upstream applets with Dagric visual
assets and layout defaults. Live window previews, grouping, tray ordering, and
clock modes may be configured, but behavior must not be rewritten merely to
make the theme look custom.

**Acceptance:** a logo-free screenshot of the idle desktop, open-app state,
tray popup, notification, and calendar reads as one Dagric family; focus,
hover, active, disabled, warning, and error states are distinct without relying
on red alone; upstream Breeze can be restored from a TTY or recovery launcher;
Plasma restart, logout/login, suspend/resume, and two-display hotplug do not
lose the panel or leave an empty shell.

### Phase 2 — Dagric Settings and Dagric Machine

Build a small, categorized Dagric Settings front end for the common paths:
System, Devices, Network, Personalization, Applications, Accounts, Privacy &
Security, Accessibility, Power, and Dagric. It should call supported system
interfaces or deep-link to the correct KDE control module. “Advanced Settings”
must always open full KDE System Settings. Do not reimplement every KCM.

Build Dagric Machine as a separate read-mostly dashboard for processor,
graphics, memory, storage, network, update state, recovery readiness, battery,
and sensors that the machine can actually report. Unsupported or unreliable
measurements must say “Unavailable” or “Not reported”—never invent a health
percentage. Privileged actions remain separate, explained, and confirmed.

**Acceptance:** Settings search finds common-language requests such as “make
text bigger,” “Wi-Fi,” “dark,” and “storage”; every tile reaches a working
destination offline; no page silently changes a privileged or destructive
setting; Machine output matches independent system commands on the test
hardware; absent sensors degrade cleanly; both apps are fully keyboard usable
and readable by Orca.

### Phase 3 — signature launcher and quick controls

Create a search-first Dagric launcher for applications, files, settings,
calculator results, clipboard/history where enabled, recent items, and system
actions. Core results must work locally without AI or a network connection.
KRunner remains callable as a fallback during rollout.

Create a unified Dagric quick-controls surface for network, Bluetooth, sound,
brightness, battery/power state, Night Light, Do Not Disturb, screenshots, and
Settings. Use the existing NetworkManager, BlueZ, audio, power, and Plasma
services; do not create a second source of truth. Preserve direct access to the
individual upstream controls for power users.

**Acceptance:** the launcher opens, accepts input, returns first useful results,
and launches the target under both X11/Wayland paths supported by the release;
search remains useful when indexing or networking is unavailable; no query is
sent off-device without explicit opt-in. Quick controls reflect external state
changes within a reasonable UI interval, never expose saved secrets, and
recover to upstream applets if the Dagric process crashes. Cold-open and input
latency must be measured on the project's low-end reference machine before the
components become default.

### Phase 4 — login and lock-screen continuity

Extend the full Dagric look-and-feel package to own the lock screen instead of
assuming the SDDM login theme also covers it. Provide clock/date, account,
password, keyboard layout, accessibility, power, battery/charging, permitted
media controls, and privacy-safe notification count. Network controls may be
added only after their authorization and secret-handling behavior is reviewed.

**Acceptance:** unlock works after cold boot, lock, suspend, lid close, password
failure, keyboard-layout change, and screen-reader activation; private message
content is hidden by default; no blur or animation creates an unreadable or
blank frame; failed Dagric QML falls back to a usable upstream lock screen.

### Phase 5 — Files defaults and safe actions

Keep Dolphin, but ship an explicit Dagric profile: clean places/devices sidebar,
large readable folder icons, visible search, useful status/storage information,
and sensible Home folders. Add a small reviewed set of context actions such as
Open Terminal Here, Resize Copy, Convert, and Compress only when inputs are
quoted safely, the output is predictable, and failure messages are plain.

**Acceptance:** new and upgraded accounts receive the intended defaults without
overwriting an owner's existing Dolphin layout; removable storage, network
locations, hidden files, long names, non-ASCII names, and low-disk failures are
tested; every custom action handles spaces and hostile filenames safely;
uninstalling Dagric defaults leaves Dolphin functional.

### Phase 6 — sound, cursor, and core icon completion

Ship an original, restrained sound family for notification, success, warning,
error, and device connection, with no startup sound by default. Ship a Dagric
cursor in Normal, Large, and Extra Large sizes with high-contrast visibility on
light and dark surfaces. Continue the icon family in priority order: first-party
apps, folders, tray states, settings categories, then broader application
coverage. Never redraw a third-party mark into a Dagric asset.

**Acceptance:** every source asset has authorship and license records; sounds
are normalized, brief, and non-startling; mute and reduced-sensory settings are
honored; pointer hotspots and scaling are verified at 100%, 150%, and 200%;
missing icons fall back cleanly rather than becoming blank placeholders.

### Phase 7 — discoverable workspaces and bounded profiles

Expose Plasma virtual desktops as a simple two-workspace default, then allow
owners to name workspaces and opt into a visual overview. Add saved workspace
arrangements only after application restore behavior is reliable.

Implement profiles as declarative bundles of already-supported settings:
Classic, Modern, Focus, Creator, Developer, and Game. A profile may choose a
style, layout, notification state, and supported power preference. It must not
claim to control fans, performance, or hardware when the machine exposes no
supported control. Developer and game software remain optional installs, not a
reason to ship every tool to every owner.

**Acceptance:** profile preview lists every proposed change; Apply is atomic or
rolls back; the previous state can be restored after logout/reboot; unsupported
actions are skipped with an explanation; window/workspace restore never opens a
privileged app or replays sensitive content without consent.

## 4. Cross-phase accessibility and rollback requirements

These requirements block release for every phase:

- Keyboard-only operation, visible focus, logical tab order, screen-reader
  labels, and `Meta+Alt+S` screen-reader access are tested from a fresh account.
- Body text targets at least 4.5:1 contrast and non-text controls at least 3:1;
  meaning is never communicated by color alone.
- UI works at 100%, 125%, 150%, and 200% scaling, with 44 px minimum touch
  targets where touch mode applies, without clipped translated text.
- Reduce Motion replaces travel/scale with a short fade and avoids decorative
  animation. High Contrast and System Sounds Off remain usable choices.
- Any display, layout, theme, panel, or profile operation captures the previous
  state before mutation. It offers Keep/Revert, automatically reverts after a
  short timeout where loss of visibility is possible, and has a documented TTY
  or recovery reset command.
- Existing user configuration is migrated conservatively. New defaults apply
  automatically only to new accounts; upgrades require an explicit owner
  choice when applying them would replace custom state.

## 5. Build, boot, VM, and live-footage gates

The following evidence is required for a release candidate, not optional polish:

1. Run the full source audit plus the focused DDL, concept, icon, translation,
   manual-coverage, release-rights, and game-platform policy gates.
2. Build both Free and Pro ISOs from the release commit. Archive checksums,
   logs, edition manifests, and the source-offer/reproducibility information.
3. Boot the newest image in BIOS and UEFI paths. Verify Plymouth → SDDM → live
   desktop and Plymouth → installed SDDM → first run → installed desktop. Normal
   boot must not leak avoidable Debian/live-build text; diagnostics remain
   reachable through the advanced boot path.
4. Test a full Calamares install, reboot, login, lock/unlock, update, snapshot,
   restore entry, suspend/resume, audio, networking, scaling, and fallback shell.
   The live-session installer shortcut must not remain on an installed desktop.
5. Record continuous screen footage from the running system. No still-image
   substitution, duplicate simultaneous desktop videos, browser/VNC/VM chrome,
   persistent banners, artificial camera shake, hidden errors, or edits that
   imply a feature worked when it did not. Show pointer movement, responsive
   UI, transitions, and the completed result from beginning to end.
6. Review the footage at normal speed with sound on and off: text must remain
   readable, frame pacing stable, cursor motion deliberate, narration aligned
   with the action, and the audience able to understand the feature without
   unexplained package, ISO, or virtualization terminology.
7. Before performance, display, touch, multi-monitor, power, recovery, or driver
   claims, repeat the relevant drill on physical hardware. Software-emulated
   QEMU footage proves flow, not hardware speed or compatibility.

## 6. Legal and source-release gates

Every release must also pass these boundaries:

- Include only software and assets with a recorded license and redistribution
  basis. Preserve package copyright notices, publish exact manifests, and keep
  the corresponding-source offer and delivery path current.
- Keep proprietary storefront clients and content out of the ISO unless written
  redistribution permission has been obtained and reviewed. Optional installs
  must be owner initiated, identify the provider and governing terms, and ask
  before changing the machine.
- Use Steam, GOG, Epic, Amazon, and other platform names only to describe
  compatibility. Use original generic Dagric artwork unless written permission
  or a clearly applicable brand policy authorizes the exact mark and context.
  Never imply partnership, certification, sponsorship, or endorsement.
- Make compatibility claims version- and title-specific where necessary;
  anti-cheat, online services, launchers, and provider policies can change.
- Run `tools/check-release-rights.py` and
  `tools/check-game-platform-policy.py` in every quality, build, and release
  workflow. A passing script supplements—not replaces—human IP review and
  qualified legal review for commercial distribution.
- Review every new sound, cursor, icon, wallpaper, screenshot, font, imported
  theme, and community contribution before it enters a sold image. Executable
  Plasma/QML themes and layouts require code review; an unreviewed theme store
  is not a safe default.

## 7. Definition of done

A phase is complete only when its source, translations, accessibility labels,
offline guide, fallback path, rollback path, and automated checks are committed;
Free and Pro images are rebuilt; live and installed VM sessions pass; continuous
footage is audited; hardware-dependent claims have physical evidence; and legal
and source-release gates are green. Until then, the feature remains a candidate
and marketing must describe it as planned or in testing.

The sequence is deliberate: establish a package-owned everyday shell first,
then give people coherent Settings, Machine, launcher, and quick controls; only
then extend identity into lock, Files, sound/cursor, and advanced profiles. That
is the shortest safe path from “Debian with a theme” to a recognizable Dagric
product without creating a fragile desktop fork.
