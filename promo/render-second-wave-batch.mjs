import {mkdir, readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const campaign = JSON.parse(await readFile(path.join(here, "campaign-200", "campaign.json"), "utf8"));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const outputRoot = process.env.DAGRIC_OUTPUT_ROOT ? path.resolve(process.env.DAGRIC_OUTPUT_ROOT) : path.join(here, "second-wave-batch");
const compositionId = process.env.DAGRIC_COMPOSITION ?? "DagricSocialBatch";
const imageFormat = process.env.DAGRIC_IMAGE_FORMAT ?? "jpeg";
const outputRootPortable = outputRoot.replaceAll("\\", "/");

const accents = ["blue", "teal", "amber", "violet"];
const sourceBySlug = new Map(topics.map((topic) => [topic.slug, topic]));
const commonQuestions = campaign.items.filter((item) => item.angle === "Common question");
const claimProofBySource = new Map(
  campaign.items.filter((item) => item.angle === "Claim and proof").map((item) => [item.sourceTopic, item]),
);

if (commonQuestions.length !== 25) {
  throw new Error(`Expected 25 common-question briefs, found ${commonQuestions.length}`);
}

const finalFiveSources = [
  "signed-release-proof",
  "measured-accessibility",
  "check-this-pc",
  "read-only-windows-migration",
  "boot-menu-rollback",
];

const engagementQuestions = [
  "What PC are you trying to keep running?",
  "Would you test a live USB before installing?",
  "What matters most: privacy, familiarity, or rollback?",
  "Which Windows app do you still need?",
  "Which desktop layout feels most familiar?",
  "What hardware should Dagric test next?",
  "What would you verify before switching operating systems?",
  "Which installation step worries you most?",
  "What Linux question should we answer next?",
  "What would you need from Dagric Free or Pro?",
  "Which game or creative app should we test?",
  "Does your current PC use Secure Boot?",
  "What should the next Dagric release improve?",
];

const tagForCategory = (category) => {
  if (["Hardware", "Secure Boot", "Windows apps", "Gaming"].includes(category)) return "Compatibility and testing";
  if (["Migration", "Install", "Filesystem", "Recovery"].includes(category)) return "Migration and recovery";
  if (["Editions", "Pricing", "Upgrade"].includes(category)) return "Pricing and conversion";
  if (["Privacy", "Proof", "Accessibility", "Foundation", "Support"].includes(category)) return "Trust and proof";
  return "Product education";
};

const isWeekend = (day) => {
  const weekday = new Date(Date.UTC(2026, 8, day)).getUTCDay();
  return weekday === 0 || weekday === 6;
};

const isThirdSlotDay = (day) => {
  const weekday = new Date(Date.UTC(2026, 8, day)).getUTCDay();
  return weekday === 2 || weekday === 4 || weekday === 6;
};

const secondTime = (day) => {
  if (day === 24) return "10:00:00";
  if (day === 25) return "12:00:00";
  return isWeekend(day) ? "19:30:00" : "08:15:00";
};

const thirdTime = (day) => {
  if (day === 24) return "14:00:00";
  return new Date(Date.UTC(2026, 8, day)).getUTCDay() === 6 ? "15:15:00" : "13:30:00";
};
const isoAt = (day, time) => `2026-09-${String(day).padStart(2, "0")}T${time}-05:00`;
const cleanCampaignCaption = (brief) => {
  const generatedPrefix = `${brief.angle}: ${brief.hook} `;
  return brief.caption.startsWith(generatedPrefix)
    ? brief.caption.slice(generatedPrefix.length)
    : brief.caption;
};

const secondItems = [];
for (let day = 1; day <= 25; day++) {
  // Rotate seven topics away from the primary calendar so the two daily posts
  // do not repeat the same product claim.
  secondItems.push({day, brief: commonQuestions[(day - 1 + 7) % commonQuestions.length]});
}
for (let day = 26; day <= 30; day++) {
  const source = finalFiveSources[day - 26];
  const brief = claimProofBySource.get(source);
  if (!brief) throw new Error(`Missing claim-and-proof brief for ${source}`);
  secondItems.push({day, brief});
}

const renderJobs = [];
for (const {day, brief} of secondItems) {
  const source = sourceBySlug.get(brief.sourceTopic);
  if (!source) throw new Error(`Missing source topic ${brief.sourceTopic}`);
  renderJobs.push({
    day,
    slot: "second",
    title: brief.title.replace(/\s+—\s+.+$/, ""),
    caption: cleanCampaignCaption(brief),
    tag: tagForCategory(brief.category),
    props: {
      ...source,
      slug: brief.slug,
      category: brief.category,
      kicker: brief.angle,
      headline: brief.hook,
      durationSeconds: brief.durationSeconds,
      style: brief.angle === "Common question" ? "question" : "proof",
      accent: accents[(day - 1) % accents.length],
      format: "vertical",
      voiceFile: undefined,
      reviewCut: false,
    },
    publishAt: isoAt(day, secondTime(day)),
  });
}

let engagementIndex = 0;
for (let day = 1; day <= 30; day++) {
  if (!isThirdSlotDay(day)) continue;
  const question = engagementQuestions[engagementIndex];
  const source = topics[(engagementIndex * 3 + 4) % topics.length];
  renderJobs.push({
    day,
    slot: "third",
    title: `${question} | Dagric OS`,
    caption: `${question} Tell us what you want Dagric to test, explain, or improve. https://dagric.com #DagricOS #Linux #PC`,
    tag: "Product education",
    props: {
      ...source,
      slug: `engagement-${String(engagementIndex + 1).padStart(2, "0")}`,
      category: "Community",
      kicker: "Your turn",
      headline: question,
      body: "Tell us what you want Dagric to test, explain, or improve.",
      cta: "Comment with your answer",
      durationSeconds: 10,
      style: "question",
      accent: accents[engagementIndex % accents.length],
      format: "vertical",
      voiceFile: undefined,
      reviewCut: false,
    },
    publishAt: isoAt(day, thirdTime(day)),
  });
  engagementIndex++;
}

await mkdir(outputRoot, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});
const manifest = [];
const plan = [];

for (let index = 0; index < renderJobs.length; index++) {
  const job = renderJobs[index];
  const composition = await selectComposition({serveUrl, id: compositionId, inputProps: job.props});
  const number = String(index + 1).padStart(2, "0");
  const filename = `${number}-sep${String(job.day).padStart(2, "0")}-${job.slot}-${job.props.slug}-${job.props.durationSeconds}s-final.mp4`;
  const outputLocation = path.join(outputRoot, filename);

  await renderMedia({
    serveUrl,
    composition,
    codec: "h264",
    outputLocation,
    inputProps: job.props,
    scale: 1.5,
    crf: 20,
    imageFormat,
    ...(imageFormat === "jpeg" ? {jpegQuality: 90} : {}),
    concurrency: 3,
    overwrite: true,
  });

  manifest.push({
    order: index + 1,
    day: job.day,
    slot: job.slot,
    slug: job.props.slug,
    durationSeconds: job.props.durationSeconds,
    resolution: "1080x1920",
    narrated: false,
    file: filename,
  });
  plan.push({
    date: job.publishAt,
    slot: job.slot,
    channels: ["youtube", "instagram", "tiktok"],
    video: `${outputRootPortable}/${filename}`,
    title: job.title.slice(0, 96),
    caption: job.caption,
    tag: job.tag,
  });

  await writeFile(path.join(outputRoot, "manifest.json"), JSON.stringify({videos: manifest}, null, 2));
  await writeFile(path.join(outputRoot, "second-wave-plan.json"), JSON.stringify(plan, null, 2));
  process.stdout.write(`[${index + 1}/${renderJobs.length}] ${filename}\n`);
}

await writeFile(
  path.join(outputRoot, "README.md"),
  [
    "# Dagric OS second-wave batch",
    "",
    "Forty-three final caption-led vertical videos for a two-post daily baseline and a third engagement slot on Tuesdays, Thursdays, and Saturdays.",
    "",
    "- 30 second-slot product videos.",
    "- 13 third-slot community-question videos.",
    "- No review labels.",
    "- No downloaded music or unverified narration.",
    "- Exact captions, channels, tags, and Chicago timestamps are in `second-wave-plan.json`.",
    "",
  ].join("\n"),
);
