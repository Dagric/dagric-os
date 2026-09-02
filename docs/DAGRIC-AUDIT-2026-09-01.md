# Dagric OS engineering audit — 1 September 2026

## Executive verdict

Dagric is a broad, coherent developer candidate with real differentiators:
Windows migration, approachable hardware guidance, a carefully assembled
gaming stack, offline help, Family Limits, and the Rewind recovery model. The
current source tree implements all 20 audited concepts and both editions build
and boot in virtual machines.

It is **not ready for public release this week unless the physical-hardware,
update and destructive-recovery gates close**. Virtual installed-system tests
now prove the principal disk and firmware paths, but cannot prove GPU drivers,
Wi-Fi, suspend, Btrfs exhaustion, accessibility speech, payment entitlements,
or recovery after a real power interruption.

## What was audited

The audit maps product promises to commands, launchers, packages, policies,
hooks, documentation, CI, edition manifests, signed boot files, and retained
runtime evidence. `tools/check-concepts.py` is the executable map: it currently
reports **20/20 implementation contracts present**. This number means the
feature wiring exists; it is deliberately not called 20/20 release readiness.

The current artifacts are:

| Edition | Bytes | SHA-256 |
| --- | ---: | --- |
| Free | 2,251,653,120 | `bcd2999e19e68658dc95cbc75005cd5351743f01e69babd0481ab03e8d7ea8f6` |
| Pro | 4,152,623,104 | `2f7632d896b93c5e28a45e3f21dd3572e0c3eb99870933aefd95bc559d513cb6` |

They remain audit artifacts under `out/final-pass`; nothing was signed,
uploaded, sold, deployed, or substituted for a public release.

## Measured results

- 58 JSON documents parse.
- 23 Python sources compile.
- Two Polkit policies deny inactive/remote callers, require administrator
  authentication for active users, and point to helpers shipped in the image.
- Eight GitHub Actions references are pinned to immutable 40-character commits.
- No tracked private-key marker, sensitive-looking credential path, merge
  debris, or unsafe Polkit default was found.
- Five mutation tests prove the source gate rejects broken JSON, invalid Python,
  unsafe/missing Polkit helpers, unpinned Actions, credentials, private-key
  material, and unresolved merge markers.
- 119 shell entry points parse and pass ShellCheck's error-level rules.
- 20 JavaScript/ES-module files pass Node's parser.
- Five translation catalogs are present and exactly up to date.
- 26 deployed site pages pass placeholder, link, sitemap and tunnel checks.
- All 317 Debian trixie package names resolve; package lists contain no percent
  sign capable of truncating live-build's parser.
- Rewind passes seven core and eight privileged-controller tests.
- Both artifact hashes verify, edition markers are correct, common packages are
  present in both images, and Pro-only gaming/security/VM/backup packages are
  absent from Free and present in Pro.
- Both ISOs contain a Microsoft-signed shim first hop and Debian-signed GRUB.
- Fresh evidence from the exact final images reaches first run under Free BIOS,
  UEFI and Microsoft-keyed Secure Boot, and reaches the correctly branded Pro
  first-run screen under UEFI.
- Free completed a fresh offline UEFI erase-disk install to a 50 GiB virtual
  disk (300 MiB FAT32 EFI plus 49.71 GiB Btrfs), passed bootloader installation,
  rebooted to SDDM, accepted the new user's login, and opened installed-system
  first run. Snapper's root configuration exists and its setup service is active.
- That installed Free system passed **47/47 root runtime assertions**:
  edition marker, Btrfs/Snapper setup, UEFI mount and signed packages, firewalld,
  AppArmor, unattended updates, browser privacy JSON, Rewind and Family privilege
  boundaries, recovery/migration/accessibility/storage tools, all five locale
  catalogs, Free/Pro package separation, APT consistency, intentional package
  verification differences only, and no failed system services.
- Pro completed a fresh offline UEFI erase-disk install to a 50 GiB virtual
  disk, rebooted through the installed Plymouth path, reached the Pro-branded
  SDDM login and accepted its new user's credentials. Its installed-system
  auditor passed **65/65 assertions**, including the complete Wine/Wine32,
  DXVK32, GameMode, MangoHud amd64+i386 and Lutris stack; active OpenSnitch;
  VM, security and backup packages; safe disabled-by-default service policies;
  APT/package integrity; and zero failed services.
- The exact final Free ISO completed a fresh encrypted UEFI installation. Its
  plan and resulting disk contain a 300 MiB FAT32 EFI partition plus a 49.71
  GiB `crypto_LUKS` root containing Btrfs. Reboot presented the pre-boot unlock,
  the correct passphrase reached SDDM, and the created account logged in. A
  clean shutdown followed by read-only NBD inspection reconfirmed GPT, VFAT,
  LUKS metadata and the passphrase with `cryptsetup --test-passphrase`.
- The exact final Free ISO also completed a fresh legacy-BIOS installation to
  a blank 50 GiB virtual disk. It rebooted from the installed disk, reached
  SDDM, accepted the created account, opened installed-system first run, and
  passed **45/45 root runtime assertions** with no failed services.
- Those two installed disks predate only the final Rewind wrapper's
  authentication-status propagation change. The installer and package payloads
  are otherwise the same, and direct SquashFS inspection proves that both final
  ISOs contain the corrected wrapper. The exact final images separately pass
  their fresh firmware boot and combined artifact gates.
- The repeated stress harness runs source/security, concept, mutation and both
  Rewind suites in fresh processes and finishes with all broader parsers:
  the two final post-fix runs passed **308 gate executions across 60 rounds**.
- The final combined artifact gate passed both hashes, edition/package split,
  edition markers, Microsoft-shim/Debian-GRUB signatures, plausible sizes and
  four fresh exact-image boot evidence sets.

The preserved installed-system reports are
`out/final-pass/reports/free-bios-installed-audit.txt`,
`out/final-pass/reports/free-uefi-installed-audit.txt` and
`out/final-pass/reports/pro-uefi-installed-audit.txt`.

## Findings by severity

### Release blockers

1. **Physical Secure Boot installation remains unproven.** The executable VM
   matrix now passes Free legacy BIOS, Free and Pro UEFI, and exact-final Free
   encrypted UEFI install/reboot/login paths. A physical Secure Boot installation
   still requires fresh install/reboot proof on retail firmware.
2. **No physical-device matrix exists for this candidate.** At minimum cover a
   representative AMD, Intel and NVIDIA PC, including networking, audio,
   Bluetooth, suspend/resume, battery where applicable, updates and recovery.
3. **The candidate is from a dirty working tree.** Generated media and unrelated
   user changes are present. A release must be rebuilt from a reviewed commit.
4. **Family Pack commerce is intentionally nonfunctional.** Its page and Worker
   still contain price, machine-cap, Stripe and documentation placeholders. The
   site correctly excludes it; do not publish or sell it until the entire
   entitlement flow is tested.

### High-risk runtime gaps

1. **Rewind needs destructive-environment testing.** Test cancellation,
   interrupted start/finish, reboot with an open session, snapshot boot,
   documented rollback, and actual Btrfs data/metadata/qgroup exhaustion. The
   new 1 GiB guard catches obvious low space but cannot model Btrfs ENOSPC.
   Authentication cancellation on the installed audit ISO first exposed an
   unfriendly raw Polkit “Not authorized / incident reported” dialog. The first
   source fix then exposed a second defect: `refresh()` continued after pkexec
   failed and promoted an empty temporary catalog, so the GUI falsely reported
   timeline damage. Source now propagates the helper status before any rename,
   and both final SquashFS payloads contain that correction; a live installed
   cancellation/recovery sequence remains required.
2. **OpenSnitch is not yet a proven security boundary.** Validate the configured
   `/tmp/osui.sock` control path and per-machine TLS/key behavior on installed
   Pro before making strong firewall claims.
3. **Forty-one AppArmor profiles remain in complain mode.** Review real workload
   denials before selectively moving them to enforce; globally flipping them
   would trade a marketing number for broken applications.
4. **Full-disk encryption recovery needs deeper fault testing.** Correct-password
   install/reboot now passes; add wrong-password, update, snapshot and
   rescue-media behavior.
5. **Gaming compatibility remains empirical.** The stack is complete, but no OS
   can make publisher-blocked kernel anti-cheat drivers work by copying Microsoft
   drivers. Publish tested results and route incompatible titles to Windows VM,
   dual boot or streaming instead of claiming every Steam game.

### Medium-risk quality gaps

1. Accessibility needs live keyboard, Orca/AT-SPI, large-text, contrast,
   reduced-motion, X11 and Wayland verification.
2. Translation catalogs are structurally complete but need native review and UI
   overflow inspection.
3. Windows migration needs real profiles, BitLocker messaging, interrupted copy,
   Unicode names, symlinks and files larger than 4 GiB.
4. Backup claims need a restore drill; creating a backup is only half the feature.
5. Performance tuning needs reproducible frame-time, idle-memory, cold/warm boot,
   power draw and suspend measurements on physical devices.

## Defects fixed during this audit

1. Added executable contracts for every audited product concept.
2. Added mutation coverage for every major failure family in the source/security
   checker and included it in CI.
3. Added a built-artifact auditor for checksums, edition package separation,
   edition markers, signed EFI contents, plausible sizes and retained boot proof.
4. Added one-command audit and repeated stress harnesses.
5. Corrected the stale installer comment that still described the root-caused
   2026-08-03 UEFI helper failure as unknown.
6. Excluded a malformed literal `%SystemDrive%` host-cache directory from Git
   and both build-copy paths. The user copy was not deleted.
7. Fixed the mutation suite's Windows-Git/WSL safe-directory boundary after the
   stress environment exposed it.
8. Fixed Rewind's administrator-authentication cancellation path after the fresh
   installed-system test exposed the raw Polkit error dialog.
9. Fixed Rewind's follow-on empty-catalog promotion after live cancellation
   testing proved the first fix suppressed stderr but still opened a false
   “timeline damaged or incomplete” state.
10. Added a FAT evidence-disk installed-system auditor and used it to preserve
    a 47/47 Free UEFI runtime report outside the guest.
11. Completed a Pro offline install/reboot and preserved a 65/65 root runtime
    report outside the guest.
12. Corrected the installed auditor's Multi-Arch query after it joined the two
    healthy MangoHud architecture statuses into one false failure, and narrowly
    recognized the intentional Pro SDDM badge rewrite while still rejecting all
    other package drift.

## Week plan

1. Freeze and review the intended source; keep unrelated/generated media out of
   the release commit.
2. Install/reboot/update Free and Pro on disposable BIOS and UEFI disks; add
   encrypted UEFI and Secure Boot cases.
3. Break Rewind deliberately on those installs and preserve the recovery proof.
4. Run the physical hardware, gaming and accessibility matrices.
5. Rebuild from the clean commit, verify and sign one manifest, stage privately,
   download it back, compare exact bytes, then make the release decision.

The companion checklist is `docs/DAGRIC-CHECKLIST-2026-09-01.md`; the earlier
artifact and boot record is `docs/WEEK-READINESS-2026-09-01.md`.
