import fs from "node:fs/promises";
import path from "node:path";
import { assessDiscovery, annotateHistoricalReview, compareDiscoveryPriority } from "./marketing-opportunity-discovery.mjs";

const outputDir = process.argv[2] || path.resolve("outputs", "contest-marketing-audit");
const categories = ["launch", "startup", "saas", "community"];
const excludeDomains = new Set([
  "ahrefs.com", "wikipedia.org", "youtube.com", "pinterest.com", "reddit.com",
  "linkedin.com", "medium.com", "tumblr.com", "blogger.com", "wordpress.com",
  "github.com", "gitlab.com", "vimeo.com", "quora.com", "stackoverflow.com",
  "slideshare.net", "flickr.com", "behance.net", "dribbble.com", "patreon.com"
]);

const contestSeeds = [
  ["GatewayHacks 2026", "Hackathon", "https://gatewayhacks-2026.devpost.com/rules"],
  ["CodeLaunch USA 2026", "Pitch competition", "https://codelaunch.com/events/2026-usa/"],
  ["Global AI Builders Cup — United States", "Pitch competition", "https://aibuilderscup.com/united-states"],
  ["Snowflake Startup Challenge", "Pitch competition", "https://www.snowflake.com/en/startup-challenge/"],
  ["The Pitch by Deel", "Pitch competition", "https://www.deel.com/the-pitch-by-deel/"],
  ["SXSW Pitch 2027", "Pitch competition", "https://sxsw.com/pitch/"],
  ["Web Summit Rio PITCH 2027", "Pitch competition", "https://rio.websummit.com/en/startups/pitch/"],
  ["FMItech Pitch 2027", "Pitch competition", "https://www.fmi.org/industry-topics/technology/fmitech-pitch"],
  ["Slush 100", "Pitch competition", "https://slush.org/audience/startups/slush100"],
  ["Venture.ch 2027", "Pitch competition", "https://www.venture.ch/homepage-2027"],
  ["Hostinger 21-Day Startup Challenge", "Startup challenge", "https://www.hostingerchallenges.com/faq"],
  ["VivaTech Startup Challenges", "Innovation challenge", "https://vivatech.com/challenges"],
  ["Microsoft Imagine Cup", "Student competition", "https://imaginecup.microsoft.com/"],
  ["MIT Solve Global Challenges", "Social-impact challenge", "https://solve.mit.edu/challenges"],
  ["MassChallenge US Early Stage", "Accelerator competition", "https://masschallenge.org/programs-us-early-stage/"],
  ["43North", "Startup competition", "https://43north.org/"],
  ["Arch Grants Startup Competition", "Startup competition", "https://archgrants.org/competition/"],
  ["Startup World Cup", "Pitch competition", "https://www.startupworldcup.io/"],
  ["TechCrunch Startup Battlefield", "Startup competition", "https://techcrunch.com/startup-battlefield/"],
  ["Y Combinator", "Accelerator application", "https://www.ycombinator.com/apply"],
  ["Techstars Accelerators", "Accelerator application", "https://www.techstars.com/accelerators"],
  ["F6S Programs", "Accelerator directory", "https://www.f6s.com/programs"],
  ["NLnet Open Calls", "Open-source grant call", "https://nlnet.nl/propose/"],
  ["Prototype Fund", "Open-source funding call", "https://prototypefund.de/en/"],
  ["Free Software Awards", "Open-source award", "https://www.fsf.org/awards"],
  ["Linux Foundation Mentorship", "Open-source program", "https://mentorship.lfx.linuxfoundation.org/"],
  ["OpenSSF Community", "Open-source showcase", "https://openssf.org/community/"],
  ["FOSDEM Calls for Participation", "Open-source conference call", "https://fosdem.org/"],
  ["All Things Open Call for Papers", "Open-source conference call", "https://allthingsopen.org/call-for-papers"],
  ["SCaLE Call for Papers", "Open-source conference call", "https://www.socallinuxexpo.org/scale/"],
  ["Open Source Summit Call for Proposals", "Open-source conference call", "https://events.linuxfoundation.org/open-source-summit-north-america/program/cfp/"],
  ["DistroWatch Submit Distribution", "Linux distribution listing", "https://distrowatch.com/dwres.php?resource=submit"],
  ["AlternativeTo Add Application", "Software directory", "https://alternativeto.net/manage-item/"],
  ["SourceForge Create Project", "Open-source directory", "https://sourceforge.net/create/"],
  ["Open Hub Add Project", "Open-source directory", "https://openhub.net/projects/new"],
  ["Free Software Directory", "Open-source directory", "https://directory.fsf.org/wiki/Form:Entry"],
  ["Product Hunt Launch", "Product launch", "https://www.producthunt.com/posts/new"],
  ["Peerlist Launchpad", "Product launch", "https://peerlist.io/launchpad"],
  ["Hacker News Show HN", "Developer showcase", "https://news.ycombinator.com/showhn.html"],
  ["DEV Community", "Developer showcase", "https://dev.to/new"],
  ["HackerNoon Start Writing", "Technology publication", "https://hackernoon.com/new"],
  ["Lobsters Submit Story", "Developer community", "https://lobste.rs/stories/new"],
  ["Slashdot Submit Story", "Technology publication", "https://slashdot.org/submission"],
  ["Indie Hackers Product", "Founder community", "https://www.indiehackers.com/products/new"],
  ["Wellfound Company Profile", "Startup directory", "https://wellfound.com/recruit/overview"],
  ["Crunchbase Company Profile", "Company directory", "https://www.crunchbase.com/add-new"],
  ["StackShare Submit Stack", "Developer directory", "https://stackshare.io/submit"],
  ["SaaSHub Submit Product", "Software directory", "https://www.saashub.com/services/submit"],
  ["Capterra Vendor Listing", "Software directory", "https://www.capterra.com/vendors/sign-up"],
  ["G2 Seller Profile", "Software directory", "https://sell.g2.com/create-profile"],
];

function decode(value = "") {
  return value
    .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

async function fetchText(url, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: { "user-agent": "Mozilla/5.0 (compatible; DagricOpportunityAudit/1.0; +https://dagric.com)" }
    });
    const text = await response.text();
    return { ok: response.ok, status: response.status, url: response.url, text: text.slice(0, 120000), fetchedAtUtc: new Date().toISOString() };
  } catch (error) {
    return { ok: false, status: 0, url, text: "", error: String(error), fetchedAtUtc: new Date().toISOString() };
  } finally {
    clearTimeout(timer);
  }
}

function parseDirectoryPage(html, category) {
  const chunks = html.split('<div class="row">').slice(1);
  return chunks.map((chunk) => {
    const name = decode(chunk.match(/<a class="name"[^>]*>([\s\S]*?)<\/a>/)?.[1]);
    const domain = decode(chunk.match(/<span class="dom">([\s\S]*?)<\/span>/)?.[1]);
    const description = decode(chunk.match(/<p class="row-desc">([\s\S]*?)<\/p>/)?.[1]);
    const dr = Number(chunk.match(/title="Domain Rating (\d+)"/)?.[1] || 0);
    const cost = chunk.match(/<a class="chip (free|freemium|paid)"/)?.[1] || "unknown";
    return { name, domain, description, dr, cost, category, url: domain ? `https://${domain}` : "" };
  }).filter((item) => item.name && item.domain && !excludeDomains.has(item.domain));
}

function discoverLinks(html, baseUrl) {
  const links = [];
  for (const match of html.matchAll(/href=["']([^"'#]+)["']/gi)) {
    try {
      const url = new URL(match[1], baseUrl).toString();
      if (!links.includes(url)) links.push(url);
    } catch {}
  }
  return links;
}

function isSubmissionRoute(url) {
  try {
    const parsed = new URL(url);
    if (/\.(?:css|js|mjs|png|jpe?g|gif|svg|webp|woff2?|ico)(?:$|\?)/i.test(parsed.pathname + parsed.search)) return false;
    return /(?:^|[\/_-])(submit|submission|add-product|add-startup|create-project|new-product|launch|apply|register|signup)(?:$|[\/?#_-])/i.test(parsed.pathname + parsed.search);
  } catch {
    return false;
  }
}

async function auditOne(item) {
  const home = await fetchText(item.url);
  const links = discoverLinks(home.text, home.url || item.url);
  const submitUrl = links.find(isSubmissionRoute) || "";
  const termsUrl = links.find((url) => /terms|rules|conditions/i.test(url)) || "";
  const aboutUrl = links.find((url) => /about|company|history/i.test(url)) || "";
  const socialUrls = links.filter((url) => /linkedin\.com|x\.com|twitter\.com|instagram\.com|facebook\.com|youtube\.com|github\.com/i.test(url)).slice(0, 8);
  const submit = submitUrl && submitUrl !== home.url ? await fetchText(submitUrl, 8000) : { text: "", ok: false, status: 0, url: submitUrl };
  const terms = termsUrl ? await fetchText(termsUrl, 8000) : { text: "", ok: false, status: 0, url: termsUrl };
  return assessDiscovery(item, { home, submit, terms, submitUrl, termsUrl, aboutUrl, socialUrls });
}

await fs.mkdir(outputDir, { recursive: true });
let candidates = [];
for (const category of categories) {
  const page = await fetchText(`https://www.submission.directory/category/${category}`);
  candidates.push(...parseDirectoryPage(page.text, category));
}
for (const [name, category, url] of contestSeeds) {
  candidates.push({ name, category, url, domain: new URL(url).hostname, description: "Official opportunity seed", dr: null, cost: "unknown" });
}

const unique = [];
const seen = new Set();
for (const candidate of candidates) {
  const key = `${candidate.name.toLowerCase()}|${candidate.domain}`;
  if (seen.has(key)) continue;
  seen.add(key);
  unique.push(candidate);
}

const audited = [];
const concurrency = 8;
for (let index = 0; index < unique.length; index += concurrency) {
  const batch = unique.slice(index, index + concurrency);
  audited.push(...await Promise.all(batch.map(auditOne)));
  process.stdout.write(`audited ${Math.min(index + concurrency, unique.length)}/${unique.length}\n`);
}

let manualReviews = [];
try {
  const overrideDocument = JSON.parse(await fs.readFile(path.join(outputDir, "reviewed-overrides.json"), "utf8"));
  manualReviews = Array.isArray(overrideDocument.reviews) ? overrideDocument.reviews : [];
} catch {}

const reviewsByName = new Map(manualReviews.filter((review) => typeof review?.name === "string").map((review) => [review.name.toLowerCase(), review]));
for (let index = 0; index < audited.length; index++) {
  const opportunity = audited[index];
  const review = reviewsByName.get(opportunity.name.toLowerCase());
  audited[index] = annotateHistoricalReview(opportunity, review);
}

audited.sort(compareDiscoveryPriority);
await fs.writeFile(path.join(outputDir, "opportunities.json"), JSON.stringify({
  schema: "dagric-marketing-opportunity-discovery-v2",
  auditMode: "discovery-only",
  submissionAuthorized: false,
  notice: "Scraping and historical reviews do not verify organizers, entry costs, current deadlines, rights, or eligibility. Current manual review and explicit release/website acceptance are required before any submission.",
  generatedAtUtc: new Date().toISOString(),
  discoverySource: "https://www.submission.directory/ plus official contest/program sites",
  counts: {
    total: audited.length,
    eligible: 0,
    verified: 0,
    blockedPendingReviewAndAcceptance: audited.length,
    pagesFetched: audited.filter((x) => x.sourceFacts.home.fetchSucceeded).length,
    termsFetchedUnreviewed: audited.filter((x) => x.termsFetchStatus === "fetched_unreviewed").length,
    historicalReviews: audited.filter((x) => x.manualReviewIsHistorical).length,
  },
  opportunities: audited,
}, null, 2) + "\n");
console.log(JSON.stringify({ total: audited.length, eligible: audited.filter((x) => x.eligible).length, verified: audited.filter((x) => x.verified).length, outputDir }));
