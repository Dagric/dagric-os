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

The packages, all currently at **1.1.0**:

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

## A published fix is not a silent fix

`0300-hardening.hook.chroot` allows unattended-upgrades to install from four
Debian origins. **`Origin: Dagric` is not among them**, and that is the current
behaviour whether or not it was intended: publishing a new `dagric-tools` does
not silently push it to machines. Owners see it in Discover (the PackageKit
backend and the packagekit daemon both ship, so APT updates do surface) and
install it with a click.

If the intent is that a shipped bug can be fixed without the owner noticing,
add `"origin=Dagric,label=Dagric OS";` to that hook's `Origins-Pattern`. If the
intent is that changes to the owner's own tools are always consented to, leave
it — but do not assume "security updates land silently" covers Dagric's own
packages, because it does not.

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
