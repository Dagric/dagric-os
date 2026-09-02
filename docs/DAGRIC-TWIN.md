# Dagric Twin — first safe milestone

Dagric Twin is Dagric's local proof engine for performance changes.  This first
milestone implements one complete, deliberately narrow loop:

1. An owner records an explicit unchanged launch baseline.
2. Twin evaluates a single bounded candidate: Dagric's existing launch-code
   prefetch, guarded by PSI.
3. The owner explicitly runs a one-launch canary.
4. Twin records only wall-clock duration, exit status and CPU/memory/I/O PSI.
5. After five successful samples of each kind, Twin retains the candidate for
   seven days only if its local p95 duration improves by at least 5% without a
   PSI regression; it quarantines regressions for one day.

Twin stores only a keyed digest of a system executable, never its path or
arguments. It never records files, URLs, document names, command lines, serial
numbers, MAC addresses, DMI strings, EDIDs, browser data, keystrokes or mouse
events. It has no service, timer, network activity, desktop entry or telemetry.

## Performance Contract

The current candidate is `bounded-launch-prefetch-v1`:

| Field | Contract |
| --- | --- |
| Scope | One explicit launch of a system-installed executable |
| Resource | Page-cache advisory prefetch only |
| Safety | PSI fails closed; no background warming; policy action is capped at 1 second and never kills the application |
| Measurement | Process wall time, exit status and PSI before/after |
| Retain rule | At least five clean samples each and 5% p95 improvement |
| Rollback | Skip prefetch and quarantine the candidate for 24 hours |
| Expiry | Retained evidence expires after seven days |

This is **not** a claim to measure first-useful-frame latency, input latency,
power or thermals; those need instrumented real-hardware validation before they
can join the contract. Nor does Twin change CPU governors, I/O weights,
schedulers, GPU settings, DAMON, `sched_ext`, drivers or package updates.

## Advanced usage

The tool is intentionally for validation and support, not daily consumer use:

```sh
dagric-twin shadow -- /usr/bin/true
dagric-twin baseline -- /usr/bin/true
dagric-twin canary -- /usr/bin/true
dagric-twin evaluate -- /usr/bin/true
dagric-twin status
dagric-twin audit
```

Real applications should be tested with a repeatable, non-destructive launch
fixture. Do not use a command that edits data or sends messages merely to gather
performance samples.

## Next evidence-driven expansions

1. Add first-window/first-useful-frame probes for Dagric-owned Qt applications.
2. Add a cgroup-based background disturbance budget for Dagric-owned work only.
3. Add an append-only explanation ledger and Doctor read-only report.
4. Add transactional Btrfs A/B update deployment and boot-health rollback.
5. Only then test privileged policy modules in opt-in, hardware-qualified
   canaries with independent recovery evidence.
