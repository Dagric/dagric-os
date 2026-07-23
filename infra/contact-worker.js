// Dagric OS — contact-form backend.
// Accepts a JSON POST from the site's /contact form, validates + spam-guards
// it, and stores the message as a private object in the R2 bucket
// `dagric-contact`. Messages are read in the Cloudflare dashboard
// (R2 -> dagric-contact) — no email address is exposed anywhere.
const ORIGIN = "https://dagric-os.web.app";
const MAX = { name: 120, email: 200, topic: 40, message: 5000 };

export default {
  async fetch(req, env) {
    const cors = {
      "Access-Control-Allow-Origin": ORIGIN,
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
