# The Freehold update channel

How configuration reaches machines, before and after they're sold.

## Two delivery paths, one source of truth

Everything lives in `config/includes.chroot/` (plus hooks). It reaches
machines two ways:

1. **The ISO** — `build.ps1` bakes the files straight into the image.
   This is how new machines get their configuration.
2. **The APT repository** — `repo.ps1` assembles the *same files* into
   versioned `.deb` packages and generates a signed repo in `out\repo`.
   This is how machines you've **already sold** get configuration updates:
   bump a package version, publish the repo, and every Freehold machine
   picks it up with its normal background update run.

The packages:

| Package | Contains | Bump it when... |
|---|---|---|
| `freehold-branding` | wallpaper, logo, SDDM background | the look changes |
| `freehold-desktop-defaults` | Plasma skel defaults, Firefox policies | default behavior changes |
| `freehold-security-policy` | sysctl hardening, APT no-recommends (conffiles) | the security baseline evolves |

## Building and signing

```powershell
.\repo.ps1     # builds the .debs and the signed repo into out\repo
```

The 4096-bit RSA signing key is generated on first run and stored in the
`freehold-repo-keys` Docker volume — **never in this git repo**. Backup the
volume (`docker run --rm -v freehold-repo-keys:/keys debian tar cz -C /keys .`)
and keep the archive somewhere safe: whoever holds this key can push packages
to every customer machine.

## Publishing

Serve `out\repo` over HTTPS (any static host works). Clients enroll with:

```bash
curl -fsSL https://YOUR-HOST/freehold-repo.gpg.asc | gpg --dearmor \
    | sudo tee /usr/share/keyrings/freehold.gpg > /dev/null
echo 'deb [signed-by=/usr/share/keyrings/freehold.gpg] https://YOUR-HOST/ ./' \
    | sudo tee /etc/apt/sources.list.d/freehold.list
sudo apt update && sudo apt install freehold-branding freehold-desktop-defaults freehold-security-policy
```

Future step: preinstall the three packages and the repo source in the ISO
itself (add them to a package list once the repo has a permanent URL), so
sold machines are enrolled from the factory.

## Release checklist

1. Edit files in `config/includes.chroot/`
2. Bump `Version:` in the affected `packages/*/DEBIAN/control`
3. `.\repo.ps1` → upload `out\repo` to the host
4. `.\build.ps1` → new ISO for new machines
5. Commit, tag, and note the change in a CHANGELOG
