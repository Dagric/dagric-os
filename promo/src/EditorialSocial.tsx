import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {ACCENT, ACCENT2, BG, BG2, GOOD, INK, LINE, MUTED, PANEL, SANS, Logo, Wordmark} from "./theme";
import type {BatchSocialProps} from "./BatchSocial";

type EditorialMode = "statement" | "demo" | "proof" | "steps" | "compare" | "community";

const accents = {
  blue: ACCENT,
  teal: ACCENT2,
  amber: "#f0a04b",
  violet: "#a78bfa",
};

const supportingImages: Record<string, string[]> = {
  "windows-10-pc-still-works": ["dagric-hero-desktop.png", "dagric-welcome-live.png", "dagric-desktop-live.png"],
  "zero-dagric-telemetry": ["dagric-desktop-live.png", "dagric-hub.png", "dagric-files.png"],
  "no-dagric-account": ["dagric-uefi-installed-desktop.png", "dagric-firstrun.png", "dagric-desktop-live.png"],
  "check-this-pc": ["dagric-hardware-check.png", "dagric-desktop-live.png", "dagric-welcome-live2.png"],
  "try-live-usb-first": ["dagric-welcome-live.png", "dagric-desktop-live.png", "dagric-hardware-check.png"],
  "read-only-windows-migration": ["dagric-files.png", "dagric-desktop-live.png", "dagric-hub.png"],
  "familiar-start-menu": ["dagric-launcher.png", "dagric-desktop-live.png", "dagric-uefi-installed-desktop.png"],
  "dagric-hub": ["dagric-hub.png", "dagric-hardware-check.png", "dagric-desktop-live.png"],
  "seven-installer-steps": ["dagric-installer-welcome.png", "dagric-installer-partitions.png", "dagric-installer-summary.png"],
  "encryption-and-btrfs": ["dagric-installer-partitions.png", "dagric-installer-summary.png", "dagric-bootmenu.png"],
  "boot-menu-rollback": ["dagric-bootmenu.png", "dagric-uefi-installed-desktop.png", "dagric-desktop-live.png"],
  "seven-desktop-layouts": ["dagric-looks.png", "dagric-launcher.png", "dagric-desktop-live.png"],
  "signed-release-proof": ["dagric-welcome-live2.png", "dagric-plymouth-boot.png", "dagric-uefi-install-done.png"],
  "measured-accessibility": ["dagric-firstrun.png", "dagric-welcome-live.png", "dagric-desktop-live.png"],
  "upgrade-free-to-pro": ["dagric-hub.png", "dagric-desktop-live.png", "dagric-looks.png"],
};

const modeFor = (props: BatchSocialProps): EditorialMode => {
  if (props.slug.startsWith("engagement-") || props.category.toLowerCase() === "community") return "community";
  if (["seven-installer-steps", "read-only-windows-migration", "boot-menu-rollback", "check-this-pc"].some((slug) => props.slug.includes(slug))) return "steps";
  if (["signed-release-proof", "measured-accessibility", "zero-dagric-telemetry", "secure-boot"].some((slug) => props.slug.includes(slug))) return "proof";
  if (["free-edition", "pro-one-time-purchase", "upgrade-free-to-pro", "no-dagric-account"].some((slug) => props.slug.includes(slug))) return "compare";
  if (["dagric-hub", "familiar-start-menu", "seven-desktop-layouts", "gaming-tools", "creator-toolkit", "developer-stack", "windows-apps-with-bottles"].some((slug) => props.slug.includes(slug))) return "demo";
  return "statement";
};

const baseSlug = (slug: string) => slug
  .replace(/^\d+-sep\d+-(second|third)-/, "")
  .replace(/-(common-question|claim-and-proof)$/, "")
  .replace(/^engagement-\d+$/, "dagric-hub");

const imagesFor = (props: BatchSocialProps): string[] => {
  const base = baseSlug(props.slug);
  const selected = supportingImages[base] ?? [props.image, "dagric-desktop-live.png", "dagric-hub.png"];
  return Array.from(new Set([props.image, ...selected])).slice(0, 3);
};

const ease = Easing.bezier(0.22, 1, 0.36, 1);

const EditorialBackground: React.FC<{accent: string; variant: number}> = ({accent, variant}) => {
  const frame = useCurrentFrame();
  const x = 46 + Math.sin((frame + variant * 17) / 48) * 16;
  const y = 24 + Math.cos((frame + variant * 23) / 61) * 12;
  const x2 = 74 + Math.cos((frame + variant * 11) / 72) * 11;
  return (
    <AbsoluteFill style={{background: BG, overflow: "hidden"}}>
      <div style={{position: "absolute", inset: -180, background: `radial-gradient(circle at ${x}% ${y}%, ${accent}2b, transparent 37%), radial-gradient(circle at ${x2}% 72%, ${ACCENT2}18, transparent 34%), linear-gradient(160deg, ${BG}, ${BG2})`}} />
      <div style={{position: "absolute", inset: 0, opacity: 0.24, backgroundImage: "linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px)", backgroundSize: variant % 2 ? "64px 64px" : "48px 48px"}} />
    </AbsoluteFill>
  );
};

const TopBrand: React.FC<{accent: string; category: string; label: string}> = ({accent, category, label}) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: "clamp", easing: ease});
  return (
    <div style={{position: "absolute", left: 54, right: 54, top: 58, display: "flex", alignItems: "center", justifyContent: "space-between", opacity: enter, transform: `translateY(${(1 - enter) * -16}px)`}}>
      <div style={{display: "flex", alignItems: "center", gap: 14}}>
        <Logo size={54} />
        <div>
          <div style={{font: `800 19px ${SANS}`, color: INK, letterSpacing: 3}}>DAGRIC OS</div>
          <div style={{font: `650 15px ${SANS}`, color: MUTED, letterSpacing: 1.5, marginTop: 3}}>{category.toUpperCase()}</div>
        </div>
      </div>
      <div style={{font: `750 16px ${SANS}`, color: accent, letterSpacing: 2.4}}>{label}</div>
    </div>
  );
};

const Progress: React.FC<{accent: string}> = ({accent}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const width = interpolate(frame, [0, durationInFrames - 1], [0, 972], {extrapolateRight: "clamp"});
  return (
    <div style={{position: "absolute", left: 54, right: 54, bottom: 54, height: 3, background: "rgba(255,255,255,.09)", borderRadius: 99}}>
      <div style={{width, height: 3, background: accent, borderRadius: 99, boxShadow: `0 0 18px ${accent}99`}} />
    </div>
  );
};

const HookWords: React.FC<{text: string; accent: string; compact?: boolean}> = ({text, accent, compact = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words = text.split(/\s+/);
  return (
    <div style={{fontFamily: SANS, fontWeight: 830, fontSize: compact ? 68 : 82, lineHeight: 0.98, letterSpacing: -2.8, color: INK, textAlign: "left"}}>
      {words.map((word, index) => {
        const pop = spring({frame: frame - index * 2, fps, config: {damping: 17, stiffness: 135, mass: 0.75}});
        const highlighted = index >= Math.max(1, words.length - 3);
        return (
          <span key={`${word}-${index}`} style={{display: "inline-block", marginRight: 18, color: highlighted ? accent : INK, opacity: pop, transform: `translateY(${(1 - pop) * 32}px) rotate(${(1 - pop) * (index % 2 ? 1.6 : -1.2)}deg)`}}>
            {word}
          </span>
        );
      })}
    </div>
  );
};

const ScreenCard: React.FC<{src: string; accent: string; frameLabel: string; rotate?: number; focus?: boolean}> = ({src, accent, frameLabel, rotate = 0, focus = false}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 18, stiffness: 105, mass: 0.85}});
  const float = Math.sin(frame / 24) * 5;
  const push = interpolate(frame, [0, durationInFrames], [1.0, focus ? 1.055 : 1.025]);
  return (
    <div style={{position: "relative", background: "#07101a", border: `1px solid ${accent}55`, borderRadius: 24, padding: 11, overflow: "hidden", boxShadow: "0 34px 100px rgba(0,0,0,.55)", opacity: enter, transform: `translateY(${(1 - enter) * 62 + float}px) rotate(${rotate}deg) scale(${0.95 + enter * 0.05})`}}>
      <div style={{height: 34, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 10px"}}>
        <div style={{display: "flex", gap: 7}}>{[0, 1, 2].map((dot) => <div key={dot} style={{width: 8, height: 8, borderRadius: 99, background: dot === 0 ? accent : "#405067"}} />)}</div>
        <div style={{font: `650 13px ${SANS}`, color: MUTED, letterSpacing: 1.1}}>{frameLabel.toUpperCase()}</div>
      </div>
      <div style={{height: 470, borderRadius: 15, overflow: "hidden", background: "#050a10"}}>
        <Img src={staticFile(src)} style={{width: "100%", height: "100%", objectFit: "contain", transform: `scale(${push})`}} />
      </div>
    </div>
  );
};

const CursorCue: React.FC<{accent: string; from: [number, number]; to: [number, number]}> = ({accent, from, to}) => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [10, 55], [from[0], to[0]], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
  const y = interpolate(frame, [10, 55], [from[1], to[1]], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
  const pulse = 0.7 + Math.sin(frame / 4) * 0.16;
  return <div style={{position: "absolute", left: x, top: y, width: 34, height: 34, borderRadius: 99, border: `3px solid ${accent}`, boxShadow: `0 0 0 ${10 + pulse * 9}px ${accent}28`, transform: `scale(${pulse})`}} />;
};

const IntroScene: React.FC<{props: BatchSocialProps; mode: EditorialMode; accent: string; variant: number}> = ({props, mode, accent, variant}) => {
  const frame = useCurrentFrame();
  const label = mode === "community" ? "A REAL QUESTION" : mode === "proof" ? "CLAIM → EVIDENCE" : mode === "steps" ? "WATCH THE WORKFLOW" : "THE SHORT VERSION";
  const line = interpolate(frame, [8, 28], [0, 1], {extrapolateRight: "clamp", easing: ease});
  return (
    <AbsoluteFill style={{padding: "210px 58px 150px", justifyContent: "center"}}>
      <div style={{display: "flex", alignItems: "center", gap: 16, marginBottom: 34, opacity: line}}>
        <div style={{width: 90 * line, height: 5, borderRadius: 99, background: accent}} />
        <div style={{font: `800 18px ${SANS}`, letterSpacing: 3.5, color: accent}}>{label}</div>
      </div>
      <HookWords text={props.headline} accent={accent} compact={props.headline.length > 58} />
      <div style={{marginTop: 42, maxWidth: 850, font: `500 ${variant % 2 ? 29 : 31}px/1.38 ${SANS}`, color: MUTED}}>{props.kicker}</div>
    </AbsoluteFill>
  );
};

const DemoScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => (
  <AbsoluteFill style={{padding: "180px 44px 140px", justifyContent: "center"}}>
    <div style={{position: "relative"}}>
      <ScreenCard src={images[0]} accent={accent} frameLabel="Captured on Dagric OS" focus />
      <CursorCue accent={accent} from={[800, 370]} to={[575, 510]} />
    </div>
    <div style={{display: "grid", gridTemplateColumns: "1fr auto", gap: 24, alignItems: "end", margin: "40px 18px 0"}}>
      <div style={{font: `760 40px/1.08 ${SANS}`, color: INK}}>{props.headline}</div>
      <div style={{font: `800 18px ${SANS}`, color: BG, background: accent, borderRadius: 99, padding: "12px 18px", letterSpacing: 1.2}}>REAL UI</div>
    </div>
    <div style={{font: `450 27px/1.42 ${SANS}`, color: MUTED, margin: "20px 18px 0"}}>{props.body}</div>
  </AbsoluteFill>
);

const ProofScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => {
  const frame = useCurrentFrame();
  const underline = interpolate(frame, [28, 54], [0, 1], {extrapolateRight: "clamp", easing: ease});
  return (
    <AbsoluteFill style={{padding: "180px 48px 140px", justifyContent: "center"}}>
      <ScreenCard src={images[0]} accent={accent} frameLabel="Evidence capture" focus />
      <div style={{margin: "38px 16px 0", display: "grid", gridTemplateColumns: "170px 1fr", gap: 24, alignItems: "start"}}>
        <div style={{font: `850 20px ${SANS}`, color: accent, letterSpacing: 3}}>WHAT WE CAN SHOW</div>
        <div>
          <div style={{font: `780 39px/1.08 ${SANS}`, color: INK}}>{props.headline}</div>
          <div style={{width: `${underline * 100}%`, height: 4, background: accent, marginTop: 18, borderRadius: 99}} />
          <div style={{font: `480 27px/1.4 ${SANS}`, color: MUTED, marginTop: 21}}>{props.body}</div>
        </div>
      </div>
      <div style={{margin: "35px 16px 0", borderLeft: `4px solid ${accent}`, padding: "16px 20px", background: "rgba(5,12,20,.62)", font: `650 22px/1.35 ${SANS}`, color: INK}}>Evidence is linked so a reviewer can check it independently.</div>
    </AbsoluteFill>
  );
};

const stepCopy = (slug: string): string[] => {
  if (slug.includes("installer")) return ["Choose the basics", "Review the disk", "Confirm the summary"];
  if (slug.includes("migration")) return ["Mount read-only", "Choose your folders", "Review the copy"];
  if (slug.includes("rollback")) return ["Update creates a snapshot", "Choose an earlier state", "Keep a separate backup"];
  if (slug.includes("check-this-pc")) return ["Boot the live USB", "Run the report", "Test what matters"];
  return ["Open the tool", "Review the options", "Confirm when ready"];
};

const StepsScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const steps = stepCopy(props.slug);
  return (
    <AbsoluteFill style={{padding: "180px 48px 140px", justifyContent: "center"}}>
      <div style={{display: "grid", gridTemplateColumns: "0.92fr 1.08fr", gap: 30, alignItems: "center"}}>
        <div style={{display: "flex", flexDirection: "column", gap: 22}}>
          {steps.map((step, index) => {
            const show = spring({frame: frame - index * 9, fps, config: {damping: 18, stiffness: 115}});
            return (
              <div key={step} style={{display: "grid", gridTemplateColumns: "58px 1fr", gap: 16, alignItems: "center", opacity: show, transform: `translateX(${(1 - show) * -28}px)`}}>
                <div style={{width: 56, height: 56, borderRadius: 18, display: "grid", placeItems: "center", font: `850 23px ${SANS}`, color: index === 2 ? BG : accent, background: index === 2 ? accent : PANEL, border: `1px solid ${accent}66`}}>{index + 1}</div>
                <div style={{font: `720 29px/1.12 ${SANS}`, color: INK}}>{step}</div>
              </div>
            );
          })}
          <div style={{font: `450 25px/1.42 ${SANS}`, color: MUTED, marginTop: 10}}>{props.body}</div>
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 20}}>
          <ScreenCard src={images[0]} accent={accent} frameLabel="Step one" rotate={-1.4} />
          <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16}}>
            {images.slice(1, 3).map((image, index) => <div key={image} style={{height: 220, borderRadius: 18, border: `1px solid ${LINE}`, background: "#07101a", overflow: "hidden", transform: `rotate(${index ? 1.4 : -0.7}deg)`}}><Img src={staticFile(image)} style={{width: "100%", height: "100%", objectFit: "contain"}} /></div>)}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const comparisonCopy = (slug: string) => {
  if (slug.includes("pro")) return [["FREE", "Test the real computer first"], ["PRO", "One payment, extra toolkits"]];
  if (slug.includes("account")) return [["LOCAL", "Your login and your files"], ["OPTIONAL", "Only documented online services"]];
  if (slug.includes("upgrade")) return [["START FREE", "Keep the decision reversible"], ["UPGRADE LATER", "Keep files and settings"]];
  return [["THE CLAIM", "Short and specific"], ["THE PROOF", "Linked and testable"]];
};

const CompareScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const cards = comparisonCopy(props.slug);
  return (
    <AbsoluteFill style={{padding: "190px 48px 150px", justifyContent: "center"}}>
      <div style={{font: `780 51px/1.05 ${SANS}`, color: INK, margin: "0 12px 38px", maxWidth: 920}}>{props.headline}</div>
      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22}}>
        {cards.map(([title, copy], index) => {
          const enter = spring({frame: frame - index * 10, fps, config: {damping: 17, stiffness: 110}});
          return (
            <div key={title} style={{minHeight: 380, borderRadius: 28, border: `1px solid ${index ? accent : LINE}`, background: index ? `linear-gradient(155deg, ${accent}24, ${PANEL})` : PANEL, padding: 30, position: "relative", overflow: "hidden", opacity: enter, transform: `translateY(${(1 - enter) * 60}px)`}}>
              <div style={{font: `850 18px ${SANS}`, color: index ? accent : MUTED, letterSpacing: 3}}>{title}</div>
              <div style={{font: `760 37px/1.13 ${SANS}`, color: INK, marginTop: 28}}>{copy}</div>
              <div style={{position: "absolute", left: 30, right: 30, bottom: 28, height: 150, borderRadius: 18, overflow: "hidden", background: "#07101a"}}><Img src={staticFile(images[index] ?? images[0])} style={{width: "100%", height: "100%", objectFit: "cover", objectPosition: "center"}} /></div>
            </div>
          );
        })}
      </div>
      <div style={{font: `480 27px/1.42 ${SANS}`, color: MUTED, margin: "34px 12px 0", maxWidth: 900}}>{props.body}</div>
    </AbsoluteFill>
  );
};

const StatementScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => {
  const frame = useCurrentFrame();
  const wipe = interpolate(frame, [4, 30], [0, 1], {extrapolateRight: "clamp", easing: ease});
  return (
    <AbsoluteFill style={{padding: "180px 48px 145px", justifyContent: "center"}}>
      <div style={{height: 520, borderRadius: 30, overflow: "hidden", position: "relative", background: "#07101a", border: `1px solid ${LINE}`}}>
        <Img src={staticFile(images[0])} style={{width: "100%", height: "100%", objectFit: "contain", transform: `scale(${1.02 + wipe * 0.04})`}} />
        <div style={{position: "absolute", left: 0, right: 0, bottom: 0, height: 180, background: "linear-gradient(transparent, rgba(4,9,15,.96))"}} />
        <div style={{position: "absolute", left: 30, bottom: 28, font: `800 19px ${SANS}`, color: accent, letterSpacing: 3}}>RUNNING DAGRIC OS</div>
      </div>
      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 30}}>
        <div style={{borderTop: `4px solid ${accent}`, background: PANEL, padding: 24, borderRadius: "0 0 20px 20px"}}><div style={{font: `820 17px ${SANS}`, color: accent, letterSpacing: 2}}>WHAT IT DOES</div><div style={{font: `650 27px/1.28 ${SANS}`, color: INK, marginTop: 16}}>{props.headline}</div></div>
        <div style={{borderTop: `4px solid ${MUTED}`, background: PANEL, padding: 24, borderRadius: "0 0 20px 20px"}}><div style={{font: `820 17px ${SANS}`, color: MUTED, letterSpacing: 2}}>WHAT TO TEST</div><div style={{font: `470 25px/1.34 ${SANS}`, color: MUTED, marginTop: 16}}>{props.body}</div></div>
      </div>
    </AbsoluteFill>
  );
};

const CommunityScene: React.FC<{props: BatchSocialProps; accent: string; images: string[]}> = ({props, accent, images}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const responses = ["Hardware", "Windows apps", "Accessibility"];
  return (
    <AbsoluteFill style={{padding: "185px 54px 150px", justifyContent: "center"}}>
      <div style={{display: "grid", gridTemplateColumns: "116px 1fr", gap: 24, alignItems: "start"}}>
        <div style={{width: 116, height: 116, borderRadius: 34, background: `linear-gradient(145deg, ${accent}, ${ACCENT})`, display: "grid", placeItems: "center"}}><Logo size={86} /></div>
        <div style={{borderRadius: "12px 34px 34px 34px", background: INK, color: BG, padding: "34px 38px", font: `760 45px/1.13 ${SANS}`}}>{props.headline}</div>
      </div>
      <div style={{marginTop: 34, borderRadius: 26, height: 390, overflow: "hidden", border: `1px solid ${LINE}`, background: "#07101a"}}><Img src={staticFile(images[0])} style={{width: "100%", height: "100%", objectFit: "contain"}} /></div>
      <div style={{display: "flex", flexWrap: "wrap", gap: 14, marginTop: 30}}>
        {responses.map((response, index) => {
          const enter = spring({frame: frame - 18 - index * 8, fps, config: {damping: 17}});
          return <div key={response} style={{borderRadius: 99, border: `1px solid ${accent}77`, color: index === 0 ? BG : INK, background: index === 0 ? accent : PANEL, padding: "13px 20px", font: `740 20px ${SANS}`, opacity: enter, transform: `translateY(${(1 - enter) * 20}px)`}}>{response}</div>;
        })}
      </div>
      <div style={{font: `500 26px/1.35 ${SANS}`, color: MUTED, marginTop: 28}}>{props.body}</div>
    </AbsoluteFill>
  );
};

const OutroScene: React.FC<{props: BatchSocialProps; accent: string; mode: EditorialMode}> = ({props, accent, mode}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 16, stiffness: 105, mass: 0.9}});
  const cta = mode === "community" ? "Leave a real question." : props.cta;
  return (
    <AbsoluteFill style={{padding: "190px 62px 170px", justifyContent: "center"}}>
      <div style={{display: "flex", alignItems: "center", gap: 26, opacity: enter, transform: `translateY(${(1 - enter) * 42}px)`}}>
        <Logo size={118} />
        <Wordmark size={54} />
      </div>
      <div style={{width: 180, height: 6, borderRadius: 99, background: accent, margin: "52px 0 42px", transform: `scaleX(${enter})`, transformOrigin: "left"}} />
      <div style={{font: `810 68px/1.02 ${SANS}`, letterSpacing: -2.4, color: INK, maxWidth: 880}}>{cta}</div>
      <div style={{font: `480 29px/1.4 ${SANS}`, color: MUTED, marginTop: 32, maxWidth: 820}}>See the current test notes, known limits, and download options.</div>
      <div style={{font: `850 39px ${SANS}`, color: accent, marginTop: 48, letterSpacing: -0.7}}>dagric.com</div>
    </AbsoluteFill>
  );
};

export const EditorialSocial: React.FC<BatchSocialProps> = (props) => {
  const {durationInFrames} = useVideoConfig();
  const mode = modeFor(props);
  const accent = accents[props.accent];
  const images = imagesFor(props);
  const variant = Math.abs(props.slug.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0)) % 7;
  const introLength = Math.max(54, Math.round(durationInFrames * (mode === "community" ? 0.34 : 0.27)));
  const outroLength = Math.max(50, Math.round(durationInFrames * 0.20));
  const bodyLength = durationInFrames - introLength - outroLength;
  const editorialLabel = mode === "community" ? "YOUR TURN" : mode === "proof" ? "VERIFIABLE" : mode === "steps" ? "3 STEPS" : mode === "compare" ? "SIDE BY SIDE" : mode === "demo" ? "ON SCREEN" : "FIELD NOTE";

  const Body = mode === "demo" ? DemoScene : mode === "proof" ? ProofScene : mode === "steps" ? StepsScene : mode === "compare" ? CompareScene : mode === "community" ? CommunityScene : StatementScene;
  return (
    <AbsoluteFill style={{background: BG}}>
      <EditorialBackground accent={accent} variant={variant} />
      <Sequence from={0} durationInFrames={introLength} premountFor={15}><IntroScene props={props} mode={mode} accent={accent} variant={variant} /></Sequence>
      <Sequence from={introLength} durationInFrames={bodyLength} premountFor={15}><Body props={props} accent={accent} images={images} /></Sequence>
      <Sequence from={introLength + bodyLength} durationInFrames={outroLength} premountFor={15}><OutroScene props={props} accent={accent} mode={mode} /></Sequence>
      <TopBrand accent={accent} category={props.category} label={editorialLabel} />
      <Progress accent={accent} />
    </AbsoluteFill>
  );
};
