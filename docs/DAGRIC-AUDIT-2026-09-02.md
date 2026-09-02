# Dagric OS audit — 2026-09-02

## Result

Every selected source, policy, package, website, localization, privacy,
artifact, firmware-boot, installation and repeated-stress gate passed. The
final Debian staging run produced:

- `dagric-branding` 1.1.8
- `dagric-desktop-defaults` 1.1.7
- `dagric-security-policy` 1.1.6
- `dagric-tools` 1.1.15

Two fresh release candidates were built from clean source revision
`848b0203b40c8988f94424342e8047a34c733c36` and frozen for testing:

- Free: `dagric-os-1.0-amd64.iso`, 2,256,076,800 bytes,
  SHA-256 `ef02f18a982f82b0578abf264d97703b2db72c3725fef0835ef2ea6a2ddb504e`
- Pro: `dagric-os-pro-1.0-amd64.iso`, 4,156,686,336 bytes,
  SHA-256 `b150e00f7ad8aad226085cba70e034cc96112082aae23f710cdbba70a913c726`

The staged tools package contains the existing trust and Flow work plus
`dagric-blueprint`, `dagric-blackbox`, `dagric-life-support`, the shared
foundation engine, the Black Box service/timer, both desktop launchers and the
service-budget contract with executable/data modes normalized correctly.

## Evidence

| Gate | Result |
|---|---|
| Source and security | PASS — 61 JSON documents, 35 Python sources, 2 Polkit policies, 8 pinned actions, 910 tracked paths |
| Product contracts | PASS — 22/22 |
| Source mutation suite | PASS — 5 tests |
| Rewind | PASS — 7 core and 8 controller/boundary tests |
| Adaptive Pipeline and Twin | PASS — 6 pipeline and 6 Twin tests; profile privacy audit passed |
| Trust Loop | PASS — 4 tests on Windows and Linux; live report privacy audit passed |
| Dagric Flow | PASS — dark/light/high-contrast floors, token contract, 1080p/4K artwork and SDDM continuity |
| Website | PASS — 27 deployed pages, no placeholders/tunnels/broken sitemap contract |
| Dependability foundations | PASS — 6 hostile/boundary tests, live Blueprint export/audit/plan, live Black Box sample, all 5 Dagric services budgeted |
| JavaScript and shell | PASS — 20 JavaScript files and 134 shell entry points |
| Localization | PASS — 5 catalogues, 36 desktop entries in 5 languages, 121 wizard and 28 Family strings |
| Repeated stress | PASS — 708 gate executions across 100 rounds |
| Debian package resolution | PASS — all 317 names resolve; no percent-sign list corruption |
| Debian staging | PASS — four packages built; new runtime files inspected inside archive |
| Immutable artifacts | PASS — both hashes, manifests, edition markers, package split, signed EFI chain, Pipeline and Foundations payloads |
| Firmware matrix | PASS — Free BIOS, Free UEFI, Free Microsoft-keyed Secure Boot and Pro UEFI reached the branded first-run UI |
| Fresh Free install | PASS — exact final ISO, UEFI/GPT/LUKS/Btrfs install, disk-only reboot/unlock/login, 72/72 installed assertions |
| Fresh Pro install | PASS — exact final ISO, UEFI/GPT/Btrfs install, disk-only reboot/login, 90/90 installed assertions |
| Rewind checkpoint drill | PASS — exact final Pro install created a pre/post pair, captured and reviewed an `/etc` change, then removed both test snapshots |
| Pro graphics smoke | PASS with VM limitation — Vulkan and both MangoHud layers load through Mesa llvmpipe; no physical GPU was present |

Final immutable-artifact and firmware evidence is preserved under
`out/audit-848b0203/`. The exact final installed reports are
`out/install-audit-848b0203/installed-audit.txt` and
`out/install-audit-pro-848b0203/installed-audit.txt`; the latter directory also
contains the Rewind drill report and review JSON.

## Defects found and fixed during the build

The first Free build stopped before creating an ISO because the desktop-entry
localization registry did not cover the new Blueprint, Life Support and Support
Mode launchers. The registry was completed (including Rewind), all generated
desktop entries were normalized, and the desktop/window catalogue checks were
made permanent gates in both `audit-all.sh` and `stress-test.sh`. Both editions
were rebuilt after that correction and all localization gates now pass.

The artifact checker and installed-system auditor were also extended so future
green builds must prove the Foundation commands, timer enablement, private
Black Box permissions, service hardening/budgets, Blueprint privacy export,
Life Support and Support Mode in the actual image and installed system.

## Recent-request intent review

### Adaptive per-PC pipeline

The implementation meets the safe intent: it builds a privacy-safe capability
projection, chooses from a fixed action allow-list, honors PSI pressure limits,
does no background warming and fails open to normal Linux behavior. It does not
yet prove faster hardware; launch and power measurements on representative PCs
remain required.

### Dagric Twin

Twin is correctly scoped to an explicit, bounded launch-prefetch canary. It
requires successful baseline/canary samples, a local p95 gain of at least 5%,
quarantines a 2% regression, expires decisions and retains no command arguments
or application paths. It is not a full machine simulator and must not be sold
as one.

### Rewind

The privilege boundary, locking, free-space checks, snapshot parsing, automatic
APT receipt recognition and recovery handoff pass. The intended confidence goal
still requires destructive VM tests for power interruption, ENOSPC, snapshot
boot and rollback, followed by a physical recovery drill.

### Dagric Flow

The visual foundation meets its intended goal: Obsidian Pulse is the default
static wallpaper and SDDM backdrop, Obsidian/Frost schemes meet contrast floors,
and the style/token system is packaged. Horizon Bar, Home launcher, Plymouth
continuity and a graphical Support Mode remain later interface slices.

### Gaming

The current tree integrates Steam/Proton guidance, GameMode, MangoHud,
Wine/Bottles and the per-launch policy path. That improves Linux-compatible
games, but it cannot make unsupported kernel anti-cheat or Windows-only drivers
work. The honest goal is the best supported experience plus clear compatibility
ratings, not a false claim that every Steam title works.

### Trust and recovery promise

Support Mode now joins the separate Dagric systems into one allow-listed report:
hardware detection, restore/backup readiness and aggregate Pipeline/Twin/Rewind
history. It never calls local detection “Dagric Verified,” never calls a
snapshot a backup, previews before export, never uploads, refuses overwrite and
excludes personal identifiers and unfiltered logs.

### Blueprint, Black Box, Life Support, and System Tax

Blueprint exports and audits only declarative, allow-listed reconstruction
metadata and refuses overwrite; apply remains disabled. Black Box is a private,
typed, 2,048-event circular recorder with fixed retention, no network path and
systemd CPU/memory/I/O ceilings. Life Support reports read-only-root, low-space
and PSI-pressure risks but makes no automatic changes. Every Dagric background
service has a provisional resource budget; none is described as measured until
physical evidence exists. Full contracts and boundaries are in
`docs/DAGRIC-FOUNDATIONS.md`.

## Remaining stable-release blockers and honest limitations

- Both candidates now come from the same reviewed clean commit, host-export
  hashes match, and the new checksum signature verifies with the published
  Dagric release key. The current public downloads were deliberately left
  unchanged while physical qualification remains open.
- Secure Boot passed with Microsoft-keyed OVMF, but retail physical firmware,
  AMD/Intel/NVIDIA graphics, Wi-Fi, audio, Bluetooth, suspend, battery and
  display hardware remain untested for this candidate.
- Free and Pro completed real Btrfs installs, disk-only reboots and checkpoint
  create/list/delete. Interrupted update, ENOSPC, power-loss, snapshot boot,
  rollback and backup-restore drills still need destructive lab coverage.
- GameMode's client and supervisor tests pass in the VM. Its optional feature
  test reports no CPU-frequency governor (the virtual CPU exposes none) and no
  renice grant for the test account, which intentionally had not opted into the
  `gamemode` group. Do not weaken that privilege boundary to make a VM test
  green; repeat it after explicit opt-in on physical gaming hardware.
- Accessibility packages, translation structure, contrast and keyboard-driven
  installer navigation passed, but audible Orca output, high-DPI, reduced
  motion and assistive-technology use still need human/physical validation.
- Unsupported kernel anti-cheat and Windows kernel drivers remain outside what
  a Linux distribution can promise. Compatibility must be reported per title.

The current conclusion is: **the source, exact images, four firmware paths and
both installed editions pass their automated/VM gates. The signed candidate is
ready for an explicitly labelled external hardware-testing release. Stable
general availability remains blocked on destructive recovery and representative
physical-hardware qualification.**
