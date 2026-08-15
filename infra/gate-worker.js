// Dagric OS — Pro download gate.
// Verifies a Stripe Checkout session is PAID and bought the Dagric Pro price,
// then streams the ISO from a PRIVATE R2 bucket. Supports HTTP Range so the
// 3.3 GB download is resumable. Without a valid paid session: no file.
const PRICE_ID = "price_1TwRxY6lZx4VOIr30Zvozvhb";
const FILE = "dagric-os-pro-1.0-amd64.iso";
// The layouts and styles the free image does not carry, for in-place upgrades.
// Same private bucket, same licence check, ~100 KB instead of 3.8 GB.
const ASSETS = "dagric-pro-assets.tar.gz";

// ── the licence allowance ──────────────────────────────────────────────────
// One purchase upgrades ONE machine — the owner's explicit policy. Machines
// are identified by an anonymous fingerprint the upgrade tool sends as `m`: a
// SHA-256 of the machine's DMI product UUID salted with the session id, so
// the value is meaningless outside this one purchase and never a raw serial.
// Re-runs and reinstalls on the SAME machine hash to the same value and are
// always free; a second machine gets a 409 with a support pointer. The machine
// entitlement is the ONLY thing here worth gating — see the block in fetch().
//
// The byte and fetch budgets are BANDWIDTH protection for a free-software
// payload, not licensing. The ISO budget meters bytes delivered per session so
// that Range tricks cannot pull unlimited copies; the legacy fetch budget
// covers pre-fingerprint tools. Both are generous enough that no honest
// customer meets them across years of reinstalls, and both are backstops to a
// Cloudflare rate-limit rule (declared at deploy) — because a plain KV counter
// cannot hard-stop a deliberate parallel burst on its own.
//
// EVERY KV FAILURE FAILS OPEN, including a missing binding. The allowance is
// abuse control, not billing: our storage having a bad minute must never lock
// out a paying customer.
const MACHINE_CAP = 1;
const ISO_BYTE_BUDGET = 110 * 1024 * 1024 * 1024; // ~26 Pro ISOs / 50 free
const LEGACY_ASSET_CAP = 15;                      // 5 full 3-attempt runs

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
    const boughtPro = items.some((li) => li.price && li.price.id === PRICE_ID);
    if (!paid || !boughtPro) {
      return msg(403, "This session has no completed Dagric OS Pro purchase.");
    }

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
    // sale: the machine ENTITLEMENT is. One purchase upgrades one machine, and
    // moving it is a Stripe-bound support action nobody can share. That is the
    // control this block enforces; the byte budgets below are bandwidth
    // protection, not licensing.
    //
    // THE SLOT COMMITS AT /assets, NOT HERE. The tool HEADs first (a dry
    // validation — the point where `--check` or a declined consent stops), then
    // GETs /assets only after the owner says yes. Reserving on HEAD would burn
    // the single slot on an evaluation the owner walked away from, so HEAD only
    // READS: it turns away a machine a DIFFERENT fingerprint already holds and
    // reserves nothing.
    const m = url.searchParams.get("m") || "";
    const mValid = /^[a-f0-9]{64}$/.test(m);
    if (m && !mValid) {
      return msg(400, "Malformed request. Update Dagric and run the upgrade again.");
    }
    if (req.method === "HEAD" && mValid) {
      const held = await machineState(sid, m, env);
      if (held === "other") return machineTaken();
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
        const slot = await reserveMachine(sid, m, env);
        if (slot === "other") return machineTaken();
        // "ok" | "unknown" pass (fail open).
      } else {
        // Fielded tools predate the fingerprint. A generous per-session fetch
        // budget stands in — fifteen SUCCESSFUL pulls is five full 3-attempt
        // runs, enough for one machine's bad-network evenings and useless as a
        // shared link for a 190 KB tarball. Read-only here; charged only after
        // a real delivery below, because counting our own failures (a client
        // retries three times a run) burned the whole allowance in two bad
        // evenings. Remove when the fielded ISOs are all m-aware.
        const used = await readNum(`legacy:${sid}`, env);
        if (used !== null && used >= LEGACY_ASSET_CAP) {
          return msg(
            409,
            "This purchase has reached its upgrade allowance. One purchase " +
              "covers one machine — dagric.com/support can help if this is " +
              "your machine and something kept retrying."
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

// Read-only: does a machine hold this purchase's slot? Used by HEAD so a dry
// validation reserves nothing. "mine" | "other" | "free" | "unknown".
async function machineState(sid, m, env) {
  try {
    const rec = readRec(await env.LICENSE.get(`act:${sid}`));
    if (rec.machines.some((x) => x.h === m)) return "mine";
    if (rec.machines.length >= MACHINE_CAP) return "other";
    return "free";
  } catch {
    return "unknown";
  }
}

// Commit this machine's slot. "ok" (mine or newly reserved) | "other" (a
// different machine already holds the only slot) | "unknown" (KV trouble).
async function reserveMachine(sid, m, env) {
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
    if (rec.machines.length >= MACHINE_CAP) return "other";
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
function machineTaken() {
  return msg(
    409,
    "This purchase is already upgrading a different machine. One purchase " +
      "covers one machine — dagric.com/support can move it to this one " +
      "(a machine that was replaced or a virtual machine that moved counts), " +
      "or you can buy a second licence for a second machine."
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
