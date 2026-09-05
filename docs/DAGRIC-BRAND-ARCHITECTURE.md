# Dagric brand architecture

Updated: 2026-09-04

## Decision

Dagric uses a **branded-house** architecture. The company does not create a
separate identity for every feature. Dagric is the brand, Dagric OS is the
product family, and Dagric OS Free and Dagric OS Pro are editions of the same
operating system.

This keeps recognition concentrated in one name while allowing individual
tools to use either an endorsed Dagric name or a plain task name.

## Public hierarchy

| Layer | Required public name | Job |
|---|---|---|
| Legal publisher and seller | IMPRESSIONSDIRECT360 LLC | Contracts, checkout, privacy, terms, applications, and invoices |
| Brand | Dagric | The source of the product family; use sparingly outside formal brand explanations |
| Product family | Dagric OS | The default public name |
| Free edition | Dagric OS Free | Complete everyday product and the default trial path |
| Paid edition | Dagric OS Pro | The same system with additional preconfigured suites |

Do not use DAGRiC, DGR, or DGR Operations. Reserve all-uppercase DAGRIC for a
future fixed graphic wordmark, not ordinary copy.

## Product naming system

Use a Dagric-endorsed name when a tool expresses a distinctive Dagric idea:

- **Dagric Hub** — home for owner tools and setup.
- **Dagric Appearance** — personalization umbrella.
  - **Dagric Looks** changes desktop layout.
  - **Dagric Styles** changes color, wallpaper, and effects.
- **Dagric Rewind** — system rollback and recovery.
- **Dagric Blueprint** — portable system-configuration record.
- **Dagric Support Mode** — privacy-safe diagnostics for support.

Use a plain task name when immediate understanding matters more than brand
ownership:

- **Check This PC** — pre-install hardware check.
- **Migrate from Windows** — file and bookmark migration.
- **Security Checkup** — security audit.
- **Software Store**, **Graphics Drivers**, and **Finish Setup** — direct tasks.

New tools should not receive a Dagric name merely because Dagric built them.
The test is whether the branded name adds a distinct idea that a plain task name
cannot explain faster.

## Message ladder

1. Brand promise: **Your computer. Yours again.**
2. Functional promise: **A private, customizable operating system you can try
   before installing.**
3. Trust differentiator: **The proof is public.**
4. Ownership support: **Own it outright.**
5. Primary action: **Try Dagric OS Free.**
6. Secondary action: **Watch the 60-second tour.**

Each line has one job. They should not rotate as interchangeable slogans.

## Content pillars

Every campaign, article, video, and social post belongs to one primary pillar:

1. **Second Life** — Windows 10-era hardware, compatibility, migration, and
   longevity.
2. **Yours** — privacy, ownership, no required account, and no subscription.
3. **Make It Yours** — layouts, styles, wallpapers, accessibility, and control.
4. **Proof** — real demonstrations, signed releases, tests, source, and known
   limits.

The pillar chooses the story. The master Dagric name, mark, typography,
evidence standard, and call-to-action hierarchy remain stable.

## Visual hierarchy

The master brand uses Obsidian `#0C0F14`, Paper `#F5F2EB`, Interface Blue
`#7CB8EC`, the existing blue-to-mint monogram, and Pro Gold `#E3C27D`.

Dagric OS desktop themes are product experiences, not new master brands.
Obsidian Flow may use Pulse Red, Open Coast may use coral and teal, and future
themes may use different accents. They must retain the Dagric mark and product
name, but their accent color must not redefine the corporate identity.

## Voice

The repeatable sequence is:

> Problem → visible action → evidence → one next step

Use plain, calm, specific language. Avoid unverifiable superlatives, dense
feature stacks, engineering capture terms in consumer copy, or any claim that a
synthetic voice is human.

## Public boilerplate

> Dagric OS gives Windows 10-era PCs a private, customizable second life. It
> requires no Dagric account, adds no Dagric telemetry, and can be tried before
> installation. Dagric OS Free is complete for everyday use; Dagric OS Pro adds
> preconfigured creator, developer, gaming, privacy, and Windows-app suites for
> a one-time $39. Dagric OS is published by IMPRESSIONSDIRECT360 LLC and is
> built on Debian and KDE Plasma.

## Enforcement

The public machine-readable source is `site/brand-system.json`. Run
`python tools/check-brand.py` before publishing. The website release gate also
runs this check automatically.
