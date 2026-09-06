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

- The existing native lab is running the earlier r3 image, not the new work.
- Native lab networking is disabled; that backend cannot prove online updates.
- D: initially has only about 10 GiB free. No full build should start there
  without sufficient backing-drive space. C: has about 297 GiB available.
- Unrelated legal/release documentation edits must remain untouched.
- No public publication, release approval or physical-hardware claim follows
  merely from source checks or a working virtual machine.

## Acceptance ledger

Implemented in source (not yet the running VM):

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
  (36 total, including the test lifecycle checks).
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

It has roughly 94 GiB available internally; C: has roughly 201 GiB remaining
after allocation. The existing native VM, its VHD and all test disks are
unchanged. Do not delete or copy this build filesystem while mounted.

Still pending: final candidate build/readback, actual install/reboot/account
creation, encryption, online updates, recovery, real Plasma reset testing,
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

Both editions are built from `faf33b8352bca8da9332200894b45eeceaa50e37`.
Later test/build-tool commits do not change that image-source identity.

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

Pro is building serially after Free in `pro.bsYmNpcB`, using the same exact
source revision and the preserved Free package cache. It is not yet accepted.

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
