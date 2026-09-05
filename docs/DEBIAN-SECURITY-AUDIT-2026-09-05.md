# Debian package security audit — 5 September 2026

## Outcome

The failed private Pro build contains current Debian security updates, but it is **not free of known upstream vulnerabilities**. The highest-priority unresolved package groups are Chromium, runc/containerd and CUPS. At the time of this check, no newer fixing version for these candidates was available from the official `trixie-security` amd64 index. Installing a testing/unstable or bookworm package is not an appropriate substitute for a reviewed trixie fix.

This was read-only. No package upgrade, package-list refresh, service start, source-list change, exploit attempt or chroot modification was performed.

## Evidence scope

- Examined `/var/tmp/dagric-private-pro.23yIyD/build/chroot/var/lib/dpkg`, belonging to the failed private Pro build, not a finished image.
- `dpkg-query` reported **2,300 installed binary packages** from **1,297 distinct source package names**. Debian source versions were used, preserving epochs and separating binary rebuild suffixes such as `+b4`.
- 533 installed source names had records in the official [Debian Security Tracker JSON](https://security-tracker.debian.org/tracker/data/json). Absence from the tracker is not proof of safety.
- Tracker retrieved at `2026-09-05T16:29:13Z`; HTTP Last-Modified `2026-09-05 14:31:07 GMT`; response SHA-256 `25c1a76fb7a4f6ca0c44df341d16fb3d7a3b48a7225e37e14c46e26deaaa7620`.
- Compared only `releases.trixie`, using `dpkg --compare-versions`, rather than treating fixes in sid/forky as available stable updates. Excluded no-DSA/ignored/postponed and unimportant/end-of-life entries from the actionable-candidate scan.
- For the retained records, no installed source version was older than an already-recorded trixie fixed version. A high/critical-urgency-only query returned zero open entries, **but this is misleading by itself**: several important CVEs have Debian urgency “not yet assigned.” The review below includes these.
- Independently retrieved the official [trixie-security amd64 Packages index](https://security.debian.org/debian-security/dists/trixie-security/main/binary-amd64/Packages.xz) at `2026-09-05T16:32:14Z`, Last-Modified `2026-09-04 18:04:19 GMT`. It confirms the versions below. This HTTPS index read is an availability check; actual installation must continue to use APT's signed Release verification.

## Prioritized unresolved candidates

| Component in failed chroot | Exact installed version | Verified Debian issue and practical scope | Official trixie fix available at audit time? |
| --- | --- | --- | --- |
| Chromium and chromium-common | `152.0.7977.75-1~deb13u1` | Debian marks the current trixie package vulnerable to the new `CVE-2026-85042` through `CVE-2026-85053` group. Desktop-relevant examples include DevTools use-after-free, V8 race/type confusion and Compositing/Skia memory errors. Android/iOS-specific entries must not be counted as demonstrated Linux exposure. | **No.** The security index still contains `.75`; `.82` is shown in sid/bookworm-security, not trixie-security. [Debian Chromium record](https://security-tracker.debian.org/tracker/source-package/chromium). |
| runc | Binary `1.1.15+ds1-2+b4`; source `1.1.15+ds1-2` | `CVE-2025-31133`, `CVE-2025-52565`, `CVE-2025-52881`, `CVE-2026-41579` remain vulnerable for trixie. Container setup/mount/path issues can cross isolation boundaries under the prerequisites described in the advisories. In particular, the procfs-write issue includes a malicious Docker build scenario. | **No.** The tracker shows the installed trixie source version vulnerable and fixes in forky/sid; runc is absent from the security index checked. [Package record](https://security-tracker.debian.org/tracker/source-package/runc), [procfs-write CVE](https://security-tracker.debian.org/tracker/CVE-2025-52881). |
| containerd | `1.7.24~ds1-6+deb13u1` | `CVE-2026-53488`: image labels passed through the CRI plugin can result in host command execution when consumed by a susceptible plugin. `CVE-2026-46680` concerns bypassing Kubernetes runAsNonRoot; `CVE-2026-47262` concerns crafted-image resource exhaustion. These do not prove that every default Docker workflow is exploitable. | **No.** Installed version equals the security index version. Debian shows the CRI label issue fixed in forky/sid, with upstream fixes including `1.7.33`; no trixie fixed version is recorded. [Debian CVE-2026-53488](https://security-tracker.debian.org/tracker/CVE-2026-53488). |
| CUPS / cups-daemon | `2.4.10-3+deb13u2` | `CVE-2026-34980` permits command execution as the printing user when a network-exposed shared PostScript queue meets the advisory conditions. Other open CUPS entries require separate reachability review. | **No.** Installed stable `+deb13u2` is newer than security-index `+deb13u1`; Debian still marks it vulnerable. A fixed unstable version exists, but it is not an available trixie fix. [Debian CUPS CVE](https://security-tracker.debian.org/tracker/CVE-2026-34980). |

## Actual configuration checked

- The failed chroot's CUPS configuration listens on `localhost:631` and `/run/cups/cups.sock`. No `printers.conf` exists, and `cups-browsed` is not installed. Thus the network-shared queue prerequisites of CVE-2026-34980 are absent in the inspected configuration. This reduces that exposure; it does not patch CUPS or establish local-user safety.
- `docker.service`, `docker.socket`, `containerd.service` and `ssh.service` enablement symlinks still exist in the unfinished chroot. This is not a runtime finding: build hooks had failed and the image was not booted. The finished image must prove the promised inactive defaults. Presence of an installed runtime alone does not mean a listening service.
- `/etc/containerd/config.toml` has a CRI section and no explicit CRI-disable directive. It does not establish the presence of an exploitable label-consuming external plugin. Review whether CRI is needed for the advertised desktop workflow before enabling it.
- `chromium-sandbox` is not installed. That alone does not prove Chromium has no sandbox: its alternative namespace sandbox must be tested in the actual non-root desktop session. Never use `--no-sandbox` as a workaround.
- The chroot includes `firefox-esr 140.15.0esr-1~deb13u1`, matching the security index, and kernel source `6.12.107-1`, also matching the security kernel. This does not resolve Firefox branding approval or prove all browser/kernel issues fixed.
- The tracker contains many untriaged kernel records (548 retained open records in this query), including architecture/driver-specific entries. These are a triage queue, not 548 demonstrated exploitable flaws in this amd64 build. AMD microcode entries similarly need CPU/firmware-specific validation.

## Recommended release actions

1. Re-run this source-version comparison against the final image's dpkg database after the new build; this failed chroot is not release evidence.
2. Keep the release hold. Wait for an appropriate trixie fix, review a supported backport, or explicitly restrict/remove affected optional functionality after dependency and UX testing. Do not silently mix distribution suites.
3. Prove Docker, containerd, SSH and their activation sockets are inactive at first boot. Avoid using untrusted container images/build recipes with the flagged runtime versions. Review the CRI plugin as a separate optional capability.
4. Keep printing local by default and validate that enabling printer sharing makes its effect clear. Preserve the distinction between configuration mitigation and a patched package.
5. Verify Chromium sandbox behavior in a normal user session, and do not promote its flagged version as the safe default browser. Recheck trixie-security immediately before any release.
6. Continue package-specific triage for network parsers, media tools, rsync, firmware and kernel drivers. Unknown urgency is not low severity. Nothing in this audit replaces boot/runtime, multi-user, accessibility or hardware testing.

## Repeatable read-only inventory command

Inside Debian/WSL, set the exact chroot database path and query it without entering the chroot:

```sh
dpkg-query \
  --admindir=/var/tmp/dagric-private-pro.23yIyD/build/chroot/var/lib/dpkg \
  -W '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\t${db:Status-Status}\n'
```

Keep only `installed` rows. Group by source package and source version, join to the official JSON's `releases.trixie`, and use `dpkg --compare-versions INSTALLED lt FIXED` only where the tracker supplies a real fixed version. Compare any proposed update against the current **trixie** or **trixie-security** repository version. Review open records whose urgency is unassigned instead of filtering them out. The [Debian tracker documentation](https://security-tracker.debian.org/tracker/) explains the data source and links its official machine-readable interface.
