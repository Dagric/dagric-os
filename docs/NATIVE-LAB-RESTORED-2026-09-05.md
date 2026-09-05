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
