# Getting started with Dagric OS

Everything a new user needs, from download to a running desktop. Written for
someone coming from Windows who has never installed Linux.

## 1. Download

- **Dagric OS** (free) — `dagric-os-1.0-amd64.iso` (~1.9 GB)
- **Dagric OS Pro** — `dagric-os-pro-1.0-amd64.iso` (~3.3 GB)

Download the matching `SHA256SUMS` and `SHA256SUMS.sig` next to the ISO.

## 2. Verify the download (recommended)

Confirms the file arrived intact and is really from us.

**Windows (PowerShell):**
```powershell
Get-FileHash dagric-os-1.0-amd64.iso -Algorithm SHA256
```
Compare the result to the line in `SHA256SUMS`. They must match exactly.

**For the signature** (proves it's genuinely from Dagric), import our public key
(`dagric-signing-key.asc`) and run `gpg --verify SHA256SUMS.sig SHA256SUMS`.

## 3. Write it to a USB stick

You need an 8 GB+ USB stick. **This erases the stick.**

- **Easiest (Windows/Mac/Linux):** [Rufus](https://rufus.ie) or
  [Ventoy](https://www.ventoy.net). In Rufus: pick the ISO, pick the USB, leave
  the defaults, click **Start**. If asked "ISO or DD mode", choose **DD**.
- Ventoy is great if you want several ISOs on one stick — install Ventoy once,
  then just copy `.iso` files onto it.

## 4. Boot from the USB

1. Leave the stick plugged in and restart the computer.
2. As it powers on, tap the **boot-menu key** repeatedly — it's usually **F12**,
   sometimes **F10**, **F9**, or **Esc** (the screen often shows it briefly).
3. In the menu, choose the USB stick — pick the entry that starts with
   **"UEFI:"** if you see one.

Tip: if it boots straight back into Windows, the boot key was missed — restart
and try again, or enable "USB boot" / disable "Fast Boot" in the BIOS/UEFI
settings.

## 5. Try it, then install

- You land on the live Dagric desktop. **Nothing is changed on your computer
  yet** — click around, check that Wi-Fi, sound, and the trackpad work.
- When ready, double-click **Install Dagric OS** on the desktop.
- The installer walks you through language, timezone, keyboard, disk, and your
  account. On the disk step, **"Erase disk"** gives a clean install; it offers
  disk encryption if you want it.
- It takes 10–20 minutes. When it says **All done**, restart and remove the USB.

## 6. First boot

- You'll see a branded login, then the desktop, and the **Welcome** page opens
  once with quick-start tips. It links a full offline **User Guide** (printers,
  Wi-Fi, apps, backups, shortcuts).
- Install more apps anytime from **Discover** (the bag icon).

## Common questions

- **Will this delete Windows?** Only if you choose "Erase disk" on the disk that
  has Windows. To keep both, use "Install alongside" or manual partitioning
  (advanced) — or install to a *different* drive.
- **My Wi-Fi/graphics need a proprietary driver.** Open a terminal and run
  `sudo dagric-drivers` — it detects NVIDIA hardware and offers the driver.
- **Nothing is preinstalled that I didn't ask for**, and updates install quietly
  in the background — the machine never reboots itself.

Support: dagric.com/support.
