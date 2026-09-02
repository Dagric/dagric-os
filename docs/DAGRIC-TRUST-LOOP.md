# Dagric Trust Loop

Dagric's product promise is: **make the computer feel new, keep it working,
explain important changes, and always provide a way back.** This document maps
that promise to code that exists now and separates it from future architecture.

## Implemented now

| Promise | Current mechanism | Proof boundary |
|---|---|---|
| Detect this machine | Hardware Check, Adaptive Pipeline, Support Mode hardware passport | Local detection is labelled separately from Dagric Lab verification |
| Improve it safely | Approved Pipeline actions and explicit Twin canaries | Bounded action list, PSI guards, expiry, quarantine and local-only evidence |
| Explain changes | Rewind receipts plus Support Mode's aggregate Pipeline/Twin/Rewind history | No filenames, commands, application identifiers or journal scraping |
| Provide a way back | Btrfs/Snapper Rewind and recovery handoff | Restore points are explicitly not called backups |
| Protect personal files | Kup on Dagric Desktop; Borg/Vorta policy pack where available | "Configured" never means a restore has been proven |
| Move into Dagric | Read-only Windows discovery and resumable non-overwriting migration | Application replacement mapping and credential migration remain future work |
| Ask for help safely | `dagric-support preview`, `audit`, `json`, and explicit local `export` | Export is allow-listed, never uploaded, mode 0600, and refuses overwrite |
| Look like one product | Dagric Flow Obsidian/Frost, SDDM and Obsidian Pulse | Static artwork and upstream KDE interfaces preserve old-PC performance |

## Support Mode contract

Support Mode does not attempt to collect everything and remove secrets later.
It constructs a small report from an allow-list. It includes OS/kernel versions,
non-unique hardware classes, boot/root storage state, recovery readiness, and
aggregate Dagric-controlled history. It excludes serial numbers, stable machine
fingerprints, usernames, home paths, Wi-Fi data, browser or clipboard data,
commands, documents, credentials, tokens and unfiltered journal lines.

The default command is preview. Nothing is uploaded. `export` uses exclusive
creation, refuses an existing file, and writes a 0600 `.tar.gz` containing only
`report.json` and the human-readable preview.

## Recent-request audit

1. **Adaptive per-machine pipeline:** implemented as a conservative policy
   compiler. It detects capabilities, selects only approved actions and keeps
   invasive tuning out of the default path.
2. **Dagric Twin:** implemented for one bounded launch-prefetch experiment. It
   retains a candidate only after a local p95 gain of at least 5%, quarantines
   regressions, expires decisions and stores only hashed application keys.
3. **Rewind and recovery:** implemented with a privileged allow-listed
   controller, Snapper receipts, free-space guards, locking and Polkit. It still
   needs power-loss, ENOSPC and physical restore drills before release claims.
4. **Dagric Flow:** implemented as the Obsidian/Frost token system, wallpaper,
   selectable style, KDE schemes and matching SDDM surface. Horizon Bar, Home
   launcher and Plymouth continuity remain separate future slices.
5. **Gaming ambition:** Steam/Proton, GameMode, MangoHud, Wine/Bottles and the
   per-launch pipeline exist. Anti-cheat and Windows kernel-driver compatibility
   cannot honestly be promised for every Steam game.
6. **Trust architecture:** Support Mode now joins detection, protection and
   change explanations. Transactional dual-root updates, a Permission Center,
   Store Trust Cards, signed UKIs and ring rollouts remain roadmap projects.

## Release truth

Source contracts and simulations can pass without proving hardware. Dagric is
not ready to claim transactional updates, verified backups, universal game
compatibility, broad hardware verification or automatic failed-boot rollback
until the ISO, VM, power-loss and physical-hardware matrices pass. This limit is
part of the product promise, not an inconvenience to hide.
