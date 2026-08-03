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
import { BG, PANEL, LINE, INK, MUTED, ACCENT, ACCENT2, GOOD, SANS, Logo, Wordmark } from "./theme";

/**
 * "From USB stick to your desktop" — 1920x1080, ~45s.
 *
 * WHY THIS VIDEO EXISTS. DagricPromo answers "why would I want this" and the
 * vertical short answers "does it run on my machine". Neither answers the
 * question that actually stops the download, which /download states in its own
 * lead: somebody is about to repartition the only computer they own. The fear
 * is not that Linux is bad, it is that the install is a cliff with no bottom
 * visible. So this is the cliff, filmed: seven steps, every one a real capture
 * from a real install in the QEMU harness, in order, with the two reassurances
 * that are actually true said out loud — nothing touches the disk until the
 * Install button, and the installer lists every change before it makes one.
 *
 * EVERY FRAME IS A REAL CAPTURE. No mockups, no recreations, no "artist's
 * impression" of a dialog. If a screen is in this video it is because the
 * harness booted the shipped ISO and took its picture. That is the whole
 * reason it is worth watching, and it is the one rule that must not bend:
 * a single faked frame makes the other six worthless.
 */

const STEPS = 7;

/** The persistent chrome: which step, out of how many, and its name. */
const StepFrame: React.FC<{
  n: number;
  label: string;
  headline: string;
  sub: string;
  src: string;
  children?: React.ReactNode;
}> = ({ n, label, headline, sub, src }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const fade = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const rise = interpolate(frame, [4, 22], [26, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const shotIn = interpolate(frame, [10, 34], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const push = interpolate(frame, [0, durationInFrames], [1.0, 1.045]);

  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      {/* left column: the words */}
      <div
        style={{
          position: "absolute",
          left: 96,
          top: 0,
          bottom: 0,
          width: 560,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          transform: `translateY(${rise}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 26 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: "linear-gradient(135deg,#4fb3e8,#2f7fd1)",
              color: "#04101c",
              fontWeight: 800,
              fontSize: 27,
              fontFamily: SANS,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {n}
          </div>
          <div style={{ color: MUTED, fontSize: 22, fontFamily: SANS, letterSpacing: 3 }}>
            STEP {n} OF {STEPS} &middot; {label.toUpperCase()}
          </div>
        </div>

        <div
          style={{
            color: INK,
            fontSize: 56,
            fontWeight: 700,
            fontFamily: SANS,
            lineHeight: 1.14,
          }}
        >
          {headline}
        </div>
        <div
          style={{
            color: MUTED,
            fontSize: 27,
            fontFamily: SANS,
            lineHeight: 1.5,
            marginTop: 24,
          }}
        >
          {sub}
        </div>

        {/* progress rail */}
        <div style={{ display: "flex", gap: 8, marginTop: 44 }}>
          {Array.from({ length: STEPS }, (_, i) => (
            <div
              key={i}
              style={{
                height: 5,
                flex: 1,
                borderRadius: 3,
                background: i < n ? ACCENT : LINE,
                opacity: i < n ? 1 : 0.7,
              }}
            />
          ))}
        </div>
      </div>

      {/* right column: the capture */}
      <div
        style={{
          position: "absolute",
          right: 84,
          top: "50%",
          width: 1090,
          transform: `translateY(-50%) scale(${push})`,
          opacity: shotIn,
          borderRadius: 16,
          overflow: "hidden",
          border: `1px solid ${LINE}`,
          boxShadow: "0 40px 120px rgba(0,0,0,.65)",
        }}
      >
        <Img src={staticFile(src)} style={{ width: "100%", display: "block" }} />
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

const Title: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  const l1 = interpolate(frame, [14, 32], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const l2 = interpolate(frame, [28, 46], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const out = interpolate(frame, [72, 90], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        opacity: out,
      }}
    >
      <div style={{ transform: `scale(${interpolate(pop, [0, 1], [0.72, 1])})` }}>
        <Logo size={120} />
      </div>
      <div
        style={{
          color: INK,
          fontSize: 74,
          fontWeight: 700,
          fontFamily: SANS,
          marginTop: 40,
          opacity: l1,
          transform: `translateY(${(1 - l1) * 22}px)`,
        }}
      >
        From a USB stick to your desktop.
      </div>
      <div
        style={{
          color: ACCENT2,
          fontSize: 34,
          fontFamily: SANS,
          marginTop: 20,
          opacity: l2,
        }}
      >
        Seven steps, about twenty minutes &mdash; every screen here is a real capture.
      </div>
    </AbsoluteFill>
  );
};

/**
 * The one claim in this video worth its own scene, because it is the one that
 * removes the fear rather than describing it. Both halves are literally true
 * and both are visible in step 5's capture: Calamares shows the full change
 * list under "This is an overview of what will happen once you start the
 * install procedure", and until Install is pressed the machine is running
 * entirely from the USB.
 */
const NothingYet: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const fade = interpolate(
    frame,
    [0, 16, durationInFrames - 16, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const lines = [
    "Your disk is untouched until you press Install.",
    "Every change is listed before it is made.",
    "Don't like it? Pull the stick out and reboot.",
  ];
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
          fontSize: 60,
          fontWeight: 300,
          fontFamily: SANS,
          textAlign: "center",
          maxWidth: 1300,
          lineHeight: 1.25,
        }}
      >
        The whole thing is <span style={{ color: ACCENT, fontWeight: 800 }}>reversible</span> right
        up to the last click.
      </div>
      <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 20 }}>
        {lines.map((t, i) => {
          const a = interpolate(frame, [22 + i * 12, 40 + i * 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={t}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                background: PANEL,
                border: `1px solid ${LINE}`,
                borderRadius: 16,
                padding: "20px 34px",
                opacity: a,
                transform: `translateX(${(1 - a) * -26}px)`,
                minWidth: 900,
              }}
            >
              <div style={{ color: GOOD, fontSize: 34, fontFamily: SANS, lineHeight: 1 }}>&#10003;</div>
              <div style={{ color: MUTED, fontSize: 32, fontFamily: SANS }}>{t}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  const fade = interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp" });
  const sub = interpolate(frame, [22, 40], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill
      style={{ backgroundColor: BG, justifyContent: "center", alignItems: "center", opacity: fade }}
    >
      <div style={{ transform: `scale(${interpolate(pop, [0, 1], [0.72, 1])})` }}>
        <Logo size={140} />
      </div>
      <div style={{ marginTop: 34 }}>
        <Wordmark size={70} />
      </div>
      <div
        style={{
          color: ACCENT2,
          fontSize: 40,
          fontFamily: SANS,
          fontWeight: 700,
          marginTop: 26,
          opacity: sub,
        }}
      >
        dagric.com/guide
      </div>
      <div style={{ color: MUTED, fontSize: 25, fontFamily: SANS, marginTop: 14, opacity: sub }}>
        The step-by-step written version, in six languages &mdash; and it ships inside the OS.
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

export const InstallWalkthrough: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: BG }}>
    <Sequence durationInFrames={92}>
      <Title />
    </Sequence>

    <Sequence from={92} durationInFrames={150}>
      <StepFrame
        n={1}
        label="Check"
        headline="Ask the USB before you commit"
        sub="Check This PC reads your actual hardware and writes it out in plain English — what works, what needs a cable, what to change in the firmware first."
        src="dagric-hardware-check.png"
      />
    </Sequence>

    <Sequence from={242} durationInFrames={150}>
      <StepFrame
        n={2}
        label="Try"
        headline="Use the whole thing before installing it"
        sub="This is not a demo mode. It is the finished desktop running from the stick — browse the web, open your files, print something."
        src="dagric-desktop-live.png"
      />
    </Sequence>

    <Sequence from={392} durationInFrames={150}>
      <StepFrame
        n={3}
        label="Start"
        headline="Seven steps, named up front"
        sub="Welcome, Location, Keyboard, Partitions, Users, Summary, Install. You can see the whole path from the first screen."
        src="dagric-installer-welcome.png"
      />
    </Sequence>

    <Sequence from={542} durationInFrames={160}>
      <StepFrame
        n={4}
        label="Disk"
        headline="Encryption is a checkbox. Rollback is the default."
        sub="Btrfs is already selected, so a bad update is a snapshot away from undone. Tick Encrypt system and the disk is useless to anyone who steals the laptop."
        src="dagric-installer-partitions.png"
      />
    </Sequence>

    <Sequence from={702} durationInFrames={160}>
      <StepFrame
        n={5}
        label="Review"
        headline="Nothing has happened yet"
        sub="Every partition, every flag, every mount point — listed before a single byte is written. This is the last screen where Cancel still costs you nothing."
        src="dagric-installer-summary.png"
      />
    </Sequence>

    <Sequence from={862} durationInFrames={140}>
      <NothingYet />
    </Sequence>

    <Sequence from={1002} durationInFrames={150}>
      <StepFrame
        n={6}
        label="First boot"
        headline="It sets itself up with you"
        sub="One short wizard on the first start: your look, your text size, your apps. Skip it and nothing breaks — it is in the Hub whenever you want it."
        src="dagric-firstrun.png"
      />
    </Sequence>

    <Sequence from={1152} durationInFrames={150}>
      <StepFrame
        n={7}
        label="Done"
        headline="Your computer, back"
        sub="No account to make. No telemetry to switch off. Updates install themselves and never reboot you mid-sentence."
        src="dagric-uefi-installed-desktop.png"
      />
    </Sequence>

    <Sequence from={1302} durationInFrames={120}>
      <End />
    </Sequence>
  </AbsoluteFill>
);
