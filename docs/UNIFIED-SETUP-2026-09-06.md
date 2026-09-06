# Dagric setup integration and Finish repair

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
  wide Welcome illustration. Logo and text remain stationary. Motion stops at
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
- 17 scale/theme controller tests.
- 21 Qt UI tests, including Free/Pro layouts, compact windows, 150% UI size,
  visible text-size selection, live-only installation, actual artwork motion,
  stationary wordmark and reduced-motion preferences.
- Setup hook exercised in isolated Free/Pro fixtures; all seven packaged panel
  scripts executed against a simulated Plasma API, with success and injected
  widget failures. These simulations do not certify the live compositor.
- New strings translated in five locales. Entry comments explicitly identify
  machine translation and pending native-speaker review, not human approval.

The previous VM remained running on the account page during source work. Its
existing test disk and unfinished form were not discarded. New image build and
live acceptance results will be recorded below after they actually happen.
No public release, physical hardware, Secure Boot, licensing or recovery
acceptance is implied by these source/UI tests. GRUB's boot menu remains static.
