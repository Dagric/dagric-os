# Building Freehold OS

The entire OS is generated from this repository. No golden images, no
hand-configured machines — change a file, rebuild, and the change is in the
next ISO. That's what makes this a distribution instead of a one-off install.

## On Windows (recommended for this machine)

Requirements: **Docker Desktop**, running.

```powershell
cd C:\Users\1248n\Downloads\OS
.\build.ps1
```

- First build: 30–60 minutes, downloads ~1.5 GB of Debian packages
  (cached in a Docker volume, so rebuilds are much faster).
- Output: `out\live-image-amd64.hybrid.iso` (~2–3 GB).

Why Docker? `live-build` must run on a Debian system as root, and it creates
device nodes and hardlinks that the Windows filesystem can't represent. The
container builds on its own filesystem and copies only the finished ISO back
to `out\`.

## On a Debian machine or VM

```bash
sudo apt install live-build
sudo ./build.sh
```

## Testing the ISO

1. **VM first, always.** Hyper-V (already on Windows 11 Home via VirtualBox
   alternative), VirtualBox, or VMware Player. Boot the ISO → you land on the
   live desktop → "Install Freehold OS" launches Calamares.
2. **Then real hardware.** Write the ISO to USB with Rufus or Ventoy and test:
   boot, Wi-Fi, audio, display scaling, suspend/resume, the Calamares install
   with disk encryption enabled.

## Making changes

| To change... | Edit... |
|---|---|
| What software is included | `config/package-lists/*.list.chroot` |
| Files placed on the system | `config/includes.chroot/` (mirrors the filesystem) |
| Scripted setup at build time | `config/hooks/normal/*.hook.chroot` |
| Debian release, arch, ISO metadata | `auto/config` |
| Name/branding of the OS | `config/hooks/normal/0100-identity.hook.chroot` + `branding/` |

Then rebuild. Keep this folder in Git so every ISO is reproducible from a
commit.

## Troubleshooting

- Build output is teed to `build.log` (copied to `out\` even on failure).
- A package name that doesn't exist in trixie aborts the chroot stage — the
  log names it. Check spelling against https://packages.debian.org.
- If Docker complains about privileges, the `--privileged` flag in `build.ps1`
  is required: live-build needs to mount filesystems inside the container.
