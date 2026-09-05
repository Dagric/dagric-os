# Dagric onboarding and beta continuation — 5 September 2026

## Account and evidence status

- User reports completing checklist items 1, 2, 3 and 7. These are reports,
  not substitutes for candidate-bound test results.
- GitHub billing block is cleared for Actions: rerun of 33983133474 completed
  successfully. It tests the older remote revision, not this new UI payload.
- GitHub lists CLOUDFLARE_R2_AUDIT_TOKEN, created 2026-09-05T19:24:27Z. Its value
  was not retrieved or printed. A dedicated GET-only workflow now tests actual
  storage API access without upload credentials. Passing GETs alone cannot prove
  absence of broader token permissions. The policy was then inspected in the
  signed-in Cloudflare dashboard: the new active account token has exactly
  Workers R2 Storage Read, restricted to this account. No policy edits were made.
- The lab displayed the old setup window clipped to the right, with the text
  size action opening another application. This is direct observation of the
  reported UX failure, not a successful installation/reboot acceptance test.
- Physical computer models, candidate hashes and results have been requested.
  Do not mark Secure Boot, accessibility or multi-user tests passed by inference.

## Implemented in source

1. First run is a normal maximized window. KWin owns work-area geometry instead
   of a one-time centering calculation and a fullscreen-to-windowed transition.
2. First-run layout choices are limited to the existing Classic and Centered
   bottom-panel designs. Selection queues a layout until Finish; cancellation
   leaves the existing panels alone. All other layouts remain in Dagric Looks.
3. Wayland text-size trials stay inside setup. A separate unprivileged controller
   owns the 20-second rollback, acknowledges real scale readback, preserves each
   screen's old scale, rejects settings leaving less than 800×600 logical space,
   and retains the existing login rescue record when restoration fails. Late
   confirmation cannot resurrect an expired trial. X11 still clearly identifies
   changes that take effect at the next sign-in; it does not pretend to preview.
4. Shared display locking prevents the first-run controller, dedicated Display
   tool and login autoscaler from taking ownership of the same pending trial.
5. Graphite/obsidian setup surfaces and a deep-red primary accent; disabled
   navigation is visibly subdued. The desktop dark palette is neutralized too.
6. A package-owned org.dagric.desktop global theme now binds the color scheme,
   consistent DagricModern icons, wallpaper, startup splash and initial bottom
   panel. A real splash entry delegates to the shared Dagric implementation.
   The desktop hook no longer modifies upstream Breeze package files.
7. The initial menu pins real existing Hub, Guide, Settings, Software, Recovery,
   browser and file-manager entries. This is KDE's supported launcher with
   Dagric defaults, not a newly implemented assistant or custom launcher.
8. All five translation catalogs contain the new prompts: 668 translated
   messages each, no fuzzy or untranslated messages at the time of this pass.
   Seven obsolete external-window/immediate-layout prompts were removed after
   the full build preflight caught them. The wizard-string check is now in CI.
9. The first new image contains tools 1.1.20, branding 1.1.10 and desktop
   defaults 1.1.9. A follow-up advances tools to 1.1.21 to make Appearance's
   Undo fallback use the same Dagric global theme as setup. This follow-up is
   not present in the a6fdd9b6 image identified below.

## Source-distribution engineering

Live storage audit run 33989821819 succeeded against source 564119b. The read-only
API can inspect both staging and the live Free bucket: staging has r2.dev off and
no custom domains; the live bucket has no enabled public domains. Website/Free
origin/Pro-worker hold checks passed. No storage or website configuration was
changed. Separate dashboard policy inspection confirmed the single read-only
R2 permission; this was not inferred from GET success.

`tools/prepare-source-distribution.py` combines fresh actual-image extraction
with current full-cache/source-lock verification and produces a private,
non-authorizing object-transfer plan. It performs no network requests, writes
no public release records, accepts no detached passing report, and refuses an
existing output. Per-source original filenames and shared objects are retained.

The real frozen 20e24dd0 candidate passed: 1,862 source identities and 6,010
unique objects. Private output:

`out/private-source-candidate-20e24dd0-20260905/source-distribution-plan.private.json`

SHA-256: `ceb58c8c254b17dcbe5911153d7ad4ffa536f4cd0a35d5001df601b2ced94c27`.

This is meaningful integration progress, NOT completion of source distribution.
Authenticated historical source provenance, reviewed coverage/build information,
delivery/retention terms, full-byte remote readback and shared public promotion
gates remain. The new desktop payload needs new candidates and new exact maps;
the old source lock must never be relabeled as covering these UI changes.

## Verification and remaining scope

The controller's 17 offline tests cover trial/keep/revert/expiry, mixed display
baselines, rejected sizes/commands, interrupted-trial ownership, symlinks and
failed restoration. Three exercise real process/pipe lifetimes and a real
20-second watchdog with only monitor I/O replaced by fixtures. Qt 6.8.2 tests
exercise navigation gating and layout previews;
800×600, 1366×768 and 1920×1080 checks assert Next and Keep controls are on screen.
Generated QA images were inspected. Source-delivery integration has four new
real ISO/SquashFS fixtures (nine total integration tests); no downloaded code
is executed by them. One test binds both Undo implementations to the packaged
Dagric theme. The four config packages build locally. Broader source,
shell, JavaScript, concept, icon and locale checks pass.

GitHub source-quality run 33990394680 passed both fast-gates and the Debian 13
desktop-interface job at commit 0e15578. The later one-line Appearance fallback
change has its own local regression and shell checks; it is not covered by
that earlier run.

## Fresh image and live desktop evidence

- Private Free build completed successfully from a6fdd9b675d7b6ffcb5e1e394a42158bb36561b8.
- Image: `/var/tmp/dagric-private-free.BALCBQ/source/out/dagric-os-1.0-amd64.iso`.
- Bytes: 1,999,503,360.
- SHA-256: `18858d38856db8c3bc7436b36b16da25b1e0ba35c82db58d728ba5c95a21f945`.
- Native lab run: `149a0a3d16344a698903092724c54f2f`, started 20:38:12 UTC.
- Viewer: `http://localhost:6081/vnc.html`.
- The previous run e36e5e1382ec4e548919c179fa00d488 was stopped through the
  guarded lab entry point. Its disk and logs were preserved.
- Observed the actual Dagric splash (D mark and red progress), then the
  red/black desktop with one bottom panel. This is boot-to-live-desktop proof,
  not an installed-system reboot or Secure Boot result.
- Opened Set Up Dagric from the launcher. Its initial window fits the work
  area. Autostart timing/reliability is not yet established by this observation.
- Actual Wayland 100% → 125% trial stayed in the wizard; Keep and Revert stayed
  visible and navigation was disabled. An unconfirmed trial restored 100%.
  A second trial accepted with Keep retained 125% and re-enabled navigation.
  At this display resolution 150% was safely disabled.
- Selecting Centered on the taskbar page at 125% changed only the preview;
  the wizard and existing panel stayed in place with Next visible.
- Finish then closed the wizard and applied the Centered bottom panel. The
  Super key opened the launcher. No optional applications were selected.
- Initial launcher showed browser, Settings, Files and Software favorites but
  not the new Hub/Guide/Recovery pins. Do not count the configured favorite
  list as a delivered live behavior: its first-load import still needs work.

The follow-up uses Plasma's supported `kicker-extra-favoritesrc` Prepend
setting, consumed inside `portOldFavorites`, instead of a late applet write.
Existing favorites are not re-imported or overwritten. New accounts no longer
receive the obsolete launcher-branding autostart that restarts plasmashell;
the command remains available for older profiles. The removed template is
recoverable in Git. Versions become branding 1.1.11, desktop defaults 1.1.10
and tools 1.1.21. This change still needs its own fresh image/first-login check.
Upstream implementation:
https://github.com/KDE/plasma-workspace/blob/Plasma/6.3/applets/kicker/plugin/kastatsfavoritesmodel.cpp

The single-output live checks do not replace installation/reboot testing,
multi-monitor hotplug, accessibility review or physical acceptance. This lab
has no guest network or sound and uses legacy BIOS.

Still to implement/validate from the expanded brief: the simpler privacy and
recovery onboarding steps, explicit Familiar/Modern copy, automatic appearance
scheduling, a comprehensive Hub state model, consent/undo-aware Assistant,
unified reversible performance modes, optional profile meta-packages, update
channel/rollback reliability and ordinary-user hardware tests. Do not advertise
these as newly delivered by this pass. Keep the existing Debian/KDE base;
adopt Mint/MX usability ideas rather than mix distribution repositories.

## Recommendation on security (item 4) and beta (item 6)

Keep Debian stable and its authenticated security updates. Prioritize reachable
browser, container-runtime, printer and privilege-boundary findings by actual
exposure; raw tracker totals are not exploit counts. Do not suppress findings
or move the whole system to an unstable repository merely to obtain a green
report. For unfixed optional components, prefer deferring them from the beta or
keeping their services disabled with explicit documented limitations.

A free beta is a reasonable next public milestone, but it is still software
distribution. Source/notices and applicable third-party redistribution and
branding terms still apply. Beta labeling does not resolve modified-Firefox
permission or substitute for missing source delivery. Publish a scoped beta
only once its actual candidate meets those obligations and its security and
installation acceptance criteria. Keep paid checkout and current binary holds
until the applicable gates pass; never synthesize qualified-human approvals.

Primary reference for the startup default ordering:
https://github.com/KDE/plasma-workspace/blob/Plasma/6.3/startkde/startplasma.cpp

Mozilla distribution policy:
https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/
