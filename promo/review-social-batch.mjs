import {mkdir, readFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderStill, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const output = path.join(here, "review-batch", "_review-stills");
await mkdir(output, {recursive: true});

const formatExtra = {landscape: 2, square: 1, portrait: 2, vertical: 0};
const samples = [
  {topic: 0, format: "vertical"},
  {topic: 3, format: "square"},
  {topic: 5, format: "landscape"},
  {topic: 7, format: "portrait"},
  {topic: 8, format: "vertical"},
  {topic: 14, format: "square"},
  {topic: 20, format: "portrait"},
  {topic: 24, format: "landscape"},
];

const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});
for (const sample of samples) {
  const topic = topics[sample.topic];
  const durationSeconds = topic.durationSeconds + formatExtra[sample.format];
  const inputProps = {
    ...topic,
    format: sample.format,
    durationSeconds,
    voiceFile: topic.voiceScript ? `narration-batch/${topic.slug}.wav` : undefined,
  };
  const composition = await selectComposition({serveUrl, id: "DagricSocialBatch", inputProps});
  const number = String(sample.topic + 1).padStart(2, "0");
  for (const [label, fraction] of [["intro", 0.18], ["proof", 0.58], ["outro", 0.88]]) {
    await renderStill({
      serveUrl,
      composition,
      output: path.join(output, `${number}-${topic.slug}-${sample.format}-${label}.jpg`),
      frame: Math.min(composition.durationInFrames - 1, Math.round(composition.durationInFrames * fraction)),
      inputProps,
      imageFormat: "jpeg",
      jpegQuality: 90,
      overwrite: true,
    });
  }
}
