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

    let b;
    try { b = await req.json(); } catch { return json({ ok: false, error: "Bad JSON" }, 400, cors); }

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
