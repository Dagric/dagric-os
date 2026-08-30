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

The bucket lifecycle rule `delete-contact-messages-after-365-days` is enabled
for prefix `inbox/` and expires each contact object after 365 days. The default
multipart-upload abort rule remains enabled at 7 days. If the public retention
promise changes, update both the R2 lifecycle rule and `site/privacy.html` in
the same release.

## firebase.json — why the Cache-Control block looks like that
firebase.json is validated against firebase-tools' schema, whose header entries
declare `additionalProperties: false` — an unknown `_comment` key makes the
config fail validation — and JSON has no comments. So the WHY lives here.

**cleanUrls means header globs see `/download`, not `/download.html`.**
The block used to be a single `"source": "**/*.html"` entry setting
`no-cache, max-age=0`, and it matched nothing the site serves. Measured with
firebase-tools 15.0.0's own matcher (`superstatic/lib/utils/patterns`,
minimatch) against all 35 served paths: `**/*.html` fired on exactly two,
`/404.html` and `/download.html` — the paths cleanUrls 301-redirects, whose 301
responses carry no Cache-Control at all. All 22 real routes fell through to
Firebase's `max-age=3600` default, which suppresses revalidation entirely, so a
returning visitor kept a pre-deploy page for up to an hour with a valid ETag
sitting unused. The rule written to prevent exactly that was dead in both
directions for its whole life.

**The routes are enumerated instead of collapsed into one clever glob.** An
earlier draft used `/@(|download|pro|...)` — an extglob with an empty branch
asked to match `/` — and omitted `/guide` and the five locales, 6 of the 22
pages. A glob that fails to match does not announce itself; it silently
degrades to `max-age=3600`, and a spot-check on `/pro` would have reported
success. Explicit `"/"`, an extglob for the 16 top-level routes, and
`/guide/@(de|es|fr|it|pt-br)` are each the same shape as the already-working
`/@(SHA256SUMS|SHA256SUMS.sig|dagric-signing-key.asc)` entry.

**CSS and JS are in the block on purpose, and removing them makes things
worse.** `site.css` and `guide.css` are referenced unhashed and are not in the
immutable extension list (`png|jpg|jpeg|svg|webp|ico|mp4|woff2`), so they were
on the same 1-hour timer. Giving the HTML `no-cache` while leaving the
stylesheet at `max-age=3600` does not fix the skew, it guarantees it: every
visitor would get fresh markup against whatever CSS their cache held, which is
a broken render rather than an old one. Cost is a conditional request that
answers 304.

**No ordering dependency was introduced.** The `no-cache` entries and the
`immutable` entry select disjoint paths (`css|js` vs
`png|jpg|jpeg|svg|webp|ico|mp4|woff2`), so nothing relies on last-match-wins —
which superstatic does implement (`headers.js` calls `res.setHeader` for each
match in order), but which is not worth depending on.

**Verify after a deploy** — all 22 routes plus the two stylesheets, not one URL:

    for p in / download pro features faq getting-started support news about \
             contact bugs licenses privacy terms accessibility thanks-pro \
             guide guide/de guide/es guide/fr guide/it guide/pt-br \
             assets/site.css guide/guide.css; do
      printf '%-24s %s\n' "$p" "$(curl -sSI "https://dagric.com/$p" | grep -i '^cache-control')"
    done
    curl -sSI https://dagric.com/assets/dagric-logo.png | grep -i cache-control

The last line is the regression check: it must still say
`public, max-age=31536000, immutable`.

**Still on `max-age=3600`, deliberately not changed here:** `/SHA256SUMS`,
`/SHA256SUMS.sig`, `/dagric-signing-key.asc`, `/sitemap.xml`, `/robots.txt`,
`/favicon.ico`. The checksum files are the ones worth revisiting — this project
has already shipped a signature that did not describe the published ISO once,
and an hour of stale checksum is the same failure with a cache in front of it.

## site/404.html — no firebase.json entry needed
Firebase Hosting serves `<public>/404.html` for unmatched paths automatically.
The `ignore` list (`firebase.json`, `**/.*`, `**/node_modules/**`) does not
exclude it. Verify with a genuinely unknown path — `/no-such-page-xyz`, never
`/404` or `/404.html`, which cleanUrls makes special and which would report a
soft-404 as success.
