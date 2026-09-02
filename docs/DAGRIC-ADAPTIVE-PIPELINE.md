# Dagric Adaptive Pipeline

## Decision

Dagric now has one private, capability-based performance policy pipeline. It is
not an optimizer panel and is deliberately invisible during normal desktop use.
The pipeline has no launcher, tray icon, notification, telemetry endpoint or
background benchmark. Its only persistent output is a root-only local profile
at `/var/lib/dagric/pipeline/profile.json`.

Every machine receives a different policy when its usable capabilities differ:
memory tier, CPU thread count, NUMA presence, GPU vendor class, rotational or
solid-state storage, active I/O scheduler, network class, MGLRU, zram, Btrfs
and cgroup-v2 availability. It never reads serial numbers, MAC addresses, DMI
strings, EDIDs, machine IDs, user files or browser data.

## Shipped safe core

`dagric-pipeline.timer` refreshes the profile after boot and every six hours.
`dagric-pipeline.service` is hardened and can write only its own state directory.
It compiles, rather than blindly changes, the following policy:

| Capability | Current policy |
| --- | --- |
| Under 12 GiB RAM | 8 MiB maximum launch prefetch; no speculative warming |
| 12–31 GiB RAM | 32 MiB maximum launch prefetch; no speculative warming |
| 32 GiB or more | 64 MiB maximum launch prefetch; no speculative warming |
| Rotational disk | Retain Dagric's existing per-device BFQ udev policy |
| SSD or NVMe | Retain the kernel scheduler; do not impose BFQ |
| Btrfs root | Retain Dagric's existing zstd mount policy and snapshot model |
| MGLRU/zram/cgroup v2 | Detect and report; leave kernel ownership intact |

The only runtime optimization is `dagric-pipeline-launch`, used automatically by
`dagric-game-launch`. It learns only executable and shared-library mappings
outside `/home`, requests bounded `POSIX_FADV_WILLNEED` prefetch on a later
explicit launch, and fails closed whenever PSI shows CPU, memory or I/O pressure.
It reads no file contents. A missing pipeline, pressure interface or prefetch
support means the game runs normally.

## Explicit non-goals in this release

The following are represented as disabled experimental fields and are audited
as failures if enabled: DAMON/DAMOS reclaim, `sched_ext`, manual IRQ pinning,
local binary rewriting and GPU steering. They require hardware, latency and
recovery evidence; enabling them merely because an internet tweak says they are
fast would violate Dagric's safety standard.

Likewise, Dagric does not stack zswap on zram, force a universal CPU governor,
change SSD/NVMe I/O schedulers, disable filesystem barriers, or rewrite third
party executables.

## Audit contract

`sh tools/check-pipeline.sh` proves that low-memory/HDD and high-memory/NVMe
fixtures compile different policies, private identifiers are rejected, PSI
fails closed, prefetch is bounded, and user-home paths are excluded. The gate is
part of `sh tools/audit-all.sh`; installed-image audit additionally verifies the
service, timer and profile audit.

## Growth path

1. Measure: add opt-in, bounded latency and power evidence from real hardware.
2. Act safely: put only Dagric-owned maintenance work into cgroups and pause it
   under PSI; validate snapshots and recovery first.
3. Add intent transactions for Dagric-owned launchers and KWin integration.
4. Prototype `sched_ext`, DAMON and GPU policy only behind an explicit
   experimental switch with a watchdog and automatic fallback.
5. Consider application hibernation, local binary optimization and heterogeneous
   CPU/GPU/NPU scheduling only after per-device benchmark and rollback evidence.

The operating rule is simple: make one reversible change, measure the result on
that machine, keep it only when it improves a user-visible outcome, otherwise
restore the Linux default.
