# Dedicated native lab restored — September 5, 2026

Docker Desktop remains broken. An independent, guarded Debian WSL backend was
added to the personal Dagric Lab plugin and installed as
`0.3.0+codex.20260905163209`. This did not remove or alter the Docker socket.

The 15 backend safety tests pass. Real boot started at 16:33:10 UTC and reached
the Dagric Pro first-run screen and desktop in the in-app browser. Dismissing
onboarding responded correctly, and Check This PC opened a real hardware report.
This establishes initial graphical boot and
interaction only, not complete application, install or hardware qualification.

## Selected existing image

- Source: `out/dagric-os-pro-1.0-amd64.iso`, the newest completed image at test time.
- Size: 4,215,472,128 bytes.
- SHA-256: `94923d86b69523852980e2b08bc8ba3d2929433da3c67beaefde481585c73b3b`.
- Run: `d6d4c539dc8740a49f4f1bb3ff4bfd0f`.
- Receipts: Debian `/var/tmp/dagric-native-lab/stage.json`, `active.json`,
  and `run-d6d4c539dc8740a49f4f1bb3ff4bfd0f.json`.
- Viewer: `http://localhost:6081/vnc.html`.

**This September 4 image predates today's source changes.** It validates the
replacement test backend, not the new OpenSnitch, private-file or manual fixes.
Stage the fresh candidate explicitly after it finishes, using its own hash.

The guest has a new disposable 32 GiB sparse disk, no host drives or shares,
no network, no audio and legacy BIOS firmware. QEMU and the viewer run without
root privileges and listen only on loopback. Stop targets only receipt-matched
processes and preserves files. This initial backend cannot record, run Smoke or
FullTest, or supply Secure Boot, audio or physical-machine evidence.

Use the plugin's `dagric-lab.ps1` entry point with `-Backend NativeWsl`. Do not
invoke its Python backend directly for live operations. A new Codex task picks
up the updated skill automatically; this task verified the installed entry point.

## Follow-up from the running test

Check This PC correctly reported the deliberately absent network/audio and the
test disk being below Pro's 40 GB recommendation. Future test disks were changed
to 64 GiB sparse files and the plugin was revalidated/reinstalled as
`0.3.0+codex.20260905164056`. The existing 32 GiB test disk was not resized or
replaced. All 15 backend tests still pass. This is a test-configuration correction,
not a claim that the new package source has been installed in this guest.

## First revised Free image: actual desktop QA

At 17:19 UTC the old September 4 run was stopped through the plugin; all files
were preserved. The completed Free image from commit `34aafa1` was explicitly
staged with SHA-256
`a80187dfdd236c243833de84f7edfe2bfdcc24a0d4aa463fb94d255fc189aaf5`.
Run `57f3f63afb6a428588dd8bcde7ab7c30` has a new 64 GiB sparse disk.

Observed through the actual guest display:

- Welcome and setup navigation work; the text-size action opens its real dialog.
- Amber accent, Light mode and Dagric Arctic Clean wallpaper each apply, visibly
  updating both the setup controls and the underlying desktop/taskbar.
- Setup closes back to the usable desktop. Menu search finds User Guide and
  Dagric Manual; the application manual opens locally in Firefox.
- The new Typing in another language page opens at the actual installed
  `/usr/share/dagric/manual/app-fcitx5.html`, with the updated content.

The initial batch of fullscreen pointer clicks was inconclusive. Separate
single-click checks after fitting the viewer and restoring the setup window
verified each appearance action; no application defect was established or
patched on that basis. VNC text entry needed actual key events, not DOM text
insertion; that is a test-driver distinction, not an OS search failure.

This is live-session functional evidence, not installed reboot, audio, networking,
physical hardware, or multi-user certification. This first Free image has no
completed matching Pro image. The later corrected `20e24dd` pair must retain its
own distinct artifact and run receipts.

## Corrected matching candidate pair

The corrected Free candidate from `20e24dd04ea3de802531be5139f9f36fe96a1490`
was staged with its independently recorded SHA-256
`0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc`.
Run `f8be77b43bcb4fd5aaf761ac83c10314` started at 17:38:24 UTC on a new 64 GiB
test disk. The actual desktop reached first-run setup, setup dismissal worked,
Dagric Hub opened, menu search found Check This PC, and launching that result
displayed the real hardware report. It correctly identified legacy BIOS and
the intentionally absent network and sound devices; it did not report the
earlier test disk's capacity shortfall. This run was stopped through the plugin
at 17:43:52 UTC with all files preserved.

The matching Pro candidate was then explicitly staged with SHA-256
`69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa`.
Run `e36e5e1382ec4e548919c179fa00d488` started at 17:44:10 UTC and its viewer
became available at 17:44:11 UTC. The network/audio/firmware and recording
limitations described above still apply; listener readiness alone is not a
desktop or installation pass.

The Pro run subsequently reached its branded setup and usable desktop. Setup
dismissal and menu search worked. Launching OpenSnitch from its real menu route
created its tray icon; the 1.6.9 statistics window and Nodes tab opened without
a wrapper refusal. They showed no connected node. The exact image deliberately
ships `ConditionKernelCommandLine=!boot=live`, so the daemon is skipped in this
live session. This is a launcher/UI check only, not connectivity, blocking-rule
enforcement, or installed administrator/standard-account isolation evidence.

Pro's menu also found Dagric Manual and opened the actual local
`/usr/share/dagric/manual/index.html#e=pro` page with 116 help pages and the
corrected 27-page Dagric group. Searching for `notepad` returned Kate as the
single matching page; opening it loaded `/usr/share/dagric/manual/app-kate.html#e=pro`
and the relevant plain-language Windows comparison and usage instructions.
The second browser tab's offline error was expected with the lab NIC disabled.
Firefox's own Mozilla data-collection notice remained visible and informed the
website disclosure correction; it was not hidden or described as disabled.

At approximately 18:03 UTC Chromium was launched through its ordinary Pro menu
entry, without adding flags or disabling any sandbox controls. Two first-run
KDE Wallet requests (Chromium and the desktop portal) were cancelled; no wallet,
test credentials or encryption preference was created. Chromium then opened.
Its actual `chrome://sandbox` page reported:

- Layer 1: Namespace; PID and network namespaces: Yes.
- Seccomp-BPF and TSYNC support: Yes.
- Yama ptrace protection: Broker Yes, non-broker No.
- The browser's own summary: "You are adequately sandboxed."

This closes the live-session uncertainty about the alternative namespace
sandbox when the separate `chromium-sandbox` package is absent. It is a
browser-reported runtime observation, not an exploit test, universal installed
sandbox certification, or remediation of the Chromium CVEs in the package audit.
