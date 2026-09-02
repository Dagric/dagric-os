# Dagric OS week-readiness record — 1 September 2026

## Decision

The current tree is a **developer candidate**, not a public release. The Free
edition builds and reaches Dagric's first-run desktop in legacy BIOS, UEFI, and
Microsoft-keyed Secure Boot virtual machines. The Pro edition also builds and
reaches its correctly branded first-run desktop under UEFI. Source, package,
privilege-boundary, translation, site, and shell gates are green.

Later in the same audit, both editions completed fresh offline UEFI erase-disk
installs and rebooted from Btrfs. Free passed 47/47 installed-system assertions;
Pro reached its branded SDDM login, accepted the created user and passed 65/65.
The final rebuilt ISOs also have fresh exact-image BIOS/UEFI/Secure-Boot boot
evidence and pass the combined artifact gate. The exact final Free image then
completed both LUKS+Btrfs UEFI and legacy-BIOS install/reboot/login paths, with
the latter passing 45/45 installed-system assertions. Updates, physical
hardware, and destructive recovery remain separate gates.

Do not sign, upload, sell, or describe these images as release candidates yet.
They were built from a working tree with existing uncommitted work, and the
physical-device, installed-system, and remaining Rewind recovery gates below
are not complete.

## Artifacts built from the current workspace

| Edition | Artifact | Bytes | SHA-256 | Result |
| --- | --- | ---: | --- | --- |
| Free | `out/final-pass/free/dagric-os-1.0-amd64.iso` | 2,251,653,120 | `bcd2999e19e68658dc95cbc75005cd5351743f01e69babd0481ab03e8d7ea8f6` | Build, checksum and artifact gate verified |
| Pro | `out/final-pass/pro/dagric-os-pro-1.0-amd64.iso` | 4,152,623,104 | `2f7632d896b93c5e28a45e3f21dd3572e0c3eb99870933aefd95bc559d513cb6` | Build, checksum and artifact gate verified |

These audit artifacts are intentionally isolated from `out/` release files.
No public ISO, update repository, checksum, signature, website, or release was
changed.

## Passed today

- All 317 Debian package-list names resolve.
- 58 JSON documents parse.
- 23 Python sources compile.
- Both Polkit policies parse, deny inactive/remote callers, require an
  administrator for an active session, and target an absolute helper present
  in the image tree.
- All eight GitHub Action references are pinned to immutable 40-character
  commits; build workflows use read-only tokens except for the publishing job.
- No tracked private-key material, sensitive-looking credential path, or merge
  debris was found.
- All 119 shell entry points parse and pass ShellCheck's error-level analysis.
- All 20 canonical JavaScript/ES-module files pass Node's syntax parser.
- Seven Rewind core tests and eight privileged-controller tests pass.
- Five gettext catalogues, 32 translated desktop entries, 121 first-run
  strings, and 28 family strings match their sources.
- All 26 deployed site/guide pages pass the site release checks.
- The Dockerfile, both live boot entries, package staging, desktop launchers,
  and package-content guards pass.
- Free ISO checksum was independently recomputed after the verified copy from
  the build container.
- The combined two-edition `SHA256SUMS` manifest verifies both audit images.
- Free ISO contains Microsoft-signed shim followed by Debian-signed GRUB.
- Pro ISO contains the same valid Microsoft-shim/Debian-GRUB signature chain.
- The exact final Free ISO reaches **Set Up Dagric** under legacy BIOS, UEFI and
  Microsoft-keyed Secure Boot; the exact final Pro ISO reaches the correctly
  branded **Set Up Dagric — Pro** screen under UEFI.
- The combined final artifact gate verifies both hashes, edition markers,
  package split, signed boot chain, plausible sizes and all four fresh evidence
  sets.
- Two final post-fix repeated stress runs passed 308 gate executions across 60
  rounds.
- Free's installed UEFI system passed 47/47 root assertions. Pro completed its
  offline UEFI install/reboot and passed 65/65, including both MangoHud
  architectures, Wine32/DXVK32, active OpenSnitch, safe service defaults, APT
  and package integrity, and zero failed services.
- The exact final Free ISO completed encrypted UEFI install/reboot, accepted the
  pre-boot disk passphrase, reached SDDM and accepted the created user. Offline
  inspection reconfirmed GPT, 300 MiB VFAT EFI, 49.71 GiB `crypto_LUKS`, and a
  valid passphrase.
- The exact final Free ISO completed a legacy-BIOS install to a blank 50 GiB
  virtual disk, rebooted from that disk, reached SDDM, accepted the created
  user, opened first run and passed 45/45 installed-system assertions.

Framebuffer evidence is under
`out/final-pass/boot-evidence/`; each tested firmware mode also has its own QEMU
log. Complete build logs are `out/final-pass/free/build.log` and
`out/final-pass/pro/build.log`. `out/final-pass/SHA256SUMS` covers both images.

## Safety and delivery changes made

1. Added a dependency-free source/security gate for JSON, Python, Polkit,
   action pins, private-key markers, sensitive tracked paths, and merge debris.
2. Added a repository-wide shell syntax and ShellCheck error gate.
3. Added a JavaScript syntax gate for browser, Worker, and build scripts.
4. Added fast push/pull-request CI and made release tags repeat all cheap
   preflight gates before either ISO can build.
5. Reduced GitHub token permissions to read-only by default and confined write
   permission to the release-publishing job.
6. Made native and container builds run the source and Rewind gates before the
   expensive live-build stage.
7. Added a 1 GiB free-space guard before Rewind creates a snapshot.
8. Made Rewind preserve damaged active-session metadata in a mode-0600
   quarantine file instead of trapping the user behind an unreadable session.
9. Added regression tests proving low-space refusal happens before Snapper,
   corrupt state is quarantined, and a valid active session cannot be replaced.

## Release blockers that remain

These are evidence gaps, not items that can honestly be checked off by source
review alone.

1. Complete a physical Secure Boot install/reboot test on retail firmware; the
   virtual Free BIOS, Free/Pro UEFI and exact-final encrypted UEFI paths pass.
2. Exercise Rewind authentication cancellation, interrupted start/finish,
   open-session reboot recovery, snapshot boot, and the documented rollback
   flow on the freshly installed image.
3. Force real Btrfs data, metadata, and qgroup exhaustion. The new 1 GiB guard
   prevents an obviously full filesystem but cannot predict Btrfs ENOSPC.
4. Verify OpenSnitch's `/tmp/osui.sock` control path and per-machine TLS/key
   behavior on a booted Pro system before treating the application firewall as
   a security boundary.
5. Move the 41 AppArmor profiles reported in complain mode to enforce only
   after their denials are reviewed on representative workloads.
6. Run keyboard-only, Orca, 200% text, reduced-motion, Wayland, and X11 passes.
7. Boot and install on representative AMD, Intel, and NVIDIA PCs; test Wi-Fi,
   Ethernet, audio, Bluetooth, suspend/resume, battery, USB, encrypted install,
   updates, and recovery. At minimum, complete the existing MSI/RX 9070 XT
   preflight in `docs/HARDWARE-PREFLIGHT-2026-08-30.md`.
8. Reproduce the candidate from a clean, reviewed commit. Only that clean
   rebuild should be signed and promoted.
9. If the Family Pack is part of this week's launch, set its real price,
   machine cap, Stripe price/link, and parental-documentation URL in the Worker
   and page sources. The placeholder page is correctly excluded from today's
   deployed-site set and is not sellable as-is.

## Finish-this-week order

1. **Freeze:** review and commit the intended source; remove accidental or
   generated files from the candidate diff.
2. **Prove:** run staged update/rollback and destructive recovery tests on the
   installed Free and Pro systems.
3. **Break Rewind on purpose:** complete the interruption, reboot, rollback,
   and real low-space matrix.
4. **Test hardware and accessibility:** record machine IDs without personal
   identifiers and preserve screenshots/logs for every pass or failure.
5. **Release only if all blockers close:** rebuild from the clean commit,
   verify both hashes, sign one manifest covering both images, stage privately,
   download it back, and compare the public bytes before announcing it.
