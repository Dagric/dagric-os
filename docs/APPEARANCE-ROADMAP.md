# Appearance roadmap

How Dagric's customisation experience evolves, centred on one idea:
**you should see a change before you live with it.**

This is a working plan for a one-person shop, not a marketing wish list.
Every estimate assumes focused work by someone who already knows this tree,
and every item names what could go wrong. Where something is genuinely not
worth doing, it says so.

Scope: `dagric-style`, `dagric-looks`, the wallpaper set, the colour schemes,
and the Appearance section of `dagric-hub`. Nothing here changes the
philosophy in `docs/PHILOSOPHY.md` — it applies it.

---

## 1. Where it stands today

Two shell tools, both POSIX `sh`, both driven by `kdialog` text menus.

### Dagric Styles — `/usr/bin/dagric-style`

Changes the *mood*: colour scheme, accent, wallpaper, KWin effects. Panels are
left alone.

- Builds its menu by reading plain `key=value` `.style` files from three
  directories, later wins so users can override shipped ones:
  `/usr/share/dagric/styles`, `/etc/dagric/styles`,
  `~/.local/share/dagric/styles`.
- Recognised keys: `NAME`, `DESCRIPTION`, `SORT`, `EDITION`, `SCHEME`,
  `ACCENT`, `WALLPAPER`, `BLUR`, `TRANSLUCENCY`, `WOBBLY`. Every key is
  optional; an omitted key leaves that part of the desktop alone.
- Applies through stock Plasma switches only: `plasma-apply-colorscheme`,
  `plasma-apply-wallpaperimage`, `kwriteconfig6` for the accent
  (`kdeglobals`) and the three KWin effects (`kwinrc [Plugins]`), then a
  `dbus-send` to `org.kde.KWin.reconfigure`, followed by a re-apply of the
  current colour scheme to force a repaint.
- Two extra menu rows: **Accent color** (a `kdialog --getcolor` picker,
  converted from `#RRGGBB` to the `r,g,b` that `kdeglobals` wants) and
  **Reset**.
- Six styles ship. Free: Daybreak, Midnight, Dawn. Pro: Classy, Neon, Forest.
  Pro files carry `EDITION=pro` and are deleted from free images by
  `build.sh` (`grep -rlx 'EDITION=pro' … | xargs -r rm -f`), with a runtime
  check in the script as belt and braces.

### Dagric Looks — `/usr/bin/dagric-looks`

Changes the *layout*: panels, docks, menu bars.

- Same three-directory drop-in scheme, `.look` files, keys `NAME`,
  `DESCRIPTION`, `SORT`, `EDITION`, `SCRIPT`.
- `SCRIPT` is a single line of Plasma's own scripting API, executed via
  `dbus-send` → `org.kde.PlasmaShell.evaluateScript`. Every layout is
  prefixed with a `CLEAR` snippet that removes **all** existing panels first,
  and each layout re-brands the launcher with the Dagric logo so branding
  survives the switch.
- Seven layouts ship. Free: Classic, Focus, Eleven. Pro: Horizon, Command,
  Unity, Duo.

### Assets

- **Sixteen wallpaper packs** in `/usr/share/wallpapers` — each a
  `metadata.json` plus a 1920×1080 and a 3840×2160 PNG. `set_wall()` prefers
  4K, falls back to 1080p, and also accepts an absolute path to any image.
  The first six are hue variations on one composition: Dagric, DagricDawn,
  DagricDusk, DagricForest, DagricMidnight, DagricNeon. The second wave
  varies the *composition* as well — DagricSlate (corner light, graphite),
  DagricEmber (low horizon glow), DagricViolet (concentric contour rings),
  DagricArctic (plain gradient, no line work), DagricCopper (angled light
  shafts), DagricInk (a single band of light along the top edge),
  DagricAurora (vertical curtains), DagricSand (layered dune strata).
  DagricSlateClean and DagricAuroraClean are the same artwork with no
  monogram or wordmark, for owners who want a bare desktop.
- **Two Dagric colour schemes**: `DagricLight.colors`, `DagricDark.colors`.
- Seven hand-drawn look wireframes exist as SVGs — but only on the marketing
  site (`site/assets/look-*.svg`). **Nothing in the shipped image shows the
  user a picture of anything.**

### The honest summary of today

| | Styles | Looks |
|---|---|---|
| Preview before applying | none | none |
| Thumbnail of the result | none | none |
| Applies | instantly, on the live session | instantly, on the live session |
| Undo | "Reset" only | **nothing** |

Two things deserve to be said plainly, because they drive everything below:

1. **Reset is not undo.** It re-applies `daybreak.style` — the Dagric
   default. A user who had set their own accent, or who preferred Midnight,
   does not get their previous desktop back; they get Daybreak. (And because
   later directories win, if the user has their own `daybreak.style` in
   `~/.local/share`, Reset applies *theirs*.)
2. **Looks has no undo at all, and it is the most destructive action in the
   OS.** The `CLEAR` prelude removes every panel before the new layout is
   built. Anyone who had customised their panel — added a widget, moved the
   clock — loses that permanently the first time they click a layout out of
   curiosity. That is a refund-risk defect, not a polish item.

The drop-in file format is the good news. It is genuinely extensible, it is
documented in the shipped `daybreak.style` header, and it means everything
below is mostly about *presentation and safety*, not about rebuilding the
engine.

---

## 2. Shipping in this round — IN PROGRESS

**Status: in progress. Not yet in a released ISO.** Do not describe this on
the website until it has been through a VM boot test.

- **A preview gallery** replacing the flat `kdialog --menu` for Styles: a
  grid of tiles, each with a **thumbnail**, name and description, rendered
  natively rather than as a list of text rows.
- **Keep / Revert.** Choosing a style applies it and then asks. "Keep" makes
  it permanent; "Revert" puts the desktop back the way it was — the real
  previous state, not Daybreak.
- **Auto-revert.** If nothing is clicked within the timeout, the desktop
  reverts on its own. This is the safety net that makes trying things
  free of consequence, and it is the same pattern a monitor uses when you
  change resolution: the machine assumes a silent user is a stuck user.
- **Expanded wallpaper set**, so the gallery has enough to look like a
  collection rather than a sample. **DONE** — 6 packs to 16, and the eight
  new ones vary the composition rather than just the hue, so a grid of
  thumbnails reads as eight different pictures instead of one picture in
  eight colours. Two of them ship a no-branding variant.

### The missing piece, and why this took until now

The shipped image already contains everything needed to *describe* a native
UI — QtQuick (651 files), QtQuick.Controls (474) and Kirigami (246) are all
present — but **not `/usr/bin/qml6`, the runtime that executes it.** That is
why the tools have been `kdialog` menus: there was no way to run a QML file.
Debian's **`qml-qt6`** package provides that binary. Adding one small package
to `config/package-lists/desktop.list.chroot` turns a pile of already-shipped
QML modules into a usable native gallery.

That is a genuinely cheap unlock and it is worth understanding why: we are
not adding a toolkit, we are adding the loader for a toolkit we were already
paying the disk cost of.

### The engineering that is actually in this round

The gallery is the visible part. The part that matters is **state capture**:
Keep/Revert and auto-revert are impossible without being able to read the
current desktop back out. That means, for each key the applier writes, a
matching `kreadconfig6` read — colour scheme, accent, the three KWin effect
flags, and the current wallpaper. Once that exists, three later items on this
roadmap become nearly free (see §3.3 and §3.6).

**Known limitation to be honest about, including in the UI copy:** this round
previews by *applying and then undoing*. The screen really does change. That
is a big improvement over no preview, but it still momentarily mutates the
live session — a flash of redraw, and any app that caches colours at startup
may look briefly wrong. Rendering a mock instead is §3.1, and it is
deliberately not in this round because it is a different and larger job.

### Prerequisite refactor — do this first, it is the highest-leverage hour

`dagric-style` currently fuses "show a menu" and "apply a style" into one
script with no way to invoke either separately. Splitting out a
non-interactive interface:

```
dagric-style --list              # machine-readable: id, name, description, file
dagric-style --apply <id>        # apply, no UI
dagric-style --capture <file>    # write current desktop out as a .style
```

…is a couple of hours of work and it unblocks the gallery (which needs to
call the applier), auto-revert (§2), Create-your-own (§3.3), and the
time-of-day switch (§3.6). Every one of those is harder without it and
trivial with it. If only one thing from this document gets done, make it
this.

---

## 3. Near-term

Estimates are focused working time for someone fluent in this tree. **They
exclude the iteration tax, which dominates:** a full ISO rebuild is 30–60
minutes (`docs/BUILDING.md`), the free image is 2.06 GB and Pro is 3.75 GB,
and anything touching the live session has to be verified by booting the ISO
in the QEMU harness. Budget roughly *double* these numbers in wall-clock time
unless several items are batched into one build.

Discipline that has already paid for itself on this project: **verify the
binary or package exists in the built image before designing around it.**
That is exactly how the `qml6` gap was found.

### 3.1 Live preview overlay — render a mock instead of mutating the session

**Effort: 3–5 days · Risk: medium-high · Free**

Rather than applying a style and undoing it, draw a fake desktop: a small QML
scene with a mock window, panel, button and text, painted with the colours
read directly out of the target `.colors` file and the style's `ACCENT`, over
the target wallpaper. Nothing is written to `kdeglobals`; the session is never
touched until the user commits.

*Why it matters commercially:* this is the difference between a script and a
product. It is also the single most demonstrable thing in a 20-second store
video — hover a tile, the preview repaints, nothing on the real desktop
moves.

*The risk is fidelity, and it is real.* A mock that misrepresents the result
is worse than no preview, because the user feels lied to on commit. Some
things simply cannot be mocked honestly: KWin blur, translucency and wobbly
windows are compositor effects with no cheap static equivalent. Plan to
render those as an explicit annotation on the tile ("blur on") rather than
faking them, keep the label "approximate", and keep the real
apply-with-auto-revert from §2 as the confirmation step. Preview to browse;
apply to decide.

*Second risk:* the `.colors` INI parsing becomes a second implementation of
Plasma's colour model, and it will drift when upstream adds a role. Keep it
to the handful of roles that actually show in the mock and accept it will
occasionally be slightly off.

### 3.2 Richer style keys — fonts, cursor, icons, splash (and corner radius)

**Effort: 2–4 days total · Risk: low to medium, per item · Free, mostly**

The `.style` format is already the right shape; these are new optional keys.
They are not equally cheap, and the differences are worth knowing before
promising any of them:

- **Font pairing** — `kdeglobals [General] font/fixed/menuFont/toolBarFont/
  smallestReadableFont` plus `[WM] activeFont`. **Almost free in ISO size**,
  because the image already ships Noto Core, Liberation, Carlito, Caladea and
  the Droid fallback — enough for several distinct pairings without adding a
  byte. *Caveat:* the font descriptor string format changed between Plasma 5
  and Plasma 6 (the weight field in particular). Generate the strings on the
  shipped version and test them; do not copy them from a Plasma 5 blog post.
  Half a day. **Best value in this group — do it first.**
- **Cursor theme** — `plasma-apply-cursortheme`, already present with
  plasma-workspace. Applies live for new windows; some already-running apps
  keep the old cursor until restart. Cheap, but only one cursor theme ships
  today, so this costs an asset decision, not code.
- **Icon theme** — `plasma-changeicons`, also already present. Same story:
  the code is an hour, the *asset* is the cost. A second full icon theme is
  tens of megabytes on an image that is already 2 GB. Verify the licence is
  redistributable before shipping it — we sell ISOs, so every asset must be
  something we are allowed to sell.
- **Splash screen** — `ksplashrc [KSplash] Theme`, rendered by `ksplashqml`
  from plasma-workspace (confirm that binary is in the image first). High
  perceived value per hour: it is Dagric branding on every single login. Half
  a day to author a themed splash.
- **Corner radius** — *recommend cutting this.* Stock Breeze and KWin on
  Plasma 6 expose no corner-radius setting via `kwriteconfig6`. Getting it
  means depending on a third-party Plasma style or KWin effect, which is
  precisely the third-party theme-engine dependency §5 rules out, and it
  breaks on Plasma point releases — support load for a rounded corner. If it
  is ever revisited, verify against the shipped Plasma version first rather
  than assuming.

*Why it matters commercially:* right now a "style" is colours plus a picture.
With fonts and a splash it becomes an identity, and the gap between free and
Pro styles gets easier to justify.

### 3.3 "Create your own style" from the current desktop

**Effort: 1 day · Risk: low-medium · Free**

`dagric-style --capture ~/.local/share/dagric/styles/mine.style`: read back
the current scheme, accent, effect flags and wallpaper, and write a `.style`
file. It appears in the gallery next time it opens, because the loader
already scans that directory.

**This is the best effort-to-value item on the list**, for two reasons.
First, the read-back code is already being written for Keep/Revert in §2, so
most of it is done. Second, it converts Styles from a fixed menu of six into
a *system* — and it is the feeder for §3.4 and for any community effort. A
user who has made their own style has a reason to come back and a reason to
talk about it.

*The one fiddly part* is capturing the current wallpaper. There is no clean
"what is my wallpaper" call; it means reading
`~/.config/plasma-org.kde.plasma.desktop-appletsrc` for the containment's
`Wallpaper/org.kde.image/General Image` value, which is a URL and gets
awkward with multiple containments or multiple monitors. Mitigation is
built in already: `set_wall()` accepts an absolute path, so a
best-effort capture that writes a path still round-trips correctly. Fall
back to leaving `WALLPAPER` out entirely rather than writing something wrong
— an omitted key is defined behaviour.

### 3.4 Import/export a style, and a community gallery

**Effort: export/import 1–2 days · Risk: medium (security) · Free**
**Community gallery: 2–4 weeks to build, and an unbounded ongoing cost**

Export a style as one shareable file: a small tarball containing the `.style`,
optionally the wallpaper image, optionally a custom `.colors`, plus a
manifest. Import unpacks into `~/.local/share/dagric/styles` and
`~/.local/share/wallpapers`. No root needed, which is the whole point of the
three-directory scheme.

**The security line here is not negotiable, and it splits the feature in
two.** A `.style` file is *inert data* — the script reads named keys out of
it with `sed` and passes them to known commands. Importing one from a
stranger is roughly as dangerous as importing a text file. A `.look` file is
*not* inert: its `SCRIPT` line is handed straight to
`org.kde.PlasmaShell.evaluateScript`, which is arbitrary code running with
the full privileges of the user's session. Importing a `.look` from the
internet is remote code execution with extra steps.

Therefore: **import/export ships for Styles only.** Layout sharing, if it
ever happens, is by reviewed contribution to this repo — never a one-click
in-OS download. Say this out loud in the docs; it is a genuine
differentiator, not an apology.

*On the community gallery, be realistic.* A hosted gallery with uploads is
not a weekend project — it is hosting, accounts, moderation, abuse handling,
takedown requests, and a support inbox that never closes, for one person who
also maintains an operating system. **Start with a curated page**: a handful
of hand-reviewed styles on dagric.com and a Git repo that accepts merge
requests. That is hours of work, it cannot be abused, and if it turns out
nobody contributes, nothing has been lost. Only build the real thing if the
curated page fills up on its own.

### 3.5 Accent colour extracted from the wallpaper

**Effort: 4–8 hours · Risk: low technically, medium aesthetically · Free**

The insight that makes this cheap: for the *shipped* wallpapers, this is a
**build-time** job, not a runtime one. Extract the dominant colour during
build prep and bake the result into the shipped `.style` files as a normal
`ACCENT=r,g,b`. Zero runtime dependency, zero risk on the user's machine, and
the `.style` format needs no new key at all.

Runtime extraction — for a wallpaper the user chose themselves — is the
optional second half. `python3` is already in the free image
(`system.list.chroot`), but without an imaging library; `python3-pil` is
small, though check the installed size against the ISO budget before adding
it.

*The aesthetic risk is the actual risk.* Dominant-colour extraction very
often returns mud, and an auto-accent that fails a contrast check against the
scheme's text colour produces an unreadable desktop. Clamp saturation and
lightness into a usable band, check contrast, and fall back to
`ACCENT=default` when the result is poor. A feature that silently declines to
do something ugly is better than one that always fires.

*Why it matters commercially:* it demos beautifully and takes a day. Good
value for the store page.

### 3.6 Light/dark auto-switching by time of day

**Effort: 1 day (given §2's refactor) · Risk: low · Free**

A `systemd --user` timer calling `dagric-style --apply` with a light style by
day and a dark one at night — which is exactly why the non-interactive
interface in §2 is a prerequisite. Sunrise/sunset can reuse the location KDE's
Night Light already has in `kwinrc [NightColor]` rather than asking the user
for their coordinates a second time; fixed times are a perfectly acceptable
v1.

*The risk is not technical, it is behavioural:* nothing is more irritating
than a desktop that changes theme while you are working, or that overrides a
choice you just made by hand. Rule: if the user picks a style manually, the
automatic switch stands down until the next day. Ship it off by default.

*Commercially this is modest* — a row in a comparison table more than a
reason to buy. Cheap enough to be worth having; do not spend a week on it.

### 3.7 Per-monitor wallpapers, and a slideshow from the Dagric set

**Effort: slideshow 2–4 hours · per-monitor 1–2 days · Risk: low / medium**

- **Slideshow** is nearly free. Plasma's own `org.kde.slideshow` wallpaper
  plugin, pointed at `/usr/share/wallpapers`, set through the same
  `evaluateScript` route Looks already uses, exposed as a
  `WALLPAPER_MODE=slideshow` key. Note this is not new capability — Plasma has
  always had it, and `dagric-get-variety`'s own help text already tells users
  so. The value is making it one click on the Dagric set instead of a trip
  through Configure Desktop.
- **Per-monitor** is the harder one. `plasma-apply-wallpaperimage` hits every
  containment; doing it per screen means iterating `desktops()` in a Plasma
  script and writing each containment's wallpaper config individually. *The
  risk is testing, not coding:* multi-head in QEMU is fiddly, monitor
  identity is inconsistent across hotplug and docking, and this is a feature
  that fails in exactly the situation you cannot easily reproduce. Budget
  most of the two days for verification, and consider it Pro-flavoured — the
  people with three monitors are the people who buy Pro.

### 3.8 Looks: generate the thumbnail from the panel script

**Effort: 1–2 days (stopgap: 2 hours) · Risk: medium · Free**

Looks needs thumbnails as much as Styles does — arguably more, because
"Horizon — a menu bar up top with a dock below" is a sentence people have to
decode. Three options, in ascending order of merit:

- **Stopgap (2 hours):** ship the seven hand-drawn SVGs from
  `site/assets/look-*.svg` into the image. Instant, honest today — but they
  are drawn by hand, so they will drift from the `SCRIPT` line the moment a
  layout changes, and a *user-contributed* `.look` gets no thumbnail at all.
- **The right answer (1–2 days):** *generate* the wireframe by parsing the
  `SCRIPT` line — count `new Panel`, read each `.location=` and `.height=`,
  and map the `org.kde.plasma.*` widget names to blocks. A contributed layout
  then gets a correct thumbnail automatically, for free, forever. That is the
  argument for doing it properly: it is the only version that scales past the
  seven layouts we wrote ourselves.
- **Screenshots of a nested session:** correct, and far too expensive to
  maintain for one person. No.

*The risk* is that the parser is pattern-matching over JavaScript and will be
wrong for anything clever. Rule: when parsing is not confident, fall back to
a plain generic tile. **Never render a thumbnail that might be wrong** — an
inaccurate picture is worse than no picture, which is the same principle as
§3.1.

### 3.9 Give Looks a Revert — arguably before any of the above

**Effort: 1 day · Risk: medium · Free**

Not on the original list, but it follows directly from the preview-first
principle and from §1: switching layouts destroys the existing panel setup
with no way back. Capture
`~/.config/plasma-org.kde.plasma.desktop-appletsrc` before applying, restore
it and restart `plasmashell` on revert. Same Keep / Revert / auto-revert
pattern as §2, so the UI work is already done.

*Risk:* restoring panel config requires a plasmashell restart, which flickers
and briefly clears the desktop — less elegant than the Styles revert, but
vastly better than the current answer, which is "rebuild your panel by hand".

*Commercially this is defect repair, not a feature.* Someone who lost their
customised panel to an idle click is someone who asks for a refund and tells
other people why.

### Suggested order

Ranked by value delivered per day spent, for a solo developer:

| # | Item | Effort | Why here |
|---|---|---|---|
| 1 | §2 refactor (`--list` / `--apply` / `--capture`) | ~2 h | Unblocks four other items |
| 2 | §3.9 Looks Revert | 1 d | Fixes a real defect |
| 3 | §3.3 Create your own style | 1 d | Reuses §2's code; turns a menu into a system |
| 4 | §3.2 Font pairing + splash | 1 d | No ISO cost; biggest visual step per hour |
| 5 | §3.7 Slideshow | 2–4 h | Nearly free |
| 6 | §3.5 Accent from wallpaper (build-time) | 4–8 h | Demos well, no runtime risk |
| 7 | §3.8 Generated look thumbnails | 1–2 d | Scales to contributed layouts |
| 8 | §3.4 Style import/export (Styles only) | 1–2 d | Needs §3.3 first |
| 9 | §3.1 Mock preview overlay | 3–5 d | The flagship, but the priciest |
| 10 | §3.6 Time-of-day switching | 1 d | Nice to have |
| 11 | §3.7 Per-monitor wallpapers | 1–2 d | Pro audience; testing-heavy |

---

## 4. Bigger bets

These are here to be *evaluated*, and two of the three should probably be
declined. Writing down why is the point.

### A full Appearance app replacing several System Settings pages

**Cost: weeks to months, plus a permanent maintenance tax.**

The appeal is obvious: one coherent Dagric-branded Appearance app instead of
sending users into System Settings, which is dense and does not look like our
product.

The cost is not the first version — it is every version after. A KCM or
Kirigami app sits directly on top of Plasma's configuration surface, and
Plasma 6 moves quickly; config keys move, KCM APIs shift, and each Debian
stable-to-stable jump lands a pile of changes at once. You would also be
reimplementing components KDE already writes, translates into dozens of
languages, and tests on hardware you do not own. For a solo commercial
developer that is a recurring bill with no ceiling.

**Recommended position: do not replace System Settings. Own the curated top
layer and deep-link into it for the long tail.** Dagric Styles and Looks
already do the valuable part — making the ten decisions that matter into two
clicks. Add a "More appearance settings…" row that opens the relevant System
Settings page and let KDE maintain the other ninety. That is a fraction of
the cost and it degrades gracefully when upstream changes, because a link
that opens the wrong-looking page is a nuisance, whereas a reimplementation
that reads a renamed key is a bug report.

### A theme marketplace

**Cost: this is a business, not a feature.**

Payments, hosting, moderation, chargebacks, VAT/sales-tax handling across
jurisdictions for a solo trader, plus a support inbox that never empties.
There is also a licensing trap: most of the ecosystem's themes are GPL, and
you cannot take a GPL theme, put it behind a paywall, and restrict
redistribution. And every uploaded asset is a security review you now own —
see §3.4 on why `.look` files in particular can never be a download.

**Recommended position: no.** The product is a $39 operating system; a
marketplace is a second company. If the demand ever proves real, the version
worth building is *free to download and curated by us*, where Dagric's value
is the curation and the guarantee that nothing in the list is hostile. That
is consistent with the manifesto and it does not require a payments stack.

### Per-user profiles

**Cost: ~1 week. The only one of the three worth taking seriously.**

A profile bundles a style, a look, and adjacent settings — "Work", "Evening",
"Presenting" (dark, dock, notifications silenced, no screen blanking). It is
mostly *composition over things that already exist*, which is why it is a
week and not a month, and it is a natural Pro feature: the free edition gets
Styles and Looks separately, Pro gets one click that sets the whole machine
for what you are about to do.

*The risk is scope creep.* "Profile" quietly grows toward session management,
per-profile app sets, and multi-user policy, and then it is a quarter. Fence
it hard at the start: a profile is a named list of existing switches, nothing
more. If that fence holds, this is the bigger bet to take.

---

## 5. What we deliberately will not do

Each of these is a decision, with a reason. They are as much a part of the
product as the features.

- **No proprietary theme engines, and no non-redistributable assets.** We
  sell ISOs. Every font, icon and cursor in the image must be something we
  are legally allowed to sell — the same reason
  `ttf-mscorefonts-installer` is not in the build. This also rules out
  depending on third-party Plasma styles to get effects Breeze does not
  offer (see the corner-radius note in §3.2): they break on Plasma point
  releases and the support load lands on us.
- **No downloading themes from unvetted stores by default.** The "Get New
  Themes" buttons in stock Plasma pull arbitrary archives from
  store.kde.org, and Plasma themes and widgets can contain executable QML.
  Not enabled by default. If it is ever offered, it is opt-in, with a plain
  warning in plain English, and never for anything containing a script.
- **Nothing phones home.** No count of which style is popular, no "check for
  new themes" ping, no crash reports. The honest consequence: **we will never
  know which styles people actually use.** That is accepted. Ask on the
  forum, like people did before analytics.
- **No mutating the session without a way back.** Any future action that
  changes the desktop ships with revert *in the same release*, not the one
  after. This is what §3.9 is repaying.
- **No thumbnail or preview that might be wrong.** A generic tile beats an
  inaccurate picture, in both Styles and Looks. Trust is the product.
- **No theming outside Plasma's own supported switches.** No patched Qt, no
  `LD_PRELOAD` shims, no hand-editing config files where a scripting API
  exists. Dagric Looks already does this correctly by going through
  `evaluateScript` rather than editing `appletsrc` by hand — that is why it
  survives Plasma updates.
- **No changes that require a logout or reboot**, where any alternative
  exists. If one genuinely does, say so on the button before it is pressed.
- **No engagement mechanics.** No "recommended for you", no badges for
  customising, no nags to try a new theme. Rule 4 of the manifesto: the OS
  disappears behind your work.

---

## 6. How to contribute a style

*This section is for users. The drop-in format is the extension point — it is
meant to be used.*

A Dagric style is a plain text file. There is no compiler, no packaging step,
and you do not need root.

**1. Start from a shipped one.**

```sh
mkdir -p ~/.local/share/dagric/styles
cp /usr/share/dagric/styles/daybreak.style ~/.local/share/dagric/styles/mine.style
```

**2. Edit it.** Every key is optional — leave one out and Dagric leaves that
part of your desktop alone.

```
NAME=My Style
DESCRIPTION=what it looks like, in a few words
SORT=45
SCHEME=DagricDark
ACCENT=92,178,124
WALLPAPER=DagricForest
BLUR=true
TRANSLUCENCY=false
WOBBLY=false
```

- `SCHEME` — any scheme in `/usr/share/color-schemes` (Dagric ships
  `DagricLight` and `DagricDark`; Breeze's own are there too).
- `ACCENT` — `r,g,b` with each value 0–255, or `default` to use the colour
  scheme's own accent. Tip: open Dagric Styles, pick **Accent color**, choose
  your colour, then read the value back out of `~/.config/kdeglobals`.
- `WALLPAPER` — a pack name from `/usr/share/wallpapers`, **or an absolute
  path to any image on your disk**. The path form is the easy one for your
  own pictures.
- `SORT` — menu order, lower first. The shipped styles use 10–60.
- `NAME` defaults to the filename if you leave it out.
- `EDITION=pro` is used by Dagric's own build to mark Pro-only styles; there
  is no reason to put it in yours.

**3. Open Dagric Styles.** Your style is in the list. There is nothing to
install and nothing to restart.

Two more things worth knowing:

- **Later wins.** Files load from `/usr/share/dagric/styles`, then
  `/etc/dagric/styles`, then `~/.local/share/dagric/styles`. A file in your
  home directory with the same name as a shipped one *replaces* it — that is
  how you retune a Dagric style without touching the system.
- **Layouts work the same way**, with `.look` files in
  `~/.local/share/dagric/looks` and a `SCRIPT=` line written in Plasma's
  scripting API. **But note the difference:** a `.style` file is inert data,
  while a `.look` file's `SCRIPT` is *code that Plasma executes* with your
  full session privileges. Sharing and installing `.style` files is safe.
  Only run a `.look` from someone you trust, and read the `SCRIPT` line
  first — it is one line, in the open, on purpose.

**Sending one in.** If you have made something good, open a merge request
against this repository or email it to `repo@dagric.com`. Include the
`.style` file and a screenshot. If it uses your own wallpaper, say whether
you are willing to license it for redistribution — Dagric is a commercial
product, so we can only ship images we are allowed to sell, and we would
rather ask than assume. Styles that make it in are credited.
