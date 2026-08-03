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
 * The vertical cut — 1080x1920, 24 seconds, for TikTok / Reels / Shorts.
 *
 * WHY A SEPARATE COMPOSITION AND NOT A CROP. DagricPromo is 1920x1080 and 53
 * seconds. Letterboxing it into a 9:16 frame wastes 70% of the screen; centre-
 * cropping it cuts the taskbar out of every screenshot, which is the one thing
 * a Windows switcher is looking for. Neither is a video anybody watches. The
 * shape changes what the video can be, so the video is written for the shape.
 *
 * THE FIRST TWO SECONDS ARE THE WHOLE THING. On a feed, everything after the
 * third second is watched by people the first three seconds already convinced.
 * So the hook is the buying trigger stated flat — Windows 10 stopped getting
 * security updates — and not the logo. The logo is at the END, where a viewer
 * who stayed will actually read it.
 *
 * SAFE AREA. TikTok puts the caption and the button stack over the bottom ~20%
 * and the account row over the top ~12%. Nothing that has to be read lives
 * outside 230..1540, which is why this file has margins that look excessive in
 * the preview and are correct in the app.
 */

const SAFE_TOP = 250;
const SAFE_BOTTOM = 1560;

// ─────────────────────────────────────────────────────────────────────────────

const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const l1 = interpolate(frame, [2, 16], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const l2 = interpolate(frame, [22, 38], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const rule = interpolate(frame, [16, 30], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const out = interpolate(frame, [62, 78], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        padding: "0 70px",
        opacity: out,
      }}
    >
      <div
        style={{
          color: MUTED,
          fontSize: 84,
          fontWeight: 300,
          fontFamily: SANS,
          textAlign: "center",
          lineHeight: 1.15,
          opacity: l1,
          transform: `translateY(${(1 - l1) * 26}px)`,
        }}
      >
        Windows&nbsp;10 stopped getting security updates.
      </div>
      <div
        style={{
          width: 220,
          height: 4,
          borderRadius: 2,
          background: ACCENT,
          margin: "56px 0",
          transform: `scaleX(${rule})`,
        }}
      />
      <div
        style={{
          color: INK,
          fontSize: 110,
          fontWeight: 800,
          fontFamily: SANS,
          textAlign: "center",
          lineHeight: 1.1,
          opacity: l2,
          transform: `translateY(${(1 - l2) * 26}px)`,
        }}
      >
        Your PC <span style={{ color: ACCENT }}>didn&rsquo;t.</span>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

/**
 * A rectangle of the source capture, in fractions of its width and height.
 * Every capture is 1280x800 from the QEMU harness.
 */
type Crop = { x0: number; y0: number; x1: number; y1: number };

/**
 * WHY CROPPING IS NOT OPTIONAL HERE. A 1280x800 desktop shown whole across a
 * 1080-wide vertical frame renders its UI text at about 11 effective pixels —
 * on a phone, held at arm's length, in a feed. The first version of this file
 * did exactly that for Dagric Hardware Check, whose entire claim is "it tells
 * you in plain English what it found", illustrated by four lines of English
 * nobody can read. The picture contradicted the caption.
 *
 * So text-heavy captures are cropped to the part that carries the argument and
 * layout captures are shown whole, because for those the SHAPE is the message
 * (a start menu is recognised before it is read). Cropping is not faking: the
 * uncut frames are all in InstallWalkthrough, which is 16:9 and has the room.
 *
 * The geometry is exact rather than a transform-origin guess. With the source
 * at a fixed 1280x800 the rendered image height is always renderedWidth *
 * 0.625, so a percentage `top` — which resolves against the container height —
 * lands where the arithmetic says it does at any output size.
 */
const CropBox: React.FC<{ src: string; crop?: Crop; scale: number }> = ({ src, crop, scale }) => {
  if (!crop) {
    return (
      <div
        style={{
          width: "100%",
          borderRadius: 20,
          overflow: "hidden",
          border: `1px solid ${LINE}`,
          boxShadow: "0 40px 110px rgba(0,0,0,.65)",
          transform: `scale(${scale})`,
        }}
      >
        <Img src={staticFile(src)} style={{ width: "100%", display: "block" }} />
      </div>
    );
  }
  const cw = crop.x1 - crop.x0;
  const ch = crop.y1 - crop.y0;
  return (
    <div
      style={{
        width: "100%",
        // The container takes the crop's aspect ratio so the image fills it
        // exactly with nothing letterboxed and nothing cut beyond the crop.
        aspectRatio: `${cw * 1280} / ${ch * 800}`,
        position: "relative",
        borderRadius: 20,
        overflow: "hidden",
        border: `1px solid ${LINE}`,
        boxShadow: "0 40px 110px rgba(0,0,0,.65)",
        transform: `scale(${scale})`,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          position: "absolute",
          width: `${100 / cw}%`,
          left: `${(-crop.x0 * 100) / cw}%`,
          top: `${(-crop.y0 * 100) / ch}%`,
          display: "block",
        }}
      />
    </div>
  );
};

/**
 * A screenshot framed for a tall screen: the capture sits in the middle third,
 * with the line above it and the detail below. "contain", never "cover" — see
 * the note on Shot in theme.tsx.
 */
const VShot: React.FC<{
  src: string;
  kicker: string;
  line: string;
  sub: string;
  crop?: Crop;
}> = ({ src, kicker, line, sub, crop }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const fade = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const rise = interpolate(frame, [6, 24], [34, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.06]);
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <div
        style={{
          position: "absolute",
          top: SAFE_TOP,
          left: 60,
          right: 60,
          textAlign: "center",
          transform: `translateY(${rise}px)`,
        }}
      >
        <div
          style={{
            color: ACCENT2,
            fontSize: 34,
            fontWeight: 700,
            letterSpacing: 6,
            textTransform: "uppercase",
            fontFamily: SANS,
          }}
        >
          {kicker}
        </div>
        <div
          style={{
            color: INK,
            fontSize: 74,
            fontWeight: 700,
            fontFamily: SANS,
            lineHeight: 1.14,
            marginTop: 18,
          }}
        >
          {line}
        </div>
      </div>

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 46px" }}>
        <CropBox src={src} crop={crop} scale={scale} />
      </AbsoluteFill>

      <div
        style={{
          position: "absolute",
          top: SAFE_BOTTOM - 150,
          left: 70,
          right: 70,
          textAlign: "center",
          color: MUTED,
          fontSize: 40,
          fontFamily: SANS,
          lineHeight: 1.35,
          transform: `translateY(${-rise}px)`,
        }}
      >
        {sub}
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

/**
 * The price card. Both editions, because the free one is the offer and the
 * paid one is the business — a short that shows only the $39 reads as an ad,
 * and a short that shows only the free one never sells anything.
 *
 * Every figure here is the website's, verbatim: /download says "Free forever ·
 * 2.0 GB ISO" and "$39 one-time · 3.7 GB ISO", and the refund line is "14-day,
 * no-questions refund". If those change, they change here in the same commit —
 * a video is the hardest place on earth to fix a stale number, because it is
 * already on somebody's feed.
 */
const Price: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const fade = interpolate(
    frame,
    [0, 14, durationInFrames - 14, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const Row: React.FC<{ delay: number; name: string; price: string; note: string; hi?: boolean }> = ({
    delay,
    name,
    price,
    note,
    hi,
  }) => {
    const a = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 24 });
    return (
      <div
        style={{
          width: "100%",
          background: PANEL,
          border: `1px solid ${hi ? "rgba(79,179,232,.55)" : LINE}`,
          borderRadius: 26,
          padding: "40px 44px",
          marginBottom: 30,
          opacity: a,
          transform: `translateY(${(1 - a) * 40}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 20 }}>
          <div style={{ color: INK, fontSize: 60, fontWeight: 800, fontFamily: SANS }}>{name}</div>
          <div
            style={{
              color: hi ? ACCENT : GOOD,
              fontSize: 56,
              fontWeight: 800,
              fontFamily: SANS,
              whiteSpace: "nowrap",
            }}
          >
            {price}
          </div>
        </div>
        <div style={{ color: MUTED, fontSize: 36, fontFamily: SANS, marginTop: 14, lineHeight: 1.35 }}>
          {note}
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity: fade }}>
      <div
        style={{
          position: "absolute",
          top: SAFE_TOP + 40,
          left: 70,
          right: 70,
          textAlign: "center",
          color: INK,
          fontSize: 76,
          fontWeight: 300,
          fontFamily: SANS,
          lineHeight: 1.15,
        }}
      >
        Two editions.
        <br />
        <span style={{ fontWeight: 800, color: ACCENT }}>No subscription.</span>
      </div>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 70px" }}>
        <div style={{ width: "100%" }}>
          <Row delay={10} name="Dagric OS" price="Free" note="2.0 GB · the whole private desktop, forever" />
          <Row
            delay={22}
            hi
            name="Dagric Pro"
            price="$39"
            note="3.7 GB · creative, gaming, dev and Windows apps — one purchase, 14-day refund"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

const Sign: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  const fade = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const url = interpolate(frame, [18, 34], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill
      style={{ backgroundColor: BG, justifyContent: "center", alignItems: "center", opacity: fade }}
    >
      <div style={{ transform: `scale(${interpolate(pop, [0, 1], [0.7, 1])})` }}>
        <Logo size={220} />
      </div>
      <div style={{ marginTop: 50 }}>
        <Wordmark size={92} />
      </div>
      <div
        style={{
          color: ACCENT2,
          fontSize: 58,
          fontFamily: SANS,
          fontWeight: 700,
          marginTop: 34,
          opacity: url,
        }}
      >
        dagric.com
      </div>
      <div
        style={{
          color: MUTED,
          fontSize: 36,
          fontFamily: SANS,
          marginTop: 18,
          opacity: url,
        }}
      >
        Own it outright.
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

export const DagricShort: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: BG }}>
    <Sequence durationInFrames={80}>
      <Hook />
    </Sequence>

    {/* Objection first, feature second. "Will it even run on my machine?" is
        what stops a switcher, and Dagric answers it from the USB stick before
        anything is installed — a real capture of Dagric Hardware Check listing
        what it found in plain English. Leading with the desktop instead would
        be showing off to somebody who has not yet decided the thing is
        possible. */}
    <Sequence from={80} durationInFrames={130}>
      <VShot
        src="dagric-hardware-check.png"
        kicker="Before you install"
        line="Find out if it runs — in plain English"
        sub="Boot the USB, click Check This PC. Nothing is written to your disk."
        /* The report's own summary block — title through "worth knowing, but
           nothing is blocked by it". Shown at roughly 1.9x, which is the point
           where the four findings become readable on a phone. */
        crop={{ x0: 0.185, y0: 0.095, x1: 0.63, y1: 0.505 }}
      />
    </Sequence>

    <Sequence from={210} durationInFrames={130}>
      <VShot
        src="dagric-launcher.png"
        kicker="Day one"
        line="The start menu is where you left it"
        sub="Search, favourites, shut down — no relearning anything."
      />
    </Sequence>

    <Sequence from={340} durationInFrames={130}>
      <VShot
        src="dagric-hub.png"
        kicker="One window"
        line="Drivers, printers, backups, security"
        sub="Dagric Hub — the owner's tools in one place, not scattered across forums."
      />
    </Sequence>

    <Sequence from={470} durationInFrames={130}>
      <VShot
        src="dagric-installer-partitions.png"
        kicker="Installing"
        line="Encrypted, with snapshots, by default"
        sub="Btrfs and one checkbox for full-disk encryption. Roll back a bad update."
        /* The two controls the caption is about — the btrfs dropdown and the
           "Encrypt system" checkbox — are 12px of UI in the middle of a
           1280x800 frame. Uncropped, this shot proves nothing. */
        crop={{ x0: 0.24, y0: 0.21, x1: 0.92, y1: 0.60 }}
      />
    </Sequence>

    <Sequence from={600} durationInFrames={140}>
      <Price />
    </Sequence>

    <Sequence from={740} durationInFrames={100}>
      <Sign />
    </Sequence>
  </AbsoluteFill>
);
