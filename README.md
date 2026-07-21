# Freehold OS

**A Debian-based desktop operating system built to be the antithesis of
Windows: no telemetry, no ads, no forced accounts, no bloat — a computer
that works for its owner and no one else.**

Base: Debian 13 "Trixie" (stable) · Desktop: KDE Plasma · Installer: Calamares
· Codename: **Foundation**

```
Debian Stable ──► hand-picked packages ──► debloat + hardening hooks
      ──► Freehold branding ──► bootable installer ISO
```

This repository *is* the operating system: every package choice, config file,
and policy lives here, and the ISO is rebuilt from it with one command.

## Build it

On this Windows machine (Docker Desktop must be running):

```powershell
.\build.ps1        # → out\live-image-amd64.hybrid.iso
```

On any Debian box: `sudo apt install live-build && sudo ./build.sh`

Full details, testing checklist, and troubleshooting: [docs/BUILDING.md](docs/BUILDING.md)

## What makes it the antithesis

| | Windows | Freehold |
|---|---|---|
| Telemetry | On by default | **Not shipped** |
| Ads in the OS | Start menu, lock screen | **None** |
| Account required | Yes | **No** |
| Preinstalled junk | OEM + Microsoft bloat | **Every package hand-picked** |
| Updates | Forced reboots | **Silent, background, reboot when *you* choose** |
| Source code | Closed | **This repo + Debian, fully open** |

The full reasoning: [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) ·
What's next: [docs/ROADMAP.md](docs/ROADMAP.md)

## How the debloat actually works

1. **`--apt-recommends false`** (`auto/config`) — APT installs nothing that
   wasn't explicitly requested, at build time *and* forever after on installed
   systems (`config/includes.chroot/etc/apt/apt.conf.d/01freehold-norecommends`).
2. **No metapackages** — `task-kde-desktop` would drag in games, PIM suites,
   and Akonadi databases. Instead, `config/package-lists/` names every package
   individually with a comment saying why it's there.
3. **Debloat hook** — `config/hooks/normal/0200-debloat.hook.chroot` purges
   anything undesirable that slipped in, then autoremoves and cleans.
4. **Flatpak for everything else** — the base OS stays minimal; users add
   apps *they* choose through Discover.

## Repository layout

```
auto/                     live-build configuration (distro, arch, ISO settings)
config/
  package-lists/          what's in the OS — one package per line, all justified
  includes.chroot/        files copied verbatim into the OS filesystem
  hooks/normal/           build-time scripts: identity, debloat, hardening
docker/                   containerized Debian build environment for Windows
branding/                 wallpaper, boot splash, and logo sources (SVG)
docs/                     PHILOSOPHY, BUILDING, ROADMAP
test/                     QEMU boot-test harness (boot-test.ps1, vm-screenshot.ps1)
.github/workflows/        CI: builds the ISO on every push once on GitHub
build.ps1 / build.sh      one-command ISO builds (Windows / Debian)
release.ps1               versioned ISO + SHA256SUMS for distribution
out/                      finished ISOs land here
```

## Legal footing

Debian's software is free to modify and redistribute; this project follows
[Debian's derivative guidelines](https://wiki.debian.org/Derivatives/Guidelines):
its own name and branding, `ID_LIKE=debian` honesty in `os-release`, and no use
of Debian's restricted marks. If the ISO is ever distributed outside your own
machines, GPL source-availability obligations apply — easiest satisfied by
keeping this repo public and pointing recipients at Debian's source archives.
