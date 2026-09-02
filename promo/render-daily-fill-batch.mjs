import {mkdir, readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const outputRoot = process.env.DAGRIC_OUTPUT_ROOT ? path.resolve(process.env.DAGRIC_OUTPUT_ROOT) : path.join(here, "daily-fill-batch");
const compositionId = process.env.DAGRIC_COMPOSITION ?? "DagricSocialBatch";
const imageFormat = process.env.DAGRIC_IMAGE_FORMAT ?? "jpeg";

// These are the thirteen audited concepts that are not already part of the
// twelve-video launch sequence. They fill the launch calendar without
// repeating a video on the same social channel.
const dailyFillSlugs = [
  "zero-dagric-telemetry",
  "no-dagric-account",
  "familiar-start-menu",
  "encryption-and-btrfs",
  "updates-without-forced-restarts",
  "seven-desktop-layouts",
  "windows-apps-with-bottles",
  "gaming-tools",
  "creator-toolkit",
  "developer-stack",
  "human-support",
  "secure-boot",
  "debian-kde-foundation",
];

const selectedTopics = dailyFillSlugs.map((slug) => {
  const topic = topics.find((candidate) => candidate.slug === slug);
  if (!topic) throw new Error(`Missing daily-fill topic: ${slug}`);
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
    // These calendar fillers are caption-led. Leaving narration out avoids
    // publishing a voice track before its commercial-use provenance record is
    // attached to the release audit.
    voiceFile: undefined,
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
    narrated: false,
    resolution: "1080x1920",
    file: filename,
  });
  await writeFile(
    path.join(outputRoot, "manifest.json"),
    JSON.stringify({generatedAt: new Date().toISOString(), videos: manifest}, null, 2),
  );
  process.stdout.write(`[${index + 1}/${selectedTopics.length}] ${filename}\n`);
}

await writeFile(
  path.join(outputRoot, "README.md"),
  [
    "# Dagric OS daily-fill batch",
    "",
    "Thirteen final 1080×1920 caption-led videos selected from the audited social batch.",
    "",
    "- The review-cut label is removed.",
    "- Narration is intentionally omitted pending the voice provenance record.",
    "- These files fill launch-calendar gaps without repeating the twelve launch videos.",
    "",
  ].join("\n"),
);
