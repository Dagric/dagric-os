# Dagric finishing priorities — September 5, 2026

This is a workflow comparison, not a performance benchmark or a claim that
Dagric is more secure than another operating system. Public release remains
held pending the evidence and approvals in `RELEASE-HOLD-2026-09-04.md`.

| Everyday need | Reference behavior | Dagric implementation and next acceptance test |
| --- | --- | --- |
| Recover from a bad change | [Windows recovery options](https://support.microsoft.com/en-us/windows/experience/backup-recovery/recovery-options-in-windows) organizes recovery choices around the problem: updates, startup, restore, reset, and installation media. | Rewind tracks system-change sessions and hands recovery to snapshot tools. Its documentation must distinguish system recovery from restoring migration notes. Boot and test the actual recovery path; never describe an exported checklist as a system backup. |
| Update without losing a usable system | [Fedora Silverblue](https://www.fedoraproject.org/atomic-desktops/silverblue/) uses atomic system updates and retains a previous version. | Dagric's Debian package updates and Btrfs/Snapper checkpoints are **not** an atomic operating-system deployment. Keep snapshot prerequisites explicit and require an installed-machine update/recovery test. An immutable-root redesign is not being slipped into a release-finishing patch. |
| Protect personal work | [Ubuntu backup guidance](https://help.ubuntu.com/stable/ubuntu-help/backup-why.html.en) recommends regular backups, separate storage, and checking restoration. | Dagric provides backup applications and migration assistance. System snapshots and migration state packs are not substitutes for a separately stored personal-file backup. Test restore using disposable files before trusting a backup workflow. |

## What this finishing pass changes

- Match every installed visible launcher to the right offline help page. The
  failed private build exposed missing webcam, input-method and family-control
  coverage that source-only assumptions missed.
- Make local reports private at their first write and resistant to link-based
  file clobbering. Test interrupted and concurrent output, not just happy paths.
- Make a failed native build recoverable as evidence: reserve a new directory
  instead of recursively deleting whichever path an environment variable names.
- Make website search understand ordinary questions and make navigation usable
  on small screens. Keep availability and compatibility claims consistent with
  current release evidence.
- Restore a dedicated local test backend without altering the broken Docker
  socket or unrelated virtual machines. Native boot evidence is still virtual
  evidence, not physical hardware certification.

## Completion means demonstrated behavior

Source tests, package construction, image construction, desktop boot, clean
installation, installed reboot, recovery, multi-user isolation, assistive use,
and physical hardware coverage are separate gates. Passing one does not imply
passing the others. The new image must receive fresh package inventories and
exact corresponding-source verification. Firmware, third-party rights and
artwork sign-offs remain qualified-human work; no legal guarantee is claimed.

The product already includes many advanced concepts. This pass prioritizes
finishing discoverable, documented workflows over adding untested promises or
claiming that an idea is unique across every operating system.
