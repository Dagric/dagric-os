# ISO promotion audit — 2026-09-02

## Decision: do not publish the local candidates

The local ISO pair is newer than the currently published Dagric 1.0 release, and its file hashes agree with its local `out/SHA256SUMS`. That is necessary evidence, but not sufficient for promotion. The local checksum signature is invalid, and the candidates lack the clean/reproducible release provenance and physical/destructive qualification required for a public release.

## Artifact identity

| Artifact | SHA-256 | Local checksum match | Promotion status |
| --- | --- | --- | --- |
| `out/dagric-os-1.0-amd64.iso` | `8777d8223604cb035bfa74aabb33bff28233a603ded513a5db776cf144ca3238` | Yes | Do not publish |
| `out/dagric-os-pro-1.0-amd64.iso` | `5a0c0b165bac2eaaa45b8745dd3e45f84471369e115d749e19a1d61acb67b70a` | Yes | Do not publish |
| `out/_testing.iso` | `fc0fbee526a6347698ca2373cd4444b9e1d52ad2f7113ad31079b042749a55e6` | No recorded candidate trail | Do not publish |

## Blocking evidence

1. `out/SHA256SUMS.sig` reports **BADSIG** against the current local `out/SHA256SUMS` when verified with `out/dagric-signing-key.asc`.
2. The newer local hashes differ from the public signed Dagric 1.0 hashes. Replacing the website would therefore be a release promotion, not a routine file refresh.
3. The documented candidate audit records a dirty working tree and explicitly says the images are valid local test artifacts, not reproducible release artifacts tied to a reviewed commit.
4. Physical hardware qualification and destructive recovery/update drills remain open, including retail Secure Boot, GPU/Wi-Fi/audio/Bluetooth/suspend, interrupted updates, Btrfs ENOSPC, snapshot boot/rollback, and backup-restore.
5. The separate `_testing.iso` is mounted by the current QEMU test container but does not match the documented local candidate hashes or the published release. It has no usable promotion evidence.

## What did pass

- The two canonical `out/dagric-os*.iso` files hash to the values in the current local `out/SHA256SUMS`.
- Prior records report automated source, package, QEMU boot, installer, and installed-system gates for the canonical candidate pair.
- The currently public website serves a separate signed Dagric 1.0 release with a valid published checksum signature.

## Required before promotion

1. Freeze and review a clean commit.
2. Rebuild the intended edition(s) from that commit.
3. Recompute checksums and create a fresh detached signature that verifies with the published release key.
4. Complete the remaining recovery and representative physical-hardware evidence.
5. Upload to a staging location, download back, compute hashes, and compare against the newly signed checksum file.
6. Only then update the release manifest/download links and deploy the site.
