// Dagric OS — contact-form backend.
// Accepts a JSON POST from the site's /contact form, validates + spam-guards
// it, and stores the message as a private object in the R2 bucket
// `dagric-contact`. Messages are read in the Cloudflare dashboard
// (R2 -> dagric-contact) — no email address is exposed anywhere.
// THE FORM WAS DEAD ON THE PRODUCTION DOMAIN. A single allowed origin naming
// only dagric-os.web.app meant the CORS preflight failed for everyone who
// arrived the way the operating system tells them to: dagric.com is what
// /etc/os-release (HOME_URL, SUPPORT_URL, BUG_REPORT_URL), /etc/motd, the
// Calamares branding and the guide all point at, and firebase.json declares no
// redirect off it. The browser blocked the POST, the page's catch block blamed
// the visitor's connection, and the support or refund message was never sent at
// all. Both names serve the same site, so both are allowed; any new domain must
// be added here the same day it starts serving /contact.
const ORIGINS = [
  "https://dagric.com",
  "https://www.dagric.com",
  "https://dagric-os.web.app",
];
const MAX = { name: 120, email: 200, topic: 40, message: 5000 };

// Nothing may be parsed before this is checked. The field caps below are applied
// AFTER req.json() has already read and decoded the whole body, so a megabyte of
// JSON was fully parsed and only then truncated to 5 KB — the work was done
// before the limit was consulted. 16 KB is comfortably above the largest real
// message (a 5000-character message plus name, email and topic) and far below
// anything worth spending CPU on.
const MAX_BODY = 16 * 1024;

export default {
  async fetch(req, env) {
    // Echo the caller's origin when it is on the list (Vary: Origin so no cache
    // hands one site's header to another). Anything else gets the canonical
    // domain, which is not a match for that caller and so is still refused.
    const origin = req.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ORIGINS.includes(origin) ? origin : ORIGINS[0],
      "Vary": "Origin",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (req.method !== "POST")
      return json({ ok: false, error: "POST only" }, 405, cors);

    // RATE LIMITING, BECAUSE CORS IS NOT A CONTROL.
    //
    // The only guard this endpoint had was the honeypot field, which is public
    // in the page markup and skipped by anything that is not a browser. CORS
    // stops nothing here either: Access-Control-* headers are instructions to a
    // BROWSER, and curl ignores them completely. So a one-line shell loop could
    // write one R2 object per request into the owner's inbox, without limit —
    // burying real support and refund messages, which is the actual damage, and
    // costing storage and Class-A operations on the way.
    //
    // Cloudflare's rate-limiting binding is used rather than a KV counter: it
    // needs no namespace to be created, costs nothing per check, and cannot
    // itself be turned into a write amplifier the way a KV counter can. The
    // dashboard WAF rule described in wrangler.toml is still worth having in
    // front of this; that rule lives outside the repo and cannot be verified
    // from it, which is exactly why the worker should not depend on it.
    //
    // Guarded rather than assumed: if the binding is absent (an older wrangler,
    // a partial deploy) this must not throw and take the contact form down with
    // it. A missing limiter degrades to the previous behaviour, which is the
    // safe direction for a support inbox — refusing every message because the
    // limiter is missing would be worse than accepting spam.
    if (env && env.RATE_LIMIT && typeof env.RATE_LIMIT.limit === "function") {
      const ip = req.headers.get("CF-Connecting-IP") || "unknown";
      try {
        const { success } = await env.RATE_LIMIT.limit({ key: ip });
        if (!success) {
          return json(
            { ok: false, error: "Too many messages from this connection. Please wait a minute and try again." },
            429,
            { ...cors, "Retry-After": "60" }
          );
        }
      } catch {
        // A limiter that errors must not decide the request.
      }
    }

    // Refuse an oversized body before parsing it. Content-Length is a claim, not
    // a fact, so the decoded length is checked too — a lying header cannot get
    // more than MAX_BODY of work out of this.
    const declared = parseInt(req.headers.get("Content-Length") || "0", 10);
    if (declared > MAX_BODY)
      return json({ ok: false, error: "That message is too long." }, 413, cors);

    let raw;
    try { raw = await req.text(); } catch { return json({ ok: false, error: "Bad request" }, 400, cors); }
    if (raw.length > MAX_BODY)
      return json({ ok: false, error: "That message is too long." }, 413, cors);

    let b;
    try { b = JSON.parse(raw); } catch { return json({ ok: false, error: "Bad JSON" }, 400, cors); }
    if (!b || typeof b !== "object" || Array.isArray(b))
      return json({ ok: false, error: "Bad JSON" }, 400, cors);

    // Honeypot: real users never fill the hidden "website" field.
    if (b.website) return json({ ok: true }, 200, cors);

    const name = str(b.name, MAX.name);
    const email = str(b.email, MAX.email);
    const topic = str(b.topic, MAX.topic) || "general";
    const message = str(b.message, MAX.message);
    if (!message || message.length < 10)
      return json({ ok: false, error: "Please write a message (at least 10 characters)." }, 400, cors);
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      return json({ ok: false, error: "That email address doesn't look right." }, 400, cors);

    const when = new Date();
    const key = `inbox/${when.toISOString().slice(0, 10)}/${when.toISOString().replace(/[:.]/g, "-")}-${crypto.randomUUID().slice(0, 8)}.json`;
    await env.MAIL.put(key, JSON.stringify({
      when: when.toISOString(),
      topic, name, email, message,
      country: req.headers.get("CF-IPCountry") || "",
    }, null, 2), { httpMetadata: { contentType: "application/json" } });

    return json({ ok: true }, 200, cors);
  },
};

function str(v, max) { return (typeof v === "string" ? v.trim() : "").slice(0, max); }
function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "Content-Type": "application/json", ...cors },
  });
}
