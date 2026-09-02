import {readFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const slug = process.env.DAGRIC_BATCH_TOPIC;

if (!slug) {
  throw new Error("Set DAGRIC_BATCH_TOPIC to the topic slug to rebuild.");
}

const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const manifestPath = path.join(here, "review-batch", "manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const topic = topics.find((candidate) => candidate.slug === slug);
const targets = manifest.videos.filter((video) => video.topic === slug);

if (!topic) throw new Error(`Unknown social topic: ${slug}`);
if (targets.length === 0) throw new Error(`No rendered videos found for: ${slug}`);

const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});

for (const target of targets) {
  const inputProps = {
    ...topic,
    format: target.format,
    durationSeconds: target.durationSeconds,
    voiceFile: topic.voiceScript ? `narration-batch/${topic.slug}.wav` : undefined,
  };
  const composition = await selectComposition({serveUrl, id: "DagricSocialBatch", inputProps});
  const outputLocation = path.join(here, "review-batch", target.file);
  await renderMedia({
    serveUrl,
    composition,
    codec: "h264",
    outputLocation,
    inputProps,
    crf: 24,
    imageFormat: "jpeg",
    jpegQuality: 82,
    concurrency: 3,
    overwrite: true,
  });
  process.stdout.write(`Rebuilt ${target.file}\n`);
}
