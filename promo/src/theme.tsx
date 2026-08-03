import React from "react";
import { AbsoluteFill, Img, staticFile, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// The one place the brand lives. Every value below is lifted from
// site/assets/site.css so the video and the website are the same product:
// --bg #0a111c, --text #e8eef6, --muted #a6bad0, --accent #3fa9f5,
// --accent2 #59c2e8, --good #4ade80. They were hand-copied into
// DagricPromo.tsx as slightly different hexes (#0b1118, #4fb3e8, #7be0c8),
// which is how a brand drifts: nobody decides to change it, the second file
// just never gets updated. Video colours are nudged a shade brighter than the
// CSS because a 1080p H.264 render on a phone loses contrast that a monitor
// keeps — that is a deliberate exception, recorded here rather than rediscovered.
export const BG = "#0a111c";
export const BG2 = "#0e1725";
export const PANEL = "#131f31";
export const LINE = "#22344f";
export const INK = "#e8eef6";
export const MUTED = "#a6bad0";
export const ACCENT = "#4fb3e8";
export const ACCENT2 = "#7be0c8";
export const GOOD = "#4ade80";
export const WARN = "#f0a04b";
export const SANS = "system-ui, 'Segoe UI', Roboto, sans-serif";

/**
 * The DIAGRAM palette: the colours a drawn Dagric desktop is made of, as
 * opposed to the colours the video's own chrome is made of.
 *
 * These live here for the same reason the brand colours do. They were already
 * hardcoded in three places before this file existed — site/assets/look-*.svg,
 * tools/make-appearance-thumbs.sh, and again inline in DagricPromo.tsx's Looks
 * component — and the three sets have already drifted apart. Every value below
 * names the shipped file it was read out of, so the next person can check it
 * instead of copying the nearest neighbour.
 */
export const DIAGRAM = {
  // config/includes.chroot/usr/share/color-schemes/DagricLight.colors,
  // [Colors:Window] BackgroundNormal=239,240,241. Daybreak is the default
  // style (SORT=10, SCHEME=DagricLight), so this is the panel colour a new
  // owner actually gets. The site SVGs all paint panels #eef1f4, which is a
  // near-miss nobody chose — copied once, then copied six more times.
  panel: "#eff0f1",
  panelInk: "#31363b", // the clock face, as every look-*.svg sets it
  tile: "#c9d3dc", // application icons
  tile2: "#dde3e9", // task buttons and secondary menu entries
  tray: "#8794a1", // system-tray dots
  pager: "#94a3b1", // pager cells: dimmer than an app icon, which is the point
  // The kickoff button, re-branded by every one of the seven .look scripts
  // with writeConfig("icon","dagric-logo"). Gradient sampled from the shipped
  // usr/share/dagric/logo/dagric-logo.png.
  dFrom: "#59c2e8",
  dTo: "#2f7fd1",
  // branding/wallpaper/make-wallpapers.sh line 241:
  //   Dagric)  classic 0d1728 060b14 40b0ff 0.962
  // i.e. a vertical gradient 0d1728 -> 060b14, with the bloom AND the three
  // sweeps both drawn in 40b0ff (classic() passes $3 to sweeps()). The site
  // SVGs stroke their waves #3fa9f5 instead, which is the site's accent, not
  // the wallpaper's.
  wallTop: "#0d1728",
  wallBottom: "#060b14",
  wallBloom: "#40b0ff",
} as const;

// NO WEBFONT, deliberately. Remotion would need the font loaded before the
// first frame renders or the whole video ships in a fallback face, and a
// missing @remotion/google-fonts call fails silently — it looks like a design
// choice rather than a bug. system-ui is what the website falls back to
// anyway, so the two match on any machine that renders both.

/** The D monogram, drawn inline so the video needs no external logo asset. */
export const Logo: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 256 256">
    <defs>
      <radialGradient id="lbg" cx="30%" cy="20%" r="120%">
        <stop offset="0%" stopColor="#16212e" />
        <stop offset="100%" stopColor="#080d13" />
      </radialGradient>
      <linearGradient id="lac" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor={ACCENT} />
        <stop offset="100%" stopColor={ACCENT2} />
      </linearGradient>
    </defs>
    <rect width="256" height="256" rx="52" fill="url(#lbg)" />
    <path
      fill="url(#lac)"
      fillRule="evenodd"
      d="M 84 64 h 44 a 64 64 0 0 1 0 128 h -44 z M 108 88 v 80 h 18 a 40 40 0 0 0 0 -80 z"
    />
    <rect x="70" y="204" width="116" height="8" rx="4" fill={ACCENT} opacity="0.55" />
  </svg>
);

/** DAGRIC, set the way the site sets it. */
export const Wordmark: React.FC<{ size: number; opacity?: number }> = ({ size, opacity = 1 }) => (
  <div
    style={{
      color: INK,
      fontSize: size,
      fontWeight: 200,
      letterSpacing: size * 0.28,
      // letterSpacing adds a trailing gap after the final C, so centred text
      // sits half a space to the left. Pad it back.
      paddingLeft: size * 0.28,
      fontFamily: SANS,
      opacity,
      whiteSpace: "nowrap",
    }}
  >
    DAG<span style={{ fontWeight: 750, color: ACCENT }}>RIC</span>
  </div>
);

/**
 * A screenshot with a slow Ken Burns push and a caption card.
 *
 * `fit` matters and is not cosmetic. Every real capture is 1280x800 (the QEMU
 * harness resolution) — 16:10 — and both video formats are not: 1920x1080 is
 * 16:9 and the vertical short is 9:16. objectFit "cover" on the vertical would
 * crop 60% of the WIDTH off a desktop screenshot, taking the taskbar and the
 * window chrome with it, which is most of what the picture is for. So shots are
 * always "contain", and the vertical composition frames them in a card instead
 * of trying to fill the screen with them.
 */
export const Shot: React.FC<{
  src: string;
  title: string;
  sub: string;
  vertical?: boolean;
}> = ({ src, title, sub, vertical = false }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1.04, 1.12]);
  const fade = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0]
  );
  const capY = interpolate(frame, [8, 26], [40, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: vertical ? "0 40px" : 90,
        }}
      >
        <Img
          src={staticFile(src)}
          style={{
            width: "100%",
            maxHeight: vertical ? "52%" : "82%",
            objectFit: "contain",
            borderRadius: 14,
            transform: `scale(${scale})`,
            boxShadow: "0 30px 90px rgba(0,0,0,0.6)",
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          justifyContent: vertical ? "center" : "flex-end",
          alignItems: vertical ? "center" : "flex-start",
          padding: vertical ? "0 40px" : "0 90px 70px",
          transform: `translateY(${vertical ? capY + 330 : capY}px)`,
        }}
      >
        <div
          style={{
            background: "rgba(10,17,28,0.72)",
            border: `1px solid ${LINE}`,
            borderRadius: 14,
            padding: vertical ? "24px 30px" : "20px 28px",
            width: "fit-content",
            maxWidth: "100%",
            backdropFilter: "blur(6px)",
            textAlign: vertical ? "center" : "left",
          }}
        >
          <div
            style={{
              color: ACCENT2,
              fontSize: vertical ? 42 : 26,
              fontWeight: 600,
              fontFamily: SANS,
              lineHeight: 1.2,
            }}
          >
            {title}
          </div>
          <div
            style={{
              color: MUTED,
              fontSize: vertical ? 32 : 22,
              marginTop: vertical ? 12 : 4,
              fontFamily: SANS,
              lineHeight: 1.35,
            }}
          >
            {sub}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Fade a sequence in and out by frame, the pattern every scene here uses. */
export const useSceneFade = (holdOutAt: number, len = 16) => {
  const frame = useCurrentFrame();
  return interpolate(
    frame,
    [0, len, holdOutAt, holdOutAt + len],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};
