# ISO promotion audit — 2026-09-02

## Decision: approved as a signed external-test candidate; hold stable promotion

The final Free and Pro images were built from the same clean, reviewed source
revision and passed the complete automated and virtual-machine release gates.
They are suitable for an explicitly labelled external hardware-testing release.
They must not replace the current stable downloads until the representative
physical-hardware and destructive-recovery rows below are completed.

The public website was not changed by this audit. Its existing signed release
remains available while the new candidate finishes physical qualification.

## Frozen release identity

Source revision: `848b0203b40c8988f94424342e8047a34c733c36`

| Artifact | Bytes | SHA-256 | Result |
| --- | ---: | --- | --- |
| `dagric-os-1.0-amd64.iso` | 2,256,076,800 | `ef02f18a982f82b0578abf264d97703b2db72c3725fef0835ef2ea6a2ddb504e` | PASS |
| `dagric-os-pro-1.0-amd64.iso` | 4,156,686,336 | `b150e00f7ad8aad226085cba70e034cc96112082aae23f710cdbba70a913c726` | PASS |

Both host exports independently matched the combined `SHA256SUMS`. The checksum
file was freshly signed and verified in an isolated keyring with Dagric release
fingerprint `3A079F85DE74375DD65557096CE37402BA0A0EF8`.

## Passed gates

| Gate | Evidence |
| --- | --- |
| Clean reproducible source identity | Both artifacts contain provenance for the same 40-character commit; release builds reject unknown or dirty source state. |
| Full source audit | 22/22 product contracts, 134 shell entry points, 20 JavaScript files, 317 package names, security/privacy, update, Rewind, Pipeline, Twin, Foundations, localization, desktop and website checks passed. |
| Repeated stress | 708 gate executions across 100 rounds passed after fixing a source-scanner race. |
| Transactional export | Docker-volume staging, host copy and independent host SHA-256 verification passed for both multi-gigabyte images. Partial exports are deleted and cannot be promoted. |
| Immutable artifact inspection | Checksums, edition markers, Free/Pro package split, Adaptive Pipeline, Foundations payloads, image sizes and provenance passed. |
| Secure Boot chain | Both images contain Microsoft-signed shim and Debian-signed GRUB. |
| Firmware boot matrix | Final Free reached the live UI under BIOS, UEFI and Microsoft-keyed Secure Boot; final Pro reached a usable KDE desktop under UEFI. |
| Free install | Fresh 50 GB GPT/UEFI/LUKS/Btrfs install, disk-only reboot, unlock and login passed; installed audit: 72 pass, 0 fail. |
| Pro install | Fresh 50 GB GPT/UEFI/Btrfs install, disk-only reboot and login passed; installed audit: 90 pass, 0 fail. |
| Rewind drill | On the final Pro install, Rewind created a pre/post pair, captured an `/etc` change, produced a privacy-bounded review and removed both test snapshots cleanly. |
| Signed update repository | Four packages were rebuilt; APT policy files parsed; `InRelease` and `Release.gpg` verified with the Dagric release key. |

## Remaining stable-release blockers

1. Run the candidate on representative physical Intel, AMD and NVIDIA systems,
   including retail Secure Boot firmware, Wi-Fi, audio, Bluetooth, suspend,
   battery, external display and high-DPI paths.
2. Complete destructive copies of the installed-system matrix: interrupted
   update/power loss, true Btrfs ENOSPC, snapshot boot and rollback, and a
   backup-restore drill.
3. Perform human accessibility checks for audible Orca output, reduced motion,
   keyboard-only setup and representative high-DPI displays.
4. Upload to a staging location, download both full artifacts back, verify them
   against the signed checksum file, and only then change the public manifest
   or stable download links.

Unsupported Windows kernel drivers and game anti-cheat remain compatibility
limits, not defects that a Linux distribution can bypass. Dagric must continue
to report compatibility per title and must not claim that every Steam game
works.

## Promotion rule

The candidate may be offered to informed testers with the limitations above.
Stable/general-availability promotion is a **NO-GO** until every remaining
blocker has dated evidence and the staged-download hashes match the signed
manifest.
