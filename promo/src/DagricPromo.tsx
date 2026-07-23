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

const BG = "#0b1118";
const INK = "#e6edf3";
const MUTED = "#8595a6";
const ACCENT = "#4fb3e8";
const ACCENT2 = "#7be0c8";
const SANS = "system-ui, 'Segoe UI', sans-serif";

// The D monogram, drawn inline so the video needs no external logo asset.
const Logo: React.FC<{ size: number }> = ({ size }) => (
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

// A screenshot shot with a slow Ken Burns push and a caption card.
const Shot: React.FC<{ src: string; title: string; sub: string }> = ({
  src,
  title,
  sub,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1.08, 1.16]);
  const fade = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0]
  );
  const capY = interpolate(frame, [8, 26], [40, 0], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: 90,
        }}
      >
        <Img
          src={staticFile(src)}
          style={{
            width: "100%",
            maxHeight: "82%",
            objectFit: "contain",
            borderRadius: 14,
            transform: `scale(${scale})`,
            boxShadow: "0 30px 90px rgba(0,0,0,0.6)",
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          padding: "0 90px 70px",
          transform: `translateY(${capY}px)`,
        }}
      >
        <div
          style={{
            background: "rgba(11,17,24,0.72)",
            border: "1px solid #223140",
            borderRadius: 14,
            padding: "20px 28px",
            width: "fit-content",
            backdropFilter: "blur(6px)",
          }}
        >
          <div style={{ color: ACCENT2, fontSize: 26, fontWeight: 600, fontFamily: SANS }}>
            {title}
          </div>
          <div style={{ color: MUTED, fontSize: 22, marginTop: 4, fontFamily: SANS }}>
            {sub}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  const logoScale = interpolate(pop, [0, 1], [0.6, 1]);
  const word = interpolate(frame, [18, 40], [0, 1], { extrapolateRight: "clamp" });
  const tag = interpolate(frame, [34, 54], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [95, 120], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeOut,
      }}
    >
      <div style={{ transform: `scale(${logoScale})` }}>
        <Logo size={200} />
      </div>
      <div
        style={{
          color: INK,
          fontSize: 92,
          fontWeight: 200,
          letterSpacing: 26,
          marginTop: 40,
          paddingLeft: 26,
          fontFamily: SANS,
          opacity: word,
        }}
      >
        DAG<span style={{ fontWeight: 750, color: ACCENT }}>RIC</span>
      </div>
      <div
        style={{
          color: MUTED,
          fontSize: 26,
          letterSpacing: 14,
          marginTop: 10,
          paddingLeft: 14,
          fontFamily: SANS,
          opacity: tag,
        }}
      >
        OWN IT OUTRIGHT
      </div>
    </AbsoluteFill>
  );
};

const Thesis: React.FC = () => {
  const frame = useCurrentFrame();
  const items = [
    "No telemetry",
    "No ads",
    "No accounts",
    "No bloat",
  ];
  const fade = interpolate(frame, [0, 14, 110, 128], [0, 1, 1, 0]);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        opacity: fade,
      }}
    >
      <div
        style={{
          color: INK,
          fontSize: 54,
          fontWeight: 300,
          fontFamily: SANS,
          textAlign: "center",
          maxWidth: 1200,
          lineHeight: 1.3,
        }}
      >
        The desktop that works for{" "}
        <span style={{ color: ACCENT, fontWeight: 700 }}>you</span> — and no one else.
      </div>
      <div style={{ display: "flex", gap: 22, marginTop: 60 }}>
        {items.map((t, i) => {
          const a = interpolate(frame, [20 + i * 8, 36 + i * 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={t}
              style={{
                color: ACCENT2,
                fontSize: 30,
                fontFamily: SANS,
                border: "1px solid #223140",
                borderRadius: 999,
                padding: "12px 28px",
                background: "#121b26",
                opacity: a,
                transform: `translateY(${(1 - a) * 20}px)`,
              }}
            >
              {t}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Editions: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 14, 130, 150], [0, 1, 1, 0]);
  const Card: React.FC<{ x: number; title: string; lines: string[]; accent: string }> = ({
    x,
    title,
    lines,
    accent,
  }) => {
    const a = interpolate(frame, [10 + x, 30 + x], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <div
        style={{
          width: 520,
          background: "#121b26",
          border: `1px solid #223140`,
          borderTop: `3px solid ${accent}`,
          borderRadius: 16,
          padding: "36px 40px",
          opacity: a,
          transform: `translateY(${(1 - a) * 30}px)`,
        }}
      >
        <div style={{ color: accent, fontSize: 40, fontWeight: 700, fontFamily: SANS }}>
          {title}
        </div>
        {lines.map((l) => (
          <div
            key={l}
            style={{ color: MUTED, fontSize: 26, marginTop: 16, fontFamily: SANS }}
          >
            {l}
          </div>
        ))}
      </div>
    );
  };
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        opacity: fade,
      }}
    >
      <div style={{ color: INK, fontSize: 44, fontFamily: SANS, marginBottom: 44, fontWeight: 300 }}>
        Two editions
      </div>
      <div style={{ display: "flex", gap: 40 }}>
        <Card x={0} title="Dagric OS" accent={ACCENT} lines={["The full private OS", "Free, forever", "No account, no strings"]} />
        <Card x={12} title="Dagric Pro — $39" accent={ACCENT2} lines={["Creator + dev suite", "Windows apps: Bottles + Wine", "Gaming: Steam, Proton, Heroic", "Own it outright — one purchase"]} />
      </div>
    </AbsoluteFill>
  );
};

// Animated "Dagric Looks" — a mini desktop whose panels MORPH between the
// four real layouts (Classic, Focus, Horizon, Command). Motion sells the
// feature better than any still could.
const Looks: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 14, 442, 460], [0, 1, 1, 0]);
  // Screen geometry (the mini desktop)
  const SW = 1400, SH = 745, PX = (1920 - SW) / 2, PY = 150;
  // SLOW pacing: each layout HOLDS ~2.7s, then a quick 25-frame morph.
  // Hold windows: Classic 0-105, Focus 130-210, Horizon 235-315, Command 340-460.
  const K = [0, 105, 130, 210, 235, 315, 340];
  const lerp = (v: [number, number, number, number]) =>
    interpolate(frame, K, [v[0], v[0], v[1], v[1], v[2], v[2], v[3]], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
  // Panel A (the main bar): bottom full -> bottom slim -> top bar -> left dock
  const aX = lerp([0, 0, 0, 0]);
  const aY = lerp([SH - 64, SH - 48, 0, 0]);
  const aW = lerp([SW, SW, SW, 84]);
  const aH = lerp([64, 48, 44, SH]);
  // Panel B (the dock): hidden -> hidden -> floating bottom dock -> hidden
  const bO = lerp([0, 0, 1, 0]);
  const bW = 520;
  // One label per layout, visible through its whole hold window.
  const labels: Array<{ t: string; d: string; w: [number, number] }> = [
    { t: "Classic",       d: "A taskbar at the bottom — familiar from day one", w: [0, 105] },
    { t: "Focus",         d: "One tidy bar, nothing in your way",               w: [130, 210] },
    { t: "Horizon · Pro", d: "A menu bar up top with a dock below",             w: [235, 315] },
    { t: "Command · Pro", d: "A side dock for living in your apps",             w: [340, 460] },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <div style={{ position: "absolute", top: 56, width: "100%", textAlign: "center", color: INK, fontSize: 46, fontWeight: 300, fontFamily: SANS }}>
        Pick a desktop. <span style={{ color: ACCENT, fontWeight: 700 }}>Your desktop.</span>
      </div>
      {/* the mini screen */}
      <div style={{ position: "absolute", left: PX, top: PY, width: SW, height: SH, borderRadius: 22, overflow: "hidden", border: "1px solid #223140", boxShadow: "0 40px 120px rgba(0,0,0,.6)", background: "linear-gradient(135deg,#101b2c,#0a1420)" }}>
        {/* wallpaper mark */}
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
          <div style={{ fontSize: 120, fontWeight: 800, fontFamily: SANS, background: "linear-gradient(135deg,#59c2e8,#2f7fd1)", WebkitBackgroundClip: "text", color: "transparent" }}>D</div>
          <div style={{ width: 110, height: 6, borderRadius: 3, background: ACCENT, opacity: 0.55 }} />
        </div>
        {/* Panel A */}
        <div style={{ position: "absolute", left: aX, top: aY, width: aW, height: aH, background: "#eef1f4", display: "flex", alignItems: "center", padding: 10, gap: 10, flexDirection: aW < 200 ? "column" : "row" }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: "linear-gradient(135deg,#59c2e8,#2f7fd1)", color: "#fff", fontWeight: 800, fontFamily: SANS, fontSize: 20, display: "flex", alignItems: "center", justifyContent: "center", flex: "0 0 auto" }}>D</div>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ width: 34, height: 34, borderRadius: 9, background: "#c9d3dc", flex: "0 0 auto" }} />
          ))}
        </div>
        {/* Panel B (floating dock for Horizon) */}
        <div style={{ position: "absolute", left: (SW - bW) / 2, top: SH - 76, width: bW, height: 58, borderRadius: 18, background: "#eef1f4", opacity: bO, display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} style={{ width: 36, height: 36, borderRadius: 10, background: i === 0 ? "linear-gradient(135deg,#59c2e8,#2f7fd1)" : "#c9d3dc" }} />
          ))}
        </div>
      </div>
      {/* layout labels — each persists through its whole hold window */}
      {labels.map((l) => {
        const o = interpolate(
          frame,
          [l.w[0], l.w[0] + 10, l.w[1] - 10, l.w[1]],
          [0, 1, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        return (
          <div key={l.t} style={{ position: "absolute", bottom: 46, width: "100%", textAlign: "center", opacity: o }}>
            <div>
              <span style={{ color: ACCENT2, fontSize: 40, fontWeight: 700, fontFamily: SANS, border: "1px solid #223140", background: "#121b26", borderRadius: 999, padding: "12px 40px" }}>
                {l.t}
              </span>
            </div>
            <div style={{ color: MUTED, fontSize: 26, fontFamily: SANS, marginTop: 16 }}>{l.d}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  const fade = interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        opacity: fade,
      }}
    >
      <div style={{ transform: `scale(${interpolate(pop, [0, 1], [0.7, 1])})` }}>
        <Logo size={150} />
      </div>
      <div style={{ color: INK, fontSize: 70, fontFamily: SANS, fontWeight: 300, letterSpacing: 18, marginTop: 34, paddingLeft: 18 }}>
        DAG<span style={{ fontWeight: 750, color: ACCENT }}>RIC</span>
      </div>
      <div style={{ color: ACCENT2, fontSize: 40, fontFamily: SANS, marginTop: 20 }}>
        dagric.com
      </div>
      <div style={{ color: MUTED, fontSize: 24, fontFamily: SANS, marginTop: 14 }}>
        Own it outright.
      </div>
    </AbsoluteFill>
  );
};

export const DagricPromo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <Sequence durationInFrames={120}>
        <Intro />
      </Sequence>
      <Sequence from={120} durationInFrames={130}>
        <Thesis />
      </Sequence>
      <Sequence from={250} durationInFrames={150}>
        <Shot src="dagric-hero-desktop.png" title="Your desktop, calm and yours" sub="The Dagric look — no ads, no noise, no telemetry" />
      </Sequence>
      <Sequence from={400} durationInFrames={150}>
        <Shot src="dagric-welcome-live2.png" title="Feels like home" sub="A warm welcome, an offline guide, familiar layout" />
      </Sequence>
      <Sequence from={550} durationInFrames={460}>
        <Looks />
      </Sequence>
      <Sequence from={1010} durationInFrames={150}>
        <Shot src="dagric-uefi-installed-desktop.png" title="Installed and yours" sub="KDE Plasma desktop — clean, fast, private" />
      </Sequence>
      <Sequence from={1160} durationInFrames={150}>
        <Shot src="dagric-uefi-install-done.png" title="Modern-PC ready" sub="UEFI + Secure Boot install, verified end to end" />
      </Sequence>
      <Sequence from={1310} durationInFrames={160}>
        <Editions />
      </Sequence>
      <Sequence from={1470} durationInFrames={130}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
