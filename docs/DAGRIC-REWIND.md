# Dagric Rewind

> **The attraction:** Your computer has an Undo button.

Dagric should not try to beat Windows and macOS by copying their longest
feature lists. Its defensible advantage is a computer whose owner can change
things without fear. Dagric Rewind turns the snapshot and recovery work already
in the OS into a visible, understandable product.

This document separates what exists in the tree today from ideas that still
need engineering and real-hardware proof. Nothing in the future section may be
described as shipping.

## Why this is the flagship

The immediate market need is unusually concrete. Microsoft ended Windows 10
support on 14 October 2025 and directs owners of incompatible PCs toward ESU or
replacement hardware ([Microsoft lifecycle notice](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support)).
At the same time, the UN's 2024 monitor reports 62 million tonnes of electronic
waste in 2022, growing five times faster than documented recycling
([UNITAR](https://unitar.org/about/news-stories/press/global-e-waste-monitor-2024-electronic-waste-rising-five-times-faster-documented-e-waste-recycling)).
Dagric already targets those still-useful computers. Rewind gives that audience
a reason to prefer Dagric after the machine has been rescued: updates,
applications, drivers, and experiments become understandable and recoverable.

The competitor gap is real:

- Windows Recall is an opt-in history of **screen snapshots** on Copilot+ PCs.
  Microsoft documents local storage and controls, but also the limits of
  filtering and the fact that the captured unit is the screen
  ([Microsoft Recall privacy](https://support.microsoft.com/en-us/windows/privacy/privacy-and-control-over-your-recall-experience)).
- Windows Sandbox is a disposable virtual machine, unavailable on Home, whose
  apps are separate from the host and whose network is enabled by default
  ([Microsoft Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/)).
- Time Machine is an excellent file backup, but Apple documents that system
  files and apps installed as part of macOS are excluded from backups
  ([Apple Time Machine exclusions](https://support.apple.com/guide/mac-help/exclude-files-from-a-time-machine-backup-mh15622/26/mac/26)).
- Snapper exposes the correct low-level mechanisms—create, compare, and recover
  snapshots—but its interface speaks to administrators
  ([openSUSE Snapper guide](https://doc.opensuse.org/documentation/tumbleweed/snapper/)).

Rewind occupies the useful space between them: a chronological history of
**real system changes**, on the actual computer, with no screen recording,
cloud, account, or separate pretend desktop.

The timeline itself revives a good older idea. Yale's Lifestreams work proposed
a time-ordered stream as an alternative to filing everything into a desktop
hierarchy ([Lifestreams](https://cs-www.cs.yale.edu/homes/freeman/lifestreams.html)).
Rewind applies that idea to system state without turning a person's screen into
a surveillance archive. Its ownership and offline guarantees also follow the
local-first principles of control, longevity, privacy, and offline use
([Ink & Switch](https://www.inkandswitch.com/essay/local-first/)).

## What is implemented now

The first version is implemented in the image tree for both Free and Pro. It is
not a public-release claim until a fresh ISO and the physical-hardware gate have
passed:

1. **Start a Rewind session.** Pick Software install, Settings change, Driver
   update, or Try something. Dagric creates a Snapper `pre` checkpoint with a
   fixed, human-readable label.
2. **Finish and review.** Dagric creates the paired `post` checkpoint, compares
   it with the first, and summarizes paths as Software, Settings, Boot, System
   state, or Other. It reports added, changed, and removed paths but never reads
   or displays their contents.
3. **Create a known-good checkpoint.** A deliberate single checkpoint is useful
   before travel, a deadline, or a major update.
4. **See a system timeline.** Recent Snapper checkpoints and completed Rewind
   sessions appear in chronological order.
5. **Open safe recovery.** Rewind hands the owner to Btrfs Assistant and the
   existing bootable-snapshot path. It does not run a dangerous live root
   `undochange` or secretly rewrite the running system.
6. **Review automatic software changes.** Dagric already creates an exact
   `apt (pre)` / `apt (post)` pair around every APT or Discover package
   transaction. Rewind recognizes only those validated pairs and turns them
   into clickable “Software update (automatic)” receipts without creating a
   second set of snapshots.

The interface says when it cannot protect a machine. It is unavailable in the
ephemeral live session and on non-Btrfs installations; it never draws a working
Undo button over a recovery mechanism that is absent.

The code lives at:

- `/usr/bin/dagric-rewind` — unprivileged desktop controller and allow-listed
  UI protocol;
- `/usr/share/dagric/rewind/main.qml` — view-only timeline;
- `/usr/lib/dagric/rewind-ctl` — narrow privileged operations;
- `/usr/lib/dagric/rewind_core.py` — parser and summary logic;
- `/usr/share/polkit-1/actions/org.dagric.rewind.policy` — explicit
  administrator approval;
- `/var/lib/dagric/rewind/` — root-only session metadata and history.

## The safety contract

Every future Rewind integration should implement the same five-part contract:

| Part | Required answer |
|---|---|
| Before | What known checkpoint exists before the action starts? |
| Receipt | What system paths and packages changed? |
| Recovery | What tested route returns to the checkpoint? |
| Lifetime | When can retention remove it, and is it marked important? |
| Privacy | What was recorded, where is it stored, and what was never read? |

Current privacy boundary:

- no screenshots, microphone, camera, keystrokes, clipboard, browser history,
  or document contents;
- no network calls, account, advertising identifier, or telemetry;
- fixed action and preset allow-lists—QML cannot send a command or path to a
  root shell;
- root-only metadata (`0700` directory, `0600` files), atomic writes, and
  journal audit events;
- review is limited to pairs created and recorded by Dagric Rewind;
- no delete or restore operation exists in the privileged helper.

The last rule is deliberate. Snapper's own documentation recommends booting a
snapshot for a complete root rollback, and Red Hat explicitly warns against
using `snapper undochange` on `/`
([SUSE recovery guidance](https://doc.opensuse.org/documentation/leap/reference/html/book-reference/cha-snapper.html),
[Red Hat warning](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/storage_administration_guide/snapper-undochange)).

## Verification before marketing it

Automated gates run `tools/check-rewind.sh` in native and container builds. The
gate unit-tests Snapper JSON normalization and change classification, compiles
both Python sources, parses the Polkit policy, validates the launcher, asserts
that the QML and policy are packaged, and rejects a restore/delete command in
the privileged helper.

An installed Pro Btrfs VM passed the first end-to-end run on 1 September 2026:

- installed `dagric-tools` 1.1.9 through APT and automatically discovered its
  exact `apt (pre)` / `apt (post)` receipt;
- started and finished a Settings session as an ordinary user through Polkit;
- showed one approval dialog per mutation, then jumped directly to the result;
- identified an added `/etc` path as Settings and later identified both test
  paths as removed;
- hid Rewind, grub-btrfs, timekpr, cache, and log housekeeping from the receipt;
- left recovery as an explicit handoff rather than altering the live root.

The evidence and remaining limitations are recorded in
`out/REWIND-TEST-REPORT-2026-09-01.md`. The following still require testing
before a release can claim Rewind is fully verified:

- start and finish every preset as an ordinary user through Polkit;
- install and remove a small Debian package inside a session, then compare the
  summary with `snapper status`;
- cancel authentication at every prompt and confirm zero new snapshots;
- interrupt start and finish at process boundaries and verify recoverable state;
- reboot with a session open, finish it, and inspect the pair;
- boot the created read-only snapshot, perform the documented rollback flow,
  and confirm normal boot afterwards;
- exercise keyboard, screen reader, 200% text, reduced motion, 720p, and both
  Wayland and X11;
- fill the Btrfs volume near its quota and confirm the error is clear and no
  partial session is reported as complete.

## Roadmap: from feature to a new computing model

These are engineering directions, not current promises.

### Next: automatic receipts everywhere

- APT/Discover package transactions already appear automatically. Extend the
  same receipt contract to Flatpak, driver changes, and Dagric's setup helpers
  so the OS protects risky work without asking the owner to remember first.
- Turn package-manager metadata into receipts such as “VLC installed 7
  packages; 24 MB; no settings outside `/etc`.”
- Add a recovery-mode timeline before login, using the existing boot snapshot
  infrastructure rather than inventing a second rollback engine.
- Search by action, package, date, and category—still without indexing document
  contents.

### Then: personal-file Rewind, opt in by folder

Root snapshots are not a backup and should never be sold as one. A separate,
encrypted file-history engine can cover selected personal folders with clear
retention, removable-drive targets, and an explicit “this is backed up” state.
It must be tested against disk loss, not only accidental deletion.

### Later: the Reversible Computing API

Publish a small protocol that lets any installer or system tool declare an
intent, receive a checkpoint, attach a human receipt, and expose a tested
recovery route. An application should be able to say “this change is
reversible” as a property the OS can verify, not a marketing claim.

### Long horizon: a local-first personal computer stream

Btrfs already has checksummed snapshots and incremental send/receive
([kernel documentation](https://www.kernel.org/doc/html/v6.15/filesystems/btrfs.html)).
A future Dagric could move encrypted change history directly between an
owner's computers, with no Dagric cloud and no account, using openly specified
peer discovery and replication. That would combine the chronological computer
from Lifestreams with local-first ownership: continuity across devices without
renting the memory of your computer from its vendor.

That is the larger bet: **an operating system of reversible intent**. Windows
and macOS optimize for adding features. Dagric can optimize for the owner's
confidence to try, understand, and recover.
