# Completed-candidate security re-audit — 5 September 2026

## Later complete declared-dependency check

The later final run, with tracker collection at **18:59:57 UTC**, supersedes
the primary-only coverage limitation below. It reverified all three stable
repository signatures and all 24 architecture/component indexes, and still
found **zero newer installed binary packages** in those stable suites.

Exact declared embedded dependencies are now separately inventoried and triaged:
89 source/version identities for Free and 580 for Pro. Both include underlying
`linux 6.12.107-1` via the installed signed kernel's `Built-Using` field.
There are 691 Free and 945 Pro declared-dependency tracker rows, **not unique
exploitable vulnerability counts**. These overlap the unchanged 936/1,900
primary-source rows and must not be summed. Undeclared vendor code and runtime
reachability still require review.

The parser reuses the strict declared-source validator and preserves epochs,
folded fields, held-installed packages and multiarch attribution. It rejects
non-exact declarations and requires one-to-one installed status/manifest
coverage. Priority summaries separate different versions of the same source.

An actual upstream tracker-data defect also surfaced: the trixie fixing-version
field for `golang-golang-x-net` / `CVE-2023-45288` is
`1:0.23.0+dfsg-`, which `dpkg` rejects. The affected exact embedded versions
remain explicit unresolved comparison records; a tracker `resolved` label does
not clear them. Version syntax is now checked separately before comparison,
including cases where `dpkg --compare-versions` merely warns and returns 0/1.
No version was guessed or rewritten. [Debian tracker record](https://security-tracker.debian.org/tracker/CVE-2023-45288).

All **28 offline regressions pass** in Debian WSL, including real-dpkg invalid
version tests. The final audit captures implementation hashes before collection
and refuses a final report if the auditor or declaration parser changes during
the run. No tool edits occurred during this final collection.

Final receipt:
`out/private-candidate-security-20260905-release-check/candidate-security-audit.json`,
SHA-256 `3e6c9458a2aab6b0a5f3d391f5aae99d0d276603222626df759cf8e4aed7da62`.
Earlier embedded attempts are retained: `...-embedded` stopped on the malformed
tracker version and wrote no final report; `...-embedded-final` preceded strict
warning-only version validation and was superseded by this final check.

This work improves security evidence and prevents false passes. **It does not
patch the unresolved Chromium/container/printing issues or clear release.**

## Earlier primary-package collection

## Result

**Security release hold remains.** The completed, immutable Free and Pro
candidate inventories have now been checked against freshly downloaded,
signature-verified Debian repository metadata. This replaces the earlier
failed-chroot inventory as the subject of the current package check.

No newer installed Debian binary was available from the checked `trixie`,
`trixie-updates` or `trixie-security` repositories at 18:32 UTC. This includes
Pro's 198 i386 binaries, not just amd64. The installed Chromium, runc,
containerd and CUPS versions still have unresolved priority tracker records.
Being current in a stable repository does **not** mean every vulnerability
has been patched.

No package was installed, APT cache refreshed, repository suite mixed, runtime
service changed, image modified, release approved or public artifact uploaded.
The tool's zero exit code means evidence collection succeeded, not that the
candidate is secure or ready to release.

## Exact candidate and provenance

Source commit: `20e24dd04ea3de802531be5139f9f36fe96a1490`.

| Edition | Image SHA-256 | Installed rows | Architecture breakdown |
| --- | --- | ---: | --- |
| Free | `0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc` | 1,771 | 1,491 amd64; 280 all |
| Pro | `69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa` | 2,498 | 1,896 amd64; 404 all; 198 i386 |

Inputs are the extracted immutable manifests, dpkg status databases and
source-version inventories under
`out/private-source-candidate-20e24dd0-20260905/manifests/`.
Each manifest hash was checked against `immutable-input-receipt.json`;
every installed binary/version row was matched to that manifest, and every
source attribution was matched to the extracted dpkg database. Debian epochs,
binary rebuild versions and foreign architectures are preserved.

The installed source-inventory SHA-256 values match the earlier artifact audit:

- Free: `63e1caaf39017395e8389fe46926f4fc4216937399515cb2e67ba64a051b59c3`.
- Pro: `4435f26648c55764422870815f8d9c830c837114fa23864e6c67e1f569f0a1dc`.

This pass did not re-extract or rehash the original multi-gigabyte images.
The binding relies on the recorded extraction receipts described in
[the private artifact audit](PRIVATE-CANDIDATE-AUDIT-2026-09-05.md), not a new
portable signed image attestation.

## Fresh repository evidence

The auditor verified all three `InRelease` files using `gpgv` and the local
Debian archive keyring, SHA-256
`506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017`.
It required Debian origin, the exact codename, no future issue date and an
unexpired `Valid-Until` for security/updates. Stable's point-release metadata
does not contain `Valid-Until`; this limitation is recorded rather than
inventing an expiry period.

For each suite it checked the signed length and SHA-256 of all four components
(`main`, `contrib`, `non-free`, `non-free-firmware`) for both amd64 and i386:
24 compressed Packages indexes in total. Package versions were compared with
`dpkg --compare-versions` against the matching architecture only. The four
Dagric-owned packages are appropriately absent from Debian's indexes; every
other installed binary had a matching repository entry.

| Signed index | Signed Date | Valid-Until | InRelease SHA-256 |
| --- | --- | --- | --- |
| trixie | 11 July 2026 09:02:23 UTC | Not supplied | `98b25b5cd185c59d34aa6e4c3e9b5b8f01bbe9d104fe2dcfbcd30dc0a14a59ed` |
| trixie-updates | 5 September 2026 14:10:12 UTC | 12 September 2026 14:10:12 UTC | `809436cf91d55dd1a22e4c058cd33177c847de3ed945f5d6653ead0c8cb7badb` |
| trixie-security | 5 September 2026 13:22:26 UTC | 12 September 2026 13:22:26 UTC | `7d59d4d519745158ccb48f7b17d14266f8657770d14023633575cd5f228c6c48` |

The [Debian Security Tracker JSON](https://security-tracker.debian.org/tracker/data/json)
was retrieved at `2026-09-05T18:32:08.545532+00:00`, Last-Modified
`Sat, 05 Sep 2026 17:41:19 GMT`, SHA-256
`020779778767a9e2eab9414d0a23cdfd760e2f2bdadc7cc948b29012e3c2d7e0`.
That JSON is an HTTPS observation, **not** a signed advisory attestation.

## Priority findings and actual exposure

| Component | Exact candidate version | Current conclusion |
| --- | --- | --- |
| Chromium, Pro only | `152.0.7977.75-1~deb13u1` | Twelve newly open records in the `.82` advisory group remain in the tracker. Linux-relevant V8, compositing, DevTools and other issues need a fixing trixie build. Android/iOS-only records are not proof of Linux exposure. The existing normal-user sandbox observation is useful but does not fix browser memory-safety issues. [Debian Chromium](https://security-tracker.debian.org/tracker/source-package/chromium). |
| runc, Pro only | Binary `1.1.15+ds1-2+b4`; source `1.1.15+ds1-2` | Four open records remain; no newer stable binary was found. **CVE-2026-41579 is explicitly not exploitable under Docker**, because of Docker's layer handling, per its advisory. Do not generalize that exemption to the other three issues. [Debian CVE-2026-41579](https://security-tracker.debian.org/tracker/CVE-2026-41579). |
| containerd, Pro only | `1.7.24~ds1-6+deb13u1` | Three open records remain. The CRI label issue depends on CRI and a label-consuming plugin; this is not proof that every default Docker use is exploitable. Other resource-exhaustion and Kubernetes-policy issues require separate reachability analysis. [Debian containerd](https://security-tracker.debian.org/tracker/source-package/containerd), [CRI label advisory](https://security-tracker.debian.org/tracker/CVE-2026-53488). |
| CUPS, both editions | `2.4.10-3+deb13u2` | Eleven raw open records require package-specific triage. For CVE-2026-34980, the network-exposed shared PostScript-queue prerequisites are not present in the immutable default configuration. This is mitigation evidence, not a CUPS patch or local-user safety result. [Debian CUPS advisory](https://security-tracker.debian.org/tracker/CVE-2026-34980). |

The [runc procfs-write advisory](https://github.com/opencontainers/runc/security/advisories/GHSA-cgrx-mc8f-2prm)
describes a malicious Docker build scenario for CVE-2025-52881, and says
upstream runc 1.1.x is no longer supported. Disabling startup services cannot
make that version safe when the owner later runs untrusted images or recipes.
The substantial upstream patch series and dependency changes are not a safe
one-line local backport. A supported Debian fix or separately maintained,
reviewed and tested package migration is required.

### Printing and CRI default review

- CUPS in both immutable filesystems listens on `localhost:631` and the Unix
  socket. `cups-browsed` is absent. `Browsing Yes` still allows advertising
  shared queues; it is not the same as remote-printer discovery being enabled.
- `dagric-pdf-queue.service` creates a PDF queue at first boot with
  `printer-is-shared=false`. The absence of `printers.conf` in the preboot
  filesystem must not be described as absence of a queue after boot. Installed
  tests should confirm the actual queue's shared flag and effective listeners.
- A prospective `Browsing No` plus `DefaultShared No` default is consistent
  with keeping local printing and PDF output while making server sharing an
  explicit choice. The [CUPS configuration manual](https://openprinting.github.io/cups/doc/man-cupsd.conf.html)
  distinguishes advertisement from queue sharing. Before shipping a change,
  test PDF output, a real printer, network-printer discovery, and owner-enabled
  sharing. No such runtime/configuration change was made in this pass.
- Upstream [containerd's CRI guide](https://github.com/containerd/containerd/blob/release/1.7/docs/cri/config.md)
  says CRI configuration is not used by Docker/Moby, `ctr` or `nerdctl`.
  Its [configuration manual](https://github.com/containerd/containerd/blob/release/1.7/docs/man/containerd-config.toml.5.md)
  documents `disabled_plugins`. This supports testing an explicit
  `io.containerd.grpc.v1.cri`-disabled desktop default. It must preserve existing
  configuration and non-CRI plugins, pass Docker/Compose smoke tests, and
  document how an owner deliberately opts into Kubernetes/CRI. It does not
  fix runc or non-CRI containerd vulnerabilities. No candidate was changed.

## Why raw counts are not vulnerability claims

The machine report retains every non-resolved primary-source tracker record,
including unimportant, no-DSA and unassigned-urgency records, plus any resolved
record whose fixing trixie source version is newer than the installed version.
No older-than-recorded-trixie-fix case was found.

| Edition | Raw records retained | Unassigned urgency | Unimportant | Low | Primary source names with no tracker records |
| --- | ---: | ---: | ---: | ---: | ---: |
| Free | 936 | 647 | 285 | 4 | 586 |
| Pro | 1,900 | 1,459 | 435 | 6 | 764 |

These are **triage records, not counts of demonstrated exploitable flaws**.
Zero high/critical-labelled records is not clearance: priority container and
Chromium records have not-yet-assigned Debian urgency. Conversely, the two
Firefox raw entries illustrate why human interpretation matters:

- Debian says the locale-exposure entry is not a security issue in Firefox by
  itself. [CVE-2019-12383](https://security-tracker.debian.org/tracker/CVE-2019-12383).
- Debian's notes say current Firefox uses the system libvpx; the current
  libvpx package is fixed, despite the historical Firefox source entry still
  reading open/unimportant. [CVE-2023-5217](https://security-tracker.debian.org/tracker/CVE-2023-5217).

This primary-source audit does **not** cover all declared or undeclared
embedded/vendor dependencies. In particular, Free's signed kernel package
names `linux-signed-amd64` as its packaging source; underlying `linux` appears
through `Built-Using`. Pro additionally has a direct Linux source row from
`linux-libc-dev`, producing 609 raw kernel records. The resulting Free/Pro
count difference is not proof of different kernel safety. Embedded source
mapping, source delivery and version-aware vulnerability triage remain
separate requirements. Absence of tracker records is not proof of safety.

## Reproduce and inspect

Read-only audit; supply a **new** output directory so earlier evidence is not
overwritten:

```sh
python3 tools/audit-candidate-security.py \
  --candidate out/private-source-candidate-20e24dd0-20260905 \
  --output out/private-candidate-security-NEW-AUDIT
python3 test/test-candidate-security-audit.py
```

All **17 offline regressions passed** in Debian WSL: suite/origin/date checks,
expired metadata, duplicate fields, corrupted index bytes, stable's explicit
expiry limitation, unknown/no-DSA retention, stable-vs-sid isolation, resolved
records on old candidates, Debian epoch/binNMU ordering, and architecture
separation. Actual signature verification also succeeded for this collection.

Final evidence is in `out/private-candidate-security-20260905-multiarch/`:

- `candidate-security-audit.json`, SHA-256
  `95952d9171153a880f94fb5de588c5135c0b4ba0e91ecf04208e96cdbabd07f6`.
- Per-suite `InRelease`, verified cleartext `Release`, signature logs, and
  24 checksum-verified compressed package indexes.
- The exact tracker JSON and its retrieval metadata.

The earlier `out/private-candidate-security-20260905-reaudit/` amd64-only
collection is retained as history and **superseded** for update-availability
conclusions by the multiarch collection. Nothing in either report closes
runtime, physical hardware/Secure Boot, multi-user, artwork, firmware rights,
browser trademark or corresponding-source release gates.
