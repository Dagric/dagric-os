# The Dagric update channel

How fixes reach machines that have already been sold.

This document used to describe a Docker-volume signing key, a `repo.ps1`
wrapper, and a future host called `repo.dagric.com`. None of those exist.
Docker on the build machine is permanently broken (Windows `AF_UNIX` bind
returns `EACCES` even elevated), which took the old signing key with it, and
`repo.dagric.com` was never registered. What follows is what actually runs.

## Two delivery paths, one source of truth

Everything lives in `config/includes.chroot/` (plus hooks). It reaches
machines two ways:

1. **The ISO** — `build.sh` bakes the files straight into the image.
   This is how new machines get their configuration.
2. **The APT repository** — `packages/build-repo.sh` assembles the *same
   files* into versioned `.deb` packages and generates a signed repo in
   `site/repo`. This is how machines you have **already sold** get fixes:
   bump a package version, publish, and every enrolled machine picks it up.

The channel is live. `https://dagric-os.web.app/repo/dists/trixie/Release`
returns `Origin: Dagric`, `Label: Dagric OS`, `Suite`/`Codename: trixie`.

Owners use **Dagric Update** (or `sudo dagric-update`) to install the newest
signed packages without reinstalling or touching their home files. Its routine
update path cannot remove packages or switch Debian releases; see
[DAGRIC-UPDATES.md](DAGRIC-UPDATES.md) for the exact preservation and recovery
contract.

The packages — do not trust a version number written into this document, read the
current one from `packages/*/DEBIAN/control` and what the channel already serves
from `site/repo/dists/trixie/main/binary-amd64/Packages`, because step 2 of the
checklist below has to raise the first above the second or `build.sh` refuses to
start. This line said a flat **1.1.0** long enough to be wrong about both: the
tree is at 1.1.3 and the channel publishes 1.1.1.

| Package | Contains | Bump it when... |
|---|---|---|
| `dagric-branding` | wallpapers, logo, SDDM theme, splash | the look changes |
| `dagric-desktop-defaults` | Plasma skel defaults, Firefox policies, `mimeapps.list` | default behavior changes |
| `dagric-security-policy` | sysctl hardening, APT no-recommends (conffiles) | the security baseline evolves |
| `dagric-tools` | `/usr/bin/dagric-*`, the wizard, manual, guide, welcome, styles, looks, icons, translations | the product itself changes |

`dagric-tools` is the one that matters most: before the channel existed, a bug
in a Dagric tool could only be fixed by reinstalling the operating system.

Nothing in `dagric-tools` overlaps `dagric-branding`. Two packages shipping the
same path is a dpkg **unpack error**, not a warning, so `logo/`, `sddm/` and
`splash/` belong to branding and are excluded from the tools package.

## Building and signing

```sh
sh packages/build-repo.sh          # → site/repo, signed and verified
```

It runs natively in WSL — no container. It requires `dpkg-deb`,
`apt-ftparchive` (from `apt-utils`) and `gpg`.

**One key, not two.** The old design generated a separate repo key. The
release key that already signs the ISO checksums —
**`6CE37402BA0A0EF8`** — signs the repository as well. A second key would be a
second irreplaceable no-passphrase secret guarding a threat model that does not
separate: whoever holds either can already publish a forged image *or* push a
package to every customer machine. The practical win is that an owner who
imported the key to verify their download is already set up to trust their
updates.

The key must be in the builder's keyring before the script will sign; it fails
loudly rather than publishing something unsigned. **Back it up.** It is not in
this git repo, and it cannot be regenerated — losing it means every enrolled
machine stops accepting updates.

## Layout: a suite repo, not a flat one

The repo uses `dists/trixie/main/binary-amd64`, not the simpler flat
`deb URL ./` form the old document described. That is not style, it is the
host. For a flat repo apt requests `URL/./Release` with the dot-segment
literally in the path, and Firebase Hosting's `cleanUrls` does not normalise it
away. Measured against the deployed site:

```
/repo/Release     -> 200
/repo/./Release   -> 302
```

apt followed the redirect, found no index, and reported *"does not have a
Release file"* — which reads exactly like a repo that was never published, on a
repo that was published perfectly. The `dists/` layout never emits a dot
segment, and is what every real Debian mirror uses anyway.

The packages are `Architecture: all`, but apt only looks in `binary-<arch>` for
architectures the `Release` declares, so `amd64` is what gets advertised.

## Publishing

`site/repo` is inside the website, so the same deploy that publishes the
download page publishes the channel:

```sh
firebase deploy --only hosting
```

Hosting it on the download site rather than a dedicated `repo.dagric.com` was
deliberate: it is already HTTPS, already deployed by one command, and is a name
the project controls — so the channel needs no new infrastructure and cannot be
lost with a lapsed domain.

## Enrollment

**New machines are already enrolled.** The ISO ships both halves:
`/usr/share/keyrings/dagric.gpg` and
`/etc/apt/sources.list.d/dagric.list`. Nothing to do.

**Machines installed BEFORE the channel existed** have neither file. Enroll one
with:

```bash
curl -fsSL https://dagric-os.web.app/repo/dagric-repo.gpg.asc \
    | gpg --dearmor | sudo tee /usr/share/keyrings/dagric.gpg > /dev/null

echo 'deb [signed-by=/usr/share/keyrings/dagric.gpg] https://dagric-os.web.app/repo trixie main' \
    | sudo tee /etc/apt/sources.list.d/dagric.list

sudo apt update
sudo apt install dagric-branding dagric-desktop-defaults dagric-security-policy dagric-tools
```

That last `apt install` is what a pre-channel machine needs and a new one does
not: on a factory image the files are already on disk but no package *owns*
them, so apt has nothing to upgrade. Installing the packages hands those paths
to dpkg, and every later fix arrives as a normal upgrade.

Verify enrollment worked:

```bash
apt-cache policy dagric-tools     # should show the dagric-os.web.app origin
```

## One published fix is silent; the other three are not

**This section said the opposite until 2026-08-29.** It stated that
`Origin: Dagric` was in no origin pattern and that no Dagric package ever
installed itself. That is no longer true, and this is the runbook an operator
reads before changing the policy — so it is worth being exact.

The policy lives in **`config/includes.chroot/etc/apt/apt.conf.d/52dagric-unattended`**,
which is a **conffile of `dagric-security-policy`**. It is no longer written by
`0300-hardening.hook.chroot`; that hook now only asserts it (by name, entry by
entry — see below). Editing the hook to change the policy does nothing.

| Package | Behaviour | Why |
|---|---|---|
| `dagric-security-policy` | **installs itself** | Kernel hardening sysctls and the APT policy. Its own description promises the baseline "can evolve via updates", which was untrue while nothing matched it. |
| `dagric-tools` | waits for a click | The wizard, Hub, manual, helpers — the owner's own tools. |
| `dagric-branding` | waits for a click | Wallpapers, login theme, splash. |
| `dagric-desktop-defaults` | waits for a click | Desktop and browser defaults. |

`Origins-Pattern` admits `origin=Dagric,codename=trixie,label=Dagric OS`; a
`Package-Blacklist` holds the other three back **by name**. The blacklist is the
only thing keeping them click-to-install — remove an entry and that package
starts installing itself silently.

**The origin string must match the published `Release` byte for byte.** Verified
2026-08-29 against the live channel: `Origin: Dagric`, `Label: Dagric OS`,
`Codename: trixie`. A mismatch does not error anywhere — the pattern simply
never matches and the baseline silently stops updating itself.

`0300-hardening.hook.chroot` asserts every one of the five origins and all three
held-back entries **by exact value**. It used to count them instead, and that
was measurably useless: `apt-config -c FILE` re-reads `/etc/apt/apt.conf.d`, so
the file was counted twice, and stock `50unattended-upgrades` added more on top —
a file with all four Debian security origins deleted still measured 8 and passed
a `>= 5` threshold. Do not turn it back into a count.

**Taking over a file that already exists.** `52dagric-unattended` and
`99dagric-app-names` shipped for months via `includes.chroot`, unowned by any
package, so every machine in the field has them on disk. A package that newly
claims such a path as a conffile makes dpkg prompt — and under
unattended-upgrades there is no stdin, so the upgrade **fails** with
`end of file on stdin at conffile prompt`. `dagric-security-policy`'s `preinst`
moves any unowned copy to `.dpkg-old` first. If you ever promote another
hook-written file to a conffile, add it to that list in the same commit.

## Release checklist

**BUILD FIRST, PUBLISH SECOND.** This list used to have them the other way round,
and that order cannot work: the build stages the `dagric-*` packages as local
files pinned above 1000, so once the channel already publishes the same version,
apt sees the same version offered with different bytes, calls it a downgrade, and
kills the build — about twenty minutes in. `build.sh` now refuses to start in that
state and says so in five seconds instead, but the fix is the ordering below.

1. Edit files in `config/includes.chroot/`
2. Bump `Version:` in **every** affected `packages/*/DEBIAN/control`
3. `sh build.sh` → new ISO, and the version gate confirms the channel is behind
4. `sh packages/build-repo.sh` → rebuilds and re-signs `site/repo`
5. Copy `out/SHA256SUMS` to `site/` and **re-sign it** — the build regenerates the
   sums, so `site/SHA256SUMS.sig` covers the previous contents until you do
6. `firebase deploy --only hosting` → the channel and the new sums are live
7. Commit, tag, and note the change in the news page
