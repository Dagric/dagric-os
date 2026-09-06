# Dagric setup integration and Finish repair

Current revision: `79b5cd868e52fcaf6c9e2ae1dcfab4033ff1dda6`. The first images
documented below are superseded by the bounded display-startup repair. They remain on
disk as test evidence, not the recommended candidates.

## Changes

- Text-size cards display a checkmark and “Selected”, plus a percentage and
  sentence preview. Unknown scaling is not shown as a misleading 0% selection.
  X11 waits for a successful configuration write and states that the change
  takes effect at the next sign-in. Wayland retains its timed Keep/Revert trial.
- Finish is deferred until the QML child exits successfully. A private FIFO
  keeps queued state in the parent shell; Close/crash does not install queued
  apps, and repeated Finish messages cannot apply twice.
- Taskbar scripts build replacement panels before retiring old panels. Script
  exceptions remove the newly created panels and preserve the previous ones.
  Failure reports do not announce successful setup.
- Page changes no longer crossfade two sets of readable text over each other.
- The existing Aperture artwork gently moves during Plasma startup and on the
  wide Welcome illustration. Logo and text remain stationary. Ambient motion stops at
  the final startup stage, while hidden, or with reduced motion enabled. No
  artificial boot delay, shader, network request or per-frame Canvas repaint.
- Free and Pro share one live desktop entry: **Set Up Dagric**. It offers
  **Install Dagric** and **Try it first**. Install hands off to Calamares only
  after the welcome window closes. Calamares retains account/password creation,
  partition selection and summary; an explicit install confirmation is enabled.
  Personalization runs for the installed user after reboot. Installed sessions
  cannot launch this installation path.

This is a unified entry and guided handoff, not an embedded replacement for
Calamares. Trial personalization is not automatically copied to a new account.
Passwords do not enter the QML protocol, receipts or setup state files. Existing
Calamares administrator-group policy and Free/Pro storage floors are unchanged.

## Evidence and limits

- 9 real-shell/FIFO regression cases: Finish ordering, duplicate messages,
  cancellation, crashes, failed layout, live-only install, X11 success/failure,
  invalid layout input.
- 23 scale/theme/query tests, including real lock contention, clean exit
  while waiting, ignoring premature requests, killing a stalled query that
  ignores TERM, rejecting partial results, and preventing lock inheritance.
- 22 Qt UI tests, including Free/Pro layouts, compact windows, 150% UI size,
  visible text-size selection, live-only installation, actual artwork motion,
  stationary wordmark and reduced-motion preferences.
- Setup hook exercised in isolated Free/Pro fixtures; all seven packaged panel
  scripts executed against a simulated Plasma API, with success and injected
  widget failures. These simulations do not certify the live compositor.
- New strings translated in five locales. Entry comments explicitly identify
  machine translation and pending native-speaker review, not human approval.

The previous VM remained running on the account page during source work. Before
testing the new image, the blank account form was inspected, then that run was
stopped using the lab's identity-checked Stop action. Its disk and logs were
preserved; the in-memory form was not preserved. New tests use fresh lab disks.
No public release, physical hardware, Secure Boot, licensing or recovery
acceptance is implied by these source/UI tests. GRUB's boot menu remains static.

## Clean candidate and additional checks

Source candidate: `a97085c222610eea3e299d0b576d536e07944eb0`.
The full source-only audit and source/catalogue regeneration check passed in
`/var/tmp/dagric-unified-setup.MYz3ML/source`; logs are adjacent to that checkout.
The real Qt QML executable (without a privileged backend) also exited cleanly
after both Finish and Install, rather than merely emitting a protocol message.

The panel implementation was checked against KDE's
[scripting API](https://develop.kde.org/docs/plasma/scripting/api/) and its
[Plasma 6.3 implementation](https://raw.githubusercontent.com/KDE/plasma-workspace/Plasma/6.3/shell/shellcorona.cpp).
The latter sends a D-Bus error reply for a failed script; setup waits for that
reply rather than treating fire-and-forget delivery as success.

## Pro image and observed desktop behavior

- Built from `a97085c222610eea3e299d0b576d536e07944eb0` in
  `/var/tmp/dagric-private-pro.MXAs8b/source`.
- Verified candidate:
  `D:\Dagric-releases\20260906-unified-setup\Pro\dagric-os-pro-1.0-amd64.iso`.
- SHA-256: `5a524dce9dc27a18a33e6d47e8bb5017a85ba571dd0cc35d665b1904d7861a19`.
- Header-only preparer cleanup was applied to a separate copy, followed by
  payload manifest verification, exact source-file checks, package ownership
  checks, account/confirmation configuration checks, and BIOS/UEFI boot-entry
  readback. These are structural checks, not physical boot certification.
- The Windows copy was independently hashed against that verified candidate.
- Native lab run: `fa6d63c7d7374656bc410145da8765bd`.

Observed in the running Pro desktop:

1. Welcome identified Pro and offered Install Dagric / Try it first.
2. The 125% Wayland trial changed actual desktop scaling. Allowing the countdown
   to expire restored 100%. A second trial kept at 125% showed Selected 125%
   and the sentence preview afterward. Keep/Revert remained visible in the
   compact trial; choice cards and the sample are hidden during that compact
   confirmation to reserve room for its safety controls.
3. Choosing Classic did not move the setup window or replace the panel early.
4. Finish closed setup and applied the Classic bottom panel. The desktop stayed
   responsive, and its Set Up Dagric shortcut reopened the welcome screen.
5. Install Dagric closed welcome and opened the correctly titled Pro installer.
   At 125% scaling, Location, Keyboard, Partitions and Users remained readable
   with bottom navigation visible. The fresh virtual disk was selected only as
   an uncommitted installation preview. Users displayed full name, login name,
   computer name, password and confirmation fields; Next was disabled while
   required information was missing. No account password was entered and no
   installation was started in this run.

The startup artwork's motion was verified in Qt rendering tests, not captured
from the live boot (the desktop was already ready when inspected).

## Free build dependency repair

The first Free build from `a97085c` failed safely in the new installer validation
hook because `python3-yaml` was not installed. Pro already included that library
transitively. Commit `3e0ddddab083641b923ac1319f4d73d38ef4a90d` declares it
explicitly for both editions and adds a regression check. All three setup
integration tests passed. The previous failed build was preserved.

A fresh Free build uses this corrected commit. Its full source-only audit passed
at `/var/tmp/dagric-unified-free.qCvOrz/source-audit.log`; the build completed
successfully in `/var/tmp/dagric-private-free.XOfROn/source`.

- Verified candidate:
  `D:\Dagric-releases\20260906-unified-setup\Free\dagric-os-1.0-amd64.iso`.
- SHA-256: `8167cb1fcbd7ad1acec94f6a9d5c2d941345a94d451c5365e9f937204e662bad`.
- The same payload/source/ownership/installer/boot-structure readback passed;
  `python3-yaml` installation was explicitly checked inside the image.
- The Windows copy's SHA-256 matched. Pro and Free must not be represented as
  having identical build commits.
- Pro run `fa6d63c7d7374656bc410145da8765bd` was stopped after cancellation of
  the untouched account form. Its disk and logs were preserved.
- Fresh Free lab run: `44a5bfb6cd8643298afe6e3ac2654d1e`. The branded startup
  artwork appeared and transitioned to the Free welcome screen. Text-size
  selection/sample were visible, but all sizing controls remained disabled.

## First-login display lock repair

The Free live test exposed a startup race shared by both editions. The login
autoscaler and the welcome worker use `display-trial.lock`; the worker used a
nonblocking acquisition without handling contention. Its process had exited,
and no status file existed, so the welcome UI could not enable its controls.
Starting the helper later worked. A regression test holding this same lock
reproduced `BlockingIOError: [Errno 11] Resource temporarily unavailable` against
the original worker.

Commit `52a26d27b0ce6878998d4174c8e76297c86b54fb` waits without stealing the lock,
publishes a waiting state, discards premature requests, and uses an increasing
status revision when the controller becomes ready. Closing setup or terminating
the worker while waiting exits without changing the display. The interface
explains the wait and keeps navigation available; private worker diagnostics
are retained while setup is open instead of silently discarded. One new notice
was machine-translated in all five locales and marked for native-speaker review.

The failure-reproduction test now passes, as do all 20 controller/theme tests
and 22 Qt tests. Source/catalogue regeneration passed with 679 translated
messages in each locale. Full fresh builds and live checks for this final
revision are recorded below when complete.

Free run `44a5bfb6cd8643298afe6e3ac2654d1e` was stopped after these diagnostics;
its disk and logs were preserved. Neither diagnostic run installed the system
or created an account.

## Extended cold-boot finding and bounded-query repair

Both revision-2 builds from `52a26d2` completed successfully after the full
source and locale audits in `/var/tmp/dagric-setup-r2.QGCg6l`. The Free image was
also read back against the exact source, package ownership, payload checksums,
installer account sequence and fresh-user autostart template.

Its verified SHA-256 was
`587aad1a6658c4b3056b01505ba6bcde40d8c870b90ab2b98f783fdc018136f4`, copied to
`D:\Dagric-releases\20260906-unified-setup-r2\Free\dagric-os-1.0-amd64.iso`.
That candidate is superseded too; do not treat its build success as a passing
initial-display acceptance result.

Free run `d444726afc9641f18c077843d72b64fe` correctly showed the new waiting
message, but the wait persisted. Guest `lslocks` identified login autoscaling
PID 1900 as the owner; `pstree` showed its read-only `kscreen-doctor -o` child,
PID 1952, had stalled. A separate query completed normally at 1280x800. Ending
only that identified stuck query with TERM immediately released the lock:
the waiting message disappeared and the Normal and Bigger cards became usable,
without restarting setup or the desktop. This was a diagnostic intervention,
not a clean cold-boot pass. The run disk and logs were preserved when stopped.

Commit `79b5cd868e52fcaf6c9e2ae1dcfab4033ff1dda6` bounds shared KScreen reads to
five seconds plus a one-second forced-termination grace, discards partial output
on failure, closes the inherited display-lock descriptor for those queries,
and bounds first-login retry count. Welcome's direct display reads are bounded
as well. The controller's outer read allowance accommodates the child's timeout.
The regression suite includes a fake query that ignores TERM and prints partial
monitor data: it is killed, its data is rejected, and the next query succeeds.

All 23 scale/theme/query tests passed. The same 22-test QML UI is unchanged from
the preceding passing run. Catalogues were regenerated and rechecked, with 679
translated messages per locale and human-review caveats unchanged. Final fresh
image and cold-boot results follow after they have actually been verified.

The initial revision-3 build pair in `/var/tmp/dagric-setup-r3.xZwN2V` passed
source checks but stalled repeatedly on Debian CDN downloads. Fresh requests
to another CDN address succeeded. The exact owned build session was terminated
after verifying its process list; all build directories were preserved. A fresh
pair in `/var/tmp/dagric-setup-r3.IQZAYo` uses a build-scoped WGETRC with 15-second
timeouts, four attempts and DNS-cache disabling. This does not change the OS
image's network settings or disable any signature/certificate verification.

## Final candidate images

Both final images were built from `79b5cd868e52fcaf6c9e2ae1dcfab4033ff1dda6`.
The Free build in the restarted pair rejected a failed `base-files` download;
its fresh Free-only retry completed successfully. Pro completed successfully
in the pair. Do not treat the pair's overall nonzero status as a Pro failure
or its failed original Free attempt as the final Free artifact.

- Free source/build: `/var/tmp/dagric-private-free.LfSRPA/source`.
  Log: `/var/tmp/dagric-setup-r3.IQZAYo/free-retry-build.log`.
- Pro source/build: `/var/tmp/dagric-private-pro.NSGuoX/source`.
  Log: `/var/tmp/dagric-setup-r3.IQZAYo/pro-build.log`.
- Free: `D:\Dagric-releases\20260906-unified-setup-r3\Free\dagric-os-1.0-amd64.iso`.
  SHA-256: `97a1af1bc3af93dd9e457b68f3c9c2c0dd21ae76912ff5d2f6b87430966a43c6`.
- Pro: `D:\Dagric-releases\20260906-unified-setup-r3\Pro\dagric-os-pro-1.0-amd64.iso`.
  SHA-256: `2dd51dad72931c7fba13f661933fabbc9874bb69fba517bfa87949fc508e2b4f`.

Each image's payload manifest, twelve exact modified/source-related files,
package ownership, edition branding, storage floor, installer confirmation,
account sequence and fresh-account setup were read back successfully. The
new-user template contains setup autostart but no completion stamp; installation
unpacks the pristine squashfs before creating the user. Optional preparer
metadata was cleared on copies while essential metadata and BIOS/UEFI boot
structures were preserved. Both Windows copies matched their verified hashes.
`verification.json` is alongside each Windows image, with `release_approved:false`.

Final Free run `09326fa8e9824ac7a8def7bc3d6a81fb` cold-booted from the verified
image. Its sizing controls became ready without terminal commands or manual
intervention. Bigger 125% was applied and kept; the Selected checkmark,
percentage, sample text and navigation were visible. Choosing Classic did not
move the setup window or replace the panel early. Finish closed setup cleanly,
then applied the Classic panel; the desktop remained responsive. No optional
apps were selected in this run.

Reopening **Set Up Dagric** and choosing **Install Dagric** opened the Free
installer. Welcome, Location, Keyboard, Partitions and Users remained usable at
125%. A proposed erase-disk plan was selected only for the new isolated 64 GiB
lab disk, solely to reach Users; no installation was submitted. The user form
contained full name, login, computer name, password and repeat-password fields.
Automatic login was unchecked and Next was disabled with required fields blank.
The untouched account form was cancelled. The lab stopped this exact run and
preserved its disk and logs at 2026-09-06 06:45:44 UTC.

Final Pro run `1d10ae575f3c47aab08a885dd8944588` started at 06:46:12 UTC from
the verified Pro image on a new isolated disk. The branded startup artwork
transitioned to the Pro welcome screen. Text controls became ready on this cold
boot without terminal intervention. Bigger 125% applied, Keep/Revert were
visible, and keeping the size displayed the Selected checkmark, 125% label and
sample sentence. Classic selection did not replace the current panel early or
move the setup window. With no optional apps selected, Finish closed setup,
applied the Classic panel, and left a responsive desktop with **Set Up Dagric**.

Reopening Pro setup and choosing Install opened the correctly branded Pro
installer. Welcome, Location, Keyboard, Partitions and Users were inspected at
125%. Only a proposed partition plan on the new lab disk was selected to reach
Users. The full-name, login, computer-name and password-confirmation fields were
visible; automatic login remained unchecked and blank required fields blocked
Next. No credentials were entered and no installation was submitted. The form
was cancelled, then Set Up Dagric was reopened for the user.

The final Pro lab remains available at <http://localhost:6081/vnc.html> while
these processes are running. It has no guest network, audio or host-drive
sharing. The final images and their hashes are also listed in
`D:\Dagric-releases\20260906-unified-setup-r3\README.md`.

### Final scope boundary

This pass verifies the setup UI, image contents and installer handoff, not a
completed installation or new-user login after reboot. No password was entered,
installation was executed, or encryption/update/rollback acceptance completed.
Physical hardware, Secure Boot, online app installation, sound and qualified
rights approval remain separate gates. The exact-file image comparison is not
a substitute for the full corresponding-source distribution gate. The working
tree still contains unrelated pre-existing legal/report changes; these were
preserved rather than represented as a coherent release commit. No GitHub push
or public download deployment was made by this setup-repair pass.
