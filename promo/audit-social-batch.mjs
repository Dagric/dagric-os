import {mkdir, readFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderStill, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const manifest = JSON.parse(await readFile(path.join(here, "review-batch", "manifest.json"), "utf8"));
const topicBySlug = new Map(topics.map((topic) => [topic.slug, topic]));
const outputRoot = path.join(here, "review-batch", "_audit-frames");
const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});

let completed = 0;
for (const entry of manifest.videos) {
  const topic = topicBySlug.get(entry.topic);
  if (!topic) throw new Error(`Unknown topic in manifest: ${entry.topic}`);
  const inputProps = {
    ...topic,
    format: entry.format,
    durationSeconds: entry.durationSeconds,
    voiceFile: topic.voiceScript ? `narration-batch/${topic.slug}.wav` : undefined,
  };
  const composition = await selectComposition({serveUrl, id: "DagricSocialBatch", inputProps});
  const formatDir = path.join(outputRoot, entry.format);
  await mkdir(formatDir, {recursive: true});
  await renderStill({
    serveUrl,
    composition,
    output: path.join(formatDir, `${path.parse(entry.file).name}.jpg`),
    frame: Math.min(composition.durationInFrames - 1, Math.round(composition.durationInFrames * 0.58)),
    inputProps,
    imageFormat: "jpeg",
    jpegQuality: 86,
    overwrite: true,
  });
  completed += 1;
  process.stdout.write(`[${completed}/${manifest.total}] ${entry.file}\n`);
}
