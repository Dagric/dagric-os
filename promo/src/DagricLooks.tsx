import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Img,
  staticFile,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BG, LINE, INK, MUTED, ACCENT, ACCENT2, SANS, DIAGRAM } from "./theme";

/**
 * "Pick a desktop. Your desktop." — Dagric Looks, all seven layouts.
 * 1920x1080, 30fps, 1020 frames (34.0s).
 *
 * WHY THIS EXISTS. DagricPromo already has a Looks scene and it is wrong in
 * ways that cost money. It animates FOUR of the seven layouts, which means the
 * free edition reads as two layouts when it ships three (Classic, Focus,
 * Centered), and Pro reads as "adds two" when it adds four. It draws Horizon's
 * bottom panel as a floating, rounded, screen-centred dock with a second
 * Dagric launcher sitting on it — horizon.look adds exactly one widget to that
 * panel, org.kde.plasma.icontasks, and sets nothing but .location and .height.
 * That scene is not edited here (it is out of scope and still shipping); this
 * file is the replacement that does not carry those errors forward.
 *
 * THE ONE STRUCTURAL RULE. Every rectangle on screen that represents a panel
 * comes out of LOOKS below, through rectFor() and <LookTile>, and there is no
 * other drawing path. The wide grid shot and every close-up are literally the
 * same mounted <LookTile> under a different CSS transform, not two drawings
 * that have to be kept in agreement. That matters because the repo already
 * shows what happens when they are two drawings: site/assets/look-horizon.svg
 * and tools/make-appearance-thumbs.sh depict the same layout incompatibly, and
 * only the second one matches the script. Here that class of bug has nowhere
 * to live.
 *
 * WHAT THE RENDERER STRUCTURALLY CANNOT DRAW: a floating panel, a centred
 * panel, a rounded panel, an inset panel, a length-limited panel, an
 * auto-hiding panel, a second kickoff, or a wallpaper/colour change between
 * layouts. rectFor() has three cases and all three return an edge-flush,
 * square-cornered rectangle spanning its whole edge — except where a left dock
 * already owns the top-left corner, which shortens the top panel by the dock's
 * thickness on Command and Unity (see the corner note in LookTile; the two
 * shipped asset sets disagree about that corner and the tie is broken on the
 * scripts' own construction order). Nothing else insets anything, because a
 * grep across all seven
 * .look files for floating / alignment / lengthMode / hiding / offset /
 * minimumLength / maximumLength returns nothing at all. Only .location and
 * .height are ever assigned, and the only non-panel statements in any of the
 * seven scripts are the two kickoff branding calls.
 *
 * NO WIDGET EVER TRAVELS BETWEEN PANELS. There are no cross-layout morphs in
 * this composition, and if one is ever added it must be a REBUILD and not a
 * tween: dagric-looks line 39 prefixes every layout with
 * `var ps=panels(); for(var i=0;i<ps.length;i++){ps[i].remove();}` and line 124
 * applies "$CLEAR $SCRIPT", so panels are destroyed and recreated, never
 * moved. An animation that slides a pinned application from one panel to
 * another would be claiming a persistence the tool does not have — which is
 * exactly the claim site/index.html:192 makes ("Every layout keeps your apps,
 * files, and settings") and the shipped manual contradicts. The tile entry in
 * SCENE 1 is already the right grammar: panels grow in from their own edge.
 *
 * TYPE FLOOR: nothing carrying a fact is set below 44px, because this plays at
 * 320px wide on a phone and 44px lands at 7.3px there. Anything smaller must
 * be redundant with something already said larger or shown as a shape — the
 * per-tile PRO chip (36px) is redundant with the legend, and the provenance
 * line (28px) states no product fact.
 */

// ────────────────────────────────────────────────────────────────────────────
// THE DATA. Transcribed field-for-field from the SCRIPT= lines of the seven
// files in config/includes.chroot/usr/share/dagric/looks/. Each row names its
// source file so the two can be diffed by eye. `gu` is the multiplier inside
// Math.round(gridUnit*N); `widgets` is the literal addWidget() order, applet
// ids included, nothing dropped and nothing reordered.
//
// Read the SCRIPT lines with:
//   grep -h '^SCRIPT=' config/includes.chroot/usr/share/dagric/looks/*.look
// ────────────────────────────────────────────────────────────────────────────

type Edge = "top" | "bottom" | "left";
type PanelSpec = { edge: Edge; gu: number; widgets: string[] };
type Look = {
  id: string;
  name: string;
  description: string;
  sort: number;
  pro: boolean;
  panels: PanelSpec[];
};

const LOOKS: Look[] = [
  {
    // looks/classic.look — SORT=10, no EDITION line, so free.
    id: "classic",
    name: "Classic",
    description: "a taskbar at the bottom, familiar and comfortable",
    sort: 10,
    pro: false,
    panels: [
      {
        edge: "bottom",
        gu: 2.2,
        widgets: [
          "kickoff",
          "pager",
          "taskmanager",
          "marginsseparator",
          "systemtray",
          "digitalclock",
          "showdesktop",
        ],
      },
    ],
  },
  {
    // looks/focus.look — SORT=20, no EDITION line, so free.
    // Note gridUnit*2 in the file, not *2.0; same number.
    id: "focus",
    name: "Focus",
    description: "one tidy bar, nothing in your way",
    sort: 20,
    pro: false,
    panels: [
      {
        edge: "bottom",
        gu: 2.0,
        widgets: [
          "kickoff",
          "icontasks",
          "marginsseparator",
          "systemtray",
          "digitalclock",
        ],
      },
    ],
  },
  {
    // looks/eleven.look — SORT=30, no EDITION line, so free.
    // The two panelspacers bracketing icontasks are the entire centring
    // mechanism, and kickoff is added BEFORE the first one, so the launcher
    // stays hard left. Nothing here sets an alignment.
    id: "eleven",
    name: "Centered",
    description: "a centered taskbar, clean and modern",
    sort: 30,
    pro: false,
    panels: [
      {
        edge: "bottom",
        gu: 2.4,
        widgets: [
          "kickoff",
          "panelspacer",
          "icontasks",
          "panelspacer",
          "systemtray",
          "digitalclock",
        ],
      },
    ],
  },
  {
    // looks/horizon.look — SORT=40, EDITION=pro.
    // The bottom panel gets ONE addWidget call. No launcher, no floating, no
    // centring, no radius: `var d=new Panel; d.location="bottom";
    // d.height=Math.round(gridUnit*3); d.addWidget("org.kde.plasma.icontasks");`
    id: "horizon",
    name: "Horizon",
    description: "a menu bar up top with a dock below",
    sort: 40,
    pro: true,
    panels: [
      {
        edge: "top",
        gu: 1.6,
        widgets: [
          "kickoff",
          "appmenu",
          "panelspacer",
          "systemtray",
          "digitalclock",
        ],
      },
      { edge: "bottom", gu: 3.0, widgets: ["icontasks"] },
    ],
  },
  {
    // looks/command.look — SORT=50, EDITION=pro.
    // On a location="left" panel, .height is the dock's thickness. Nothing in
    // this repo documents that, so no caption in this video puts a pixel width
    // on it; the spec line says "left 3.2 grid units" and stops there.
    id: "command",
    name: "Command",
    description: "a side dock for living in your apps",
    sort: 50,
    pro: true,
    panels: [
      { edge: "left", gu: 3.2, widgets: ["kickoff", "icontasks"] },
      {
        edge: "top",
        gu: 1.5,
        widgets: ["panelspacer", "systemtray", "digitalclock"],
      },
    ],
  },
  {
    // looks/unity.look — SORT=60, EDITION=pro.
    // Character-for-character identical to command.look except for the single
    // leading appmenu on the top panel. The spec lines for Command and Unity
    // therefore read identically — both print "left 3.2 · top 1.5 grid units",
    // which is what specLine() below actually emits — and that is not a
    // copy-paste slip, it is the fact. The whole difference between these two
    // layouts is one widget, so the menu bar has to be what the eye sees.
    id: "unity",
    name: "Unity",
    description: "a side dock with a global menu bar on top",
    sort: 60,
    pro: true,
    panels: [
      { edge: "left", gu: 3.2, widgets: ["kickoff", "icontasks"] },
      {
        edge: "top",
        gu: 1.5,
        widgets: ["appmenu", "panelspacer", "systemtray", "digitalclock"],
      },
    ],
  },
  {
    // looks/duo.look — SORT=70, EDITION=pro.
    // Duo's bottom panel and Classic's are both 46 logical pixels, so they
    // MUST render at exactly the same thickness here.
    // They do, because GU is one expression for the whole file. The shipped
    // SVGs draw them 40px and 34px, a 15% disagreement about two numbers that
    // are the same number; do not "fix" one tile and reintroduce it.
    // No kickoff, no systemtray and no clock on this panel: they are upstairs.
    id: "duo",
    name: "Duo",
    description: "two panels, top and bottom, for power users",
    sort: 70,
    pro: true,
    panels: [
      {
        edge: "top",
        gu: 1.6,
        widgets: [
          "kickoff",
          "appmenu",
          "panelspacer",
          "systemtray",
          "digitalclock",
        ],
      },
      {
        edge: "bottom",
        gu: 2.2,
        widgets: ["pager", "taskmanager", "showdesktop"],
      },
    ],
  },
];

// Playback order is SORT ascending, which is the order dagric-looks line 94
// (`sort -n -k1,1`) builds its menu in, so the video walks the real menu from
// the top. LOOKS is already in that order; sorting makes it stay that way if a
// row is ever inserted.
const ORDER = [...LOOKS].sort((a, b) => a.sort - b.sort);

// ────────────────────────────────────────────────────────────────────────────
// GEOMETRY
// ────────────────────────────────────────────────────────────────────────────

/**
 * Grid units per tile height. THIS IS A DRAWING SCALE, NOT A MEASUREMENT.
 *
 * This repository does not determine gridUnit. A full-tree grep for it hits
 * exactly seven files — the seven .look scripts — and nothing else. It is a
 * global injected by plasmashell's own scripting engine, which is where the
 * SCRIPT string is evaluated: dagric-looks lines 52-55 ship the whole thing to
 * org.kde.PlasmaShell.evaluateScript over D-Bus. Worse for anyone wanting a
 * pixel number, the image deliberately refuses to pin what gridUnit derives
 * from — etc/skel/.config/kdeglobals is two lines with no font block,
 * 0520-display-defaults.hook.chroot lines 14-23 decline on the record to set
 * either kdeglobals [KScreen] ScaleFactor or kcmfonts forceFontDPI, and
 * /usr/lib/dagric/display-autoscale changes the per-output scale at every
 * login. So there is no single true pixel height, and this video never prints
 * one: the captions print grid units, which is what the .look file contains.
 *
 * What one constant for the whole file DOES buy is that the seven multipliers
 * stay in exact proportion WITHIN A TILE: a tile divides its own height by 27,
 * so the ratio between two panels of the same layout is the ratio between their
 * .look multipliers — Horizon's 3.0 dock is exactly 2.0x its own 1.5 sibling.
 *
 * ACROSS tiles that is not true in the grid scene, and the difference is
 * deliberate rather than an oversight: R1 (the free row) is 270 tall and R2
 * (the Pro row) is 207, so a grid unit is 10.0px on the free row and 7.67px on
 * the Pro row. Horizon's 3.0gu dock therefore draws 23px against Classic's
 * 2.2gu bar at 22px — a 36% difference in the data reading as 4% on screen.
 * The free row is drawn larger because the whole argument of this scene is that
 * three layouts is a complete desktop and not a trial, and that is worth more
 * than a cross-row thickness comparison nobody makes. The close-ups are where
 * thickness is actually read, and there every tile is the same size.
 * Written down because the previous version of this paragraph claimed the
 * proportions held everywhere, which was the same overstatement it was warning
 * about two paragraphs down.
 *
 * That is a claim about ratios, and an earlier version of this comment
 * overstated it into a claim about the shipped SVGs' defect being structurally
 * impossible here. It was not. thick() used to Math.round its result, and at
 * grid scale (GU = 7.667) that rounded 1.5 and 1.6 grid units onto the same 12
 * pixels and left Horizon's 3.0 dock one pixel thicker than Classic's 2.2 bar —
 * reproducing, in the two frames where all seven tiles are on screen, exactly
 * the flattening this paragraph claimed could not happen. Rounding is gone from
 * thick() and the claim is now the narrower true one. Recorded rather than
 * quietly corrected, because a comment asserting a property the code does not
 * have is the defect this project keeps finding.
 *
 * For reference, the defect in the shipped site SVGs is real and separate: they
 * compress every panel above about 2.2gu, drawing horizon's 3.0 dock the same
 * 40px as classic's 2.2 bar.
 *
 * 27 is a legibility exaggeration and is chosen, not measured: scaled to a
 * 1920-wide screen it works out at ~40px per grid unit, which is less
 * exaggerated than the ~48px/gu the repo's own thumbnail generator draws. If a
 * real number is ever needed it has to be measured on a booted image, out of
 * ~/.config/plasma-org.kde.plasma.desktop-appletsrc after applying a layout.
 */
const GU_DIVISOR = 27;

/**
 * The only place a panel becomes a rectangle.
 *
 * Three cases, every one full-length and flush to its edge, because not one of
 * the seven scripts sets floating, alignment, lengthMode, hiding, offset,
 * minimumLength or maximumLength. `inset` is the thickness of the layout's
 * left dock, if it has one — see the corner note in <LookTile>.
 */
const rectFor = (p: PanelSpec, w: number, h: number, t: number, inset: number) => {
  if (p.edge === "left") return { left: 0, top: 0, width: t, height: h };
  if (p.edge === "top")
    return { left: inset, top: 0, width: w - inset, height: t };
  return { left: inset, top: h - t, width: w - inset, height: t };
};

/**
 * "top 1.6 · bottom 3.0 grid units" — generated from the panel table, never
 * typed, so it cannot drift from the shape drawn beside it.
 *
 * A single-panel layout reads "bottom · 2.2 grid units": the multiplier is the
 * point, and the panel COUNT is already both drawn in the tile and said in the
 * description, so repeating it here only cost the line a wrap. The
 * non-breaking space keeps "grid units" together when the two-panel version
 * does wrap, instead of orphaning "units" on a line of its own.
 */
const specLine = (look: Look) => {
  const parts = look.panels.map((p) =>
    look.panels.length === 1 ? `${p.edge} · ${p.gu.toFixed(1)}` : `${p.edge} ${p.gu.toFixed(1)}`
  );
  return `${parts.join(" · ")} grid units`;
};

// ────────────────────────────────────────────────────────────────────────────
// WIDGETS
//
// One glyph per applet id, sized as a fraction of its own panel's thickness so
// the same widget on Command's 1.5gu strip and on Horizon's 3.0gu dock is the
// same object at two scales. The repeated-glyph COUNTS (2 pager cells, 3 task
// buttons, 5 task icons, 3 tray dots, 3 menu entries) are a rendering choice,
// not a product fact: a SCRIPT fixes the kind and order of applets, never how
// many windows are open. They are held identical across all seven tiles so no
// layout reads as busier than another for a reason the product does not cause.
// That also settles the 4-vs-5-vs-7 disagreement between the shipped SVGs and
// the shipped PNG thumbnails.
// ────────────────────────────────────────────────────────────────────────────

const Widget: React.FC<{ id: string; t: number; vertical: boolean }> = ({
  id,
  t,
  vertical,
}) => {
  // A flex item whose long axis follows the panel. Only kickoff and icontasks
  // ever appear on a vertical panel (command.look and unity.look put nothing
  // else on their left dock), so the swap below is only ever exercised by
  // squares — but it is written generically rather than special-cased,
  // because a hand-written vertical variant for a widget no .look places
  // vertically would be code describing data that does not exist.
  const box = (long: number, cross: number, extra: React.CSSProperties = {}) => ({
    width: vertical ? cross : long,
    height: vertical ? long : cross,
    flex: "0 0 auto" as const,
    ...extra,
  });
  const strip = (extra: React.CSSProperties = {}) => ({
    display: "flex" as const,
    flexDirection: (vertical ? "column" : "row") as "row" | "column",
    alignItems: "center" as const,
    flex: "0 0 auto" as const,
    ...extra,
  });

  switch (id) {
    // The branded launcher. Every one of the seven scripts calls
    // k.writeConfig("icon","dagric-logo") on it, so the D survives a layout
    // switch — one of the very few claims about this feature that the code
    // supports outright. Drawn exactly ONCE per layout, on whichever panel the
    // script names. Horizon's dock and Duo's bottom bar get none.
    case "kickoff":
      return (
        <div
          style={box(t * 0.72, t * 0.72, {
            borderRadius: t * 0.2,
            background: `linear-gradient(135deg, ${DIAGRAM.dFrom}, ${DIAGRAM.dTo})`,
            color: "#fff",
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: t * 0.44,
            lineHeight: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          })}
        >
          D
        </div>
      );

    // A VIRTUAL-DESKTOP SWITCHER, not application icons. Two narrow cells,
    // visibly dimmer and thinner than an app icon, which is how the repo's own
    // tools/make-appearance-thumbs.sh draws it. look-classic.svg draws three
    // icon-sized tiles here instead, which is wrong twice over: classic.look
    // uses taskmanager, not icontasks, so it has no pinned launchers at all.
    // Only classic.look and duo.look contain a pager.
    case "pager":
      return (
        <div style={strip({ gap: t * 0.09 })}>
          {[0, 1].map((i) => (
            <div
              key={i}
              style={box(t * 0.34, t * 0.5, {
                borderRadius: t * 0.06,
                background: DIAGRAM.pager,
              })}
            />
          ))}
        </div>
      );

    // Wide, labelled task buttons. classic.look and duo.look only.
    case "taskmanager":
      return (
        <div style={strip({ gap: t * 0.16 })}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={box(t * 2.4, t * 0.42, {
                borderRadius: t * 0.08,
                background: DIAGRAM.tile2,
              })}
            />
          ))}
        </div>
      );

    // Icon-only tasks. focus, eleven, horizon, command, unity.
    case "icontasks":
      return (
        <div style={strip({ gap: t * 0.16 })}>
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={box(t * 0.62, t * 0.62, {
                borderRadius: t * 0.16,
                background: DIAGRAM.tile,
              })}
            />
          ))}
        </div>
      );

    // Draws nothing and grows. This one element is why Centered's task block
    // lands centred and why the tray and clock sit hard right on horizon,
    // command, unity and duo: the layout falls out of the widget ORDER in the
    // script rather than being positioned by hand.
    case "panelspacer":
      return <div style={{ flex: 1 }} />;

    // Also draws nothing and also grows. Plasma's separator applet is
    // invisible, so drawing a glyph for it would be inventing a widget — but
    // giving it zero width would put Focus's tray immediately beside its task
    // icons, and BOTH shipped asset sets (look-focus.svg's tray at cx=560 of
    // 640, and the MVG recipe) put the tray and clock at the far end. classic
    // and focus only.
    case "marginsseparator":
      return <div style={{ flex: 1 }} />;

    case "systemtray":
      return (
        <div style={strip({ gap: t * 0.14 })}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={box(t * 0.18, t * 0.18, {
                borderRadius: t * 0.09,
                background: DIAGRAM.tray,
              })}
            />
          ))}
        </div>
      );

    // 7:17 is the site's own diagram convention — every one of the seven
    // look-*.svg files sets that time — so the video and the artwork beside it
    // on the page agree. The real capture in SCENE 0 reads 6:53 PM; that is a
    // photograph of one moment, not a convention, and the two are not in
    // conflict. Do not "fix" either to match the other.
    case "digitalclock":
      return (
        <div
          style={{
            flex: "0 0 auto",
            color: DIAGRAM.panelInk,
            fontFamily: SANS,
            fontWeight: 500,
            fontSize: t * 0.42,
            lineHeight: 1,
            whiteSpace: "nowrap",
          }}
        >
          7:17
        </div>
      );

    // The peek sliver at the far end of the bar. classic and duo only, and
    // missing from BOTH of the shipped SVGs that should have it — the same
    // omission in the same place in both, because classic and duo are exactly
    // the two layouts whose panel ends in showdesktop. marginLeft auto is what
    // puts it at the end on Duo, whose bottom panel has neither a spacer nor a
    // separator to do the job.
    //
    // Nearly the full height of the bar, not a small tile: the repo's own
    // thumbnail recipe draws it `rectangle 469,247 475,266` inside a panel
    // spanning y 243-270, i.e. a thin strip running almost edge to edge, which
    // is what Plasma's show-desktop corner actually looks like. Drawn in the
    // icon colour rather than the generator's translucent white, which would
    // be invisible on a light panel — and a widget nobody can see is the same
    // defect as a widget that was left out.
    case "showdesktop":
      return (
        <div
          style={box(t * 0.16, t * 0.8, {
            borderRadius: t * 0.04,
            background: DIAGRAM.tile,
            [vertical ? "marginTop" : "marginLeft"]: "auto",
          })}
        />
      );

    // The global menu: one active entry then two quiet ones. Present on
    // horizon, unity and duo, absent from command — and that single applet is
    // the entire difference between command.look and unity.look, produced here
    // from the data rather than from a per-layout branch.
    case "appmenu":
      return (
        <div style={strip({ gap: t * 0.18 })}>
          {[
            { w: t * 0.92, c: DIAGRAM.tile },
            { w: t * 0.66, c: DIAGRAM.tile2 },
            { w: t * 0.66, c: DIAGRAM.tile2 },
          ].map((p, i) => (
            <div
              key={i}
              style={box(p.w, t * 0.2, {
                borderRadius: t * 0.05,
                background: p.c,
              })}
            />
          ))}
        </div>
      );

    default:
      // Unreachable for the seven shipped files. Loud rather than silent: a
      // dropped widget is exactly the defect this composition exists to avoid,
      // so an unknown applet id draws a red bar instead of nothing.
      return <div style={box(t * 0.5, t * 0.5, { background: "#ff3b30" })} />;
  }
};

// ────────────────────────────────────────────────────────────────────────────
// THE TILE — one layout, drawn at whatever size the caller asks for.
// ────────────────────────────────────────────────────────────────────────────

const LookTile: React.FC<{ look: Look; w: number; h: number; entry: number }> = ({
  look,
  w,
  h,
  entry,
}) => {
  const GU = h / GU_DIVISOR;
  // NOT Math.round. Rounding to whole pixels collapses distinct multipliers
  // onto the same thickness at small tile sizes, and the two places it happens
  // are the two places the difference is the whole point:
  //   grid view, GU = 7.667 -> round(1.5*GU) = 12 and round(1.6*GU) = 12, so
  //     Command/Unity's 1.5 top strip and Horizon/Duo's 1.6 top bar drew
  //     identically, and Horizon's 3.0 dock (the thickest panel in the set)
  //     came out 23px against Classic's 2.2 bar at 22px — a 36% difference in
  //     the data rendered as 4%.
  // The browser antialiases fractional heights perfectly well, and a ratio
  // that is true at every zoom is worth more than a crisp edge. Verified after
  // the change by measuring the rendered rows rather than by reasoning.
  const thick = (p: PanelSpec) => GU * p.gu;

  // CORNER OWNERSHIP, command and unity. A left panel and a top panel have to
  // resolve the top-left corner, and this repo does not determine the answer —
  // the site SVGs give it to the dock, the PNG thumbnails give it to the top
  // bar, so the two shipped asset sets are mirror images of each other. Broken
  // here on the only ordering fact the scripts supply: `var s` (left) is
  // constructed before `var t` (top) in both files, so the dock runs full
  // height and the top strip starts at x = dock thickness.
  const leftPanel = look.panels.find((p) => p.edge === "left");
  const inset = leftPanel ? thick(leftPanel) : 0;

  return (
    <div
      style={{
        position: "absolute",
        width: w,
        height: h,
        overflow: "hidden",
        borderRadius: Math.max(6, h * 0.016),
        border: `1px solid ${LINE}`,
        // The wallpaper: vertical gradient plus the bloom, both from
        // make-wallpapers.sh line 241 (`classic 0d1728 060b14 40b0ff 0.962`).
        // bloom() draws an ellipse as wide as the frame and 88% of H tall,
        // centred at 45% of H, at near-full strength — which is why a real
        // Dagric desktop reads far bluer than the two gradient hexes suggest.
        background: `radial-gradient(ellipse 62% 46% at 50% 45%, rgba(64,176,255,0.42) 0%, rgba(64,176,255,0.12) 55%, rgba(64,176,255,0) 78%), linear-gradient(180deg, ${DIAGRAM.wallTop} 0%, ${DIAGRAM.wallBottom} 100%)`,
      }}
    >
      {/* The three sweeps, at the literal bezier control points of sweeps() in
          make-wallpapers.sh lines 100-103, expressed as fractions of W and H,
          with its stroke-opacities .30 / .20 / .12 and its colour (the bloom's
          own, not the site's accent). */}
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        style={{ position: "absolute", inset: 0 }}
      >
        {[
          { o: 0.3, a: 0.76, b: 0.7, c: 0.83, d: 0.74, x1: 0.32, x2: 0.68 },
          { o: 0.2, a: 0.83, b: 0.77, c: 0.9, d: 0.81, x1: 0.36, x2: 0.72 },
          { o: 0.12, a: 0.9, b: 0.85, c: 0.96, d: 0.88, x1: 0.4, x2: 0.76 },
        ].map((s, i) => (
          <path
            key={i}
            d={`M 0 ${h * s.a} C ${w * s.x1} ${h * s.b}, ${w * s.x2} ${h * s.c}, ${w} ${h * s.d}`}
            fill="none"
            stroke={DIAGRAM.wallBloom}
            strokeOpacity={s.o}
            strokeWidth={Math.max(1, h * 0.006)}
          />
        ))}
      </svg>

      {/* The wallpaper brand mark, at 24% from the top — brand() in
          make-wallpapers.sh composites the logo at gravity north, Y0=H*24/100.
          All seven site SVGs put a lone D at the vertical CENTRE instead. The
          DAGRIC wordmark and the OWN IT OUTRIGHT strapline that brand() adds
          beneath it are omitted here FOR LEGIBILITY at tile scale — they are
          on the shipped wallpaper, they are just illegible at 368px wide. */}
      <div
        style={{
          position: "absolute",
          top: h * 0.24,
          width: "100%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: h * 0.17,
            lineHeight: 1,
            background: `linear-gradient(135deg, ${DIAGRAM.dFrom}, ${DIAGRAM.dTo})`,
            WebkitBackgroundClip: "text",
            color: "transparent",
          }}
        >
          D
        </div>
        <div
          style={{
            width: h * 0.15,
            height: Math.max(2, h * 0.009),
            borderRadius: 999,
            background: DIAGRAM.wallBloom,
            opacity: 0.6,
            margin: `${h * 0.018}px auto 0`,
          }}
        />
      </div>

      {/* NO APPLICATION WINDOWS, NO CURSOR, NO WINDOW CHROME, NO PANEL SHADOW.
          A tile is shown at 3x during the tour and the fastest route from
          "diagram" to "fabricated screenshot" is a convincing fake window.
          InstallWalkthrough.tsx:29-32 states the rule this is the other half
          of: the only photograph in this video is a real capture, and
          everything else must look drawn on purpose. */}

      {look.panels.map((p, i) => {
        const t = thick(p);
        const r = rectFor(p, w, h, t, p.edge === "left" ? 0 : inset);
        const vertical = p.edge === "left";
        // Panels grow in from their own edge — the parsed `location` IS the
        // entry direction, and it is a rebuild rather than a slide from
        // somewhere else. See the CLEAR note in the file header.
        const off = (1 - entry) * t;
        const dx = p.edge === "left" ? -off : 0;
        const dy = p.edge === "top" ? -off : p.edge === "bottom" ? off : 0;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              ...r,
              transform: `translate(${dx}px, ${dy}px)`,
              background: DIAGRAM.panel,
              display: "flex",
              flexDirection: vertical ? "column" : "row",
              alignItems: "center",
              gap: t * 0.16,
              padding: t * 0.14,
              boxSizing: "border-box",
              // Square corners, always. See rectFor().
            }}
          >
            {p.widgets.map((id, j) => (
              <Widget key={`${id}-${j}`} id={id} t={t} vertical={vertical} />
            ))}
          </div>
        );
      })}
    </div>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// THE STAGE — grid geometry and the camera.
// ────────────────────────────────────────────────────────────────────────────

// Row 1 is the three free layouts, drawn LARGER and read first. Row 2 is the
// four Pro ones. Nothing is greyed, locked, badged out or blurred at any frame
// of this video: at the edition boundary something is ADDED, never removed.
const R1 = { w: 480, h: 270, y: 160, gap: 48 }; // 3*480 + 2*48 = 1536, centred at x=192
const R2 = { w: 368, h: 207, y: 546, gap: 44 }; // 4*368 + 3*44 = 1604, centred at x=158
// 16:9, deliberately. The shipped site SVGs are 640x400 — 16:10 — which makes
// every horizontal bar 11% taller relative to the screen than it really is.

const gridRect = (i: number) => {
  const free = i < 3;
  const row = free ? R1 : R2;
  const n = free ? 3 : 4;
  const total = n * row.w + (n - 1) * row.gap;
  const x0 = (1920 - total) / 2;
  const k = free ? i : i - 3;
  return { x: x0 + k * (row.w + row.gap), y: row.y, w: row.w, h: row.h };
};

// The close-up: every tile resolves to this same rect, which is what makes
// px-per-gridUnit constant across all seven and stops any single layout being
// flattered or flattened relative to the others.
const CU = { x: 80, y: 225, w: 1120 };
const WIDE = { s: 1, tx: 0, ty: 0 };
const poseFor = (i: number) => {
  const g = gridRect(i);
  const s = CU.w / g.w;
  return { s, tx: CU.x - g.x * s, ty: CU.y - g.y * s };
};

// ────────────────────────────────────────────────────────────────────────────
// FRAME PLAN. Root.tsx's arithmetic rule applies to the last Sequence:
// 903 + 117 = 1020.
//
//   SCENE 0  PLATE    0 -  90   the real capture, 3.0s
//   SCENE 1  BUILD   90 - 225   the grid assembles, 4.5s
//   SCENE 2  TOUR   225 - 813   7 x 84f, 19.6s
//   SCENE 3  SPLIT  813 - 903   pull back, name the edition split, 3.0s
//   SCENE 4  CLOSE  903 - 1020  3.9s
//
// Tour beats, needed by anyone grabbing a still or checking a claim:
//   classic 225-309   focus 309-393   eleven 393-477   horizon 477-561
//   command 561-645   unity 645-729   duo 729-813
// ────────────────────────────────────────────────────────────────────────────

const PLATE_END = 90;
const STAGE_FROM = 90;
const BUILD_LEN = 135;
const TOUR_FROM = 225;
const BEAT = 84;
const TOUR_END = TOUR_FROM + BEAT * 7; // 813
const SPLIT_LEN = 90;
const CLOSE_FROM = TOUR_END + SPLIT_LEN; // 903
const CLOSE_LEN = 117;
export const DAGRIC_LOOKS_FRAMES = CLOSE_FROM + CLOSE_LEN; // 1020

/** Camera keyframes in GLOBAL frames. One pose lerped as a unit. */
const CAMERA: { at: number; len: number; pose: typeof WIDE }[] = [
  { at: STAGE_FROM, len: 1, pose: WIDE },
  // The move onto Horizon is the only one that changes ROW, and so the only
  // one that changes scale. It gets 26 frames where a pure horizontal pan
  // inside a row gets 18.
  ...ORDER.map((_, i) => ({
    at: TOUR_FROM + BEAT * i,
    len: i === 0 ? 22 : i === 3 ? 26 : 18,
    pose: poseFor(i),
  })),
  { at: TOUR_END, len: 24, pose: WIDE },
];

const Stage: React.FC = () => {
  // REBASED TO THE TIMELINE, and it has to be. Everything in this file's frame
  // plan — the CAMERA keyframes, the tour beats, the tile entry stagger — is
  // written in GLOBAL frames, because those numbers have to line up with the
  // `from` values on the Caption <Sequence>s at the bottom of the file. Inside
  // a <Sequence>, useCurrentFrame() counts from that sequence's own start, so
  // the raw value is 90 frames behind. Without the rebase the camera simply
  // never leaves the wide pose: every `frame >= CAMERA[i].at` test lags by the
  // sequence offset and the tour renders as a static grid with captions
  // sliding over it.
  const frame = useCurrentFrame() + STAGE_FROM;
  const { fps } = useVideoConfig();

  // Find the keyframe in force and lerp from the previous pose. damping 200 is
  // the only spring in this codebase and it does not overshoot, which matters:
  // a camera that bounces on arrival reads as cheap, and there are eight
  // arrivals here.
  let k = 0;
  for (let i = 0; i < CAMERA.length; i++) if (frame >= CAMERA[i].at) k = i;
  const to = CAMERA[k];
  const from = CAMERA[Math.max(0, k - 1)].pose;
  const p =
    k === 0
      ? 1
      : spring({
          frame: frame - to.at,
          fps,
          config: { damping: 200 },
          durationInFrames: to.len,
        });
  const s = from.s + (to.pose.s - from.s) * p;
  const tx = from.tx + (to.pose.tx - from.tx) * p;
  const ty = from.ty + (to.pose.ty - from.ty) * p;

  // Which tile the camera is on, for the focus dim. -1 during the wide poses.
  const focus =
    frame >= TOUR_FROM && frame < TOUR_END
      ? Math.floor((frame - TOUR_FROM) / BEAT)
      : -1;

  return (
    <AbsoluteFill
      style={{ transform: `translate(${tx}px, ${ty}px) scale(${s})`, transformOrigin: "0 0" }}
    >
      {ORDER.map((look, i) => {
        const g = gridRect(i);
        // Staggered entry, in SORT order. The tile card springs up first and
        // its panels grow in from their own edges 6f later.
        //
        // 13 frames apart, not 16: at 16 the seventh tile only finished
        // arriving at frame 218 and the camera dived into Classic at 225,
        // leaving seven frames of full grid. The establishing shot IS the
        // argument about how much you get, and a quarter of a second of it is
        // not an establishing shot. This lands the last tile at 198 and buys
        // 27 frames of held grid before the tour starts.
        const t0 = STAGE_FROM + 12 + i * 13;
        const card = spring({
          frame: frame - t0,
          fps,
          config: { damping: 200 },
          durationInFrames: 14,
        });
        const entry = interpolate(frame, [t0 + 6, t0 + 18], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        // Dimming is a focus device and is applied to free and Pro tiles by
        // exactly the same rule. It is never a lock, a badge or a gate.
        const dim = focus === -1 || focus === i ? 1 : 0.38;
        const sat = focus === -1 || focus === i ? 1 : 0.55;
        return (
          <div
            key={look.id}
            style={{
              position: "absolute",
              left: g.x,
              top: g.y,
              width: g.w,
              height: g.h,
              opacity: card * dim,
              filter: `saturate(${sat})`,
              transform: `scale(${interpolate(card, [0, 1], [0.88, 1])})`,
              boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
              borderRadius: Math.max(6, g.h * 0.016),
            }}
          >
            <LookTile look={look} w={g.w} h={g.h} entry={entry} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// SCENE 0 — the only photograph in the piece.
// ────────────────────────────────────────────────────────────────────────────

/**
 * promo/public/dagric-looks.png, a real capture of the free ISO, shipped in
 * this folder and unused by every other composition until now.
 *
 * Shown WIDE and uncropped on purpose. The three things around the dialog —
 * the "Check This PC" and "Install Dagric OS" desktop icons, the Dagric
 * Hardware Check window behind it, and the live session taskbar — are the
 * proof that this is a booted machine and not a mock-up, and a crop tight to
 * the three list rows throws all of it away and turns evidence back into a
 * graphic. It is also the honest answer to the first question a Windows
 * refugee has, which is not "how many layouts" but "is this a real computer".
 *
 * WHAT THIS FRAME MUST NEVER BE LABELLED. The taskbar visible in it is
 * Plasma's stock panel with a re-branded launcher, NOT the Classic layout:
 * config/includes.chroot/etc/skel/.config/ ships no
 * plasma-org.kde.plasma.desktop-appletsrc, and dagric-brand-launcher says in
 * its own header that it "only touches the launcher icon, never the panel
 * layout". The Classic row being highlighted in the dialog is kdialog's
 * default selection, not an applied layout. Nothing in this scene says
 * "Classic", and nothing added to it may.
 */
const Plate: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 12, 74, 90], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, 90], [1.0, 1.05]);
  const capY = interpolate(frame, [14, 32], [-26, 0], { extrapolateRight: "clamp" });
  const capO = interpolate(frame, [14, 32], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 44 }}>
        <Img
          src={staticFile("dagric-looks.png")}
          style={{
            width: "100%",
            maxHeight: "94%",
            // "contain", never "cover": the capture is 1280x800 (the QEMU
            // harness resolution) inside a 16:9 frame, and cover would crop
            // the taskbar and the desktop icons off — which is most of what
            // this shot is for.
            objectFit: "contain",
            borderRadius: 12,
            border: `1px solid ${LINE}`,
            transform: `scale(${scale})`,
            boxShadow: "0 30px 90px rgba(0,0,0,0.6)",
          }}
        />
      </AbsoluteFill>
      {/* The label sits at the TOP of the frame, not the bottom. At the bottom
          it covered the middle of the live session's taskbar — and the taskbar
          is part of what makes this shot evidence rather than a mock-up. The
          top band of the capture is empty wallpaper to the right of the two
          desktop icons, so nothing is hidden there. */}
      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "center",
          padding: "34px 0 0",
          transform: `translateY(${capY}px)`,
          opacity: capO,
        }}
      >
        <div
          style={{
            background: "rgba(10,17,28,0.80)",
            border: `1px solid ${LINE}`,
            borderRadius: 12,
            padding: "16px 34px",
            textAlign: "center",
            backdropFilter: "blur(6px)",
          }}
        >
          <div style={{ color: ACCENT2, fontSize: 44, fontWeight: 600, fontFamily: SANS }}>
            A real capture — free edition
          </div>
          <div style={{ color: MUTED, fontSize: 30, fontFamily: SANS, marginTop: 6 }}>
            Dagric Looks, three layouts, on a live ISO
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// SCENE 1 — heading
// ────────────────────────────────────────────────────────────────────────────

const Heading: React.FC = () => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 14, 110, 132], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div
        style={{
          position: "absolute",
          top: 52,
          width: "100%",
          textAlign: "center",
          color: INK,
          fontSize: 64,
          fontWeight: 300,
          fontFamily: SANS,
        }}
      >
        {/* site/index.html's own h2 for this section, verbatim. */}
        Pick a desktop. <span style={{ color: ACCENT, fontWeight: 700 }}>Your desktop.</span>
      </div>
    </AbsoluteFill>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// SCENE 2 — the caption column.
//
// NAME and DESCRIPTION are the .look files' own NAME= and DESCRIPTION= values,
// verbatim and lower-case, because that is the text dagric-looks line 76 puts
// on the menu row and po/dagric.pot carries as the msgid in five languages.
// In particular Centered reads "a centered taskbar" (US), which is what the
// dialog prints; the manual's "a centred taskbar" is the drifted copy. And
// Classic reads "a taskbar at the bottom, familiar and comfortable", NOT
// site/index.html:198's "A taskbar at the bottom — familiar from day one",
// which is a sentence the product does not ship.
//
// The PRO chip is a faithful re-render of the " (Pro)" suffix dagric-looks
// line 78 appends to a Pro row's label — not an invention, and not a lock.
// ────────────────────────────────────────────────────────────────────────────

const Caption: React.FC<{ look: Look }> = ({ look }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [16, 30, BEAT - 14, BEAT - 2], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [16, 34], [22, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div
        style={{
          position: "absolute",
          left: 1240,
          width: 630,
          top: 0,
          height: 1080,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          fontFamily: SANS,
          transform: `translateY(${y}px)`,
        }}
      >
        {look.pro ? (
          <div style={{ marginBottom: 18 }}>
            <span
              style={{
                color: ACCENT2,
                fontSize: 36,
                fontWeight: 700,
                letterSpacing: 3,
                border: `1px solid ${ACCENT2}`,
                borderRadius: 999,
                padding: "8px 24px",
              }}
            >
              PRO
            </span>
          </div>
        ) : null}
        <div style={{ color: INK, fontSize: 96, fontWeight: 600, lineHeight: 1.05 }}>
          {look.name}
        </div>
        <div style={{ color: MUTED, fontSize: 48, lineHeight: 1.3, marginTop: 20 }}>
          {look.description}
        </div>
        {/* The only numbers this repository can support. Printed so nobody has
            to measure pixels off the video to find out what the shapes mean —
            and so the identical Command and Unity spec lines are visibly the
            truth rather than a mistake. */}
        <div style={{ color: MUTED, opacity: 0.72, fontSize: 44, lineHeight: 1.3, marginTop: 24 }}>
          {specLine(look)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// SCENE 3 — the edition split, as a shape and then as a sentence.
// ────────────────────────────────────────────────────────────────────────────

const Split: React.FC = () => {
  const frame = useCurrentFrame();
  // [32,50], not [12,32]. These boxes are a top-level overlay drawn at the
  // grid's SETTLED coordinates, while the camera is still springing back out
  // of the Duo close-up when this scene opens. Fading them in at frame 12 drew
  // each frame around where its row was about to be rather than where it was:
  // measured at frame 837 the row-1 tile started at x=178 with its border at
  // x=174, so the designed 18px gutter read as 4px and the box looked like a
  // misdrawn border rather than a bracket. Waiting for the spring to converge
  // costs 20 frames and is the difference between a deliberate diagram and a
  // rendering bug.
  const rowO = interpolate(frame, [32, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const legO = interpolate(frame, [20, 36, 78, 90], [0, 1, 1, 0.25], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rowBox = (i: number, colour: string) => {
    const a = gridRect(i === 0 ? 0 : 3);
    const b = gridRect(i === 0 ? 2 : 6);
    return {
      position: "absolute" as const,
      left: a.x - 18,
      top: a.y - 18,
      width: b.x + b.w - a.x + 36,
      height: a.h + 36,
      border: `1px solid ${colour}`,
      borderRadius: 20,
      background: `${colour}0f`,
      opacity: rowO,
    };
  };
  const Line: React.FC<{ dot: string; text: string }> = ({ dot, text }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 14 }}>
      <div style={{ width: 20, height: 20, borderRadius: 10, background: dot }} />
      <div style={{ color: INK, fontSize: 58, fontFamily: SANS, fontWeight: 400 }}>{text}</div>
    </div>
  );
  return (
    <AbsoluteFill>
      <div style={rowBox(0, ACCENT2)} />
      <div style={rowBox(1, ACCENT)} />
      {/* alignItems flex-start inside a centred wrapper, not two separately
          centred rows: centring each line individually put the two dots 48px
          apart horizontally, so the key column zig-zagged and the pairing
          between a dot and its row frame stopped reading. */}
      <div
        style={{
          position: "absolute",
          top: 828,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          opacity: legO,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
        {/* Both numbers on adjacent lines so nobody has to count tiles.
            site/index.html:308 sells the free tier as "3 layouts", :331 as
            "All 7", the compare table at :379 as "3 · 4 | 7 · 7", and
            pro.html:320 as "3 | 7". Additive phrasing, not "3 of 7": four
            layouts arrive on Pro, none are taken away from free. */}
          <Line dot={ACCENT2} text="Three layouts — free edition" />
          <Line dot={ACCENT} text="Four more on Pro — seven in all" />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// SCENE 4 — close.
// ────────────────────────────────────────────────────────────────────────────

const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const line = (at: number) =>
    interpolate(frame, [at, at + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const out = interpolate(frame, [CLOSE_LEN - 16, CLOSE_LEN], [1, 0.12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: out }}>
      {/* A veil, not a curtain. The stage is already down to 0.22 behind this,
          but a Dagric panel is near-white and four lines of text crossing two
          rows of them read as noise however good the contrast number is. At
          0.55 the tiles drop to a quiet ghost and the 3-over-4 shape is still
          countable — which is the point of leaving them up at all, since the
          split is stated once in words here and once as geometry behind. */}
      <AbsoluteFill style={{ backgroundColor: BG, opacity: 0.55 }} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          fontFamily: SANS,
          textAlign: "center",
        }}
      >
        {/* Free is leaner, never broken. All three free layouts are complete
            desktops — every one has a launcher, a task area, a system tray and
            a clock, which is true of classic.look, focus.look and eleven.look
            and checkable in the table at the top of this file. */}
        <div style={{ color: INK, fontSize: 68, fontWeight: 600, opacity: line(6) }}>
          Three layouts. Every one a full desktop.
        </div>
        <div style={{ color: MUTED, fontSize: 52, marginTop: 18, opacity: line(18) }}>
          Four more on Pro — seven in all.
        </div>
        {/* The honest version of the persistence claim, and the reason this
          video will not repeat site/index.html:192 ("Every layout keeps your
          apps, files, and settings"). It is false: dagric-looks CLEARs every
          panel before rebuilding, and the shipped manual says so plainly —
          "Switching layout removes your panel customisations, because it
          rebuilds the panels ... Your files, settings, wallpaper and colours
          are untouched. Only the panels are rebuilt." The second half is the
          reassurance a switcher actually needs, and it is the half that is
          true, so it is the half that is on screen. */}
        <div style={{ color: MUTED, opacity: line(32) * 0.78, fontSize: 44, marginTop: 40, maxWidth: 1380, lineHeight: 1.35 }}>
          Switching rebuilds the panels. Your files, settings and wallpaper are untouched.
        </div>
        <div style={{ color: ACCENT2, fontSize: 48, marginTop: 42, opacity: line(48) }}>
        {/* site/index.html's own closing sentence for this section — it hands
            off to the Styles half of the page the video sits on, and it
            multiplies the value without making a single new claim. */}
          Mix any Look with any Style.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * The provenance line. Small on purpose and carrying no product fact — it says
 * only where the pictures came from. A tile is shown at 3x during the tour and
 * a viewer is entitled to know whether they are looking at a photograph or a
 * drawing; SCENE 0 is the photograph and everything after it is this.
 *
 * IT IS LOAD-BEARING: if the table at the top of this file ever drifts from
 * config/includes.chroot/usr/share/dagric/looks/, this sentence becomes the
 * defect. Re-check it whenever a .look file changes.
 */
const Provenance: React.FC = () => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [10, 30], [0, 0.55], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 1004,
        color: MUTED,
        opacity: o,
        fontSize: 28,
        fontFamily: SANS,
      }}
    >
      drawn from the shipped .look files
    </div>
  );
};

// ────────────────────────────────────────────────────────────────────────────
// STRUCTURAL DEVIATION, DELIBERATE.
//
// The other three compositions are a flat list of abutting, non-overlapping
// <Sequence>s, each fading itself against BG. That convention exists so cuts
// never gap. This piece has no cuts after SCENE 0 — it is one continuous
// camera move over one persistent stage — so the stage is a single long
// Sequence and the heading, captions, split and close are overlays on top of
// it. Do not "restore" it to a cut list: that destroys the camera move and
// turns the piece into the slideshow it was designed not to be.
//
// Root.tsx's arithmetic rule still holds and still has to be checked: the last
// Sequence is CLOSE at 903 + 117 = 1020, which is DAGRIC_LOOKS_FRAMES.
// ────────────────────────────────────────────────────────────────────────────

export const DagricLooks: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <Sequence from={0} durationInFrames={PLATE_END}>
        <Plate />
      </Sequence>

      <Sequence from={STAGE_FROM} durationInFrames={DAGRIC_LOOKS_FRAMES - STAGE_FROM}>
        <StageFade />
      </Sequence>

      <Sequence from={STAGE_FROM} durationInFrames={BUILD_LEN}>
        <Heading />
      </Sequence>

      {ORDER.map((look, i) => (
        <Sequence key={look.id} from={TOUR_FROM + BEAT * i} durationInFrames={BEAT}>
          <Caption look={look} />
        </Sequence>
      ))}

      <Sequence from={TOUR_END} durationInFrames={SPLIT_LEN}>
        <Split />
      </Sequence>

      <Sequence from={CLOSE_FROM} durationInFrames={CLOSE_LEN}>
        <Close />
      </Sequence>
    </AbsoluteFill>
  );
};

/**
 * The stage plus its own fade envelope and provenance line.
 *
 * The stage dims rather than disappearing under the closing card: the grid is
 * the argument the words are summarising, and the 3-over-4 shape stays
 * countable behind them. It is stated once in 58px type in SCENE 3 and once as
 * geometry here, which is the only form of the split that survives a 320px
 * phone render.
 */
const StageFade: React.FC = () => {
  // Sequence-local here, unlike <Stage>: this envelope is about the stage's
  // own lifetime (fade up on arrival, dim under the closing card), not about
  // the shared timeline.
  const frame = useCurrentFrame();
  const local = CLOSE_FROM - STAGE_FROM;
  const o = interpolate(frame, [0, 16, local, local + 22], [0, 1, 1, 0.22], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <Stage />
      <CaptionScrim />
      <Provenance />
    </AbsoluteFill>
  );
};

/**
 * A soft wipe to BG down the right third, on only while the camera is in a
 * close-up.
 *
 * NOT decoration. The close-up puts a tile at x 80-1200 and the caption column
 * at 1240; the NEXT tile in the row lands at x 1312 and runs off the right of
 * the frame, so without this the layout name is set on top of a dimmed second
 * desktop and the neighbour's wallpaper D sits inches from the word "Classic".
 * Dimming that tile further is not the answer — the dim is a focus device
 * applied by one rule to free and Pro tiles alike, and deepening it for the
 * neighbour only would start to read as a gate.
 *
 * It fades with the first and last camera moves rather than snapping, so the
 * wide grid shots in SCENE 1 and SCENE 3 are never scrimmed — the whole point
 * of those is that all seven tiles are visible at once.
 */
const CaptionScrim: React.FC = () => {
  const frame = useCurrentFrame() + STAGE_FROM;
  const o = interpolate(
    frame,
    [TOUR_FROM, TOUR_FROM + 22, TOUR_END - 10, TOUR_END + 14],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <div
      style={{
        position: "absolute",
        // Starts at the close-up tile's right edge (CU.x + CU.w = 1200) and is
        // fully opaque well before the neighbour tile arrives at 1312. It must
        // not begin one pixel earlier: the previous version started at 1160
        // and laid a 30% veil over the last 40px of the tile, which is where
        // Horizon's and Duo's clocks live — dimming a widget the layout
        // genuinely has, in the name of legibility for the caption beside it.
        left: CU.x + CU.w,
        top: 0,
        width: 1920 - (CU.x + CU.w),
        height: 1080,
        opacity: o,
        background: `linear-gradient(90deg, rgba(10,17,28,0) 0px, rgba(10,17,28,0.97) 90px, ${BG} 140px)`,
      }}
    />
  );
};
