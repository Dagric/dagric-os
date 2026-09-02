# Dagric peer-distribution review — 2026-09-02

DistroWatch blocks automated profile access, so it was used only to identify
the peer set. Technical conclusions below were checked against the projects'
official documentation. This is a product-gap review, not a popularity ranking.

## What Dagric should learn

### Bazzite

Bazzite's image-based system retains the previous deployment after an update,
supports rollback from GRUB or a helper, and exposes updates from a
controller-friendly interface. Its desktop updater also waits for acceptable
CPU, memory and battery conditions.

Dagric lesson: Rewind is a useful receipt and snapshot interface, but it does
not yet make an APT update transactional. The next update architecture must
prepare a bootable next state, retain the current state, and make rollback a
first-class update result. Update preflight should also honor load, battery,
disk headroom and metered networking.

Sources: <https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/>
and <https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/updating_guide/>.

### Zorin OS

Zorin focuses on people leaving Windows: familiar layouts, Windows-application
guidance, Microsoft document compatibility, web alternatives and approachable
help material.

Dagric lesson: Dagric Migrate safely copies common data, and Flow supplies a
coherent native identity, but migration needs an application replacement map.
The first useful version should scan the old Windows application inventory and
label each item Native, Verified Flatpak, Web, Windows-compatible, Alternative,
or Unsupported. It must never migrate credentials silently.

Sources: <https://help.zorin.com/> and <https://zorin.com/os/>.

### Nobara

Nobara's value is integration: gaming packages, graphics support and an updater
that handles distribution-specific corrections, codecs and detailed logging
instead of pretending a generic package command covers the product.

Dagric lesson: Steam, Proton, Wine/Bottles, GameMode, MangoHud and the adaptive
launch path exist, but Dagric needs one gaming readiness screen and a Dagric
update orchestrator that owns its special cases. Kernel anti-cheat and Windows
kernel drivers remain outside Dagric's control and must stay visible as limits.

Sources: <https://wiki.nobaraproject.org/> and
<https://wiki.nobaraproject.org/en/new-user-guide-general-guidelines>.

### CachyOS

CachyOS competes on measured low-latency engineering: tuned EEVDF/BORE choices,
multiple kernel variants, 1,000 Hz defaults, ThinLTO/AutoFDO builds, current
hardware patches and explicit warnings that a real-time kernel can make games
worse rather than better.

Dagric lesson: do not copy a performance kernel or scheduler by reputation.
Extend Dagric Twin into a reproducible physical benchmark lab: frame-time p95/
p99, input latency, compilation time, idle power, suspend and thermals on each
supported CPU generation. Only ship a kernel/profile choice where the measured
gain survives regression and recovery tests; keep Debian's supported kernel as
the fallback.

Sources: <https://wiki.cachyos.org/features/kernel/> and
<https://wiki.cachyos.org/cachyos_basic/why_cachyos/>.

### Pop!_OS

Pop!_OS keeps a full recovery environment that can repair, refresh or reinstall
the system, with a documented path that preserves home data during refresh.

Dagric lesson: bootable Btrfs snapshots are not a substitute for an independent
repair environment on a damaged system disk. Dagric should validate a minimal
recovery image that can inspect Rewind history, repair boot, restore a backup,
and reinstall the core while clearly showing which applications will need to be
reinstalled.

Source: <https://system76.com/support/pop-recovery>.

### Garuda Linux and openSUSE transactional systems

Garuda demonstrates approachable Snapper management and snapshot selection from
the boot path. SUSE's transactional-update design demonstrates applying changes
to a separate snapshot and selecting the result for a future boot.

Dagric lesson: keep Rewind's friendly receipts and privileged allow-list, but
move core updates away from modifying the running root. Prototype Btrfs-based
next-boot updates before considering a larger OSTree migration, and preserve a
legacy GRUB path for older PCs.

Sources: <https://forum.garudalinux.org/t/garuda-linux-harpy-eagle-210926/12853>
and <https://documentation.suse.com/sle-micro/6.0/html/Micro-transactional-updates/index.html>.

## Prioritized Dagric response

1. **Prove recovery:** boot the current snapshot/recovery path on UEFI, Secure
   Boot and legacy BIOS; run rollback after interrupted update, ENOSPC and power
   loss; perform an actual backup restore onto replacement storage.
2. **Prototype transactional updates:** use Btrfs next-boot state creation with
   current/next/recovery semantics, health confirmation and automatic previous
   entry selection. Do not advertise this until the destructive VM matrix passes.
3. **Finish Dagric Switch:** add a read-only Windows application inventory and
   honest replacement map before attempting passwords, Wi-Fi or account import.
4. **Join gaming guidance:** make one Compatibility view for drivers, Vulkan,
   Steam/Proton and known anti-cheat limits; keep community evidence separate
   from Dagric Lab results.
5. **Build a hardware/driver manager:** borrow Nobara and Zorin's clarity around
   NVIDIA, optional Mesa testing builds and detected controller/handheld drivers,
   but keep every proprietary or experimental choice explicit and reversible.
6. **Add a controller-first session:** prototype a living-room/handheld image
   with a controller-operable updater and rollback path before claiming parity
   with Bazzite or SteamOS.
7. **Promote Support Mode into a GUI:** the privacy-safe report/export engine is
   now implemented. A consumer UI should preview every included field, let the
   owner deselect sections and never upload without a separate explicit action.
8. **Gate every update:** refuse or defer automatic work under critical PSI,
   low battery, insufficient Btrfs headroom or metered networking; record the
   reason in Dagric History.

The competitive target is not to copy one distribution. It is to combine
Zorin's migration clarity, Bazzite's rollback confidence, Nobara's gaming
integration, Pop!_OS's recovery independence, and Dagric's own measurable,
privacy-preserving machine policy in one maintainable Debian/KDE product.
