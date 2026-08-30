# Dagric OS legal-review packet

Prepared August 30, 2026 for review by licensed counsel. This is a factual intake packet, not legal advice and not a representation that a lawyer has approved the site.

## Requested scope

Ask U.S./Missouri counsel with software, consumer, privacy and open-source experience to review:

- the legal seller identity and the relationship among Dagric OS, DGR Operations and the Stripe account name/statement descriptor;
- the $39 one-time digital-software sale, one-machine license, permanent local use, free updates promise and 14-day refund policy;
- warranty disclaimer, liability cap, Missouri governing-law clause and mandatory consumer rights outside Missouri or the United States;
- whether checkout obtains the required assent and accurately presents seller, refund, delivery and license terms;
- privacy disclosures and rights handling for contact messages, Stripe orders, Cloudflare delivery/KV records, Firebase logs and international processing;
- sales tax, business-registration, assumed-name/trademark and receipt/invoice requirements;
- GPL and other open-source license obligations for the ISO, modified files, source offer, notices and trademarks;
- marketing statements, accessibility claims, reviewer evaluation copies and promotion-code terms;
- incident response, data-request verification, retention exceptions and deletion procedures.

## Product and transaction facts to verify

- Publisher shown publicly: **DGR Operations**; product/brand: **Dagric OS**.
- Dagric OS is assembled from Debian 13, KDE and other open-source components.
- Free is downloadable without an account. Pro is currently advertised as a one-time **$39** purchase for one machine.
- Pro is delivered after Stripe Checkout through a Cloudflare Worker that verifies the Checkout Session and streams a private R2 object.
- The installed system does not perform recurring license checks. A one-time claim creates an anonymous machine fingerprint tied to purchase-delivery records.
- A refund ends Pro download/support access but cannot remotely disable an installed copy.
- The public terms promise a full refund requested within 14 calendar days, subject to the narrow fraud/repeated-abuse language shown on the page.
- The live Stripe public business name is Dagric OS. As of this packet date, the bank statement descriptor still reads **IMPRESSIONDIRECT360**, and the terms disclose that mismatch. Counsel should advise whether the descriptor and seller disclosures should instead be aligned.
- Contact-form submissions are private R2 objects. Cloudflare now enforces automatic deletion under `inbox/` after 365 days; messages may be deleted earlier.
- Hosting: Firebase Hosting. Checkout: Stripe. Edge delivery/contact storage: Cloudflare Workers, R2 and KV.
- Operator location and governing-law choice shown publicly: Missouri, United States.

## Public documents and implementation references

- Terms and refunds: https://dagric.com/terms and `site/terms.html`
- Privacy: https://dagric.com/privacy and `site/privacy.html`
- Licenses/source notices: https://dagric.com/licenses and `site/licenses.html`
- Accessibility: https://dagric.com/accessibility and `site/accessibility.html`
- Security: https://dagric.com/security and `site/security.html`
- Pro marketing/checkout handoff: https://dagric.com/pro and `site/pro.html`
- Download and verification: https://dagric.com/download and `site/download.html`
- Gate implementation: `infra/gate-worker.js`
- Contact implementation: `infra/contact-worker.js`
- Public source: https://github.com/Dagric/dagric-os

Provide counsel a clean repository snapshot and screenshots of the actual Stripe Checkout/receipt. Do **not** send API keys, secrets, complete Stripe session URLs, customer messages, customer lists, full identity documents or unrelated account data in an initial intake. Use the firm's secure portal for any sensitive follow-up it specifically requests.

## Questions requiring explicit answers

1. What exact legal name, assumed-name registration and postal/contact information must appear at checkout, on receipts and in the site footer?
2. May the brand be Dagric OS while the underlying seller is DGR Operations, and what explanatory wording is needed?
3. Should the Stripe statement descriptor be changed to `DAGRIC OS` or another permitted form?
4. Is affirmative assent (for example, a checkout checkbox or adjacent linked terms) required for the license, refund and liability clauses?
5. Does immediate digital delivery affect cancellation/refund rights in any market the site serves?
6. Are the refund, perpetual-use and free-updates promises internally consistent and operationally sustainable?
7. Which U.S. state privacy notices, consumer-request methods and breach procedures apply at the present transaction volume?
8. Is a 365-day contact-message retention period justified, and what exceptions/log should exist?
9. What source-code distribution or written-offer process is required for each copyleft component shipped in the ISO?
10. Which tax registrations or Stripe Tax settings are required before broad sales outreach?

## Missouri intake routes and candidates

- Bar Association of Metropolitan St. Louis Lawyer Referral and Information Service: https://www.bamsl.org/index.cfm?pg=clientReferrals
- Missouri lawyer directory: https://mobar.org/site/content/For-the-Public/Lawyer_Directory.aspx
- Jeffrey Schultz, Armstrong Teasdale (privacy/data protection, CIPP/US): https://www.armstrongteasdale.com/jeffrey-schultz/
- Casey Waughn, Armstrong Teasdale (technology/privacy profile): https://www.armstrongteasdale.com/content/uploads/pdf/casey-waughn.pdf
- Stacy Harper, Spencer Fane (data privacy/cybersecurity): https://www.spencerfane.com/professionals/stacy-harper/

The named lawyers are research leads, not endorsements. Confirm conflicts, engagement terms, relevant software/open-source experience and budget before sharing non-public information.

## Draft intake message

**Subject:** Missouri software, consumer, privacy and open-source review for Dagric OS

Hello,

I operate DGR Operations in Missouri and publish Dagric OS, a Debian/KDE-based desktop operating system. The Free edition is public; Pro is a one-time $39 digital-software purchase delivered after Stripe Checkout. I am seeking a scoped legal review of the customer terms/refund flow, privacy disclosures and retention, seller/Stripe branding, software marketing and open-source compliance before broader press outreach.

Could you confirm whether this is within your practice, identify the attorney who would handle it, and provide the conflict-check information and estimated fee or initial-consultation terms you need? I can provide the public site, repository and a short data-flow summary. I will not email credentials or customer data.

Thank you,

[Legal name]<br>
DGR Operations / Dagric OS<br>
[Email] · [Phone]

## Before contacting counsel

Fill in the owner's legal name, the exact registered/assumed-name status, preferred contact details, sales footprint, revenue/transaction count and a legal-review budget. Contacting a firm and accepting an engagement each require the owner's approval.
