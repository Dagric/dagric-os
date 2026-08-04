// Dagric OS — Pro download gate.
// Verifies a Stripe Checkout session is PAID and bought the Dagric Pro price,
// then streams the ISO from a PRIVATE R2 bucket. Supports HTTP Range so the
// 3.3 GB download is resumable. Without a valid paid session: no file.
const PRICE_ID = "price_1TwRxY6lZx4VOIr30Zvozvhb";
const FILE = "dagric-os-pro-1.0-amd64.iso";

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
        "This purchase was refunded, so Pro downloads and updates have ended. " +
          "The copy you already downloaded is yours to keep and run. " +
          "You're welcome to re-purchase anytime."
      );
    }

    // Paid — stream the ISO from the private bucket, honoring Range.
    const range = parseRange(req.headers.get("Range"));
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
      return new Response(obj.body, { status: 206, headers });
    }
    headers["Content-Length"] = String(obj.size);
    return new Response(obj.body, { status: 200, headers });
  },
};

// Look up the checkout session. Expand the charge too so we can see if the
// purchase was later REFUNDED — a refunded session still reports payment_status
// "paid", so checking that alone would let a refunded buyer keep re-downloading.
// Returns { session } on success, { missing: true } only when Stripe positively
// says the session does not exist, and { transient: true } for everything else.
async function getSession(sid, env) {
  const url =
    `https://api.stripe.com/v1/checkout/sessions/${sid}` +
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
