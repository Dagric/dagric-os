import {readFile, writeFile} from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const downloads = "C:/Users/1248n/Downloads/Dagric OS Videos";
const launch = JSON.parse(await readFile(path.join(here, "launch-batch", "schedule.json"), "utf8"));
const dailyFill = JSON.parse(await readFile(path.join(here, "daily-fill-batch", "september-2026-daily-buffer-plan.json"), "utf8"));
const secondWave = JSON.parse(await readFile(path.join(here, "second-wave-batch", "second-wave-plan.json"), "utf8"));

const channelName = {
  youtube: "YouTube",
  instagram: "Instagram",
  tiktok: "TikTok",
  snapchat: "Snapchat",
};

const rows = [];
const add = (row) => rows.push(row);
const launchAsset = (post) => path.join(here, "launch-batch", post.file).replaceAll("\\", "/");

for (const post of launch.posts.slice(0, 10)) {
  add({
    dateTime: post.publishAt,
    scheduler: "Buffer",
    platforms: "YouTube; Instagram; TikTok",
    slot: "First",
    status: "Scheduled",
    title: post.youtubeTitle,
    caption: post.caption,
    asset: launchAsset(post),
    tag: "Launch campaign",
  });
}

for (const post of launch.posts.slice(10, 12)) {
  add({
    dateTime: post.publishAt,
    scheduler: "Buffer",
    platforms: "YouTube",
    slot: "First",
    status: "Scheduled",
    title: post.youtubeTitle,
    caption: post.caption,
    asset: launchAsset(post),
    tag: post.topic === "measured-accessibility" ? "Trust and proof" : "Pricing and conversion",
  });
}

for (const post of dailyFill) {
  add({
    dateTime: post.date,
    scheduler: "Buffer",
    platforms: post.channels.map((channel) => channelName[channel]).join("; "),
    slot: "First",
    status: "Scheduled",
    title: post.title,
    caption: post.caption,
    asset: post.video,
    tag: post.tag,
  });
}

const measured = launch.posts[10];
const upgrade = launch.posts[11];
const publerRows = [
  {
    dateTime: "2026-09-24T06:00:00-05:00",
    platforms: "TikTok",
    title: measured.youtubeTitle,
    caption: "Accessibility should be measured, not promised. Dagric publishes what is supported, partially supported, and still limited. Read the report: https://dagric.com #DagricOS #Accessibility #Linux",
    asset: launchAsset(measured),
    tag: "Trust and proof",
  },
  {
    dateTime: "2026-09-24T18:00:00-05:00",
    platforms: "Instagram",
    title: upgrade.youtubeTitle,
    caption: "Start with Dagric Free and decide later. A Pro license upgrades through Dagric Hub while keeping your files and settings. Learn more: https://dagric.com #DagricOS #LinuxDesktop #PC",
    asset: launchAsset(upgrade),
    tag: "Pricing and conversion",
  },
  {
    dateTime: "2026-09-25T06:00:00-05:00",
    platforms: "TikTok",
    title: upgrade.youtubeTitle,
    caption: "Start with Dagric Free and decide later. A Pro license upgrades through Dagric Hub while keeping your files and settings. Learn more: https://dagric.com #DagricOS #LinuxDesktop #PC",
    asset: launchAsset(upgrade),
    tag: "Pricing and conversion",
  },
  {
    dateTime: "2026-09-25T18:00:00-05:00",
    platforms: "YouTube",
    title: "Dagric OS Live-VM Desktop Tour",
    caption: "See Dagric OS running in a real VM: launch apps, open settings, and explore the KDE desktop from the live ISO. This is test footage—not a render. Learn more: https://dagric.com #DagricOS #Linux #KDE",
    asset: `${downloads}/Source Footage/dagric-clean-apps-settings-source.mp4`,
    tag: "Trust and proof",
  },
];

for (const post of publerRows) {
  add({...post, scheduler: "Publer", slot: "First", status: "Scheduled"});
}

for (const post of secondWave) {
  add({
    dateTime: post.date,
    scheduler: "Buffer",
    platforms: post.channels.map((channel) => channelName[channel]).join("; "),
    slot: post.slot === "second" ? "Second" : "Third",
    status: "Scheduled",
    title: post.title,
    caption: post.caption,
    asset: post.video,
    tag: post.tag,
  });
}

const snapchatTimes = [
  "2026-09-02T20:15:00-05:00",
  "2026-09-04T08:15:00-05:00",
  "2026-09-06T08:15:00-05:00",
  "2026-09-07T06:00:00-05:00",
  "2026-09-09T08:15:00-05:00",
  "2026-09-11T08:15:00-05:00",
  "2026-09-13T08:15:00-05:00",
  "2026-09-14T06:00:00-05:00",
  "2026-09-16T08:15:00-05:00",
  "2026-09-18T08:15:00-05:00",
  "2026-09-20T08:15:00-05:00",
];

for (let index = 0; index < snapchatTimes.length; index++) {
  const post = launch.posts[index];
  add({
    dateTime: snapchatTimes[index],
    scheduler: "Later",
    platforms: "Snapchat",
    slot: "Snapchat",
    status: "Scheduled",
    title: post.youtubeTitle,
    caption: post.caption,
    asset: launchAsset(post),
    tag: "Snapchat Spotlight",
  });
}

rows.sort((a, b) => a.dateTime.localeCompare(b.dateTime) || a.scheduler.localeCompare(b.scheduler) || a.title.localeCompare(b.title));

const parts = (dateTime) => {
  const date = new Date(dateTime);
  return {
    date: new Intl.DateTimeFormat("en-US", {month: "short", day: "numeric", year: "numeric", timeZone: "America/Chicago"}).format(date),
    time: new Intl.DateTimeFormat("en-US", {hour: "numeric", minute: "2-digit", timeZone: "America/Chicago"}).format(date),
  };
};

const csvEscape = (value) => `"${String(value).replaceAll('"', '""')}"`;
const csvHeaders = ["Date", "Time", "Scheduler", "Platforms", "Slot", "Status", "Title", "Caption", "Campaign tag", "Asset"];
const csv = [
  csvHeaders.map(csvEscape).join(","),
  ...rows.map((row) => {
    const when = parts(row.dateTime);
    return [when.date, when.time, row.scheduler, row.platforms, row.slot, row.status, row.title, row.caption, row.tag, row.asset]
      .map(csvEscape)
      .join(",");
  }),
].join("\n");

const mdEscape = (value) => String(value).replaceAll("|", "\\|").replaceAll("\n", " ");
const markdown = [
  "# Dagric OS master social schedule — September 2026",
  "",
  "Live-audited August 31, 2026. Time zone: America/Chicago.",
  "",
  "- Feed plan: 219 channel posts — 73 each on YouTube, Instagram, and TikTok.",
  "- Publicly scheduled feed posts: 219 — 215 in Buffer and 4 in Publer.",
  "- Buffer now has every dated September post in its queue.",
  "- Unrelated undated Buffer drafts: 4; intentionally excluded from this schedule.",
  "- Snapchat: 11 scheduled Later posts with Auto Publish and Save to Profile enabled.",
  "- One older August 31 Snapchat draft is intentionally excluded.",
  "",
  "| Date | Time | Scheduler | Platforms | Slot | Status | Title | Tag |",
  "| --- | --- | --- | --- | --- | --- | --- | --- |",
  ...rows.map((row) => {
    const when = parts(row.dateTime);
    return `| ${when.date} | ${when.time} | ${mdEscape(row.scheduler)} | ${mdEscape(row.platforms)} | ${mdEscape(row.slot)} | ${mdEscape(row.status)} | ${mdEscape(row.title)} | ${mdEscape(row.tag)} |`;
  }),
  "",
  "Exact captions and absolute video paths are in the CSV companion file.",
  "",
].join("\n");

await writeFile(path.join(downloads, "September 2026 Master Social Schedule.csv"), csv, "utf8");
await writeFile(path.join(downloads, "September 2026 Master Social Schedule.md"), markdown, "utf8");

const channelPosts = rows
  .filter((row) => row.platforms !== "Snapchat")
  .reduce((total, row) => total + row.platforms.split("; ").length, 0);

process.stdout.write(JSON.stringify({rows: rows.length, channelPosts, snapchatRows: snapchatTimes.length}, null, 2));
