# OpenSnitch local administrator boundary — 5 September 2026

Status: implemented in candidate source, with isolated automated evidence.
This is not installed-image, physical multi-user, or commercial-release approval.
The older image and any already-running interface are not retroactively fixed.

## Threat and supported mechanism

OpenSnitch's unprivileged interface is a gRPC **server**. Its root daemon is the
client. The prior `unix:///tmp/osui.sock` endpoint could be precreated by another
ordinary account, which is not solved by `/tmp`'s sticky bit.

The 1.6.9 upstream launcher supports `--socket` and `--socket-auth`; its config
fallback to `/tmp` occurs when it uses preferences rather than an explicit
argument. The daemon supports `-ui-socket`, and the actual packaged 1.6.9-3 binary
confirmed it through `chroot ... /usr/bin/opensnitchd -help`. Its existing service
starts with `-rules-path /etc/opensnitchd/rules`; that argument and all other
upstream unit privileges/restart settings remain in effect.

Primary evidence:

- [Upstream UI 1.6.9](https://github.com/evilsocket/opensnitch/blob/v1.6.9/ui/bin/opensnitch-ui)
- [Upstream daemon CLI](https://github.com/evilsocket/opensnitch/blob/v1.6.9/daemon/main.go)
- [Daemon socket override and config reload](https://github.com/evilsocket/opensnitch/blob/v1.6.9/daemon/ui/client.go)
- [Upstream configuration guide](https://github.com/evilsocket/opensnitch/wiki/Configurations)
- [Debian diversion lifecycle guidance](https://www.debian.org/doc/debian-policy/ap-pkg-diversions.html)

## Candidate implementation

- `systemd-tmpfiles` creates `/run/dagric-opensnitch`, root:sudo, mode `02770`.
  Ordinary accounts cannot bind or enter it. Existing sudo administrators are
  already authorized to administer the entire machine; this does not isolate
  administrators from each other.
- The daemon, shipped JSON and interface all use the exact local endpoint
  `unix:///run/dagric-opensnitch/osui.sock`. The wrapper validates the directory
  and trusted vendor executable/ancestors and refuses root GUI execution.
  No launcher fallback to `/tmp` is permitted.
- Package `dagric-tools` 1.1.19 introduces a dpkg diversion of the vendor command,
  covering both its menu and identical autostart command. Upstream updates still
  replace the diverted vendor file; Dagric does not copy/fork vendor Python code.
- A failed first installation/upgrade only reverses its newly created diversion.
  It does not stop the preexisting firewall or rewrite its settings. Ordinary
  upgrades preserve the diversion. Removal restores upstream configuration only
  when its address exactly matches Dagric's managed value, stops the managed
  daemon, warns that the protection has been removed, and does not restart it.
  The managed service drop-in is package-owned under `/usr/lib`, not a surviving
  `/etc` conffile. Python-absent removal warns that manual config recovery is needed.
- The privileged Pro-upgrade home-directory loop was removed. An absent UI
  default is written via QSettings by the logged-in account, not by root traversing
  arbitrary user-owned paths. Existing preferences are preserved.
- Nine new owner-facing messages are extracted with the Python gettext parser
  and translated/compiled in all five locales: 670 entries each, zero fuzzy or
  untranslated entries. This is automated completeness, not native-speaker review.

## Owner experience and remaining limits

The installed Calamares `users.conf` inspected in the failed Pro build lists
`sudo` in `defaultGroups` and sets `sudoersGroup: sudo`; its first owner therefore
has the required group. Standard accounts cannot open this machine-wide control
interface. Their existing OpenSnitch rules and the separate system firewall
remain applicable. With no administrator interface connected, unmatched traffic
follows the daemon default, initially **allow**. This is not a deny-by-default
security guarantee. Expected nonadministrator autostart refusal has no blocking
dialog. The offline help explains these limits and asks owners to sign out/back
in or restart after upgrading so an old running UI is replaced.

The managed local launcher uses filesystem access control and explicit `simple`
authentication, not TLS. It does not use custom remote/TLS UI preferences. Custom
administrator network configurations require their own compatibility review.
There are no shared private keys embedded into the image.

## Evidence and required follow-up

`test/test-opensnitch-boundary.py` passes 14 checks as root in Debian WSL:
directory ownership/type/mode rejection, no root GUI, no nonadmin modal, no
endpoint override, trusted executable ancestors, exact admin launch arguments,
preference preservation, narrow private atomic config migration, invalid and
linked configuration refusal, and source/package/translation wiring.

Its isolated synthetic-UID test lets UID 65534 bind a **test** public temporary
socket, proves the same UID receives EACCES for the **test** protected endpoint,
and lets a nonroot process with supplementary sudo membership bind the protected
endpoint with inherited group ownership. It touches neither real
`/tmp/osui.sock` nor real `/run/dagric-opensnitch` and creates no user accounts.

`test/test-opensnitch-package.py` passes 11 checks using actual dpkg lifecycle transactions in
unmounted temporary chroots, including fresh install, Free-to-Pro, vendor update,
first-introduction abort, later-version abort, removal without purge, reinstall,
missing-Python operation, conflicting diversion and config preservation. Runtime
log assertions prove abort handlers leave the old service untouched, while
successful removal stops and reloads without restarting it.

Required before approval: boot/install the candidate, observe real administrator
connection prompts and rule enforcement, perform two genuine local-account
prebind/connection attempts, test logout/login/restart and package upgrade on the
installed system, and capture physical multi-user evidence. The physical release
gate remains unapproved. Existing historical security disclosures must not be
replaced with claims that deployed/older images have passed this work.
