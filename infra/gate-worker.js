// Dagric OS — Pro download gate.
// Verifies a Stripe Checkout session is PAID and bought one of the Dagric Pro
// prices, then streams the ISO from a PRIVATE R2 bucket. Supports HTTP Range so
// the 3.3 GB download is resumable. Without a valid paid session: no file.
const FILE = "dagric-os-pro-1.0-amd64.iso";
// The layouts and styles the free image does not carry, for in-place upgrades.
// Same private bucket, same licence check, ~100 KB instead of 3.8 GB.
const ASSETS = "dagric-pro-assets.tar.gz";

// ── what was bought, and how many machines it covers ───────────────────────
// The allowance used to be the constant MACHINE_CAP = 1, which was true for as
// long as there was one thing to buy. There are now two: single Pro, and the
// Family Pack, which is the same Pro on several computers in one household.
// So the number has to come from WHAT WAS BOUGHT. The Stripe lookup below
// already expands line_items, so the price id of the purchased item is sitting
// in the answer we are already fetching; this table is the only place that
// turns it into a number of machines.
//
// ONE TABLE ANSWERS BOTH QUESTIONS, ON PURPOSE:
//   1. Is this a Dagric Pro purchase at all?  -> is the price id a key here
//   2. How many machines does it cover?       -> the value
// They were about to become two lists — one deciding who gets in, one deciding
// how many — and two lists that must agree are two lists that eventually will
// not. A price present in the gate but missing from the caps table would take
// the fallback and quietly sell a Family Pack as a single; a price in the caps
// table but missing from the gate would be a paid customer told their purchase
// does not exist. Neither can happen while there is one table.
//
// ── PRICE IDS ARE THE OWNER'S TO CREATE. NOTHING HERE MAY BE GUESSED. ──
// PRICE_PRO_SINGLE below is NOT a new value: it is the live id carried over
// verbatim from the constant this block replaces, and it is what every $39
// checkout on the site resolves to today. It is left intact deliberately —
// blanking a working production id during a refactor would reject every real
// purchase until somebody noticed. Confirm it against the Stripe dashboard
// before deploying anyway.
//
// PRICE_FAMILY_PACK IS A PLACEHOLDER AND CANNOT WORK UNTIL IT IS REPLACED.
// It is not a Stripe id, it is not shaped like one, and no live session will
// ever match it. The owner creates the Family Pack price in Stripe and pastes
// its id here.
//
// CREATE THE FAMILY PACK LINK WITH ADJUSTABLE QUANTITY *OFF*. Quantity is
// ignored here on purpose -- the cap is a max over the prices bought, never a
// sum -- so with adjustable quantity on, a buyer who sets 2 pays twice and
// still gets one household's worth, and someone who buys five of the SINGLE
// price in one checkout pays five times and gets ONE machine. Both are refunds.
// Stripe remembers this setting when you clone a payment link, so it is easy to
// inherit without noticing.
//
// ORDER OF OPERATIONS, AND IT MATTERS: create the price in Stripe -> paste the
// id here -> deploy this worker -> and only THEN publish the Family Pack link
// on the site. Publish first and a family buyer matches no known price and
// gets the ordinary "no completed Dagric OS Pro purchase" 403: loud, on the
// very first buyer, which is the right direction for a mistake to fail, but it
// is still somebody who paid and cannot download.
const PRICE_PRO_SINGLE = "price_1TwRxY6lZx4VOIr30Zvozvhb";
const PRICE_FAMILY_PACK = "REPLACE_ME_family_pack_price_id_from_stripe";

// The machines each price covers. FAMILY_MACHINES is also the number the page
// promises, so the two move together or the page is lying — grep the site for
// it before changing it here.
// SET ME. This is a placeholder exactly like the price id above, and for the
// same reason: the comment above says "grep the site for it before changing it",
// and grepping the site today finds FAMILY_MACHINES_PLACEHOLDER, not a number.
// A constant that has silently committed to 5 while the page has committed to
// nothing cannot be kept in sync by any procedure. Left at 0 it throws below, so
// a half-finished wiring-up fails at deploy instead of quietly selling five
// machines for the price of one.
const FAMILY_MACHINES = 0;
const MACHINE_CAPS = {
  [PRICE_PRO_SINGLE]: 1,
  [PRICE_FAMILY_PACK]: FAMILY_MACHINES,
};

// THE PASTE ERROR THIS CATCHES IS THE MOST LIKELY ONE THERE IS. MACHINE_CAPS is
// an object literal with computed keys: paste the same Stripe id into both
// constants and the second key silently overwrites the first, so every single
// -licence $39 buyer is handed the family allowance. No error, no log, nothing
// in any test. A module-scope throw fails the DEPLOY, which is the only party
// that should ever be inconvenienced by a configuration mistake.
if (
  PRICE_FAMILY_PACK === PRICE_PRO_SINGLE ||
  Object.keys(MACHINE_CAPS).length !== 2 ||
  !Number.isInteger(FAMILY_MACHINES) ||
  FAMILY_MACHINES < 2
) {
  throw new Error(
    "MACHINE_CAPS misconfigured: two DISTINCT Stripe price ids are required, " +
      "and FAMILY_MACHINES must be an integer of at least 2 and must equal the " +
      "number printed on site/family.html."
  );
}

// A LOOKUP MISS FALLS BACK TO ONE MACHINE, NEVER TO THE FAMILY NUMBER. Missing
// line_items, an unrecognised price id, a shape Stripe changed under us, a
// typo'd table value — every one of them resolves to 1, the smallest allowance
// anybody could have paid for. The asymmetry is the whole point: a cap that
// comes out too small is a support email that takes a minute to fix, and a cap
// that comes out too big is a $39 licence quietly behaving like the household
// one, on machines we will never hear about and cannot take back. This is the
// one number in this file where being generous costs the sale instead of
// protecting the customer, so it is the one number that fails small.
const MACHINE_CAP_FALLBACK = 1;

// ── the licence allowance ──────────────────────────────────────────────────
// A purchase upgrades the machines it paid for and no more. Machines are
// identified by an anonymous fingerprint the upgrade tool sends as `m`: a
// SHA-256 of the machine's DMI product UUID salted with the session id, so
// the value is meaningless outside this one purchase and never a raw serial.
// Re-runs and reinstalls on the SAME machine hash to the same value and are
// always free; a machine beyond the allowance gets a 409 with a support
// pointer. The machine entitlement is the ONLY thing here worth gating — see
// the block in fetch().
//
// The byte and fetch budgets are BANDWIDTH protection for a free-software
// payload, not licensing. The ISO budget meters bytes delivered per session so
// that Range tricks cannot pull unlimited copies; the legacy fetch budget
// covers pre-fingerprint tools. Both are generous enough that no honest
// customer meets them across years of reinstalls, and both are backstops to a
// Cloudflare rate-limit rule (declared at deploy) — because a plain KV counter
// cannot hard-stop a deliberate parallel burst on its own. The ISO budget is
// per session and stays flat: a five-machine household pulling five 3.3 GB
// copies is 16.5 GB against a 110 GB ceiling, nowhere near it.
//
// EVERY KV FAILURE FAILS OPEN, including a missing binding. The allowance is
// abuse control, not billing: our storage having a bad minute must never lock
// out a paying customer.
//
// FAILING OPEN ON STORAGE IS NOT FAILING OPEN ON ENTITLEMENT, and the two get
// confused precisely because they live in the same functions. Storage failing
// open means: KV cannot tell us which machines are already using this purchase,
// so let this machine through rather than accuse a customer of something our
// database cannot actually establish. Entitlement failing open would mean:
// we could not tell what was bought, so assume the bigger purchase. The first
// is the posture of this whole file and is preserved below unchanged. The
// second has never been the posture and must not become it. The cap is not
// read from KV at all — it comes from Stripe's answer about the line item, and
// when that answer is unusable the cap is 1, not FAMILY_MACHINES.
const ISO_BYTE_BUDGET = 110 * 1024 * 1024 * 1024; // ~26 Pro ISOs / 50 free
// Per MACHINE, not per purchase: fifteen successful pulls is five full
// 3-attempt runs, which was one machine's worth of bad-network evenings when
// one machine was all a purchase could have. A household with five machines on
// pre-fingerprint tools would otherwise share one machine's budget between
// five and hit a licence-shaped 409 for what is only a bandwidth backstop.
const LEGACY_ASSET_CAP_PER_MACHINE = 15;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const sid = url.searchParams.get("session_id") || "";
    if (!/^cs_[A-Za-z0-9_]{8,}$/.test(sid)) {
      return msg(400, "Missing or malformed session. Use the download link from your purchase page.");
    }

    // Ask Stripe about this checkout session (server-side; key never leaves).
    const look = await getSession(sid, env);
    // Only Stripe saying "no such session" may accuse the customer. Anything we
    // could not interpret (outage, rate limit, our own broken key) must NOT tell
    // a paying customer their purchase doesn't exist — this link is bookmarked
    // and re-used long after checkout, so a Stripe incident would otherwise
    // deny every legitimate buyer with the most alarming message we have.
    if (look.missing) return msg(403, "Unknown purchase session.");
    if (!look.session) {
      return msg(
        503,
        "We can't reach Stripe to confirm your purchase right now — your purchase is fine. " +
          "Please retry in a minute; this link keeps working.",
        { "Retry-After": "30", "Cache-Control": "no-store" }
      );
    }
    const s = look.session;

    const paid = s.payment_status === "paid";
    const items = (s.line_items && s.line_items.data) || [];
    // What was bought decides both whether this is Pro and how many machines it
    // covers. See MACHINE_CAPS: an unknown or missing price id yields cap 1.
    const bought = machinesAllowed(items);
    if (!paid || !bought.isPro) {
      return msg(403, "This session has no completed Dagric OS Pro purchase.");
    }
    const cap = bought.cap;

    // Refund check — FAIL-OPEN: only block on POSITIVE evidence of a refund, so
    // a paying customer is never wrongly locked out if Stripe's shape shifts.
    const charge = s.payment_intent && s.payment_intent.latest_charge;
    const refunded =
      charge && (charge.refunded === true || Number(charge.amount_refunded) > 0);
    if (refunded) {
      return msg(
        403,
        "This purchase was refunded, so Pro downloads and support have ended. " +
          "The copy you already downloaded is yours to keep and run, and it keeps " +
          "receiving updates. You're welcome to re-purchase anytime."
      );
    }

    // ── the machine entitlement ─────────────────────────────────────────────
    // The upgrade tool sends `m`, an anonymous per-purchase fingerprint. A
    // browser downloading the ISO never does — `m` present means the tool is
    // asking.
    //
    // WHAT IS ACTUALLY WORTH GATING. Everything the upgrade installs is Debian
    // main — free software anyone can already download — and the one Dagric
    // asset it fetches is a ~190 KB tarball a buyer can trivially re-host. So
    // neither the ISO stream nor the tarball is where a shared code costs a
    // sale: the machine ENTITLEMENT is. A purchase upgrades the number of
    // machines it paid for — one, or the household number for a Family Pack —
    // and moving a slot is a Stripe-bound support action nobody can share. That
    // is the control this block enforces; the byte budgets below are bandwidth
    // protection, not licensing.
    //
    // `cap` is threaded into every one of these calls rather than read from a
    // constant inside them. The functions below have no other way to know what
    // was bought — they see a session id and a hash, not a line item — so a
    // helper that quietly defaulted would be a helper that quietly decided the
    // licence.
    //
    // THE SLOT COMMITS AT /assets, NOT HERE. The tool HEADs first (a dry
    // validation — the point where `--check` or a declined consent stops), then
    // GETs /assets only after the owner says yes. Reserving on HEAD would burn
    // a slot on an evaluation the owner walked away from — the whole licence
    // when the purchase covers one — so HEAD only READS: it turns away a machine
    // the purchase has no room for and reserves nothing.
    const m = url.searchParams.get("m") || "";
    const mValid = /^[a-f0-9]{64}$/.test(m);
    if (m && !mValid) {
      return msg(400, "Malformed request. Update Dagric and run the upgrade again.");
    }
    if (req.method === "HEAD" && mValid) {
      const held = await machineState(sid, m, cap, env);
      if (held === "other") return machineTaken(cap);
      // "mine" | "free" | "unknown" all pass — the reservation is at /assets,
      // and a dry HEAD must never be the thing that consumes the slot.
      return new Response(null, { status: 200, headers: { "Cache-Control": "no-store" } });
    }

    // ---------------------------------------------------------------------
    // /assets — the same licence, a much smaller payload.
    //
    // dagric-upgrade-to-pro turns an installed free machine into a Pro one
    // without a reinstall. Almost everything it needs is in Debian main and
    // needs no permission from us; the exception is the four Plasma layouts and
    // three colour styles, which the free ISO DELETES at build time rather than
    // hiding behind a flag, because a flag is one line of text to edit.
    //
    // So this is the one thing an upgrade has to ask for, and it asks with the
    // licence it already has. Everything above this line — the session shape,
    // the Stripe lookup, paid, the right price, refunded — has already run and
    // applies unchanged. A tarball of a few hundred kilobytes is the entire
    // difference between having paid and not.
    //
    // Deliberately NOT Range-aware, unlike the ISO below: it is small enough
    // that a failed fetch is cheaper to repeat than to resume, and the upgrade
    // tool is safe to re-run.
    if (url.pathname.replace(/\/+$/, "") === "/assets") {
      // Commit the machine slot HERE — the owner has committed to the upgrade.
      if (mValid) {
        const slot = await reserveMachine(sid, m, cap, env);
        if (slot === "other") return machineTaken(cap);
        // "ok" | "unknown" pass (fail open).
      } else {
        // Fielded tools predate the fingerprint. A generous per-session fetch
        // budget stands in — fifteen SUCCESSFUL pulls is five full 3-attempt
        // runs, enough for one machine's bad-network evenings and useless as a
        // shared link for a 190 KB tarball. Read-only here; charged only after
        // a real delivery below, because counting our own failures (a client
        // retries three times a run) burned the whole allowance in two bad
        // evenings. Remove when the fielded ISOs are all m-aware.
        //
        // SCALED BY THE CAP, because without a fingerprint this counter is the
        // only thing standing between a five-machine household and a 409 that
        // reads like a licence problem. It is not one: this budget is bandwidth
        // protection for a 190 KB tarball, and five machines legitimately need
        // five machines' worth of retries.
        const used = await readNum(`legacy:${sid}`, env);
        // BOUNDED, because this branch counts nothing per machine. There is no
        // fingerprint here, so nothing is reserved and nothing is attributed:
        // scaling a shared counter by the cap means a leaked Family Pack code
        // upgrades cap x 15 machines, not 15. The scaling is still right --
        // five machines legitimately need five machines' worth of retries --
        // but it is capped at three machines' worth so the widening is bounded
        // rather than proportional. This whole branch exists only for ISOs
        // already in the field that do not send a fingerprint, and it should be
        // DELETED once those are gone; that is the real fix.
        const legacyBudget = LEGACY_ASSET_CAP_PER_MACHINE * Math.min(cap, 3);
        if (used !== null && used >= legacyBudget) {
          return msg(
            409,
            "This purchase has reached its upgrade allowance. It covers " +
              coversPhrase(cap) +
              " — dagric.com/support can help if these are your machines and " +
              "something kept retrying."
          );
        }
      }
      const a = await env.PRO.get(ASSETS);
      if (!a) {
        return msg(
          503,
          "The Pro extras are temporarily unavailable. Your purchase is fine, and " +
            "the upgrade will have stopped without changing anything on your " +
            "machine — please run it again in a few minutes.",
          { "Retry-After": "60", "Cache-Control": "no-store" }
        );
      }
      if (!mValid) await bumpNum(`legacy:${sid}`, env); // charge on delivery only
      return new Response(a.body, {
        headers: {
          "Content-Type": "application/gzip",
          "Content-Length": String(a.size),
          "Cache-Control": "no-store",
        },
      });
    }

    // A plain HEAD (no fingerprint — a download manager sizing the file) falls
    // through to here and gets real headers; Cloudflare serves it bodyless.

    // Paid — stream the ISO from the private bucket, honoring Range.
    const range = parseRange(req.headers.get("Range"));

    // BANDWIDTH BUDGET, not a licence check: the ISO is free software, so a cap
    // on it protects egress, not a sale. Meter BYTES DELIVERED per session
    // against a generous ceiling, so range gymnastics buy nothing — a resumed
    // download totals about one ISO no matter how it is chunked or where it
    // resumes. (The earlier "count starts" form let `Range: bytes=1-` stream an
    // unlimited, uncounted near-complete tail — the whole cap was a mirage.)
    // Checked here on the running tally; charged AFTER serving, so a client
    // abort is never double-billed. KV read-modify-write is not atomic, so a
    // deliberate parallel burst can overshoot this — the route's Cloudflare
    // rate-limit rule (see wrangler.toml) is the real throttle; this is the
    // backstop, and it protects a payload that is free anyway.
    if (req.method === "GET") {
      const usedBytes = await readNum(`bytes:${sid}`, env);
      if (usedBytes !== null && usedBytes > ISO_BYTE_BUDGET) {
        return msg(
          409,
          "This download link has moved far more data than one customer needs, " +
            "so it has been paused. If it's really you, dagric.com/support will " +
            "sort it out quickly."
        );
      }
    }
    const obj = range
      ? await env.PRO.get(FILE, { range })
      : await env.PRO.get(FILE);

    // A range that starts at or past the end of the file is NOT a server fault:
    // download managers routinely probe with `Range: bytes=<size>-` to confirm a
    // finished download is complete. R2 returns null for that, which used to be
    // reported as 500 "File temporarily unavailable" — telling a customer whose
    // download actually succeeded that something broke. The correct answer is
    // 416 with the real size, which every client understands as "already done".
    if (!obj && range) {
      const head = await env.PRO.head(FILE);
      if (head) {
        return new Response(null, {
          status: 416,
          headers: {
            "Content-Range": `bytes */${head.size}`,
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
          },
        });
      }
    }
    if (!obj) return msg(500, "File temporarily unavailable — try again shortly.");

    const headers = {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="${FILE}"`,
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-store",
    };
    if (range) {
      // Announce what R2 ACTUALLY returned, not what was asked for. A client may
      // request more bytes than exist (`bytes=0-99999999999`); R2 clamps the body
      // but the requested length would make Content-Length promise data that is
      // never sent, leaving the download hanging until it times out.
      const off = (obj.range && obj.range.offset != null) ? obj.range.offset : range.offset;
      const len = (obj.range && obj.range.length != null)
        ? obj.range.length
        : obj.size - off;
      headers["Content-Range"] = `bytes ${off}-${off + len - 1}/${obj.size}`;
      headers["Content-Length"] = String(len);
      if (req.method === "GET") await addNum(`bytes:${sid}`, len, env);
      return new Response(obj.body, { status: 206, headers });
    }
    headers["Content-Length"] = String(obj.size);
    if (req.method === "GET") await addNum(`bytes:${sid}`, obj.size, env);
    return new Response(obj.body, { status: 200, headers });
  },
};

// Look up the checkout session. Expand the charge too so we can see if the
// purchase was later REFUNDED — a refunded session still reports payment_status
// "paid", so checking that alone would let a refunded buyer keep re-downloading.
// Returns { session } on success, { missing: true } only when Stripe positively
// says the session does not exist, and { transient: true } for everything else.
// ── the allowance store ─────────────────────────────────────────────────────
// Cloudflare KV, bound as LICENSE. EVERY helper FAILS OPEN: any storage error
// (including the binding being absent) returns the "no opinion" value —
// "unknown" / null — and the request proceeds. Abuse control must never become
// the thing that locks out a paying customer. KV is eventually consistent and
// read-modify-write is not atomic, so a deliberate parallel burst can overshoot
// any cap here; that is the Cloudflare rate-limit rule's job, and these are the
// backstop for a payload (free-software ISO, re-hostable tarball) whose worst
// case is wasted egress, not a lost sale.
function readRec(raw) {
  try { return raw ? JSON.parse(raw) : { machines: [] }; }
  catch { return { machines: [] }; } // corrupt value → treat as empty, fail open
}

// How many machines did this checkout buy? Returns { isPro, cap }.
//
// isPro is the same question the gate has always asked — does a line item carry
// a price id we sell Pro under — so nothing gets looser here: a session that
// bought something else, or nothing we recognise, is still not a Pro purchase.
// cap is the new part, and it is deliberately conservative in every direction:
//
//   * No known price id in the session -> isPro false, and cap is the fallback
//     rather than 0 or undefined, so a caller that ignores isPro (a future one;
//     there is none today) still cannot be handed a number bigger than one.
//   * A table value that is not a sane count — a typo, a string, a zero — is
//     skipped rather than trusted. A malformed entry must not become a licence.
//   * hasOwnProperty, not `in` or a bare lookup: price ids arrive from Stripe
//     as strings and a bare `MACHINE_CAPS[id]` would happily find "constructor"
//     on the prototype chain and treat a function as a machine count.
//   * QUANTITY IS IGNORED ON PURPOSE. Two Family Packs in one checkout grant
//     the household number, not twice it. Reading quantity would be the more
//     literal answer, but it is the one place where a shape we misread hands
//     out more than was paid for, and buying two packs at once is a support
//     conversation that happens roughly never. Under-granting is fixable by a
//     human in a minute; over-granting is not fixable at all.
//   * Several known prices in one session -> the largest, not the sum. Somebody
//     who bought a single and a family in one go has a family's worth of
//     machines, which is what they would get if they had checked out twice.
function machinesAllowed(items) {
  let isPro = false;
  let cap = MACHINE_CAP_FALLBACK;
  for (const li of items || []) {
    const id = li && li.price && li.price.id;
    if (typeof id !== "string") continue;
    if (!Object.prototype.hasOwnProperty.call(MACHINE_CAPS, id)) continue;
    const n = MACHINE_CAPS[id];
    if (typeof n !== "number" || !Number.isFinite(n) || n < 1) continue;
    const seats = Math.floor(n);
    if (!isPro) {
      isPro = true;
      cap = seats;
    } else if (seats > cap) {
      cap = seats;
    }
  }
  return { isPro, cap };
}

// "one machine" / "5 machines". One helper because this phrase is user-facing
// in two places and they were about to disagree with each other.
function coversPhrase(cap) {
  return cap === 1 ? "one machine" : `${cap} machines`;
}

// Read-only: does a machine hold one of this purchase's slots? Used by HEAD so
// a dry validation reserves nothing. "mine" | "other" | "free" | "unknown".
//
// `cap` is a parameter, not a constant read from module scope, because this
// function cannot see the purchase — it has a session id and a hash. The old
// version closed over MACHINE_CAP = 1 and was correct only for as long as there
// was one thing to buy; a Family Pack would have been told its second machine
// belonged to somebody else. Callers pass what Stripe said was bought.
async function machineState(sid, m, cap, env) {
  try {
    const rec = readRec(await env.LICENSE.get(`act:${sid}`));
    if (rec.machines.some((x) => x.h === m)) return "mine";
    if (rec.machines.length >= cap) return "other";
    return "free";
  } catch {
    // STORAGE failing open, not entitlement: we could not find out which
    // machines are in use, which is never grounds to accuse a paying customer.
    // The cap itself is not stored here and is unaffected by this catch.
    return "unknown";
  }
}

// Commit this machine's slot. "ok" (mine or newly reserved) | "other" (the
// purchase's slots are all held by other machines) | "unknown" (KV trouble).
// `cap` comes from the purchase — see machineState above.
async function reserveMachine(sid, m, cap, env) {
  try {
    const key = `act:${sid}`;
    const rec = readRec(await env.LICENSE.get(key));
    const now = Date.now();
    const mine = rec.machines.find((x) => x.h === m);
    if (mine) {
      mine.last = now;
      await env.LICENSE.put(key, JSON.stringify(rec));
      return "ok";
    }
    if (rec.machines.length >= cap) return "other";
    rec.machines.push({ h: m, first: now, last: now });
    await env.LICENSE.put(key, JSON.stringify(rec));
    return "ok";
  } catch {
    return "unknown";
  }
}

// The one 409 a machine over its entitlement gets, worded once. The tool maps
// 409 to its own "already upgrading a different machine" message; a browser
// never reaches this (it sends no `m`).
//
// IT MUST STATE THE REAL NUMBER. This text used to assert "One purchase covers
// one machine" from a constant, which stops being true the moment a Family Pack
// exists — and the customer reading it is by definition the one who just hit
// the limit, so telling a household of five that they bought one machine is
// both wrong and the worst possible moment to be wrong. The number here is the
// number Stripe says they paid for.
function machineTaken(cap) {
  if (cap === 1) {
    return msg(
      409,
      "This purchase is already upgrading a different machine. One purchase " +
        "covers one machine — dagric.com/support can move it to this one " +
        "(a machine that was replaced or a virtual machine that moved counts), " +
        "or you can buy a second licence for a second machine."
    );
  }
  return msg(
    409,
    `This purchase already covers ${cap} machines, and all ${cap} slots are ` +
      "in use by other computers. dagric.com/support can move a slot to this " +
      "machine (a machine that was replaced or a virtual machine that moved " +
      "counts), or you can buy another licence for more machines."
  );
}

// Numeric-counter helpers. readNum returns the value or null (fail open);
// bumpNum adds one, addNum adds n. All swallow storage errors.
async function readNum(key, env) {
  try { return Number((await env.LICENSE.get(key)) || 0); }
  catch { return null; }
}
async function bumpNum(key, env) { return addNum(key, 1, env); }
async function addNum(key, n, env) {
  try {
    const v = Number((await env.LICENSE.get(key)) || 0) + n;
    await env.LICENSE.put(key, String(v));
    return v;
  } catch {
    return null;
  }
}

async function getSession(sid, env) {
  // STRIPE_API_BASE exists for the test harness only; production never sets
  // it and talks to Stripe.
  const base = (env && env.STRIPE_API_BASE) || "https://api.stripe.com";
  const url =
    `${base}/v1/checkout/sessions/${sid}` +
    `?expand[]=line_items&expand[]=payment_intent.latest_charge`;
  for (let attempt = 0; ; attempt++) {
    let res = null;
    try {
      res = await fetch(url, { headers: { Authorization: `Bearer ${env.STRIPE_KEY}` } });
    } catch {
      /* network failure — retryable */
    }
    if (res && res.ok) {
      try {
        return { session: await res.json() };
      } catch {
        /* unparseable body — retryable */
      }
    } else if (res && res.status === 404) {
      return { missing: true }; // definitive: no such session
    } else if (res && res.status < 500 && res.status !== 429) {
      // 400/401/403 = a bad expand param or a broken key: OUR misconfiguration,
      // never the buyer's fault, and retrying will not help.
      return { transient: true };
    }
    if (attempt >= 1) return { transient: true };
    await new Promise((r) => setTimeout(r, 300)); // one short backoff for 429/5xx
  }
}

function parseRange(h) {
  if (!h) return null;
  const m = /^bytes=(\d+)-(\d*)$/.exec(h.trim());
  if (!m) return null;
  const offset = Number(m[1]);
  const end = m[2] === "" ? null : Number(m[2]);
  if (end !== null && end < offset) return null;
  return end === null ? { offset } : { offset, length: end - offset + 1 };
}

// The ERROR page only. A paid session never reaches this function: the success
// path above returns the ISO body with Content-Type application/octet-stream and
// a Content-Disposition attachment, and renders no HTML at all. msg() fires on
// 400/403/500/503 — an expired link, a session that is not paid, R2 unavailable.
//
// TWO THINGS WERE WRONG HERE AND ONLY ONE OF THEM WAS COSMETIC.
//
// 1. THE RECOVERY LINK WAS DEAD. It pointed at https://dagric-os.web.app/#pro:
//    the superseded Firebase hostname (dagric-os.web.app serves a byte-identical
//    copy of dagric.com and carries <link rel="canonical" href="https://dagric.com/">),
//    and a #pro fragment that exists on neither host — the only ids on either are
//    download, main, pricing, tbl-compare-editions, tbl-windows-equivalents. Pro
//    is a page, /pro, not an anchor. So the one link offered to a customer whose
//    download just failed landed them on the wrong hostname at the top of the
//    homepage. Now https://dagric.com/pro.
//
// 2. THE PALETTE WAS THE PRE-REDESIGN ONE. #0a111c / #e8eef6 / #3fa9f5 and a
//    #59c2e8->#2f7fd1 gradient wordmark, against Daybook's --ink-0 #0C0F14,
//    --paper #F5F2EB, --accent #7CB8EC and a Georgia display face. Contrast was
//    never the problem and is not now. Both versions were rendered from this
//    template and measured in a browser, not estimated:
//      new, on #0C0F14: wordmark #F5F2EB 17.17:1, body #C0C8D4 11.38:1,
//                       link #7CB8EC 9.07:1
//      old, on #0a111c: gradient stops 9.29:1 and 4.57:1 (44px/800, large
//                       text), body #9db1c8 8.61:1, link #3fa9f5 7.39:1
//    Nothing was failing; nothing is failing. This was a brand fix.
//
//    The old markup also had no viewport meta, so its layout viewport measured
//    980px in a 320px window — a phone rendered it zoomed out. With the meta
//    and the margin reset it now measures scrollWidth 320 = clientWidth 320.
//
//    DO NOT set the wordmark to --accent-deep #14487A. That token is a FILL
//    (it is the only fill on the site that carries #fff text, at 9.38:1); as
//    text on #0C0F14 it measures 2.05:1, under the 3:1 large-text floor. The
//    Daybook wordmark is .brand{color:var(--on)} = --paper. It is a flat colour
//    rather than a clipped gradient for the same reason the rest of the site
//    dropped .grad: background-clip:text with color:transparent renders nothing
//    at all wherever it is unsupported, so the failure mode is an invisible
//    product name on an error page.
//
// lang="en" and a viewport meta are here because this page has neither a
// stylesheet nor a nav to inherit them from.
function msg(status, text, extra) {
  const body = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Dagric OS</title>
<body style="background:#0C0F14;color:#C0C8D4;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;margin:0;padding:24px">
<div><div style="font-size:44px;font-weight:500;letter-spacing:-.012em;color:#F5F2EB;font-family:Georgia,'Iowan Old Style','Palatino Linotype','Source Serif 4','Noto Serif','Liberation Serif',serif">Dagric OS</div>
<p style="color:#C0C8D4;max-width:420px">${text}</p>
<p><a style="color:#7CB8EC" href="https://dagric.com/pro">Get Dagric Pro</a></p></div>`;
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8", ...extra },
  });
}
