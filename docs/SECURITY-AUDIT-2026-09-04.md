# Dagric OS and dagric.com security audit — 2026-09-04

This is a defensive source, configuration, runtime and production-edge review.
It is not a penetration-test certificate and it does not claim that no defects
remain. The reviewed business identity is IMPRESSIONSDIRECT360 LLC, with
Dagric as the product/fictitious name.

## Outcome

- Confirmed website fixes are deployed to production.
- Confirmed operating-system fixes are in the source tree and staged Debian
  packages. They require a new ISO/package release before customers receive
  them.
- The local recording VM is running, but its unauthenticated VNC and noVNC
  interfaces are now bound to host loopback only. The container no longer runs
  privileged.
- No credential-shaped token was found across 4,511 tracked or non-ignored
  repository text files. The scan reports only the file and token class, never
  the matching value.

## Confirmed findings and fixes

### Website and edge workers

| Risk | Finding | Fix | Status |
|---|---|---|---|
| High | The contact endpoint could process an untrusted browser origin before rejecting it. | Reject unknown `Origin` values before rate limiting or storage. | Live |
| High | The Pro download session was passed in a query string by the installed upgrade tool. URLs can leak into logs and history. | Accept `Authorization: Bearer` and send the session through a private request header. | Worker live; OS client needs release |
| Medium | The contact endpoint did not enforce JSON or its real UTF-8 byte limit. | Require `application/json`, measure encoded bytes and return `415`/`413`. | Live |
| Medium | Worker failures around rate-limit/R2 bindings could escape as uncontrolled errors. | Fail closed with bounded `503` responses and no-store headers. | Live |
| Medium | Unsupported gate methods could reach purchase-validation work. | Allow only `GET` and `HEAD`; reject others before Stripe or storage access. | Live |
| Medium | Malformed byte ranges were not rejected precisely. | Validate safe integer ranges and return `416` without reading the private object. | Live |
| Medium | Static pages lacked several browser isolation headers and the purchase completion route was cacheable. | Add CORP, origin isolation, no-sniff, framing and referrer controls; make `/thanks-pro` private/no-store. | Live |
| Medium | The content policy allowed a broader execution surface than the site needs. | Add explicit frame, worker, media, manifest, mixed-content and Trusted Types directives. | Live |

Production worker versions deployed during the audit:

- Gate: `b9cc4635-1462-42be-8401-555674a12b98`
- Contact: `2e8a31c6-7d1d-436d-8fe0-125570d26b3d`

### Operating system and installers

| Risk | Finding | Fix | Release state |
|---|---|---|---|
| Critical | The AI setup path executed a mutable remote installer as root. | Replace it with a version-, size- and SHA-256-pinned Ollama archive; validate members and links; stage atomically through a narrow Polkit helper; harden the service. | Source/package staged |
| High | The Pro asset installer authenticated through a URL and trusted an unpinned archive. | Use a private authorization header, pin the reviewed archive digest, allow-list members, strip owner/permission metadata and retain rollback. | Source/package staged |
| High | Temporary copies of Firefox credential databases could remain after migration interruption. | Track them with `atexit`, remove immediately after use and force password/tab/context exports to mode `0600`. | Source/package staged |
| High | GE-Proton selection could take the first release asset, including the wrong CPU architecture, without validating the publisher's digest. | Select the exact x86-64 asset and require its published digest. | Source/package staged |
| Medium | Several temporary files and the QEMU monitor socket used predictable or reserve-later names. | Use private `mktemp -d` directories with cleanup traps and validate input before deriving or deleting an output path. | Source/package staged |
| Medium | The VM helper interpolated a username into a privileged shell string. | Pass the username as a positional parameter to a literal privileged command. | Source/package staged |
| Medium | The Remotion version used by the video pipeline was below its current security floor. | Upgrade and lock Remotion and its CLI to `4.0.520`; add dependency auditing to quality, build and release gates. | Source live |

The Ollama service is restricted to localhost, uses a dedicated system user,
starts with `NoNewPrivileges`, a private temporary directory, protected home
and system paths, a strict umask and only its model directory writable.

### Test and recording environment

| Risk | Finding | Fix | Status |
|---|---|---|---|
| High | noVNC was unauthenticated and published on every host interface. Anyone on the local network could have viewed or controlled the guest. | Bind raw VNC and noVNC to `127.0.0.1` only. | Running |
| High | The long-lived QEMU container ran with Docker `--privileged`. | Drop all capabilities, enable no-new-privileges, use a read-only root, limit PIDs and pass only `/dev/kvm`. | Running |
| Medium | QEMU options and paths were assembled by unquoted word splitting. | Build an exact positional-argument vector and validate the VNC display and web port. | Running |
| Medium | The test image and its direct Python control package were mutable. | Pin the Debian image by digest and `vncdotool` to `1.3.0`; make source checks enforce both. | Running |
| Medium | The KVM setup helper used an unpinned privileged image. | Pin the Alpine helper by digest and mount kernel modules read-only; ordinary checks run unprivileged. | Source live |

The current container reports `Privileged=false`, `ReadonlyRootfs=true`,
`CapDrop=["ALL"]`, `no-new-privileges`, and loopback-only port mappings. The
viewer returns HTTP 200 at `http://127.0.0.1:6080/vnc.html`.

## Login and remote-access review

- Autologin is limited to the disposable live trial session. The installed
  system does not enable it globally; Calamares presents it as an explicit
  owner choice.
- The Pro image ships an SSH server for owners who choose it, but the service
  and socket are disabled by default, root login is disabled, and SSH is
  removed from all ordinary firewalld zones including NetworkManager's shared
  hotspot zone.
- Build-time SSH host keys are removed. Each installed machine generates its
  own keys before SSH can start.
- USBGuard and container/runtime daemons remain off until the owner opts in.

## Validation evidence

The following passed after the fixes:

- worker unit tests: 6/6;
- browser runtime checks on the home, search, contact and purchase-result pages
  under the new content policy;
- live edge checks for rejected origins, preflight, media type and unsupported
  methods;
- source-policy scan, including 4,511 files, dependency pins and nine security
  contracts;
- browser migration security tests: 2/2;
- dependency audit: zero known production npm vulnerabilities;
- Dockerfile validation and full ShellCheck analysis of the changed VM/boot
  harnesses;
- clean rebuild of the pinned test image;
- package staging for all four Dagric packages, including the new privileged
  helper and Polkit policy;
- website link/sitemap/brand gate and production header verification;
- TLS 1.2 succeeds, TLS 1.1 is rejected and the current certificate validates
  for `dagric.com`.

## Remaining risks and required next proofs

1. **OpenSnitch on Pro still uses `/tmp/osui.sock`.** Upstream supports a
   per-user runtime socket on current 1.6.x, but Dagric must change both the root
   daemon and desktop UI endpoints together and prove the connection on an
   installed Pro boot. Changing one side silently turns the application
   firewall into a disconnected monitor. Until that proof exists, shared
   multi-user machines should leave OpenSnitch off. The public security page
   discloses this limitation.
2. **Some Debian AppArmor profiles are in complain mode.** They log rather than
   enforce. Converting all profiles without workload tests can break legitimate
   applications and is not safe as a blind bulk change.
3. **Physical-hardware proof is still missing** for enforcing Secure Boot,
   encrypted install/reboot, touchscreen login, broad graphics and Wi-Fi, and a
   keyboard-free Orca pass.
4. **The website still permits inline styles.** The site has many static inline
   style attributes but no untrusted HTML insertion sink. Removing this policy
   exception requires a mechanical style migration and a full visual regression
   pass.
5. **No independent third-party security audit has occurred.** This document is
   an internal defensive review.
6. **A new OS image has not been built from the final patched tree.** The VM is
   running the newest existing Pro ISO, dated 2026-09-04, inside the hardened
   harness. That ISO predates at least the final harness/source changes in this
   audit and must not be represented as containing every fix above.

## Release gate

Do not publish the next ISO until the full audit suite passes in a clean Linux
build environment, the new Free and Pro images are rebuilt and signed, and the
installed-system matrix confirms firewall state, unique SSH host keys, package
updates, migration permissions and AI installer rollback. Keep the OpenSnitch
limitation public until its prompt and daemon/UI connection are observed on the
new installed Pro image.
