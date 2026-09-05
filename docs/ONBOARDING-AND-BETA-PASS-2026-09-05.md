# Dagric onboarding and beta continuation — 5 September 2026

## Account and evidence status

- User reports completing checklist items 1, 2, 3 and 7. These are reports,
  not substitutes for candidate-bound test results.
- GitHub billing block is cleared for Actions: rerun of 33983133474 completed
  successfully. It tests the older remote revision, not this new UI payload.
- GitHub lists CLOUDFLARE_R2_AUDIT_TOKEN, created 2026-09-05T19:24:27Z. Its value
  was not retrieved or printed. A dedicated GET-only workflow now tests actual
  storage API access without upload credentials. Passing GETs alone cannot prove
  absence of broader token permissions; review the configured Cloudflare policy.
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
9. Package versions advance to tools 1.1.20, branding 1.1.10 and desktop defaults
   1.1.9. These are not yet installed on the older frozen candidates.

## Source-distribution engineering

Live storage audit run 33989821819 succeeded against source 564119b. The read-only
API can inspect both staging and the live Free bucket: staging has r2.dev off and
no custom domains; the live bucket has no enabled public domains. Website/Free
origin/Pro-worker hold checks passed. No storage or website configuration was
changed. Token-policy least-privilege review remains separate from GET success.

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

The controller's 12 offline tests cover trial/keep/revert/expiry, mixed display
baselines, rejected sizes/commands, interrupted-trial ownership, symlinks and
failed restoration. Qt 6.8.2 tests exercise navigation gating and layout previews;
800×600, 1366×768 and 1920×1080 checks assert Next and Keep controls are on screen.
Generated QA images were inspected. Source-delivery integration has four new
real ISO/SquashFS fixtures (nine total integration tests); no downloaded code
is executed by them. The four config packages build locally. Broader source,
shell, JavaScript, concept, icon and locale checks pass.

These tests do not replace a new image build, live Wayland scale testing,
installation/reboot testing, multi-monitor hotplug or physical acceptance.

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
