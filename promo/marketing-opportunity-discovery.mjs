// Pure discovery classification: fetched text is evidence to review, never permission
// to enter a contest, accept terms, or represent Dagric as release-ready.
export const DISCOVERY_BLOCKED_STATUS = "Blocked — current manual review and release/website acceptance required";

function plainText(html = "") {
  return html.replace(/<[^>]+>/g, " ").replace(/&nbsp;/gi, " ").replace(/\s+/g, " ").trim();
}

export function textHeuristics(html = "") {
  const plain = plainText(html).toLowerCase();
  return {
    freeWordFound: /\bfree\b/.test(plain),
    freeEntryPhraseFound: /\b(?:no (?:entry|application|submission) fees?|free (?:to (?:enter|submit|list|launch|apply)|entry|submission)|submission is free of charge)\b/.test(plain),
    submissionLanguageFound: /\bsubmit\b|add (your )?(product|startup|project|tool)|launch your|apply now|applications? open/.test(plain),
    relevanceLanguageFound: /software|startup|product|developer|open.source|technology|desktop app|project/.test(plain),
    // Deliberately retain this signal even alongside a contradictory "free" claim.
    feeRiskPhraseFound: /entry fees?|required fees?|purchase.{0,80}pass|paid submission|(?:ticket|pass|membership).{0,60}(?:required|mandatory)/.test(plain),
    rightsRiskPhraseFound: /assign[^.]{0,80}(ownership|rights)|exclusive[^.]{0,80}licen[cs]e|transfer[^.]{0,80}(copyright|ownership)|irrevocable[^.]{0,80}sublicen[cs]able|(?:equity|convertible note)/.test(plain),
    currentOpenPhraseFound: /applications? (are )?open|submissions? (are )?open|apply now|submit now|launch now|add your/.test(plain),
    closedPhraseFound: /applications? (?:are )?(?:officially )?closed|submissions? (?:are )?closed|deadline (?:has )?passed/.test(plain),
  };
}

function fetchFacts(page, requestedUrl, checkedAtUtc) {
  return {
    requestedUrl: requestedUrl || "",
    resolvedUrl: page?.url || requestedUrl || "",
    fetchSucceeded: page?.ok === true,
    httpStatus: page?.status ?? 0,
    fetchedAtUtc: page?.fetchedAtUtc || checkedAtUtc,
    error: page?.error || null,
  };
}

export function assessDiscovery(item, pages, checkedAtUtc = new Date().toISOString()) {
  const { home, submit, terms, submitUrl = "", termsUrl = "", aboutUrl = "", socialUrls = [] } = pages;
  const pageSignals = textHeuristics(`${home?.text || ""}\n${submit?.text || ""}`);
  const termsSignals = textHeuristics(terms?.text || "");
  const termsFetchStatus = !termsUrl ? "not_found" : terms?.ok === true && plainText(terms.text) ? "fetched_unreviewed" : "fetch_failed_or_empty";
  const hasSubmissionRoute = Boolean(submitUrl);
  const blockers = ["current_manual_review_required", "release_acceptance_required", "website_acceptance_required"];
  const reasons = ["Discovery only: current manual rules review and explicit release/website acceptance are required"];
  if (!home?.ok) reasons.push(`site unavailable (${home?.status || home?.error || "unknown"})`);
  if (!pageSignals.relevanceLanguageFound) reasons.push("no clear software/startup relevance language found");
  if (!pageSignals.submissionLanguageFound || !hasSubmissionRoute) reasons.push("submission route or submission language not found");
  if (!pageSignals.freeEntryPhraseFound) reasons.push("no specific free-entry phrase found; a generic free keyword is not entry-cost evidence");
  if (pageSignals.feeRiskPhraseFound || termsSignals.feeRiskPhraseFound) reasons.push("possible fee/pass requirement found; review exact current costs");
  if (pageSignals.rightsRiskPhraseFound || termsSignals.rightsRiskPhraseFound) reasons.push("possible license/ownership/equity condition found");
  if (pageSignals.closedPhraseFound) reasons.push("closed-application language found; current dates must be checked");
  if (termsFetchStatus !== "fetched_unreviewed") {
    blockers.push("terms_unavailable");
    reasons.push("terms unavailable or empty; rights and obligations remain unknown");
  } else {
    reasons.push("terms text fetched but not reviewed; absence of risk keywords is not clearance");
  }
  const reviewPriorityScore = Math.max(0,
    Number(home?.ok === true) * 3 + Number(hasSubmissionRoute) * 2 +
    Number(pageSignals.relevanceLanguageFound) * 2 + Number(pageSignals.freeEntryPhraseFound) +
    Number(termsFetchStatus === "fetched_unreviewed") - Number(pageSignals.closedPhraseFound) * 2 -
    Number(pageSignals.feeRiskPhraseFound || termsSignals.feeRiskPhraseFound) * 2 -
    Number(pageSignals.rightsRiskPhraseFound || termsSignals.rightsRiskPhraseFound) * 2);
  return {
    ...item,
    auditMode: "discovery-only",
    // Legacy URL field retained for consumers; it is not an authenticity judgment.
    officialUrl: home?.url || item.url,
    httpStatus: home?.status ?? 0,
    submitUrl: submit?.url || submitUrl,
    termsUrl,
    aboutUrl,
    socialUrls,
    sourceFacts: {
      home: fetchFacts(home, item.url, checkedAtUtc),
      submission: fetchFacts(submit, submitUrl, checkedAtUtc),
      terms: fetchFacts(terms, termsUrl, checkedAtUtc),
    },
    heuristics: { page: pageSignals, terms: termsSignals, hasSubmissionRoute },
    termsFetchStatus,
    reviewPriorityScore,
    rankingMeaning: "Heuristic manual-review priority only; not authenticity, eligibility, or submission clearance",
    // Fail closed for older consumers that still read these fields.
    officialFree: null,
    currentOpen: null,
    rightsRisk: null,
    verified: false,
    eligible: false,
    submissionAuthorized: false,
    verificationStatus: "unverified",
    eligibilityStatus: "not_assessed",
    currentDatesStatus: "not_reviewed",
    entryCostStatus: "not_reviewed",
    termsReviewStatus: "not_reviewed",
    releaseAcceptanceStatus: "not_confirmed",
    websiteAcceptanceStatus: "not_confirmed",
    blockers,
    status: DISCOVERY_BLOCKED_STATUS,
    auditReason: reasons.join("; "),
    checkedAtUtc,
  };
}

export function annotateHistoricalReview(opportunity, review) {
  return {
    ...opportunity,
    ...(review ? { manualReview: review, manualReviewIsHistorical: true } : {}),
    // A legacy decision, including "submit", carries no current authority.
    verified: false,
    eligible: false,
    submissionAuthorized: false,
    status: DISCOVERY_BLOCKED_STATUS,
  };
}

export function compareDiscoveryPriority(a, b) {
  return (b.reviewPriorityScore || 0) - (a.reviewPriorityScore || 0) || (b.dr || 0) - (a.dr || 0);
}
