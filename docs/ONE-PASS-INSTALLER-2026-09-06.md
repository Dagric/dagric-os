# One-pass setup and desktop controls — 6 September 2026

## Scope

This change replaces the previous welcome-to-installer handoff with desktop
personalization inside Calamares, shared by Free and Pro. It is not a release
approval. The currently running VM and all earlier images/disks are preserved.

## Changes

- Live **Set Up Dagric** starts the installer directly. Disk selection, desktop
  choices, account creation and the final review are in one installer window.
- The **Your desktop** page previews light/dark colors, Familiar/Centered
  taskbars, three icon families, three application-text sizes and three existing
  wallpapers. A visible check mark identifies each selection. Returning to the
  page retains the choices. The final summary uses readable profile names.
- A strict allowlist validates the profile before partition execution. After
  the installer creates the account, a Dagric Python job writes preferences into
  that target account, checks ownership, rejects symlink directory traversal,
  and writes the first-run completion marker last. It never reads passwords.
- Initial Plasma layout consumes those preferences without resetting an
  existing user's panels. Fonts are application text sizes, not copied monitor
  configurations. Recovery of interrupted installations is not yet accepted.
- Guided storage uses Btrfs and existing zram defaults, hiding unnecessary swap
  and filesystem dropdowns. Manual partitioning remains advanced; nothing is
  preselected, encryption stays available, and erase/confirmation warnings stay.
- English storage labels explain whole-system space versus per-user allowances.
  Keeping another operating system still requires a space decision; that cannot
  safely be removed. Other locales retain upstream labels pending translation.
- **Desktop & taskbar** groups appearance, widgets, panel controls, text and
  display size. Actions use fixed, unprivileged commands. The native Plasma
  widget browser and panel editor remain upstream interfaces, not rewritten
  implementations. Third-party widgets are explicitly identified as code.
- Default/Familiar/Centered panels have a 48-pixel floating presentation.
  Existing owners are not forcibly migrated. A new pinned settings shortcut
  uses an existing Dagric icon, not a new imitation of another product's logo.
- All three icon themes now inherit color-aware Breeze icons instead of forcing
  dark-theme symbols into light mode. Existing third-party trademarks and
  the existing Dagric artwork are preserved; no new AI graphic was produced.

## Tests so far

- Eight target-profile tests, including 108 combinations, ownership, invalid
  inputs, symlink rejection, privileged-account rejection and simulated write
  failure. FIFO, oversized and malformed config input is also rejected without
  logging private file contents. Fixtures are directories, not real accounts.
  The QML choice labels and IDs are also checked against the backend allowlist.
- Six setup/panel integration tests, including Free/Pro hook idempotence,
  validation before partition jobs, apply after account creation, and existing
  panel preservation. Plasma scripting is mocked in these tests.
- Static installed-icon scanning found Lynis had no icon. The image hook now
  fills that empty field with Breeze's existing security symbol, preserving
  any upstream icon and desktop actions. The new settings app also joins the
  existing per-app X11 window-identity mechanism; Wayland's generic QML app ID
  remains a documented limitation of the shared QML runtime.
- 29 Qt tests (22 existing plus 7 installer test lifecycle/cases), zero failures.
  Installer previews reviewed at 820×660 and 520×420, including 150% text.
- Existing Finish regression: 9 passing; display/theme regression: 23 passing.
- Icon audit: 32 Dagric icons × 9 sizes × 3 families = 864 valid PNGs.
- The complete source-only audit passed after the final polish, including
  offline-help coverage, panel contracts, shell/Python/JavaScript checks and
  localization drift checks. This is not ISO or release acceptance.

The real Calamares 3.3.14 executable was also exercised headlessly inside the
isolated package-complete Free build root: the shipped QML page selected Light,
Familiar, Old school, 150% text and Arctic. Calamares carried that exact profile
through GlobalStorage, ran the shipped Dagric validation job, and a test-only
assertion job verified receipt. The test exits normally and loads no partition,
account-creation, mount, unpack or bootloader job. Its finished page has reboot
disabled. The same test also passed in the Pro build root. Fixture evidence:
`/var/tmp/dagric-onepass-free.PrgxHFIy/build/chroot/tmp/dagric-calamares-check-7_um3i0p`
and `/var/tmp/dagric-onepass-pro.qLvijl6J/build/chroot/tmp/dagric-calamares-check-f_bah6i2`.

The above are code/fixture checks, not proof of a completed install and reboot.
New candidate builds and actual Calamares/Plasma acceptance must be recorded
below before saying these changes are available in the running VM.

## Implementation references

Checked against Calamares v3.3.14 and Plasma 6.3 source, matching the candidate
package series. The QML chooser uses the supported single-selection
`config.packageChoice` interface with legacy custom handling, not a patched
upstream binary. The new job descriptor uses Calamares's `type: job` format.

- [Calamares chooser configuration](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/packagechooser/packagechooser.conf)
- [Calamares QML chooser](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/packagechooserq/PackageChooserQmlViewStep.cpp)
- [Calamares partition configuration](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/partition/partition.conf)
- [Plasma scripting](https://develop.kde.org/docs/plasma/scripting/api/)
- [Plasma 6.3 panel properties](https://github.com/KDE/plasma-workspace/blob/Plasma/6.3/shell/scripting/panel.h)

## Remaining acceptance

Actual new-image boot, interactive installer navigation, install/reboot into the
selected desktop, encryption, updates and rollback. Human translation and
accessibility checks remain necessary. This task does not clear source-delivery,
rights, physical hardware or other release gates.

## Build checks and retries

The first isolated Free build stopped at the launcher-localization gate; the
new entry was added with explicitly unreviewed machine translations in five
languages. No gate was bypassed. A subsequent build passed that check but wget
stalled on an HTTP bootstrap package. HTTPS retrieval of the same official
Debian file succeeded. Only that build's verified process tree was stopped;
its source, logs and incomplete directory were retained. Bootstrap now uses
HTTPS with the host's normal certificate and archive-signature verification.
The active VM was not stopped or modified.

The broader audit also required a real offline-help route for the new control
page; `app-desktop.html` now explains its controls. The panel design contract
now matches the intentional 48-pixel floating layout. Native Calamares testing
identified an existing slideshow timer using an undefined property; it now
uses the installed Qt 6 slideshow's `activatedInCalamares` property.

## Storage and preservation

The final image source is commit `8ce310a781542440eee17f0ac4fd0d6c1fda2ef6`.
An intermediate Free build at `a6521f3b1433ce435849a0bc1aeb5c37482cb371`
completed and passed payload, package-ownership and installer-order verification.
It does not include the last two icon fixes and is not the final candidate.
The superseded Pro build at that earlier revision was cancelled during
compression; its unfinished chroot was removed after checking its processes
and unmounting only its own build mounts. Source, cache, package inventory and
logs remain. Reconstructable `/usr` payloads from the earlier failed Free/Pro
build roots were also removed; their Calamares fixture logs remain.

To protect space on D:, three older Windows archives were copied to
`C:\Users\1248n\Downloads\Dagric-preserved-releases`, verified file-by-file by
SHA-256 and size, then removed from their old locations: the 5 September
Obsidian build and the 6 September unified-setup/r2 builds. The r3 archive stays
at its existing D: path. No VM disk was deleted, moved or replaced.
The final build jobs were paused for this relocation and then resumed.
Verification outputs now go on C: rather than allocating further copies on D:.

Direct Linux-to-Windows ISO output later failed with an incomplete copy. Final
verification therefore used an 8-GiB bounded temporary Linux RAM filesystem,
one edition at a time. Windows copied the verified ISO and evidence from that
staging area, then independently checked the complete destination SHA-256.
Only after successful delivery was temporary RAM staging unmounted. This did
not restart WSL or the active VM.

## Final private candidates

Both final builds completed from clean clones of
`8ce310a781542440eee17f0ac4fd0d6c1fda2ef6`, with `dagric-tools` 1.1.24.
The later verifier/documentation changes did not build these images.

| Edition | Delivered Windows image | SHA-256 |
| --- | --- | --- |
| Free | `C:\Users\1248n\Downloads\Dagric-one-pass-candidates\Free\dagric-os-1.0-amd64.iso` | `619ade5c0924aaff9f5f54e9e2b2a6c14404f13420ec76a26b0d3f26b85c64f7` |
| Pro | `C:\Users\1248n\Downloads\Dagric-one-pass-candidates\Pro\dagric-os-pro-1.0-amd64.iso` | `360ff34bea796fd502ac66dbfef0a43d4d7b6f5d1d34c60ae384bc697add4b48` |

Sizes: Free 1,999,831,040 bytes; Pro 3,901,816,832 bytes.
Each delivery contains `verification.json`, the original payload checksum
manifest and the selected audited files. Optional preparer metadata was cleared
in a new copy; the built input images and all checked payload bytes were
preserved. BIOS/UEFI boot structures are present; this is not proof of booting.

Read-back verification passed for all ISO payload checksums, the listed exact
source files and Dagric package ownership records, installer validation before
partitioning, personalization after account creation, and the retained account,
encryption and final-confirmation controls.

Actual Calamares handoff tests also passed in both final build roots:

- Free: `/var/tmp/dagric-onepass-free.4YOiLPoZ/build/chroot/tmp/dagric-calamares-check-cq301vrc`
- Pro: `/var/tmp/dagric-onepass-pro.Hrp0Jhkf/build/chroot/tmp/dagric-calamares-check-a4tyq0gh`

Static icon resolution found zero unresolved entries across all three icon
styles: 76 visible application entries in Free, 107 in Pro. This checks asset
presence, not the appearance of every icon in a running compositor.

**Not established:** new-image interactive boot, a full account-creating
installation, reboot, encryption operation, updates/rollback or physical
hardware acceptance. The existing r3 VM was left running because no answer was
received to the unsaved-work question. These are private test candidates, not
a release approval or a public beta publication.
