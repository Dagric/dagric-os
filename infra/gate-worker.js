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
    // Expand the charge too so we can see if the purchase was later REFUNDED —
    // a refunded checkout session still reports payment_status "paid", so
    // checking that alone would let a refunded buyer keep re-downloading.
    const sres = await fetch(
      `https://api.stripe.com/v1/checkout/sessions/${sid}` +
        `?expand[]=line_items&expand[]=payment_intent.latest_charge`,
      { headers: { Authorization: `Bearer ${env.STRIPE_KEY}` } }
    );
    if (!sres.ok) return msg(403, "Unknown purchase session.");
    const s = await sres.json();

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
    if (!obj) return msg(500, "File temporarily unavailable — try again shortly.");

    const headers = {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="${FILE}"`,
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-store",
    };
    if (range) {
      const end = range.offset + (range.length ?? obj.size - range.offset) - 1;
      headers["Content-Range"] = `bytes ${range.offset}-${end}/${obj.size}`;
      headers["Content-Length"] = String(end - range.offset + 1);
      return new Response(obj.body, { status: 206, headers });
    }
    headers["Content-Length"] = String(obj.size);
    return new Response(obj.body, { status: 200, headers });
  },
};

function parseRange(h) {
  if (!h) return null;
  const m = /^bytes=(\d+)-(\d*)$/.exec(h.trim());
  if (!m) return null;
  const offset = Number(m[1]);
  const end = m[2] === "" ? null : Number(m[2]);
  if (end !== null && end < offset) return null;
  return end === null ? { offset } : { offset, length: end - offset + 1 };
}

function msg(status, text) {
  const body = `<!doctype html><meta charset="utf-8"><title>Dagric OS</title>
<body style="background:#0a111c;color:#e8eef6;font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center">
<div><div style="font-size:44px;font-weight:800;background:linear-gradient(135deg,#59c2e8,#2f7fd1);-webkit-background-clip:text;color:transparent">Dagric OS</div>
<p style="color:#9db1c8;max-width:420px">${text}</p>
<p><a style="color:#3fa9f5" href="https://dagric-os.web.app/#pro">Get Dagric Pro</a></p></div>`;
  return new Response(body, { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
