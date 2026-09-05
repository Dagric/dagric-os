# Private Pro build resumed September 5

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
