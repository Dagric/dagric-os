# Dagric infrastructure

## gate-worker.js — the Pro download paywall
Cloudflare Worker `dagric-gate` (live at https://dagric-gate.dagric.workers.dev).
Verifies a Stripe Checkout session is PAID for the Dagric Pro price, then
streams `dagric-os-pro-1.0-amd64.iso` from the PRIVATE R2 bucket `dagric-pro`
with HTTP Range support (resumable). Bindings (set at deploy, never in git):
- `PRO`: R2 bucket binding -> dagric-pro
- `STRIPE_KEY`: secret_text -> Stripe secret key

Deploy: upload via the Cloudflare API (multipart: metadata.json + worker.js
as an ES module) or `wrangler deploy`. The public bucket `dagric-downloads`
holds ONLY the free ISO + checksums; the Pro ISO must never be placed there.

## contact-worker.js — the contact-form backend
Cloudflare Worker `dagric-contact` (live at https://dagric-contact.dagric.workers.dev).
Accepts JSON POSTs from /contact, validates + honeypot-filters, and stores each
message as a private object in R2 bucket `dagric-contact` under inbox/<date>/.
READ MESSAGES: Cloudflare dashboard -> R2 -> dagric-contact -> inbox/.
Binding: `MAIL` (r2_bucket -> dagric-contact). No secrets. No email address
is published anywhere on the site.
