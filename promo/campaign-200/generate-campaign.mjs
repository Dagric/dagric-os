import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const promoDir = path.resolve(here, "..");
const topics = JSON.parse(fs.readFileSync(path.join(promoDir, "social-batch.json"), "utf8"));

const angles = [
  {
    id: "plain-answer",
    label: "Plain answer",
    opener: (t) => `${t.category}: here is the plain answer.`,
    direction: "Lead with the answer, show the matching Dagric screen, and end on the documented next step.",
  },
  {
    id: "show-the-screen",
    label: "Show the screen",
    opener: (t) => `Do not take our word for it—look at ${t.category.toLowerCase()} on the actual desktop.`,
    direction: "Use a tight product-screen recording with two callouts; keep the cursor slow and the labels readable.",
  },
  {
    id: "before-you-switch",
    label: "Before you switch",
    opener: (t) => `Before you switch a PC, check this: ${t.kicker.toLowerCase()}.`,
    direction: "Frame the clip as one precaution a cautious owner can complete before changing a disk or buying Pro.",
  },
  {
    id: "three-point-check",
    label: "Three-point check",
    opener: (t) => `Three things to verify about ${t.category.toLowerCase()}.`,
    direction: "Present three short, evidence-based checkpoints; the final checkpoint must point to the site or live USB.",
  },
  {
    id: "claim-and-proof",
    label: "Claim and proof",
    opener: (t) => `${t.headline} Here is the proof path.`,
    direction: "Put the qualified claim on screen, then show the relevant UI, guide, manifest, or policy page that supports it.",
  },
  {
    id: "common-question",
    label: "Common question",
    opener: (t) => `A common Dagric question: ${t.headline.toLowerCase()}`,
    direction: "Use an on-screen question, a direct answer, and one limitation or condition so the answer stays trustworthy.",
  },
  {
    id: "decision-guide",
    label: "Decision guide",
    opener: (t) => `Is this the right choice for your PC? Start with ${t.category.toLowerCase()}.`,
    direction: "Give a yes/no decision rule and tell viewers how to test their own machine instead of promising universal compatibility.",
  },
  {
    id: "owner-story",
    label: "Owner story",
    opener: (t) => `Imagine this is the PC you already own. ${t.kicker}.`,
    direction: "Use a simple owner scenario, avoid testimonials or invented outcomes, and finish with a concrete action the viewer can take.",
  },
];

const durationPattern = [12, 18, 24, 30, 15, 21, 27, 36];
const platforms = ["TikTok", "Instagram Reels", "YouTube Shorts", "Snapchat Spotlight"];
const toolCycle = {
  "TikTok": ["Buffer", "Later", "Publer"],
  "Instagram Reels": ["Later", "Publer", "Buffer"],
  "YouTube Shorts": ["Publer", "Buffer", "Later"],
  "Snapchat Spotlight": ["Later"],
};
const tags = {
  "TikTok": "#DagricOS #Linux #PC",
  "Instagram Reels": "#DagricOS #LinuxDesktop #PC",
  "YouTube Shorts": "#DagricOS #Linux #Shorts",
  "Snapchat Spotlight": "#DagricOS #Linux",
};

function clipText(value, max) {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1).trimEnd()}…`;
}

function nextSlot(platform, after) {
  const date = new Date(after);
  const rules = {
    "TikTok": { day: 0, hour: 9 },
    "Instagram Reels": { day: 3, hour: 18 },
    "YouTube Shorts": { day: 5, hour: 16 },
    "Snapchat Spotlight": { day: 2, hour: 20 },
  };
  const rule = rules[platform];
  date.setHours(rule.hour, 0, 0, 0);
  const distance = (rule.day - date.getDay() + 7) % 7;
  date.setDate(date.getDate() + distance);
  if (date <= after) date.setDate(date.getDate() + 7);
  return date;
}

const counters = Object.fromEntries(platforms.map((p) => [p, 0]));
const nextDates = {
  "TikTok": new Date("2026-09-27T09:00:00-05:00"),
  "Instagram Reels": new Date("2026-09-30T18:00:00-05:00"),
  "YouTube Shorts": new Date("2026-10-02T16:00:00-05:00"),
  "Snapchat Spotlight": new Date("2026-09-29T20:00:00-05:00"),
};

const items = [];
for (let topicIndex = 0; topicIndex < topics.length; topicIndex += 1) {
  const topic = topics[topicIndex];
  for (let angleIndex = 0; angleIndex < angles.length; angleIndex += 1) {
    const angle = angles[angleIndex];
    const idNumber = items.length + 1;
    const platform = platforms[(idNumber - 1) % platforms.length];
    const toolOptions = toolCycle[platform];
    const scheduler = toolOptions[counters[platform] % toolOptions.length];
    counters[platform] += 1;
    const publishAt = nextDates[platform];
    nextDates[platform] = nextSlot(platform, publishAt);
    const durationSeconds = durationPattern[(topicIndex + angleIndex) % durationPattern.length];
    const opener = angle.opener(topic);
    const qualifiedBody = topic.body;
    const voiceover = `${opener} ${qualifiedBody} ${topic.cta}.`;
    const angleLead = `${angle.label}: ${opener}`;
    const caption = clipText(`${angleLead} ${topic.headline} ${qualifiedBody} ${topic.cta}: https://dagric.com ${tags[platform]}`, platform === "Snapchat Spotlight" ? 160 : 1000);

    items.push({
      id: `DGR-${String(idNumber).padStart(3, "0")}`,
      slug: `${topic.slug}-${angle.id}`,
      status: "SCRIPTED_NOT_RENDERED",
      sourceTopic: topic.slug,
      category: topic.category,
      angle: angle.label,
      durationSeconds,
      masterFormat: "1080x1920 MP4, 9:16, 30fps",
      audio: angleIndex % 3 === 0 ? "original voiceover; no music" : "caption-led; optional platform-cleared commercial audio",
      title: clipText(`${topic.headline} — ${angle.label}`, 100),
      hook: opener,
      productionDirection: angle.direction,
      onScreenBeats: [
        `0–3s: ${opener}`,
        `3–${Math.max(8, durationSeconds - 5)}s: ${qualifiedBody}`,
        `${Math.max(8, durationSeconds - 5)}–${durationSeconds}s: ${topic.cta} · dagric.com`,
      ],
      voiceover,
      caption,
      imageReference: topic.image,
      platform,
      scheduler,
      publishAtAmericaChicago: publishAt.toLocaleString("sv-SE", { timeZone: "America/Chicago" }).replace(" ", "T"),
      rightsNotes: "Use only Dagric-owned product captures and branding. No downloaded music. Third-party names are descriptive; no affiliation or endorsement implied.",
      claimSafety: "Keep the exact qualification in the source topic. Do not imply universal hardware/app compatibility or vendor endorsement.",
    });
  }
}

const slugs = new Set(items.map((item) => item.slug));
const captions = new Set(items.map((item) => item.caption));
if (items.length !== 200 || slugs.size !== 200 || captions.size !== 200) {
  throw new Error(`Deduplication failed: ${items.length} items, ${slugs.size} slugs, ${captions.size} captions`);
}

const scheduleOrder = [...items].sort((a, b) => a.publishAtAmericaChicago.localeCompare(b.publishAtAmericaChicago));
for (let i = 1; i < scheduleOrder.length; i += 1) {
  const previous = new Date(scheduleOrder[i - 1].publishAtAmericaChicago);
  const current = new Date(scheduleOrder[i].publishAtAmericaChicago);
  const hours = (current - previous) / 3_600_000;
  if (hours < 12) {
    throw new Error(`Schedule spacing failed between ${scheduleOrder[i - 1].id} and ${scheduleOrder[i].id}: ${hours} hours`);
  }
}

fs.mkdirSync(here, { recursive: true });
fs.writeFileSync(path.join(here, "campaign.json"), `${JSON.stringify({ timezone: "America/Chicago", generatedAt: new Date().toISOString(), count: items.length, items }, null, 2)}\n`);

const csvColumns = ["id", "status", "slug", "platform", "scheduler", "publishAtAmericaChicago", "durationSeconds", "title", "caption"];
const csv = [csvColumns.join(","), ...scheduleOrder.map((item) => csvColumns.map((column) => `"${String(item[column]).replaceAll('"', '""')}"`).join(","))].join("\n");
fs.writeFileSync(path.join(here, "master-schedule.csv"), `${csv}\n`);

for (const scheduler of ["Buffer", "Later", "Publer"]) {
  const rows = scheduleOrder.filter((item) => item.scheduler === scheduler);
  const schedulerCsv = [csvColumns.join(","), ...rows.map((item) => csvColumns.map((column) => `"${String(item[column]).replaceAll('"', '""')}"`).join(","))].join("\n");
  fs.writeFileSync(path.join(here, `${scheduler.toLowerCase()}-queue.csv`), `${schedulerCsv}\n`);
}

const counts = {};
for (const item of items) {
  counts[item.scheduler] ??= {};
  counts[item.scheduler][item.platform] = (counts[item.scheduler][item.platform] ?? 0) + 1;
}

const readme = `# Dagric 200-video campaign\n\nThis folder is the deduplicated production and publishing ledger for 200 **unique scripted videos**. The rows are production briefs, not finished MP4 files. Every item remains \`SCRIPTED_NOT_RENDERED\` until a human-reviewed final export exists.\n\n## Guardrails\n\n- One unique master concept per ID; no repeated caption or slug.\n- One scheduler owns each post. Do not copy a row into a second scheduler.\n- The master calendar leaves at least 12 hours between every two planned posts.\n- Times are in America/Chicago.\n- Use only Dagric-owned captures/branding and original narration. Do not import trending audio unless the platform explicitly clears it for commercial use.\n- Do not schedule review-batch MP4s; they contain a review-only label and are only 720-based proofs.\n- Scheduler free-tier limits require rolling uploads. Buffer and Publer each allow only 10 queued posts per connected account; Later currently allows 12 posts per profile per month on this workspace.\n- Publer does not support Snapchat, so all Snapchat rows stay in Later.\n\n## Research-based baseline slots\n\n- TikTok: Sunday 9:00 AM.\n- Instagram Reels: Wednesday 6:00 PM.\n- YouTube Shorts: Friday 4:00 PM.\n- Snapchat Spotlight: Tuesday 8:00 PM as an initial test slot; replace it with account analytics after enough posts.\n\n## Files\n\n- \`campaign.json\`: all scripts, shot directions, captions, rights notes, and ownership.\n- \`master-schedule.csv\`: chronological deduplicated plan.\n- \`buffer-queue.csv\`, \`later-queue.csv\`, \`publer-queue.csv\`: scheduler-specific imports/working lists.\n\n## Allocation\n\n\`\`\`json\n${JSON.stringify(counts, null, 2)}\n\`\`\`\n`;
fs.writeFileSync(path.join(here, "README.md"), readme);

console.log(JSON.stringify({ count: items.length, uniqueSlugs: slugs.size, uniqueCaptions: captions.size, counts }, null, 2));
