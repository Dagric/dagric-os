# Dagric OS editions

One source tree, two products. The free edition builds adoption and trust;
Pro is the paid step-up with the full creator/developer suite and, later,
support contracts.

```
.\build.ps1                  →  dagric-os-1.0-amd64.iso        (free)
.\build.ps1 -Edition pro     →  dagric-os-pro-1.0-amd64.iso    (Pro)
```

Mechanics: `config/package-lists/pro-*.list.chroot` only exist in Pro
builds; the `0600-pro-edition` hook applies Pro-only config (it reads
`/etc/dagric-edition`, which the build writes). Everything else —
branding, security baseline, debloat rules, installer — is IDENTICAL.
Free is never a crippled Pro; Pro is never a different OS.

## Dagric OS (free)

Everything already shipped: debloated KDE Plasma, zero telemetry,
silent updates that never force a reboot, Firefox, LibreOffice essentials
(Writer/Calc/Impress), Elisa music library, Flathub, NTFS/exFAT,
Dagric Welcome, branded installer, and the **Migration Assistant**
(`dagric-migrate` — copies Documents/Pictures/Music/Videos/Desktop and
Chrome/Edge/Firefox bookmarks over from the Windows partition, read-only,
never touching Windows). Drive-health watching too: plasma-disks warns
before a failing disk dies, and the Security Checkup reports SMART status.

**Security baseline** (genuinely strong — free is lean, not insecure):
AppArmor mandatory access control enforced from boot, an expanded hardened
kernel (kexec disabled, BPF/perf locked down, network-spoof protections,
non-world-readable homes), firewalld, silent security updates, and Lynis
on-demand security auditing. Plus day-one functional support most switchers
need: scanners, printer breadth, firmware updates (fwupd), VPN import, media
codecs + Netflix/Spotify (EME), MS-Office-metric fonts, fingerprint login,
GPU video decode, `.deb` double-click, and a screen reader.
Pro adds *proactive* monitoring on top (the Security Suite) — free is not
crippled, Pro is a clear step up.

## Dagric OS Pro — everything above, plus

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

**Gaming & Windows apps**
| | |
|---|---|
| Windows apps | Wine (64- and 32-bit) + winetricks — run classic .exe software; Bottles via one-click consent install |
| Windows itself | "Windows in a window" — KVM/QEMU + virt-manager preinstalled with UEFI (OVMF) and software TPM (swtpm) for Windows 11 guests; `dagric-vm` enables it with consent. Windows is never bundled — the helper points to Microsoft's official ISO download |
| Games | Steam via one-click consent install (`dagric-get-steam` — NEVER bundled); 32-bit Vulkan prepped; `dagric-gaming` adds community Proton-GE on request |
| Performance | gamemode governor + MangoHud FPS overlay |

**Stability**
| | |
|---|---|
| System restore | Timeshift — scheduled restore points, roll back a bad update (rsync mode on ext4; btrfs snapshot mode on btrfs installs) |

**Security Suite** (the Pro step-up; free keeps a strong baseline — see below)
| | |
|---|---|
| App firewall | OpenSnitch — per-application outbound control; ships in monitor mode, blocking opt-in from the GUI |
| USB control | USBGuard — block BadUSB / USB-drop attacks. Ships masked; `dagric-usb-protect` (Hub → USB Protection) generates an allow-list from the devices currently attached and only then arms the daemon, so enabling it can never deauthorize the owner's own keyboard/mouse. Same tool disarms it. |

**Developer toolchain**
| | |
|---|---|
| Containers | Docker (+ compose) and Podman preinstalled |
| Any-distro shells | Distrobox — Ubuntu/Fedora/Arch userlands in a terminal with full host integration |
| Toolchain | build-essential, git, Python (pip + venv) |
| SSH | client ready; server installed but OFF until enabled |

**Owner-consent helpers (never auto-run)**
- `sudo dagric-drivers` — detects NVIDIA hardware, installs the
  proprietary driver from Debian non-free on request
- `dagric-get-resolve` — guided official DaVinci Resolve install
  (Blackmagic's license forbids preinstalling it; no honest OS can)
- `dagric-ai` — one-command local LLM setup (Ollama); models run
  entirely on the machine, nothing leaves it
- `dagric-vm` — enables the VM stack (groups + service) with consent
- `dagric-get-joplin` — local-first Markdown notes (OneNote/Notion
  alternative, offline, optional E2E-encrypted sync)
- `dagric-get-onlyoffice` — MS-Office-style ribbon suite with the best
  open-source .docx/.xlsx/.pptx fidelity, alongside LibreOffice

## Pro roadmap (engineering ahead of promises)

These are real projects, not checkbox features — listed here so the
pitch never outruns the product:

- **Immutable core / atomic updates with rollback** — requires moving to
  an image-based update model (ostree/ABroot-style). Large but doable.
  First step (smaller): btrfs as the default install filesystem so
  Timeshift/Snapper get instant atomic snapshots instead of rsync copies.
- **umu-launcher** — containerized Proton for non-Steam .exe files;
  not yet packaged in Debian, revisit when it lands (or vendor it).
- **LocalAI** — OpenAI-compatible self-hosted engine (LLM + Whisper +
  image gen) as an alternative backend for `dagric-ai`.
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
| Dagric OS | free | The full OS. No account, no strings. |
| Dagric Pro | one-time or per-seat | Creator + dev suite preconfigured, priority updates |
| Dagric Enterprise | per seat/year | Fleet dashboard, compliance, SLAs (future) |
