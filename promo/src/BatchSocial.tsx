import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {ACCENT, ACCENT2, BG, BG2, GOOD, INK, LINE, MUTED, PANEL, SANS, Logo, Wordmark} from "./theme";

export type BatchFormat = "landscape" | "square" | "portrait" | "vertical";
export type BatchStyle = "statement" | "proof" | "question" | "split" | "steps";

export type BatchTopic = {
  slug: string;
  category: string;
  kicker: string;
  headline: string;
  body: string;
  cta: string;
  image: string;
  durationSeconds: number;
  style: BatchStyle;
  accent: "blue" | "teal" | "amber" | "violet";
  voiceFile?: string;
};

export type BatchSocialProps = BatchTopic & {
  format: BatchFormat;
  reviewCut?: boolean;
};

const accents = {
  blue: ACCENT,
  teal: ACCENT2,
  amber: "#f0a04b",
  violet: "#a78bfa",
};

const formatMetrics = (format: BatchFormat) => {
  const tall = format === "vertical" || format === "portrait";
  return {
    tall,
    pad: format === "vertical" ? 54 : format === "portrait" ? 48 : 46,
    title: format === "vertical" ? 72 : format === "portrait" ? 58 : format === "square" ? 54 : 56,
    body: format === "vertical" ? 34 : format === "portrait" ? 29 : format === "square" ? 28 : 26,
    kicker: format === "vertical" ? 25 : 21,
    safeTop: format === "vertical" ? 130 : format === "portrait" ? 72 : 44,
    safeBottom: format === "vertical" ? 170 : format === "portrait" ? 80 : 44,
  };
};

const Fade: React.FC<{children: React.ReactNode; outAt: number}> = ({children, outAt}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 10, outAt - 10, outAt], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>;
};

const Chrome: React.FC<{format: BatchFormat; category: string; accent: string; narrated: boolean}> = ({format, category, accent, narrated}) => {
  const m = formatMetrics(format);
  return (
    <>
      <div style={{position: "absolute", top: m.safeTop, left: m.pad, display: "flex", gap: 12, alignItems: "center"}}>
        <div style={{width: 10, height: 10, borderRadius: 99, background: accent, boxShadow: `0 0 22px ${accent}`}} />
        <div style={{color: MUTED, fontFamily: SANS, fontSize: m.kicker, fontWeight: 700, letterSpacing: 3, textTransform: "uppercase"}}>{category}</div>
      </div>
      {narrated ? (
        <div style={{position: "absolute", top: m.safeTop, right: m.pad, color: accent, fontFamily: SANS, fontSize: 17, fontWeight: 750, letterSpacing: 2}}>VOICEOVER</div>
      ) : null}
    </>
  );
};

const Intro: React.FC<BatchSocialProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const m = formatMetrics(props.format);
  const accent = accents[props.accent];
  const enter = spring({frame, fps, config: {damping: 180}, durationInFrames: 28});
  const rule = interpolate(frame, [8, 28], [0, 1], {extrapolateRight: "clamp"});
  const align = props.style === "question" || m.tall ? "center" : "left";
  return (
    <Fade outAt={durationInFrames}>
      <AbsoluteFill style={{background: `radial-gradient(circle at ${m.tall ? "50% 30%" : "20% 30%"}, ${accent}25, transparent 44%), ${BG}`, padding: `${m.safeTop + 70}px ${m.pad}px ${m.safeBottom}px`, justifyContent: "center", alignItems: align === "center" ? "center" : "flex-start"}}>
        <Chrome format={props.format} category={props.category} accent={accent} narrated={Boolean(props.voiceFile)} />
        <div style={{color: accent, fontSize: m.kicker, fontFamily: SANS, fontWeight: 750, letterSpacing: 3, textTransform: "uppercase", textAlign: align as "center" | "left", opacity: enter}}>{props.kicker}</div>
        <div style={{height: 4, width: m.tall ? 160 : 210, background: accent, borderRadius: 99, margin: "26px 0 30px", transform: `scaleX(${rule})`, transformOrigin: align === "center" ? "center" : "left"}} />
        <div style={{color: INK, fontSize: m.title, lineHeight: 1.06, fontFamily: SANS, fontWeight: 800, maxWidth: m.tall ? "100%" : "82%", textAlign: align as "center" | "left", transform: `translateY(${(1 - enter) * 36}px)`, opacity: enter}}>{props.headline}</div>
      </AbsoluteFill>
    </Fade>
  );
};

const Proof: React.FC<BatchSocialProps> = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const m = formatMetrics(props.format);
  const accent = accents[props.accent];
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.045]);
  const rise = interpolate(frame, [0, 22], [34, 0], {extrapolateRight: "clamp"});
  const tall = m.tall;
  const split = props.style === "split" && !tall;
  return (
    <Fade outAt={durationInFrames}>
      <AbsoluteFill style={{background: BG2, padding: `${m.safeTop + 62}px ${m.pad}px ${m.safeBottom + 24}px`}}>
        <Chrome format={props.format} category={props.category} accent={accent} narrated={Boolean(props.voiceFile)} />
        <div style={{height: "100%", display: "flex", flexDirection: split ? "row" : "column", gap: tall ? 32 : 28, alignItems: "center", justifyContent: "center"}}>
          <div style={{width: split ? "55%" : "100%", height: tall ? "44%" : split ? "72%" : "58%", border: `1px solid ${LINE}`, borderRadius: tall ? 22 : 16, overflow: "hidden", background: "#070c13", boxShadow: "0 28px 80px rgba(0,0,0,.5)", transform: `scale(${zoom})`}}>
            <Img src={staticFile(props.image)} style={{width: "100%", height: "100%", objectFit: "contain"}} />
          </div>
          <div style={{width: split ? "41%" : "100%", transform: `translateY(${rise}px)`, textAlign: tall || props.style === "question" ? "center" : "left"}}>
            <div style={{color: INK, fontFamily: SANS, fontWeight: 800, fontSize: tall ? m.title * 0.62 : m.title * 0.58, lineHeight: 1.12}}>{props.headline}</div>
            <div style={{color: MUTED, fontFamily: SANS, fontSize: m.body, lineHeight: 1.38, marginTop: 20}}>{props.body}</div>
            {props.style === "steps" ? (
              <div style={{display: "flex", justifyContent: tall ? "center" : "flex-start", gap: 12, marginTop: 24}}>
                {["CHECK", "CHOOSE", "CONFIRM"].map((label, index) => <div key={label} style={{color: index === 2 ? BG : accent, background: index === 2 ? accent : PANEL, border: `1px solid ${index === 2 ? accent : LINE}`, borderRadius: 99, padding: "9px 14px", fontFamily: SANS, fontSize: tall ? 16 : 15, fontWeight: 800, letterSpacing: 1}}>{label}</div>)}
              </div>
            ) : null}
          </div>
        </div>
      </AbsoluteFill>
    </Fade>
  );
};

const Outro: React.FC<BatchSocialProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const m = formatMetrics(props.format);
  const accent = accents[props.accent];
  const pop = spring({frame, fps, config: {damping: 180}, durationInFrames: 26});
  return (
    <Fade outAt={durationInFrames}>
      <AbsoluteFill style={{background: `linear-gradient(150deg, ${BG}, ${PANEL})`, alignItems: "center", justifyContent: "center", padding: `${m.safeTop}px ${m.pad}px ${m.safeBottom}px`, textAlign: "center"}}>
        <div style={{transform: `scale(${0.8 + pop * 0.2})`}}><Logo size={m.tall ? 150 : 105} /></div>
        <div style={{marginTop: 24}}><Wordmark size={m.tall ? 54 : 42} /></div>
        <div style={{color: INK, fontFamily: SANS, fontSize: m.tall ? 41 : 33, fontWeight: 750, lineHeight: 1.2, marginTop: 30, maxWidth: "90%"}}>{props.cta}</div>
        <div style={{color: accent, fontFamily: SANS, fontSize: m.tall ? 35 : 28, fontWeight: 800, marginTop: 18}}>dagric.com</div>
        {props.reviewCut !== false ? (
          <div style={{color: GOOD, fontFamily: SANS, fontSize: m.tall ? 22 : 18, marginTop: 14}}>Review cut · not yet published</div>
        ) : null}
      </AbsoluteFill>
    </Fade>
  );
};

export const BatchSocial: React.FC<BatchSocialProps> = (props) => {
  const {durationInFrames} = useVideoConfig();
  const intro = Math.max(60, Math.round(durationInFrames * 0.31));
  const outro = Math.max(54, Math.round(durationInFrames * 0.22));
  const proof = durationInFrames - intro - outro;
  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      {props.voiceFile ? <Audio src={staticFile(props.voiceFile)} volume={1} /> : null}
      <Sequence from={0} durationInFrames={intro}><Intro {...props} /></Sequence>
      <Sequence from={intro} durationInFrames={proof}><Proof {...props} /></Sequence>
      <Sequence from={intro + proof} durationInFrames={outro}><Outro {...props} /></Sequence>
    </AbsoluteFill>
  );
};
