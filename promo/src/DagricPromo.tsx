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
        <Card x={12} title="Dagric Pro" accent={ACCENT2} lines={["Creator + dev suite", "Gaming: Wine, Steam, Proton", "Backup, phone sync, more"]} />
      </div>
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
        <Shot src="dagric-bootmenu.png" title="Boots in seconds" sub="Branded from the very first screen" />
      </Sequence>
      <Sequence from={400} durationInFrames={150}>
        <Shot src="dagric-welcome-live.png" title="Feels like home" sub="A warm welcome, an offline guide, familiar layout" />
      </Sequence>
      <Sequence from={550} durationInFrames={150}>
        <Shot src="dagric-uefi-installed-desktop.png" title="Installed and yours" sub="KDE Plasma desktop — clean, fast, private" />
      </Sequence>
      <Sequence from={700} durationInFrames={150}>
        <Shot src="dagric-uefi-install-done.png" title="Modern-PC ready" sub="UEFI + Secure Boot install, verified end to end" />
      </Sequence>
      <Sequence from={850} durationInFrames={160}>
        <Editions />
      </Sequence>
      <Sequence from={1010} durationInFrames={130}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
