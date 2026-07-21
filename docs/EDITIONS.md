# Freehold OS editions

One source tree, two products. The free edition builds adoption and trust;
Pro is the paid step-up with the full creator/developer suite and, later,
support contracts.

```
.\build.ps1                  →  freehold-os-1.0-amd64.iso        (free)
.\build.ps1 -Edition pro     →  freehold-os-pro-1.0-amd64.iso    (Pro)
```

Mechanics: `config/package-lists/pro-*.list.chroot` only exist in Pro
builds; the `0600-pro-edition` hook applies Pro-only config (it reads
`/etc/freehold-edition`, which the build writes). Everything else —
branding, security baseline, debloat rules, installer — is IDENTICAL.
Free is never a crippled Pro; Pro is never a different OS.

## Freehold OS (free)

Everything already shipped: debloated KDE Plasma, zero telemetry,
hardened defaults, silent updates that never force a reboot, Firefox,
LibreOffice essentials (Writer/Calc/Impress), Flathub, NTFS/exFAT,
Freehold Welcome, branded installer.

## Freehold OS Pro — everything above, plus

**Creator suite**
| | |
|---|---|
| Browsers | Chromium alongside Firefox ESR |
| Email/calendar | Thunderbird |
| Office | The complete LibreOffice suite |
| Image | GIMP (with PhotoGIMP layout), Krita, Inkscape |
| 3D | Blender |
| Video | OBS Studio (recording/streaming) + Kdenlive (editing) |
| Backup | Borg + Vorta GUI (local/encrypted) + rclone (70+ cloud providers) |
| Mobile | KDE Connect — Android/iOS notifications, files, clipboard, remote input (firewall ports preconfigured) |
| Look | Papirus icon theme, Pro identity |

**Developer toolchain**
| | |
|---|---|
| Containers | Docker (+ compose) and Podman preinstalled |
| Toolchain | build-essential, git, Python (pip + venv) |
| SSH | client ready; server installed but OFF until enabled |

**Owner-consent helpers (never auto-run)**
- `sudo freehold-drivers` — detects NVIDIA hardware, installs the
  proprietary driver from Debian non-free on request
- `freehold-get-resolve` — guided official DaVinci Resolve install
  (Blackmagic's license forbids preinstalling it; no honest OS can)
- `freehold-ai` — one-command local LLM setup (Ollama); models run
  entirely on the machine, nothing leaves it

## Pro roadmap (engineering ahead of promises)

These are real projects, not checkbox features — listed here so the
pitch never outruns the product:

- **Immutable core / atomic updates with rollback** — requires moving to
  an image-based update model (ostree/ABroot-style). Large but doable.
- **Fleet management dashboard** — builds on the signed APT repo
  (`docs/REPOSITORY.md`); needs a server-side product.
- **Compliance profiles** (disk-encryption enforcement, audit logging,
  centralized policy) — enterprise tier.
- **10-year LTS + 24/7 SLA support** — a staffing commitment, priced per
  seat (Red Hat/Canonical model).
- **OEM preinstall partnerships** — after real-hardware validation.

## Pricing sketch

| Tier | Price | Gets |
|---|---|---|
| Freehold OS | free | The full OS. No account, no strings. |
| Freehold Pro | one-time or per-seat | Creator + dev suite preconfigured, priority updates |
| Freehold Enterprise | per seat/year | Fleet dashboard, compliance, SLAs (future) |
