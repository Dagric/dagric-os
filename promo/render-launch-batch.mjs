import {mkdir, readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const outputRoot = process.env.DAGRIC_OUTPUT_ROOT ? path.resolve(process.env.DAGRIC_OUTPUT_ROOT) : path.join(here, "launch-batch");
const compositionId = process.env.DAGRIC_COMPOSITION ?? "DagricSocialBatch";
const imageFormat = process.env.DAGRIC_IMAGE_FORMAT ?? "jpeg";

const launchSlugs = [
  "windows-10-pc-still-works",
  "check-this-pc",
  "try-live-usb-first",
  "read-only-windows-migration",
  "dagric-hub",
  "seven-installer-steps",
  "boot-menu-rollback",
  "free-edition",
  "pro-one-time-purchase",
  "signed-release-proof",
  "measured-accessibility",
  "upgrade-free-to-pro",
];

const selectedTopics = launchSlugs.map((slug) => {
  const topic = topics.find((candidate) => candidate.slug === slug);
  if (!topic) throw new Error(`Missing launch topic: ${slug}`);
  return topic;
});

await mkdir(outputRoot, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});
const manifest = [];

for (let index = 0; index < selectedTopics.length; index++) {
  const topic = selectedTopics[index];
  const inputProps = {
    ...topic,
    format: "vertical",
    durationSeconds: topic.durationSeconds,
    voiceFile: topic.voiceScript ? `narration-batch/${topic.slug}.wav` : undefined,
    reviewCut: false,
  };
  const composition = await selectComposition({serveUrl, id: compositionId, inputProps});
  const number = String(index + 1).padStart(2, "0");
  const filename = `${number}-${topic.slug}-vertical-${topic.durationSeconds}s-final.mp4`;
  const outputLocation = path.join(outputRoot, filename);

  await renderMedia({
    serveUrl,
    composition,
    codec: "h264",
    outputLocation,
    inputProps,
    scale: 1.5,
    crf: 20,
    imageFormat,
    ...(imageFormat === "jpeg" ? {jpegQuality: 90} : {}),
    concurrency: 3,
    overwrite: true,
  });

  manifest.push({
    order: index + 1,
    topic: topic.slug,
    headline: topic.headline,
    durationSeconds: topic.durationSeconds,
    narrated: Boolean(topic.voiceScript),
    resolution: "1080x1920",
    file: filename,
  });
  await writeFile(path.join(outputRoot, "manifest.json"), JSON.stringify({generatedAt: new Date().toISOString(), videos: manifest}, null, 2));
  process.stdout.write(`[${index + 1}/${selectedTopics.length}] ${filename}\n`);
}

await writeFile(path.join(outputRoot, "README.md"), [
  "# Dagric OS launch batch",
  "",
  "Twelve final 1080×1920 videos selected from the audited social review batch.",
  "",
  "- The review-cut label has been removed.",
  "- These files are intended for TikTok, Instagram Reels, YouTube Shorts, and Snapchat.",
  "- Review narrated finalists end-to-end before scheduling.",
  "",
].join("\n"));
