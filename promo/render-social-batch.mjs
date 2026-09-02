import {mkdir, readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, renderStill, selectComposition} from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const topics = JSON.parse(await readFile(path.join(here, "social-batch.json"), "utf8"));
const outputRoot = path.join(here, "review-batch");
const formats = {
  landscape: {width: 1280, height: 720, extraSeconds: 2},
  square: {width: 720, height: 720, extraSeconds: 1},
  portrait: {width: 720, height: 900, extraSeconds: 2},
  vertical: {width: 720, height: 1280, extraSeconds: 0},
};
const topicLimit = Number.parseInt(process.env.DAGRIC_BATCH_LIMIT ?? "", 10);
const selectedTopics = Number.isFinite(topicLimit) ? topics.slice(0, topicLimit) : topics;
const selectedFormats = process.env.DAGRIC_BATCH_FORMAT
  ? Object.fromEntries(Object.entries(formats).filter(([name]) => name === process.env.DAGRIC_BATCH_FORMAT))
  : formats;

await mkdir(outputRoot, {recursive: true});
for (const format of Object.keys(selectedFormats)) await mkdir(path.join(outputRoot, format), {recursive: true});

const serveUrl = await bundle({entryPoint: path.join(here, "src", "index.ts")});
const manifest = [];
let completed = 0;
const total = selectedTopics.length * Object.keys(selectedFormats).length;

for (let topicIndex = 0; topicIndex < selectedTopics.length; topicIndex++) {
  const topic = selectedTopics[topicIndex];
  for (const [format, spec] of Object.entries(selectedFormats)) {
    const durationSeconds = topic.durationSeconds + spec.extraSeconds;
    const inputProps = {
      ...topic,
      format,
      durationSeconds,
      voiceFile: topic.voiceScript ? `narration-batch/${topic.slug}.wav` : undefined,
    };
    const composition = await selectComposition({serveUrl, id: "DagricSocialBatch", inputProps});
    const number = String(topicIndex + 1).padStart(2, "0");
    const filename = `${number}-${topic.slug}-${format}-${durationSeconds}s.mp4`;
    const outputLocation = path.join(outputRoot, format, filename);
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
    if (process.env.DAGRIC_BATCH_STILLS === "1") {
      const stillDir = path.join(outputRoot, "_review-stills");
      await mkdir(stillDir, {recursive: true});
      for (const [label, fraction] of [["intro", 0.18], ["proof", 0.58], ["outro", 0.88]]) {
        await renderStill({
          serveUrl,
          composition,
          output: path.join(stillDir, `${number}-${topic.slug}-${format}-${label}.jpg`),
          frame: Math.min(composition.durationInFrames - 1, Math.round(composition.durationInFrames * fraction)),
          inputProps,
          imageFormat: "jpeg",
          jpegQuality: 88,
          overwrite: true,
        });
      }
    }
    completed += 1;
    manifest.push({number: completed, topic: topic.slug, format, durationSeconds, narrated: Boolean(topic.voiceScript), file: path.relative(outputRoot, outputLocation)});
    await writeFile(path.join(outputRoot, "manifest.json"), JSON.stringify({generatedAt: new Date().toISOString(), completed, total, videos: manifest}, null, 2));
    process.stdout.write(`[${completed}/${total}] ${filename}\n`);
  }
}

await writeFile(path.join(outputRoot, "README.md"), [
  "# Dagric OS social video review batch",
  "",
  `Generated ${manifest.length} review MP4s across ${topics.length} topics.`,
  "",
  "These are review cuts and have not been uploaded or published. Choose finalists before any public post.",
  "",
  "- `landscape/`: 16:9 YouTube and web review cuts",
  "- `square/`: 1:1 feed cuts",
  "- `portrait/`: 4:5 feed cuts",
  "- `vertical/`: 9:16 Shorts, Reels, TikTok, and Snapchat cuts",
  "- `manifest.json`: exact topic, length, format, narration status, and filename",
  "",
].join("\n"));
