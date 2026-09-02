import {execFile} from "node:child_process";
import {mkdir, readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {promisify} from "node:util";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, renderStill, selectComposition} from "@remotion/renderer";

const execFileAsync = promisify(execFile);
const here = path.dirname(fileURLToPath(import.meta.url));
const delivery = String.raw`C:\Users\1248n\Downloads\Dagric OS Videos`;
const sourceRoot = path.join(delivery, "Narrated Replacements");
const outputRoot = path.join(delivery, "Editorial Samples");
const visualRoot = path.join(outputRoot, "_visual-masters");
const stillRoot = path.join(outputRoot, "_review-frames");
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const narration = JSON.parse(await readFile(path.join(sourceRoot, "narration-manifest.json"), "utf8"));

const findTopic = (slug) => {
  const topic = topics.find((candidate) => candidate.slug === slug);
  if (!topic) throw new Error(`Missing topic: ${slug}`);
  return topic;
};

const productSamples = [
  {slug: "windows-10-pc-still-works", batch: "launch"},
  {slug: "check-this-pc", batch: "launch"},
  {slug: "dagric-hub", batch: "launch"},
  {slug: "pro-one-time-purchase", batch: "launch"},
  {slug: "signed-release-proof", batch: "launch"},
].map(({slug, batch}) => ({props: {...findTopic(slug), format: "vertical", reviewCut: false, voiceFile: undefined}, batch, topic: slug}));

const engagementRecord = narration.videos.find((video) => video.topic === "engagement-01");
if (!engagementRecord) throw new Error("Missing engagement-01 narration record");
const engagementHeadline = engagementRecord.title.replace(/\s*\|\s*Dagric OS\s*$/, "");
const communitySample = {
  batch: "second",
  topic: "engagement-01",
  props: {
    ...findTopic("dagric-hub"),
    slug: "engagement-01",
    category: "Community",
    kicker: "Your turn",
    headline: engagementHeadline,
    body: "Tell us what you want Dagric to test next. Specific hardware and app names help.",
    cta: "Leave a real question.",
    durationSeconds: 10,
    style: "question",
    accent: "teal",
    format: "vertical",
    reviewCut: false,
    voiceFile: undefined,
  },
};

const samples = [...productSamples, communitySample];
await mkdir(visualRoot, {recursive: true});
await mkdir(stillRoot, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});
const manifest = [];

for (let index = 0; index < samples.length; index++) {
  const sample = samples[index];
  const sourceAudioRecord = sample.topic === "engagement-01"
    ? engagementRecord
    : narration.videos.find((video) => video.batch === sample.batch && video.topic === sample.topic);
  if (!sourceAudioRecord) throw new Error(`Missing narration for ${sample.topic}`);

  const composition = await selectComposition({serveUrl, id: "DagricEditorialBatch", inputProps: sample.props});
  const number = String(index + 1).padStart(2, "0");
  const filename = `${number}-${sample.topic}-editorial-sample.mp4`;
  const visual = path.join(visualRoot, filename);
  const output = path.join(outputRoot, filename);

  await renderMedia({
    serveUrl,
    composition,
    codec: "h264",
    outputLocation: visual,
    inputProps: sample.props,
    scale: 1.5,
    crf: 18,
    imageFormat: "png",
    concurrency: 3,
    overwrite: true,
  });

  await execFileAsync("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y",
    "-i", visual,
    "-i", sourceAudioRecord.output,
    "-map", "0:v:0", "-map", "1:a:0",
    "-c:v", "copy", "-c:a", "copy",
    "-t", String(sample.props.durationSeconds),
    "-movflags", "+faststart",
    "-metadata", "title=Dagric OS human-directed editorial sample",
    "-metadata", "comment=Synthetic narration retained from the licensed local audio master; visual direction rebuilt in Remotion",
    output,
  ]);

  for (const [label, fraction] of [["hook", 0.18], ["body", 0.58], ["outro", 0.88]]) {
    await renderStill({
      serveUrl,
      composition,
      output: path.join(stillRoot, `${number}-${sample.topic}-${label}.jpg`),
      frame: Math.min(composition.durationInFrames - 1, Math.round(composition.durationInFrames * fraction)),
      inputProps: sample.props,
      imageFormat: "jpeg",
      jpegQuality: 92,
      scale: 1.5,
      overwrite: true,
    });
  }

  manifest.push({
    number: index + 1,
    topic: sample.topic,
    mode: sample.props.style,
    durationSeconds: sample.props.durationSeconds,
    file: output,
    narrationSource: sourceAudioRecord.output,
  });
  process.stdout.write(`[${index + 1}/${samples.length}] ${filename}\n`);
}

await writeFile(path.join(outputRoot, "sample-manifest.json"), JSON.stringify({generatedAt: new Date().toISOString(), videos: manifest}, null, 2));
await writeFile(path.join(outputRoot, "README.md"), [
  "# Dagric editorial redesign samples",
  "",
  "Six complete vertical samples covering statement, workflow, real-UI demo, comparison, proof, and community formats.",
  "",
  "These replace the one-template visual approach with topic-specific editorial structures. Synthetic narration remains truthfully identified in file metadata; the distracting on-screen AI badge is removed.",
  "",
].join("\n"));
