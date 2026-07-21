# The Freehold Manifesto

Freehold OS exists to be the opposite of what desktop computing has become.
Every design decision is checked against one question: **who does this serve —
the person at the keyboard, or someone else?**

## What Windows does — and what we do instead

| Windows | Freehold OS |
|---|---|
| Telemetry on by default, opt-out buried | **Zero telemetry.** There is nothing to opt out of. |
| Ads in the Start menu, lock screen, File Explorer | **No ads. Anywhere. Ever.** |
| Forces a Microsoft account to install | **No account required.** Your machine doesn't need permission to exist. |
| Preinstalled trialware, Candy Crush, OEM bloat | **Every package hand-picked.** ~0 apps you didn't ask for. |
| Forced reboots for updates at the worst moment | Security updates apply silently in the background. **The machine reboots when you say so.** |
| Reinstalls "suggested apps" after updates | What you remove **stays removed**. |
| Nags you toward Edge, OneDrive, Copilot | The default browser is the default browser. **No dark patterns.** |
| Opaque system you rent | **Every line of source is inspectable.** The build for this exact OS is in this repo. |

## Rules for every future change

1. **Additive, never extractive.** A component is included because it does a job
   for the user — never because it does a job *on* the user.
2. **One tool per job.** Two media players is one media player too many.
3. **Removable means removable.** Anything preinstalled can be purged with one
   `apt` command and never comes back.
4. **Quiet by default.** No popups, no "tips", no engagement mechanics.
   The OS should disappear behind your work.
5. **Familiar, not foreign.** KDE Plasma with a taskbar, launcher, and system
   tray where a Windows user expects them. Switching should feel like relief,
   not homework.
6. **The user is root.** Guardrails, yes (sudo, firewall, hardening) — but the
   owner of the machine outranks the OS, always.

## Why Debian underneath

Debian is community-run — no corporation's growth targets upstream of your
desktop. It's famously stable, security-patched for years per release, and its
only usage-reporting tool (`popularity-contest`) is opt-in — and we don't even
ship it. We stand on Debian for the 60,000 packages and security response, and
we maintain only the delta that makes Freehold, Freehold.
