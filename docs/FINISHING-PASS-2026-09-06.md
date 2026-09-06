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
- 12 desktop-controller tests passed with mocked compositor/service calls.
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
