# Dagric finishing pass — implementation and acceptance

Requested scope: complete installation/reboot/recovery checks; shorter setup;
persistent responsive preview; integrated panel controls; per-application Qt
identity and accessibility; reversible desktop defaults; safer build scheduling.

## Working order

1. Implement and test the setup and desktop controls without replacing the VM.
2. Add a shared application runner and verify real window identity.
3. Add build locking, preflight space checks and pre-build source validation.
4. Freeze one source revision, build serially, and read back both images.
5. Exercise installation, account creation, reboot, encryption and recovery in
   isolated test disks, retaining logs and explicitly recording unavailable tests.

## Current constraints

- The native lab now runs the verified Free preview described below, not r3.
- Native lab networking is disabled; that backend cannot prove online updates.
- D: initially had about 10 GiB free and now has about 7.9 GiB. No full build
  or installation acceptance should assume that sparse test disks will fit.
- C: has about 198.8 GiB free. The private build filesystem experienced kernel
  resource-allocation/write errors and has been unmounted for inspection.
- Unrelated legal/release documentation edits must remain untouched.
- No public publication, release approval or physical-hardware claim follows
  merely from source checks or a working virtual machine.

## Acceptance ledger

Implemented in source (the Free preview contains these controls, but not the
later private-user-state seed correction):

- Recommended setup with optional customization; persistent preview; consistent
  light/dark card surfaces and point-size-based text; keyboard focus scrolling.
- Integrated selected-taskbar height, edge, length, alignment, floating and
  visibility controls. Illustrations are labeled previews, not actual changes.
- Independent 60-second rollback watcher starts before applying a change.
  A failed apply attempts recovery; unrecoverable failures retain the journal.
- Confirmed desktop-layout reset with private backup, timed revert and durable
  undo. It resets taskbars/widgets/wallpapers, not colors, fonts, scaling,
  applications, accounts or personal documents. Old-session previews are
  archived instead of applying stale panel IDs to another session.
- A PySide6 runner sets the real desktop-file identity for all five Quick apps.
  Fresh images and package upgrades install the same runner aliases.
- Native build lock, Linux plus Windows backing-drive capacity checks, and
  mandatory pre-copy regression/UI validation. Docker builds share a cache lock;
  the Windows launcher has a mutex and backing-drive preflight. Native and Docker
  builds must not be run together; their kernel locks are separate.

Observed checks:

- 30 Qt Quick tests passed, including optional customization and preview
  persistence at 520×420, selection names and keyboard activation.
- Six additional Quick checks passed for native-control request payloads,
  failure handling, reset confirmation and disabling controls without a bridge
  (36 total, including the test lifecycle checks). A later display-numbering
  regression brought the final Qt run to 37 passed, 0 failed, 0 skipped.
- 17 desktop-controller tests passed with mocked compositor/service calls.
  These exercise actual transaction/state-file code, not actual Plasma changes.
- 8 target-profile and 6 setup/panel integration tests passed.
- 6 build guard regressions passed. A real preflight refused Pro on D: (9.9 GiB
  free despite roughly 360 GiB logical WSL space).
- 10 real Qt window identity checks passed: five apps on Xvfb/X11 and five on
  Weston/Wayland. `out/qt-identity-runtime.json` contains observed WM_CLASS,
  desktop-file properties and Wayland set_app_id messages. The production runner
  was unchanged, but its application root pointed at minimal fixture windows.
  This is not installed-ISO or screen-reader acceptance.
- The full source-only audit passed; it does not approve rights or release.

Build storage is an isolated 96-GiB ext4 file on C:, mounted only as build
storage (not a VM disk):

`C:\Users\1248n\Downloads\Dagric-finishing-build-storage.xXCAD82b\build-filesystem.ext4`

`/var/tmp/dagric-finishing-build-mount.oyMtGNsN`

It is a roughly 94-GiB filesystem. It is now unmounted and preserved, after
checking that no process or child mount was using it. No existing test disk
was deleted. Do not delete it or copy it while mounted.

Still pending: replacement Free and completed Pro build/readback, actual
install/reboot/account creation, encryption, online updates, recovery,
screen-reader acceptance, human translations, and physical hardware tests.
Docker Desktop failed to start because of its local dockerInference socket;
no factory reset or global WSL restart was attempted.

References used for implementation:

- https://develop.kde.org/docs/plasma/scripting/api/
- https://doc.qt.io/qtforpython-6/PySide6/QtGui/QGuiApplication.html

## Compatibility review before final candidates

The initial `893bbfb` Free attempt was stopped during bootstrap. Its source and
log remain in `free.gQZta1Os` on the build mount; no ISO was produced and no Pro
build began. Plain IPv6-capable retrieval hung, while the exact official URL
returned HTTP 200 immediately over IPv4. `DAGRIC_BUILD_IPV4=1` now selects a
build-host-only Wget policy with bounded retries/timeouts. It does not alter the
installed OS's IPv6 settings, TLS validation or Debian archive signatures.

Plasma 6.3 source review found that changing a panel edge restores its orientation
defaults, so thickness must be set afterward. Its visibility getter also maps
WindowsGoBelow to `none`; the shared config enum is now read to preserve that
mode in undo. The label is accurately “Allow windows underneath.” Apply and
revert now require acknowledgment and read back real panel properties; widget
minimum thickness is explained rather than silently advertised as the chosen
size. Additional regressions cover these boundaries and bounded recovery files.

## Frozen candidate evidence

Both edition attempts used `faf33b8352bca8da9332200894b45eeceaa50e37`.
Only Free completed. Later commits do not change that image-source identity;
the newest permissions fix requires replacement images.

Free completed successfully in `free.256FAgj9` on the private build mount.
The initial bounded download attempt failed for six bootstrap packages. The
resume used preserved package caches; Debian's normal archive signature and
package checksum verification remained enabled. No old installed filesystem was
substituted for the new source.

- Original ISO SHA-256: `44e5c1305c9357e2277532c210401f9e56ddce81f8e41c538574b9c0a41bd477`.
- Verified metadata-cleaned copy: `d62e00d948f8e204520c58f734bcd4a7cfe9ce5f2114da033464d8b6573473b1`;
  2,018,508,800 bytes. Only the optional ISO preparer header was cleared; payload
  hashes and the original image were preserved. Required notices were not stripped.
- Every payload checksum passed. The listed Dagric source/configuration files,
  package ownership checks, five runner aliases and required PySide6 package
  were read back from the actual image. This is not a complete dependency-source
  distribution audit or a qualified rights approval.
- Actual packaged Calamares passed QML → GlobalStorage → Dagric validation-job
  integration. The test deliberately excludes destructive installation jobs.
  Evidence: `free.256FAgj9/build/chroot/tmp/dagric-calamares-check-zjsc4in4`.
- All five full installed Quick pages rendered using the real runner, packages
  and assets. Synthetic catalogues and an offscreen engine inspection/exit
  hook were used, with no desktop-changing actions. Evidence:
  `free.256FAgj9/build/chroot/tmp/dagric-quick-check-ja901uat`.
  An earlier Rewind fixture omitted its required `ready` field; correcting the
  fixture removed the resulting binding warning without changing OS code.
- The full source-only audit passed again, including security-boundary, source
  delivery gate, website, shell, localization and update/recovery regressions.
  Its source-only mode explicitly does not approve a generated image for release.

Windows delivery, independently rehashed after copying:

`C:\Users\1248n\Downloads\Dagric-finishing-faf33b8-20260906\Free\dagric-os-1.0-amd64.iso`

Pro ran serially after Free in `pro.bsYmNpcB`, using the same exact source
revision and preserved package cache. It failed in the Plymouth hook while
saving `/boot/initrd.img-6.12.107+deb13-amd64`: `sync` reported `Cannot allocate
memory`. The host kernel recorded allocation failures and loop0/ext4 write I/O
errors. No new Pro ISO was produced. A later successful `sync` does not prove
the earlier file contents survived intact. PhotoGIMP's optional download also
failed, so it was not installed in this incomplete root.

The exact private build mount was checked for open consumers and child mounts,
then unmounted without force. Read-only `e2fsck -fn` on its verified backing
file completed all five passes with exit 0. That establishes no detected
filesystem-structure errors, not boot-image content integrity or a cured host
resource problem. The file and build directories are preserved; no automatic
repair, resumed Pro build, global WSL restart or disk deletion was performed.

Copied evidence is under `out/finishing-evidence-20260906`: Pro console/build
logs, the read-only filesystem check, Calamares integration evidence and the
five installed Quick pages' generated results, logs and renderings. Mount and
kernel inspection is recorded in `out/finishing-storage-inspection.json`.

## Fresh Free VM

The Dagric Lab skill stopped only the receipt-identified old r3 processes;
run `1d10ae575f3c47aab08a885dd8944588` and its disk remain saved. Nothing material
was deleted in this finishing pass.

New run `87bb39bb7936400eac886ba8d1ce603f` booted the verified Free hash above.
At 13:44 UTC the browser showed a working desktop and Calamares automatically,
with one sequence containing Partitions, Your desktop, Users, Summary, Install
and Finish. This establishes live desktop/installer startup, not installation.

The fixed native lab remains BIOS-only, offline and without audio/recording.
After staging Free, D: has approximately 7.9 GiB free. That is not sufficient
headroom to assume full Free and Pro installations will both fit. C: build and
delivery space is separate; do not bypass the lab's fixed storage boundary.

### Observed installer and desktop interaction

- Guided disk selection explains whole-drive erasure and advanced custom
  layouts; accounts share free space rather than needing separate partitions.
  The sole target was the fresh 64-GiB `vda` test disk. Btrfs and the encryption
  option were visible. No partitioning, passwords or installation were submitted.
- Recommended/Customize worked inside the installer. Light, Familiar, Classic
  icons and 150% text visibly changed their selected state and the persistent
  preview. Keyboard focus scrolled choices into view without moving the window
  or the real taskbar. Larger text did not launch another Settings application.
- The installer was canceled before account creation. No credentials were
  entered and the test disk remains uninstalled.
- Desktop & taskbar launched as its own Dagric application. It initially
  refused to write its journal: the live account's `.local` and
  `.local/state/dagric` were 0775. `namei -l` confirmed the exact ownership and
  modes. Only those two user-owned directories in the disposable live session
  were changed to 0700; refreshing then loaded actual Plasma panel properties.
- A real taskbar thickness preview changed 48 to 52 pixels and displayed the
  countdown. After timeout, the UI and visible panel returned to 48 pixels.
  A second preview was applied and the settings window was closed with 34
  seconds remaining. The visible panel returned to its original thickness
  before reopening settings; the reopened UI read back 48 pixels. This is
  runtime evidence for that single panel and session, not all hardware.
- Default-layout preview ran after explicit confirmation; Keep enabled the
  saved-layout undo action. Undo last layout reset started another timed preview;
  Keep completed it and restored enabled controls, with the desktop still
  responsive. This is a smoke check on a near-default single-account layout,
  not an exhaustive custom-widget or multi-monitor reset test.

### Corrections after live testing

`0996-private-user-state.hook.chroot` now seeds `.config`, `.local`,
`.local/state` and `.local/state/dagric` as 0700 for future live/installer users.
It checks for symlinks, non-directories and foreign ownership before touching
the named directories. Existing installed user directories are not silently
rewritten; the controller's strict permission guard was not weakened.

The Pro PhotoGIMP hook now requires both successful curl completion and the
exact pinned SHA-256 before unpacking. It uses a unique temporary directory,
bounded connect/transfer timeouts and an explicitly build-only IPv4 option.
A failed transfer leaving a file behind can no longer enter the unpack branch.

Four private-directory fixture tests and four actual download-fragment tests
passed. They are included in the build preflight and source audit. Image
verification now checks the four skeleton directory modes, so the older Free
preview cannot be mistaken for an image containing this latest fix.

The taskbar selector previously displayed Plasma's internal ID (for example,
the only taskbar appeared as Taskbar 2). It now displays ordinal numbering from
1, while application requests retain the real internal ID. The Qt regression
checks that a displayed Taskbar 1 still sends the fixture's real ID 7. The
`dagric-tools` payload version is 1.1.26; the Free preview contains 1.1.25.

The full source-only audit passed after the directory/download changes, and
the separate final Qt suite passed with the label correction. Logs explicitly
exclude generated-image acceptance and qualified release approval.
