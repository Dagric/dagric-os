# Private Pro build resumed September 5

## Current matching candidate pair

Started at approximately 17:04 UTC (12:04 PM America/Chicago), from committed
source `34aafa1403a65762e2d6e08915a548cb8634cf9e`, pushed to
`origin/codex/release-safety`:

- Free: Debian `/var/tmp/dagric-private-free.9DLEfN`.
- Pro: Debian `/var/tmp/dagric-private-pro.vUYrFJ`.

Each has `source/out/SOURCE_COMMIT`, `build/build.log`, its own build tree and
private `source/out` destination. Both staged `dagric-tools` 1.1.19. The Free
preflight resolved all 316 package names; the simultaneous Pro host-APT refresh
skipped that preflight after update failed, so do not count it as a Pro-specific
pass. Both independently used signed repository metadata in their own build environments.

Free completed successfully at approximately 17:17 UTC: 1,999,503,360 bytes,
SHA-256 `a80187dfdd236c243833de84f7edfe2bfdcc24a0d4aa463fb94d255fc189aaf5`.
Pro failed at a new `0600-pro-edition` assertion. Its administrator policy was
correct, but the assertion wrongly assumed exact YAML whitespace and an inline
group list. A semantic YAML check now replaces that textual assumption. Seven
regressions and the complete revised embedded audit pass against the failed
chroot's actual files without altering them. This attempt has no matching Pro
image; a fresh pair must be built from the corrected commit.

The existing daily follow-up was updated through the app to these two paths;
its video program and post time slots were preserved. It stays quiet on unchanged
state. Keep the PC and desktop app running for local scheduled work.

## Historical failed attempt

Docker Desktop still fails on its dockerInference socket after the confirmed
Windows reboot. The supported native Debian build path is usable through WSL.

Previous candidate: Debian `/var/tmp/dagric-private-pro.23yIyD`.
Source: `4bdc043c6e5e1418d5d173f5fceb792afc4d31ea`.
Build directory: `/var/tmp/dagric-private-pro.23yIyD/build`.
Expected private output: `/var/tmp/dagric-private-pro.23yIyD/source/out`.
Status: failed in `0340-offline-docs.hook.chroot`. The manual's Dagric group
count was stale and five installed application launchers lacked manual routes.
Those source defects were fixed on September 5 and the exact hook passed
against the failed candidate's launcher inventories and corrected documentation.
No new completed image or boot evidence is claimed.

The source check, source-map regression tests, release-workflow tests, updater
tests, adaptive-pipeline tests and locale tests passed. The build resolved all
316 package names, passed Rewind and pipeline gates, and staged all four Dagric
configuration packages. That earlier source had 661 entries per locale. The
corrected source now has 670 entries per locale, including nine new OpenSnitch
messages, with zero
fuzzy, untranslated, missing or extra entries. Native-language review remains
separate from these mechanical checks.

Use `tools/resume-private-pro-build.sh` from Debian for another isolated Pro build,
or pass `free` for a separate companion build from the same committed source.
It builds a clone of committed source and leaves the original `out/` untouched.
The failed candidate predates this launcher addition. Check for running builds
before retrying. The launcher creates a new candidate directory; it does not
wipe a previous build or reuse that build's source identity.

An initial inline WSL launch lost its shell variables at the Windows quoting
boundary. It was interrupted; its temporary `/source`, `/build`, and
`/var/tmp/dagric-resume-pro.MNdsvc` directories remain for inspection. Subsequent
builds use a script file and explicit contained paths.

The existing daily follow-up includes checking this candidate before video work.
Keep release distribution held. Fresh package versions require fresh candidate
inventories and corresponding-source validation; the earlier source map does
not automatically approve a newly built image.
