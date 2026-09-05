# Mozilla distribution review packet

Status: technical remediation complete; qualified-human review and candidate-
bound evidence remain required before commercial distribution.

## Current disposition

Dagric OS redistributes Debian's `firefox-esr` binary package without modifying
its executable, source, default settings, bookmarks, extensions, first-run
content, or `distribution/policies.json`. The prior Dagric enterprise policy was
removed from the image source and from the `dagric-desktop-defaults` update
package. Repository checks and the installed-system audit now fail if a Dagric
Firefox distribution policy reappears.

This is intended to follow Mozilla's unmodified-distribution path. It is still a
legal/trademark conclusion that a qualified human must review against the
current policy and bind to the exact candidate commit. Open-source rights in
Firefox code do not by themselves grant rights to Mozilla's marks.

Official policies:

- https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/
- https://www.mozilla.org/en-US/foundation/trademarks/policy/
- https://www.mozilla.org/en-US/about/legal/firefox/

## Candidate evidence to review

- the candidate's exact `firefox-esr` package name, version, Debian Section and
  binary-to-source-map entry;
- absence of
  `config/includes.chroot/usr/lib/firefox-esr/distribution/policies.json`;
- absence of a Firefox policy in the built `dagric-desktop-defaults` package;
- installed-system audit result showing no Dagric policy at
  `/usr/lib/firefox-esr/distribution/policies.json`;
- first-launch screenshots or recording from the installed candidate; and
- the exact candidate commit, release tag and Mozilla policy retrieval date.

## Release decision record

Before release, a qualified human legal/IP/trademark reviewer must record
`unmodified-distribution-reviewed`, the exact candidate commit and tag, their
name and role, an approval time, and an HTTPS evidence location in the protected
commercial-release approval. The release gate binds the disposition to
`configuration_sha256: "absent"` and rejects either a reintroduced policy or a
mismatched disposition.

Do not describe the distribution as cleared until that record exists.
