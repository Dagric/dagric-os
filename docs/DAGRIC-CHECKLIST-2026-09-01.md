# Dagric OS full product checklist — 1 September 2026

Status is evidence-based: **PASS** means the named evidence exists, **PARTIAL**
means the implementation is present but a required runtime matrix is open, and
**BLOCKED** means the product must not be released or sold in that state.

## Release decision

- [x] Free and Pro build from the current workspace.
- [x] Both artifacts have independently verified SHA-256 hashes.
- [x] Free boots in BIOS, UEFI, and Microsoft-keyed Secure Boot VMs.
- [x] Pro boots in a UEFI VM and identifies itself as Pro.
- [x] Free installs offline to a blank UEFI disk, reboots, reaches SDDM, logs in,
  and starts the installed-system setup wizard.
- [x] The installed Free system passes the root runtime auditor: 47/47 checks
  covering Btrfs/Snapper, UEFI, signed boot packages, firewall, AppArmor,
  privacy policy, recovery/family helpers, tools, edition separation, APT,
  package verification and failed services.
- [x] Pro installs offline to a blank UEFI disk, reboots through the installed
  Plymouth path, reaches its Pro-branded SDDM login, accepts the created user,
  and passes **65/65** installed-system assertions with no failed services.
- [x] Direct SquashFS inspection confirms the corrected Rewind wrapper is in
  both exact final ISOs; their installer/package payload matches the audited
  installed disks apart from that final wrapper change.
- [x] The exact final Free ISO completes a LUKS+Btrfs UEFI install, reboots,
  accepts the disk passphrase, reaches SDDM, and accepts the created user;
  offline GPT/LUKS signature and passphrase verification also pass.
- [x] The exact final Free ISO installs offline to a blank legacy-BIOS disk,
  reboots from that disk, reaches SDDM, accepts the created user, opens first
  run, and passes **45/45** installed-system assertions.
- [ ] Both editions update and recover.
- [ ] The candidate is rebuilt from a clean, reviewed commit.
- [ ] Physical AMD, Intel, and NVIDIA test machines pass the hardware matrix.
- [ ] One signed manifest covers the exact promoted bytes and verifies after a
  private upload/download round trip.

**Current decision: BLOCKED for public release; valid developer candidate.**

## Concept checklist

| # | Concept | Built now | Stress/evidence now | Required before release | Status |
| ---: | --- | --- | --- | --- | --- |
| 1 | Build and reproducibility | Native and container build paths, Free/Pro edition pruning, CI gates | Final Free/Pro ISOs built; combined hashes and artifact gate verify; build logs retained | Clean-commit rebuild and byte-for-byte comparison | PARTIAL |
| 2 | Offline graphical installer | Calamares, signed BIOS/UEFI pieces, Dagric offline-safe bootloader helper, Btrfs default | Fresh Free BIOS and UEFI plus Pro UEFI installs completed; 45/45, 47/47 and 65/65 runtime audits pass; exact final Free LUKS+Btrfs install/reboot/unlock/login passes | Physical Secure Boot installation and real-device storage matrix | PARTIAL |
| 3 | BIOS, UEFI, Secure Boot | GRUB BIOS, Microsoft-signed shim, Debian-signed GRUB, EFI fallback repair | Exact final Free ISO reaches first run in BIOS, UEFI and Microsoft-keyed Secure Boot; exact Pro ISO reaches Pro first run in UEFI; artifact signatures pass | Retail firmware and physical Secure Boot install/reboot | PARTIAL |
| 4 | Desktop, branding, first run | Plasma defaults, SDDM, Plymouth, Hub, appearance, setup wizard | Free and Pro reach correctly branded setup screens | Complete every wizard branch on X11/Wayland and multiple DPI settings | PARTIAL |
| 5 | Performance and boot tuning | Scheduler/sysctl/boot-cache hooks, GameMode config, private per-machine Adaptive Pipeline and explicit-only Dagric Twin | Pipeline fixtures prove distinct low-RAM/HDD and high-RAM/NVMe policies; Twin proves expiry/quarantine, evidence threshold, PSI-regression rollback and privacy boundary | Repeatable cold/warm physical boot, idle RAM, frame-time, suspend and battery measurements across AMD, Intel and NVIDIA systems | PARTIAL |
| 6 | Accessibility | Orca, speech engine, screen-reader boot entry, contrast and keyboard launchers | Package/source guards and translated accessibility page pass | Keyboard-only, Orca speech, AT-SPI, 200% text, reduced motion, X11/Wayland | PARTIAL |
| 7 | Localization | German, French, Spanish, Brazilian Portuguese, Italian catalogs | Five catalogs rebuild exactly; desktop/wizard/family strings are covered | Native-speaker review and live layout/overflow pass for each locale | PARTIAL |
| 8 | Apps, search, offline manual | Friendly app names, Hub, Discover integration, 100+ manual pages | Site/manual parsers and launcher/package guards pass | Launch every menu entry and validate offline links on installed system | PARTIAL |
| 9 | Hardware and drivers | Hardware Check, Driver Helper, firmware set, Secure Boot/MOK guidance | Source/package contracts pass | AMD/Intel/NVIDIA GPU, Wi-Fi, audio, Bluetooth, printer, suspend/resume matrix | PARTIAL |
| 10 | Windows migration | Read-only discovery plus resumable, non-overwriting rsync copy; NTFS/exFAT support | Static safety contract confirms `--ignore-existing` and required tools | Real Windows 10/11 profiles, BitLocker handling, interrupted-copy resume, Unicode/large-file cases | PARTIAL |
| 11 | Steam and Linux gaming | Steam consent installer, Proton guidance, Lutris, GameMode, MangoHud, Vulkan and 32-bit stack | Installed Pro proves Wine/Wine32, DXVK32, GameMode, MangoHud amd64+i386 and Lutris; Free excludes Pro stack | Representative game/controller/GPU matrix and vendor anti-cheat disclosure | PARTIAL |
| 12 | Windows applications | Wine, Winetricks, Wine binfmt and Bottles helper | Pro package split and source contracts pass | Representative installers, .NET/VC runtimes, file associations, uninstall and failure recovery | PARTIAL |
| 13 | Security and privacy | Firewalld, AppArmor, unattended updates, hardened browsers, SSH/USB controls, OpenSnitch on Pro | Installed Free and Pro prove active firewalld/AppArmor, browser policy parsing and zero failed units; Pro proves active OpenSnitch and disabled-by-default SSH/USBGuard/libvirt/Docker units | Validate OpenSnitch socket/key boundary; review denials before enforcing 41 complain profiles | PARTIAL |
| 14 | Updates and package delivery | Dagric APT source, package staging, repository builder, updater and release workflow | All 317 package names resolve; package/content guards pass | Install old candidate, update through staged repo, reboot, rollback, expired-key/offline tests | PARTIAL |
| 15 | Rewind and recovery | Btrfs/Snapper controller, receipts, Polkit boundary, recovery handoff | 15 unit/boundary tests; installed Btrfs setup active; auth cancellation exposed two failure states, both are fixed, and the corrected wrapper is verified inside the final SquashFS | Interrupted operations, reboot-open-session, snapshot boot, rollback and true Btrfs ENOSPC | PARTIAL |
| 16 | Family controls | Daily screen time/bedtime UI, root helper and Polkit policy | Implementation and privilege contracts pass | Live multi-user, clock/time-zone changes, reboot, admin protection and accessibility tests | PARTIAL |
| 17 | Family Pack commerce | Fail-closed placeholder page is excluded from deploy | Site gate proves placeholders cannot be published | Real price, cap, Stripe ID/link, entitlement test and parental documentation | BLOCKED |
| 18 | Windows virtual machine | virt-manager, QEMU/KVM, OVMF, swtpm and Dagric helper | Pro manifest/source contract passes | Licensed Windows install, TPM/Secure Boot, networking, USB, snapshots and no-KVM fallback | PARTIAL |
| 19 | Backups and storage | Kup on Free; Borg/Vorta on Pro; SMART and Btrfs maintenance | Package split/manual contracts pass | Create, corrupt and restore data from local and remote backup targets | PARTIAL |
| 20 | Website and release delivery | Static site, gate Worker, checksums, release/proof scripts | 26 deployable pages pass placeholder/link/sitemap/tunnel checks | Private staging, payment/download test, rollback drill, exact-byte public verification | PARTIAL |

## Gaming truth checklist

- [x] Ship the complete Linux gaming plumbing in Pro, including the 32-bit
  libraries older games still require.
- [x] Make Steam an explicit-consent install rather than silently accepting a
  third-party license for the user.
- [ ] Publish a tested compatibility list by game, GPU, driver, Proton version,
  controller and online/anti-cheat result.
- [ ] Test shader compilation, sleep/resume, HDR/VRR where supported, overlays,
  controller hot-plug, multiple monitors and game updates.
- [ ] State clearly that “all Steam games like Windows” is not an honest Linux
  promise: games whose publishers require unsupported Windows kernel drivers or
  disable Linux/Proton anti-cheat must use a Windows VM, dual boot, or streaming.

## Exact commands

```sh
sh tools/audit-all.sh --package-names
sudo sh tools/check-artifacts.sh out/final-pass
sh tools/stress-test.sh 50
```

The checklist closes only when every unchecked release item has preserved logs,
screenshots, hashes, or a signed test record—not when it has merely been tried.
