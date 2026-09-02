# Dagric OS audit — 2026-09-02

## Result

Every selected source, policy, package, website, localization, privacy,
artifact, firmware-boot, installation and repeated-stress gate passed. The
final Debian staging run produced:

- `dagric-branding` 1.1.8
- `dagric-desktop-defaults` 1.1.7
- `dagric-security-policy` 1.1.6
- `dagric-tools` 1.1.14

Two fresh local candidates were then built and frozen for testing:

- Free: `dagric-os-1.0-amd64.iso`, 2,256,076,800 bytes,
  SHA-256 `8777d8223604cb035bfa74aabb33bff28233a603ded513a5db776cf144ca3238`
- Pro: `dagric-os-pro-1.0-amd64.iso`, 4,156,686,336 bytes,
  SHA-256 `5a0c0b165bac2eaaa45b8745dd3e45f84471369e115d749e19a1d61acb67b70a`

The staged tools package contains the existing trust and Flow work plus
`dagric-blueprint`, `dagric-blackbox`, `dagric-life-support`, the shared
foundation engine, the Black Box service/timer, both desktop launchers and the
service-budget contract with executable/data modes normalized correctly.

## Evidence

| Gate | Result |
|---|---|
| Source and security | PASS — 61 JSON documents, 33 Python sources, 2 Polkit policies, 8 pinned actions, 778 tracked paths |
| Product contracts | PASS — 22/22 |
| Source mutation suite | PASS — 5 tests |
| Rewind | PASS — 7 core and 8 controller/boundary tests |
| Adaptive Pipeline and Twin | PASS — 6 pipeline and 6 Twin tests; profile privacy audit passed |
| Trust Loop | PASS — 4 tests on Windows and Linux; live report privacy audit passed |
| Dagric Flow | PASS — dark/light/high-contrast floors, token contract, 1080p/4K artwork and SDDM continuity |
| Website | PASS — 26 deployed pages, no placeholders/tunnels/broken sitemap contract |
| Dependability foundations | PASS — 6 hostile/boundary tests, live Blueprint export/audit/plan, live Black Box sample, all 5 Dagric services budgeted |
| JavaScript and shell | PASS — 20 JavaScript files and 132 shell entry points |
| Localization | PASS — 5 catalogues, 35 desktop entries in 5 languages, 121 wizard and 28 Family strings |
| Repeated stress | PASS — 183 gate executions across 25 rounds |
| Debian package resolution | PASS — all 317 names resolve; no percent-sign list corruption |
| Debian staging | PASS — four packages built; new runtime files inspected inside archive |
| Immutable artifacts | PASS — both hashes, manifests, edition markers, package split, signed EFI chain, Pipeline and Foundations payloads |
| Firmware matrix | PASS — Free BIOS, Free UEFI, Free Microsoft-keyed Secure Boot and Pro UEFI reached the branded first-run UI |
| Fresh Free install | PASS — UEFI/GPT/Btrfs install, disk-only reboot/login, 67/67 installed assertions |
| Fresh Pro install | PASS — UEFI/GPT/Btrfs install, disk-only reboot/login, 85/85 installed assertions |
| Rewind checkpoint drill | PASS — installed Pro snapshot created, enumerated and removed |
| Pro graphics smoke | PASS with VM limitation — Vulkan and both MangoHud layers load through Mesa llvmpipe; no physical GPU was present |

All VM evidence is preserved under
`out/foundations-candidate-20260902/`. The installed reports are
`install-evidence/free-uefi/installed-audit.txt` and
`install-evidence/pro-uefi/installed-audit.txt` below that directory.

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

## Remaining release blockers and honest limitations

- The candidates came from a dirty working tree. They are valid local test
  artifacts, not reproducible release artifacts tied to a reviewed commit.
- `out/SHA256SUMS` changed during the builds and the existing
  `out/SHA256SUMS.sig` now correctly fails verification. Nothing was published;
  a release requires a reviewed clean-tree rebuild and a new offline signature.
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
both installed editions pass their automated/VM gates. The candidate is ready
for destructive recovery and physical hardware qualification, not public
release.**
