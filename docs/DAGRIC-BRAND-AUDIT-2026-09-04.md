# Dagric brand audit

Audited: 2026-09-04

September 5 status note: this is a historical audit, not current publication
approval. Download, purchase and launch recommendations below are conditional
on release acceptance. Use `DAGRIC-BRAND-ARCHITECTURE.md` and
`../promo/BRAND-CTA-STANDARD.md` for current held-release copy, and
`../promo/POST-RELEASE-MARKETING-PLAN-2026-09-05.md` for the next campaign's gate.

## Implementation update — 2026-09-04

The structural recommendations from this audit are now implemented across the public site and the release checks:

- The public hierarchy is locked as **IMPRESSIONSDIRECT360 LLC → Dagric → Dagric OS → Free / Pro → named product experiences**.
- The homepage hero now uses one concise promise, puts **Try Dagric OS Free** before the product video, and limits the trust strip to three proofs.
- The About page explains how the company, brand, product, and editions fit together.
- The Reviewer page publishes one approved description and links to the machine-readable brand standard.
- The master identity stays blue-to-mint, black, paper, and Pro gold; variable desktop themes are explicitly treated as product-expression layers, not competing brand identities.
- `site/brand-system.json` is the source of truth, and `tools/check-brand.py` prevents naming, promise, and master-palette regressions during the release audit.

Still open: replace the shaky/drifting product videos, create formal wordmark and small-size logo variants, produce page-specific social cards and banners, and shorten the lower half of the homepage.

## Recommendation in one sentence

Do not replace the whole Dagric identity. Keep the ownership promise and proof-first character, but simplify the message, formalize the logo and color system, replace the shaky website videos, and make every public surface use the same name, promise, and visual hierarchy.

## What is already strong

### Primary promise

**Your computer. Yours again.** is the strongest public-facing line in the brand. It is short, emotional, relevant to Windows 10-era PC owners, and broad enough to cover privacy, ownership, customization, and extending hardware life. Keep it as the primary tagline.

### Distinctive trust position

**The proof is public.** is more ownable than generic “fast, private, secure Linux” language. Public source, signed files, known gaps, and test evidence give Dagric a credible personality: direct, careful, and willing to be challenged.

### Commercial story

Free first, Pro for $39 once, no subscription, and an in-place upgrade is simple and customer-friendly. The line explaining that people pay for curation, convenience, and support—not exclusivity—is unusually transparent and worth keeping.

### Base visual system

The near-black `#0C0F14`, warm off-white `#F5F2EB`, cool blue `#7CB8EC`, and Pro gold `#E3C27D` form a calm, credible system. The light theme also looks considered rather than like an inverted dark theme. Contrast and typographic hierarchy are generally strong.

## P0: fix before sending more traffic

### 1. Replace the three affected website videos

The homepage and features page currently use the same decoded video streams as the shaking duration-ladder exports:

- `site/assets/dagric-live-tour.mp4` matches the decoded video in `1-minute-open-coast-hub-youtube.mp4`.
- `site/assets/dagric-personalize-live.mp4` matches the decoded video in `15-second-personalize-live-youtube.mp4`.
- `site/assets/dagric-files-live.mp4` matches the decoded video in `30-second-wild-meadow-files-youtube.mp4`.

This is the largest immediate brand problem. The site says “proof,” “continuous motion,” and “no mock interface,” but the proof itself has editor-added camera drift. The one-minute tour also exposes `Windows in a VM` around 0:55 and says “one click” while showing a terminal command.

Replace these files only with fixed-crop, natural-speed, continuous screen recordings. The new hero tour should show one understandable outcome in the first two seconds, then three or four clearly framed features—not a long scrolling Hub list.

### 2. Put the primary action inside the first phone screen

At a measured 390×844 viewport, the primary download button starts at approximately y=868—just below the first screen. The 118px sticky navigation, 220px lead paragraph, and landscape video all appear before the action.

Recommended mobile order:

1. Logo and headline
2. Two-line value proposition
3. **Try Dagric OS Free**
4. **Watch the 60-second tour**
5. Product video
6. Three-item trust strip

Proof should remain near the claim, but the visitor should not have to scroll before learning what to do next.

### 3. Reduce the hero to one promise and three proofs

The current paragraph asks the first screen to carry Windows 10, speed, quietness, telemetry, advertising, accounts, nagging, restarts, migration, Office compatibility, and ownership. Each claim may be supportable, but together they blur the brand.

Suggested replacement:

> Dagric OS gives Windows 10 PCs a private, customizable second life. No required account, no subscription, and no Dagric telemetry. Try the complete Free edition from USB before installing.

Suggested buttons:

- Primary: **Try Dagric OS Free**
- Secondary: **Watch the 60-second tour**

Use the trust strip for only three items: **No Dagric telemetry**, **Public test record**, and **Pro is $39 once**.

### 4. Keep infrastructure language off the marketing layer

The homepage currently says “tested in a VM,” “reviewer kit for the ISO,” and “Download ISO.” Exact technical language belongs on `/testing`, `/review`, and verification instructions. On the homepage and social surfaces, use:

- “lab testing” and “physical-PC testing”
- “Dagric OS download”
- “live footage”
- “Try it from USB”

This preserves technical honesty without making the capture or packaging method the product story.

## P1: strengthen recognition and consistency

### 5. Evolve the logo system instead of starting over

The current monogram is clean and works as an app icon. Its gradient runs from `#3FA9F5` to `#7BE0C8`, and the underline is intended as a sunrise/day line. At 28-44 pixels, however, most people see a generic “D with an underline”; the underline becomes approximately one pixel at favicon size.

Keep the mark for continuity, then add:

- A simplified small-size mark without the underline below 24px
- A fixed `Dagric OS` wordmark asset instead of relying on whatever page font surrounds the icon
- Horizontal and stacked lockups
- One-color black, white, and cyan versions
- Clear-space and minimum-size rules
- A Pro lockup that uses gold as a tier signal, not as a separate logo

The website currently uses Georgia for the word beside the icon, while boot art and wallpaper use widely tracked uppercase sans-serif letters. An official wordmark would remove that inconsistency.

### 6. Lock the naming hierarchy

Use these forms everywhere:

- Company/legal seller: **IMPRESSIONSDIRECT360 LLC**
- Fictitious brand: **Dagric**
- Product: **Dagric OS**
- Paid edition: **Dagric OS Pro**

Use **Dagric OS** in title case in normal writing. Reserve **DAGRIC** for the official graphic wordmark only. Do not use `DAGRiC`, `DGR`, or `DGR Operations`.

### 7. Give the three taglines separate jobs

- Brand promise: **Your computer. Yours again.**
- Ownership support line: **Own it outright.**
- Trust/proof line: **The proof is public.**

Do not rotate all three as equal headlines. Repetition will build recognition only if each line keeps the same role.

### 8. Turn visual variety into a controlled system

The user-facing promise includes freedom and personalization, so every campaign should not look like the same blue desktop. Variation should be intentional rather than random.

Keep the master brand stable—dark ink, paper, cyan, and Pro gold—then assign campaign palettes:

| Content pillar | Wallpaper/palette direction | Brand role |
|---|---|---|
| Privacy and proof | Night Orbit: navy, violet, restrained cyan | Serious and technical |
| Personalization | Open Coast: teal, coral, warm cream | Freedom and color |
| Hardware second life | Wild Meadow: sage, gold, earth | Longevity and repair |
| Everyday productivity | Open Horizon: sky, amber, soft blue | Familiar and optimistic |

Keep the logo, typography, spacing, and CTA treatment constant while changing wallpaper and accent. That creates variety without losing recognition.

### 9. Create page-specific social share cards

The homepage, Pro, Download, About, and Reviewer pages all advertise the same `hero-desktop.png` Open Graph image. It is mostly dark empty desktop with a small centered wordmark, so it loses impact when reduced to a social preview.

Create at least four real 1200×630 share cards:

- Home: **Your computer. Yours again.** plus a readable real desktop action
- Download: **Try Dagric OS Free** plus USB/download cue
- Pro: **Everything, unlocked. $39 once.** plus creative/productivity tools
- Review/Testing: **The proof is public.** plus signed-release/test-record visual

Do not use generated screenshots of the operating system. Use actual captured UI or brand-only graphics when product footage is not appropriate.

### 10. Shorten the homepage

At phone width the homepage measures approximately 13,643px, or more than sixteen 844px screens. The detail is valuable but makes the brand feel defensive and harder to scan.

Recommended homepage sequence:

1. Promise, CTA, real product proof
2. Why it exists for Windows 10 PCs
3. Three benefits: private, personal, practical
4. Free versus Pro
5. Public proof and known limits
6. Social/video follow section

Move the full layout catalog, long security explanation, app catalog, verification instructions, and detailed policy copy to their existing dedicated pages.

## P2: social and campaign consistency

### 11. Make every social profile look like the same company

Handles differ by platform, which may be unavoidable. Compensate with identical visible branding:

- Display name: **Dagric OS**
- Avatar: the same simplified small-size monogram
- Banner headline: **Your computer. Yours again.**
- Support line: **Private. Customizable. Proven in live demos.**
- Destination: **dagric.com**

Avoid a social banner that says `DAGRiC OS`; that casing conflicts with the site and product name.

### 12. Define one brand voice

Dagric is strongest when it sounds plainspoken, calm, specific, and honest. It is weakest when it stacks claims or narrates implementation details.

Preferred pattern:

> Problem → visible action → evidence → one next step

Example:

> Windows 10 support ended, but this computer still works. Here is Dagric checking its hardware before installation. Try Dagric OS Free from USB at dagric.com.

Avoid:

- Long lists of features in one sentence
- “Revolutionary,” “game-changing,” or unverifiable superlatives
- Capture terms in consumer marketing
- Claiming synthetic narration is human
- Calling a terminal command “one click”

## Brand hierarchy to adopt

| Layer | Standard |
|---|---|
| Brand | Dagric |
| Product | Dagric OS |
| Audience | People with Windows 10-era PCs that still work |
| Primary promise | Your computer. Yours again. |
| Functional promise | A private, customizable operating system you can try before installing |
| Trust differentiator | The proof is public. |
| Commercial model | Free edition; Pro for $39 once |
| Primary action | Try Dagric OS Free |
| Secondary action | Watch a real Dagric OS demonstration |

## Recommended order of work

1. Replace the three live website videos.
2. Shorten the hero and move the primary CTA above the mobile fold.
3. Lock naming, tagline roles, and marketing-versus-technical vocabulary.
4. Produce the formal wordmark and small-size logo variants.
5. Produce page-specific social share cards and matching social banners.
6. Compress the homepage and move detail to dedicated pages.
7. Apply the four controlled campaign palettes to future video and social work.

## Audit scope

Reviewed the live homepage at desktop and 390×844 mobile widths in dark and light modes; inspected live Home, Pro, Download, About, and Reviewer page identity; compared the website videos with the current audited video exports; and inspected the local logo, wallpaper, splash, color tokens, business-identity standard, CTA standard, and social-profile audit.

No website, logo, social profile, or production media was changed during the original audit pass. The implementation update above records the brand-structure work completed afterward.
