# Dagric editorial standard

Dagric copy should sound like a maintainer explaining a product they know well.

## Public copy

- Lead with the user's task or problem, then show the evidence.
- Prefer concrete nouns and verbs over slogans and superlatives.
- State one primary action at a time.
- Use exact product names, prices, dates, limits, and support boundaries.
- Do not invent popularity, testimonials, awards, compatibility, performance, or security claims.
- Keep implementation details out of customer copy unless they answer a real buying or support question.
- Credit people and organizations in author fields. Editing, build, and design tools do not belong in public author metadata.
- Never claim that work was handmade, human-only, or produced without software assistance unless that claim is documented and relevant.

## Source comments

Comments explain a current constraint, safety boundary, or non-obvious decision. They should not narrate the editing process, argue with an earlier version, or read like a design review transcript. Put durable history and incident analysis in `docs/` or the issue tracker.

## Release review

Before public release, check the website, desktop files, wallpaper metadata, README, issue templates, and release notes for:

- obsolete organization names;
- temporary links, placeholders, and test credentials;
- internal tool credits or drafting notes;
- unsupported claims and unexplained superlatives;
- duplicated, formulaic calls to action;
- essay-length comments in shipped front-end source.

`python3 tools/check-source.py` enforces the objective parts of this standard. A maintainer still performs the final copy review.
