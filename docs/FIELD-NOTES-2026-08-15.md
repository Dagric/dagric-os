# Field notes — using Dagric as an owner would

Written after driving a real installed system (BIOS install of the rebuilt free
ISO, plus a cloud variant) through the things a buyer actually does: install an
app from the Software Store, run the Hub tools, change the look, check what the
machine says about itself.

Everything below was **measured on a running system**, not read off the tree.
Where a claim could not be checked that way it says so.

---

## What already works, and works well

Worth recording, because most of this session's writing is about defects and
that gives a false picture of the product.

| Area | Result |
|---|---|
| Boot time | **6.1 s** total (3.6 kernel + 2.5 userspace) to multi-user |
| Idle memory | **955 MB** on a 3 GB machine, full Plasma session |
| Install from Software Store | works end to end, including the polkit prompt |
| Print stack | CUPS active, PDF queue present, HP + Brother + Epson filters all shipped |
| Codecs | 269 GStreamer plugins incl. libav and vpx; mpv present |
| Office | LibreOffice + 8 metric-compatible MS fonts |
| Spellcheck | en_US now present alongside de/es/fr/it/pt |
| Images | WebP and TIFF plugins on **both** editions |
| Manual | 97 offline pages, no network needed |
| Appearance gallery | live preview, "nothing is kept until you press Keep" — genuinely good UX |
| Hardware check | plain-language report, correctly identified BIOS vs UEFI boot |
| Snapshots | pre/post pair per apt run, GRUB submenu populated |

The first-run wizard adapting its own copy between live and installed
("you're running the live trial…" vs "nothing here is permanent…") is a nice
touch, and it is the fastest way to tell the two apart when debugging.

---

## Fixed this session (all committed, all verified on a running system)

1. **Launcher favourites** — the Hub finally appears. Six earlier attempts
   deleted rows that did not exist, because the agent name was taken from
   `main.qml` instead of the database. See the commit for the correct schema.
2. **Four snapshots per apt run** → two. Debian's `80snapper` and ours both
   fired; ours now yields via `DISABLE_APT_SNAPSHOT`.
3. **`--help` hung** on `dagric-gaming` and `dagric-ai`.
4. **Floppy probing** — a dozen I/O errors per boot, now zero.
5. **Discover offline while the desktop is online** (cloud images only).

---

## Still open, ranked by what an owner would notice

### 1. Bluetooth file transfer is broken — every boot logs it twice
`obexd` starts and immediately fails:

    Unable to acquire registry: ... org.gnome.evolution.dataserver.Sources5:
    Failed to execute program ... No such file or directory

`evolution-data-server` is not installed (checked with dpkg-query), and obexd
wants it for the contacts/registry side. **Sending a file to a phone over
Bluetooth is a thing Windows switchers try**, and the desktop advertises
Bluetooth in System Settings. Either pull in what obexd needs, or stop obexd
starting so the log stops lying about a service that cannot work.
NOT yet checked: whether the transfer actually fails in the UI, or only the
registry call does. Needs a real Bluetooth adapter to settle.

### 2. `brltty` costs 571 ms of every boot on machines with no braille display
Second-slowest unit measured (`systemd-analyze blame`), behind only cloud-init.
brltty is right to ship — accessibility is a legal requirement for the
institutional buyers named in the pitch — but it should start when a braille
device appears, not unconditionally. Debian ships udev rules for exactly that.
Worth ~half a second on every boot of every machine.

### 3. `kdialog` helper processes leak
Two `kdialog` processes were still alive long after their dialogs were
dismissed, one of them the Hub's own menu. Harmless in a session, but it means
a Hub opened and closed repeatedly accumulates processes.

### 4. `systemd-ssh-generator` fails on every boot
    Failed to query local AF_VSOCK CID: Cannot assign requested address
Cosmetic and VM-specific (systemd probing a vsock that is not there), but it is
the first error in the log an owner or a support person will see.

### 5. Nothing in the shipped tools handles `--help` consistently
Only 7 of 38 `dagric-*` tools parse arguments at all. Two used to hang; the rest
ignore `--help` and run their normal flow. For GUI-launched consent helpers that
is defensible, but the ones a person might type deserve a usage line.

### 6. The layout thumbnails do not show layouts
In the Appearance gallery, the **Styles** thumbnails are real mockups; the
**Layouts** thumbnails are near-identical blue gradients with a thin strip at
the bottom. Three layouts that differ mainly in taskbar arrangement look the
same in the picker. This is the one place the customisation work undersells
itself.

### 7. Applying a layout did not visibly centre the taskbar
`eleven.look` builds the panel with `panelspacer` on both sides of `icontasks`,
which should centre it. After applying, the icons were still left-aligned.
NOT root-caused — the panel config did change (`icontasks` replaced the default
task manager), so the layout ran; only the centring did not take. Worth one
session with a real look at `plasma-org.kde.plasma.desktop-appletsrc` before and
after.

---

## Things I checked that turned out to be fine

Recorded so nobody re-investigates them.

- **GStreamer codecs** — a "0 plugins" reading was `gst-inspect-1.0` not being
  installed, not missing codecs. 269 plugins are present.
- **Duplicate bottom panels** — two `location=4` entries are the panel and the
  system tray's own containment, not two panels.
- **`lynis.desktop` pointing at a missing `su-to-root`** — the override in
  `/usr/local/share/applications` wins by XDG precedence, as designed.
- **ISO installs and the NetworkManager bug** — cloud-init is not installed on
  ISO installs and `/etc/network/interfaces.d` is empty, so they were never
  affected.

---

## The pattern worth keeping

Five of tonight's defects were invisible to file inspection and only appeared
when the software was run: an installer that failed 100% of the time, an apt
hook that errored on every transaction, a favourites clear that matched zero
rows, a network stack that lied about being offline, and a module blacklist that
did nothing. In each case the code read correctly.

The measurements that found them were cheap — run the installer, run apt, dump
the table, ask NetworkManager, check `lsmod`. The expensive part was believing
the file.
