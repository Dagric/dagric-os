# Private candidate artifact audit — 5 September 2026

## Outcome and scope

The completed Free and Pro candidate images record the same source commit,
`20e24dd04ea3de802531be5139f9f36fe96a1490`. Their immutable filesystems contain
the reviewed OpenSnitch control-socket guard and private-state writer fixes.
The final Pro filesystem no longer contains the Docker, containerd, or SSH
startup dependencies seen in the earlier failed build.

The priority upstream package versions are **unchanged** from today's
[Debian security audit](DEBIAN-SECURITY-AUDIT-2026-09-05.md). Disabling optional
services is a configuration mitigation, not a fix for those package CVEs.
These are private developer candidates, not an approved release. No release
signature, public upload, payment enablement, or approval was performed by this
audit. Upstream-signed EFI components are distinct from a signed Dagric release.

The paired static checker passed at 17:48:30 UTC. This audit
does not certify runtime service state, physical Secure Boot, browser sandbox
behavior, installed multi-user isolation, accessibility, hardware compatibility,
rights approvals, corresponding-source completeness, or release readiness.

## Exact artifacts

Both originals were retained without modification:

| Edition | Original final artifact | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Free | `/var/tmp/dagric-private-free.C8Eu6N/source/out/dagric-os-1.0-amd64.iso` | 1,999,503,360 | `0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc` |
| Pro | `/var/tmp/dagric-private-pro.QoSTpV/source/out/dagric-os-pro-1.0-amd64.iso` | 3,901,456,384 | `69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa` |

The new private view is `/var/tmp/dagric-artifact-audit.Zee11G`. Its per-edition
ISO files are private copies, alongside copied checksum receipts and exact
`SOURCE_COMMIT-free` / `SOURCE_COMMIT-pro` receipts. Neither an older Pro image
nor the earlier commit-34 Free image was substituted into this pair.

## Paired immutable gate

Command run as root in Debian WSL:

```sh
sh '/mnt/c/Users/1248n/Documents/ChatGPT/Dagric Os/tools/check-artifacts.sh' \
  --pipeline-only /var/tmp/dagric-artifact-audit.Zee11G
```

Final result: **passed, exit 0**, from 17:47:56 to 17:48:30 UTC. The checker
file's SHA-256 was
`582cb7bac18153a253dddb29732c74041d5ed684ccaf9857a7dc4c91c642f804`.
The unchanged checker covers:

- SHA-256 verification and matching exact source-commit receipts.
- Required shared packages, Pro-only package split, and edition markers.
- Adaptive Pipeline and Foundations payloads, timer wiring, and service limits.
- Nine security source files compared byte-for-byte with the recorded commit,
  allowing CRLF normalization; payload owner/mode and package ownership checks.
- Managed OpenSnitch diversion, launcher/menu/autostart route, runtime-directory
  policy, and daemon endpoint wiring.
- Pro absence of enabled dependencies for `docker.service`, `docker.socket`,
  `containerd.service`, `ssh.service`, `sshd.service`, and `ssh.socket`.
- EFI signature-list inspection and plausible edition sizes.

The first run passed the checksums, package and security checks, and EFI checks,
then failed the final size assertion because `stat -c %s` measures a symlink
itself. The initial audit view used ISO symlinks. This was an audit-view
compatibility issue: the actual Free image was 1,999,503,360 bytes, not a small
image. The initial log was preserved, only those two exact private-view
symlinks were replaced with copies, and the unchanged checker was rerun. No
gate was weakened and no original artifact was overwritten.

`sbverify --list` reports Microsoft-signed shim and Debian-signed GRUB in both
images, including the Microsoft 2011/2023 and Debian 2022 signer identities.
These are static signature-presence/identity observations. The initial
checker's wording that retail firmware "will accept" the image was not a
finding of this audit: firmware trust databases, revocations, actual signature
validation, and physical boot behavior require separate evidence.

The misleading output was then corrected in `tools/check-secureboot.sh`,
without changing any validation condition or exit-status gate. It now reports
static signature presence/identity only and explicitly leaves cryptographic
chain validation, firmware trust/revocation checks, and physical evidence
pending. Two verdict-output regressions were added to the existing artifact
test suite; all 13 tests and ShellCheck at error severity passed. The updated
EFI checker was rerun against both exact private ISO copies at 17:52:27 UTC;
both returned 0. Its SHA-256 was
`6f9078338d91401d8c6c0b6ea3102320ad7036068d1ef5431d0bdb4ba11de5e7`.
This is an audit-tool wording change, not an OS-payload rebuild or new boot.

## Installed package inventory

Both `/live/filesystem.packages` and the immutable dpkg status database were
extracted without running image code. `dpkg-query --admindir=...` read the
extracted status database and retained only installed rows. Source versions
preserve epochs and distinguish binary rebuild suffixes.

| Edition | Manifest / installed binary rows | Distinct source names | Manifest SHA-256 | Installed source inventory SHA-256 |
| --- | ---: | ---: | --- | --- |
| Free | 1,771 | 1,004 | `b9785ef8f4cbd141762545d92131b339d0744d89687cc071ecdfd55234d29074` | `63e1caaf39017395e8389fe46926f4fc4216937399515cb2e67ba64a051b59c3` |
| Pro | 2,498 | 1,297 | `87f7e8110a45cb3489c4982736540f2f465576dc82d96935ee0f343dca20ed56` | `4435f26648c55764422870815f8d9c830c837114fa23864e6c67e1f569f0a1dc` |

The failed Pro chroot in the earlier audit had 2,300 installed binaries and
1,297 source names. The final Pro has 198 additional installed binary rows;
the unchanged source-name count must not be mistaken for identical package
contents. The source-mapping audit receives these exact final manifests and
dpkg inventories independently of any release approval.

## Priority version comparison

Comparison baseline: the failed Pro chroot
`/var/tmp/dagric-private-pro.23yIyD/build/chroot`, as recorded in
`DEBIAN-SECURITY-AUDIT-2026-09-05.md`. Its tracker snapshot was retrieved at
16:29:13 UTC and security-index snapshot at 16:32:14 UTC on 5 September. This
comparison uses that recorded assessment; it does not claim a fresh tracker
or repository check at the later artifact-audit time.

| Component | Final Free | Final Pro | Difference from recorded failed-Pro priority version |
| --- | --- | --- | --- |
| Chromium / chromium-common | Not installed | Binary/source `152.0.7977.75-1~deb13u1` | None in Pro |
| runc | Not installed | Binary `1.1.15+ds1-2+b4`; source `1.1.15+ds1-2` | None in Pro |
| containerd | Not installed | Binary/source `1.7.24~ds1-6+deb13u1` | None in Pro |
| CUPS / cups-daemon | Binary/source `2.4.10-3+deb13u2` | Same | None |
| Firefox ESR | Binary/source `140.15.0esr-1~deb13u1` | Same | None |
| Linux kernel | Binary `6.12.107-1`; underlying Linux source `6.12.107-1` | Same | None |

The kernel-image packages identify `linux-signed-amd64 (6.12.107+1)` as their
packaging source. The versioned image's `Built-Using: linux (= 6.12.107-1)`
identifies the underlying Linux source; it must not be confused with the
signed-wrapper source version. Pro also contains `linux-libc-dev` from Linux
source `6.12.107-1`. Both editions contain cups-filters source
`1.28.17-6+deb13u1`; the earlier report did not give a cups-filters baseline.

No priority package changed to a fixing version. The earlier report's
Chromium, runc/containerd, and CUPS concerns therefore remain unresolved by
this rebuild. Matching the previously available Firefox/kernel updates also
does not prove every issue fixed, nor does it settle Firefox branding rights.

## Configuration evidence and limits

- The Pro immutable filesystem has **zero** `.wants` / `.requires` paths
  enabling the six Docker/containerd/SSH units listed above under the checked
  systemd directories. This differs from the unfinished chroot. It confirms
  shipped enablement wiring, not that no unit can ever be started manually,
  by a dependency, or by another activation mechanism.
- Both editions' CUPS configurations listen on `localhost:631` and
  `/run/cups/cups.sock`; neither contains `printers.conf` or the `cups-browsed`
  package. They still say `Browsing Yes` / `BrowseLocalProtocols dnssd`, so
  this is not a claim that every discovery protocol is disabled. The earlier
  shared-queue prerequisites are absent in the inspected default files;
  CUPS itself is not patched by those defaults.
- Pro's containerd configuration still contains its CRI section with no
  explicit CRI-disable directive. Disabling the service at startup does not
  remove CRI code or patch its vulnerabilities when the owner enables it.
- Pro still lacks `chromium-sandbox`. As in the earlier audit, this does not
  establish failure of Chromium's alternative namespace sandbox; a normal
  non-root runtime test remains necessary. Free does not contain Chromium.
- Both images carry root-owned, non-group/world-writable copies of the nine
  reviewed security files. The private writer is wired into Pipeline, Twin,
  Restore Assistant, and Store. The OpenSnitch guard uses the package-owned
  drop-in under `/usr/lib/systemd/system`, root:sudo mode 02770 tmpfiles rule,
  and `unix:///run/dagric-opensnitch/osui.sock`. Free carries the guard for a
  later Pro install; Pro additionally carries the upstream UI diversion and
  the canonical managed menu/autostart route.
- The OpenSnitch default is still allow/monitor, with `InterceptUnknown`
  false. Its `ConditionKernelCommandLine=!boot=live` configuration skips the
  daemon in a live session. Neither setting is evidence that blocking rules
  or installed multi-user control boundaries have been tested in this pass.

## Private evidence paths

All paths below are under `/var/tmp/dagric-artifact-audit.Zee11G` in Debian WSL:

- `setup-receipt.json`, `copy-view-receipt.json` and both source-commit receipts.
- `paired-check-artifacts.log` and `paired-check-artifacts.json`: final run.
- `paired-check-artifacts.initial-symlink-view.log` / `.json`: preserved first
  run and the audit-view size-check failure.
- `{free,pro}/filesystem.packages` and `manifest-extraction.log`.
- `{free,pro}/dpkg/status` and `installed-source-versions.tsv`.
- `{free,pro}/security-payload-audit.json`: per-file hashes/source matches,
  root ownership/modes, package/source counts, priority versions, kernel
  Built-Using metadata, and inspected service/configuration evidence.
- `{free,pro}/secureboot-static-wording-recheck.log` / `.json`: exact-image
  reruns after correcting the static-check output wording.

These local receipts are evidence, not portable signed attestations or public
download links. The original images, build directories, and live guest were
not modified. Release holds and qualified-human approvals remain separate.

## Subsequent live-session check by the coordinating agent

At approximately 18:03 UTC the same Pro hash was running in guarded lab run
`e36e5e1382ec4e548919c179fa00d488`. Chromium launched through its normal menu
route without added sandbox-disabling flags. The actual `chrome://sandbox`
page reported namespace, PID/network isolation, Seccomp-BPF and TSYNC as active,
and its own summary said "You are adequately sandboxed." Yama ptrace protection
reported Broker Yes / non-broker No. This supplies the previously pending
normal-launch namespace-sandbox observation in the live session, not an
installed-system or exploit-resistance certification. Priority upstream
versions and CVE findings are unchanged. Full details and wallet-request
cancellations are in `NATIVE-LAB-RESTORED-2026-09-05.md`.
