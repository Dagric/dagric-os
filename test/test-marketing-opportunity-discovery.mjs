import assert from "node:assert/strict";
import test from "node:test";
import { assessDiscovery, annotateHistoricalReview, compareDiscoveryPriority, DISCOVERY_BLOCKED_STATUS } from "../promo/marketing-opportunity-discovery.mjs";

// Pure in-memory fixtures: these tests never fetch, crawl, or write audit/log files.
const checkedAt = "2026-09-05T19:00:00.000Z";
const item = { name: "Example software award", url: "https://example.invalid/award", dr: 30, cost: "free" };
const page = (text, url) => ({ ok: true, status: 200, url, text });
function fixture(text = "Software award. Free to enter. Applications are open. Submit now.") {
  return {
    home: page(text, item.url),
    submit: page("Submit your software project.", "https://example.invalid/apply"),
    terms: page("Rules for this year's competition.", "https://example.invalid/rules"),
    submitUrl: "https://example.invalid/apply",
    termsUrl: "https://example.invalid/rules",
    aboutUrl: "https://example.invalid/history",
    socialUrls: ["https://example.invalid/social"],
  };
}
function assertBlocked(result) {
  assert.equal(result.auditMode, "discovery-only");
  assert.equal(result.verified, false);
  assert.equal(result.eligible, false);
  assert.equal(result.submissionAuthorized, false);
  assert.equal(result.officialFree, null);
  assert.equal(result.currentOpen, null);
  assert.equal(result.rightsRisk, null);
  assert.equal(result.status, DISCOVERY_BLOCKED_STATUS);
  assert.equal(result.termsReviewStatus, "not_reviewed");
  assert.equal(result.entryCostStatus, "not_reviewed");
  assert.equal(result.currentDatesStatus, "not_reviewed");
  assert.equal(result.releaseAcceptanceStatus, "not_confirmed");
  assert.equal(result.websiteAcceptanceStatus, "not_confirmed");
  assert.ok(result.blockers.includes("current_manual_review_required"));
  assert.ok(result.blockers.includes("release_acceptance_required"));
  assert.ok(result.blockers.includes("website_acceptance_required"));
}

test("free software language and a paid entry never imply free entry or eligibility", () => {
  const result = assessDiscovery(item, fixture("An award for free software. Submit your project. Entry fee $150; purchase a pass."), checkedAt);
  assertBlocked(result);
  assert.equal(result.heuristics.page.freeWordFound, true);
  assert.equal(result.heuristics.page.freeEntryPhraseFound, false);
  assert.equal(result.heuristics.page.feeRiskPhraseFound, true);
  assert.equal(result.cost, "free", "preserve the discovery directory's claim without endorsing it");
});

test("failed terms fetch preserves unknown rights, rather than treating empty text as safe", () => {
  const pages = fixture();
  pages.terms = { ok: false, status: 503, url: pages.termsUrl, text: "", error: "Service unavailable" };
  const result = assessDiscovery(item, pages, checkedAt);
  assertBlocked(result);
  assert.equal(result.termsFetchStatus, "fetch_failed_or_empty");
  assert.ok(result.blockers.includes("terms_unavailable"));
  assert.equal(result.sourceFacts.terms.httpStatus, 503);
  assert.equal(result.sourceFacts.terms.error, "Service unavailable");
  assert.match(result.auditReason, /rights and obligations remain unknown/);
});

test("plausible free-entry page with terms and an application route remains discovery only", () => {
  const pages = fixture();
  const result = assessDiscovery(item, pages, checkedAt);
  assertBlocked(result);
  assert.equal(result.heuristics.page.freeEntryPhraseFound, true);
  assert.equal(result.heuristics.page.currentOpenPhraseFound, true);
  assert.equal(result.heuristics.hasSubmissionRoute, true);
  assert.equal(result.termsFetchStatus, "fetched_unreviewed");
  assert.equal(result.sourceFacts.home.resolvedUrl, item.url);
  assert.deepEqual(result.socialUrls, pages.socialUrls);
  assert.equal(result.aboutUrl, pages.aboutUrl);
  assert.equal(result.checkedAtUtc, checkedAt);
  assert.ok(result.reviewPriorityScore > 0);
});

test("an old submit override is historical annotation and cannot authorize submission", () => {
  const opportunity = assessDiscovery(item, fixture(), checkedAt);
  const review = { name: item.name, decision: "submit", reason: "Looked free in 2025", reviewedAtUtc: "2025-04-01T00:00:00Z", verified: true, eligible: true };
  const result = annotateHistoricalReview(opportunity, review);
  assertBlocked(result);
  assert.deepEqual(result.manualReview, review);
  assert.equal(result.manualReviewIsHistorical, true);
  assert.equal(result.auditReason, opportunity.auditReason, "legacy reasoning must not replace current blockers");
  assert.equal(result.reviewPriorityScore, opportunity.reviewPriorityScore);
  assert.equal(opportunity.manualReview, undefined, "do not mutate input or history");
});

test("missing and empty terms are both unavailable even when homepage contains no risk keywords", () => {
  for (const termsUrl of ["", "https://example.invalid/terms"]) {
    const pages = fixture();
    pages.termsUrl = termsUrl;
    pages.terms = page("  <div> </div>  ", termsUrl);
    const result = assessDiscovery(item, pages, checkedAt);
    assertBlocked(result);
    assert.ok(result.blockers.includes("terms_unavailable"));
  }
});

test("conflicting free/open and paid/closed claims are retained as separate heuristic signals", () => {
  const result = assessDiscovery(item, fixture("Software startups: free to apply, but a pass is required. Apply now. Applications are closed."), checkedAt);
  assertBlocked(result);
  assert.equal(result.heuristics.page.freeEntryPhraseFound, true);
  assert.equal(result.heuristics.page.feeRiskPhraseFound, true);
  assert.equal(result.heuristics.page.currentOpenPhraseFound, true);
  assert.equal(result.heuristics.page.closedPhraseFound, true);
});

test("equity or other rights language is flagged but never treated as a legal determination", () => {
  const pages = fixture();
  pages.terms.text = "The prize is an equity investment or convertible note.";
  const result = assessDiscovery(item, pages, checkedAt);
  assertBlocked(result);
  assert.equal(result.heuristics.terms.rightsRiskPhraseFound, true);
  assert.equal(result.rightsRisk, null);
});

test("failed homepage remains blocked and retains HTTP/source facts", () => {
  const pages = fixture();
  pages.home = { ok: false, status: 403, text: "", url: item.url };
  const result = assessDiscovery(item, pages, checkedAt);
  assertBlocked(result);
  assert.equal(result.httpStatus, 403);
  assert.equal(result.sourceFacts.home.fetchSucceeded, false);
});

test("manual-review ordering remains useful without sorting by eligibility", () => {
  const goodLead = assessDiscovery(item, fixture(), checkedAt);
  const paidLead = assessDiscovery({ ...item, dr: 100 }, fixture("Software. Submit now. Entry fee $150; purchase a pass."), checkedAt);
  const ranked = [paidLead, goodLead].sort(compareDiscoveryPriority);
  assert.equal(ranked[0], goodLead);
  ranked.forEach(assertBlocked);
});

test("preexisting candidate clearance fields cannot leak into discovery output", () => {
  const result = assessDiscovery({ ...item, eligible: true, verified: true, submissionAuthorized: true, officialFree: true, status: "submit" }, fixture(), checkedAt);
  assertBlocked(result);
});
