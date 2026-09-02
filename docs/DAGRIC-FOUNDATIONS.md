# Dagric dependability foundations

Dagric's product promise is: **make existing PCs feel fast and modern while keeping every system change measurable, explainable, and reversible.** This change implements the safe foundation of four concepts from that promise without pretending that source checks equal hardware proof.

## Blueprint

`dagric-blueprint` exports a versioned, declarative description of the system channel, Dagric appearance, reduced-motion preference, installed Debian package names, Flatpak application IDs, and bounded hardware-policy choices. It deliberately excludes personal files, application data, passwords, credentials, network secrets, permissions, arbitrary paths, and shell configuration.

The exporter creates a new mode-0600 file and refuses to overwrite an existing path. The auditor rejects unknown or malformed nested fields, unsafe identifiers, changed omission boundaries, and invalid package IDs. `plan` only describes differences. It has no apply path and reports `apply_available: false`.

Example:

```sh
dagric-blueprint export "$HOME/dagric-blueprint.json"
dagric-blueprint audit "$HOME/dagric-blueprint.json"
dagric-blueprint plan "$HOME/dagric-blueprint.json"
```

Blueprint is reconstruction metadata, not a backup. It does not claim to preserve documents or application data.

## Black Box

`dagric-blackbox` is a private circular recorder, not telemetry. A bounded systemd oneshot samples Linux PSI summaries and uptime every five minutes. It records only typed performance summaries and five approved lifecycle marks. It never records process names, commands, arguments, browser history, clipboard data, documents, hostnames, serials, accounts, MAC addresses, or free-form notes.

The ring is limited to 2,048 events. Lifecycle marks expire after 15 minutes and pressure summaries after seven days. Writes are locked, atomic, mode 0600, and stored under a mode-0700 directory. There is no network upload path. The service is constrained to 64 MiB, 5% CPU, idle I/O priority, a read-only system view, and its one private writable directory.

## Life Support

`dagric-life-support` currently performs a read-only assessment of three dependable signals: a read-only root filesystem, dangerously low writable storage, and sustained recent PSI pressure from Black Box. It reports normal, caution, or critical, explains every finding, and recommends recovery actions. It does not automatically mutate the system.

SMART health, temperatures, battery degradation, GPU resets, memory errors, and failed-boot detection are explicitly reported as unimplemented until privileged integration and physical fault-injection tests exist.

## Resource budgets

Every current `dagric-*.service` has a declared CPU, memory, wakeup, network, I/O, and gaming-behavior budget in `usr/share/dagric/budgets/services.json`. The checker fails if a Dagric service exists without a budget. All current numbers are marked `measured: false` and `decision: provisional`; they are ceilings in source, not claimed real-world measurements.

## Release boundary

The following are intentionally not claimed complete:

- **Transactional roots:** Blueprint cannot apply changes until atomic A/B or equivalent rollback roots pass destructive VM and hardware tests.
- **Recovery automation:** Life Support recommends; it does not silently repair, roll back, or disable hardware.
- **TUF-style update trust:** the existing signed APT path is not yet a complete threshold/expiry/rollback-protected TUF design.
- **Replay:** Black Box records bounded symptoms but does not replay a failure scenario.
- **Signed quirk service:** per-device quirks require signed metadata, expiry, rollback, conflict resolution, and hardware-lab evidence.
- **SBOM and reproducibility:** CI definitions exist, but release artifacts are not yet proven reproducible or accompanied by a complete SBOM.
- **Physical validation:** provisional service budgets, accessibility, suspend/resume, drivers, games, and fault recovery still require representative PCs.

These boundaries are release blockers for the corresponding claims. They are not hidden roadmap details.

## Verification

Run:

```sh
sh tools/check-foundations.sh
sh tools/audit-all.sh
sh tools/stress-test.sh 25
```

The foundation tests include malicious nested Blueprint fields, secret-field attempts, path traversal package IDs, overwrite refusal, Black Box free-form event rejection, retention expiry, ring overflow, read-only-root detection, storage exhaustion, critical I/O pressure, and complete background-service budget coverage.
