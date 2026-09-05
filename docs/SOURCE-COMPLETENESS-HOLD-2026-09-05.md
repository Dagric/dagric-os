# Primary mapping is not complete corresponding-source clearance

This is an audit-tooling change. It does not change, relabel, approve, sign or
publish the completed candidate images built from
`20e24dd04ea3de802531be5139f9f36fe96a1490`.

## Candidate evidence

The independent immutable-image audit extracted these inventories from the
completed images, not from a mutable build directory:

| Edition | ISO SHA-256 | Installed binaries |
| --- | --- | ---: |
| Free | `0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc` | 1,771 |
| Pro | `69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa` | 2,498 |

The private primary map passes the existing one-to-one checker and contains
1,294 source identities: 1,293 Debian sources and the exact Dagric source commit.
Every Debian mapping was compared with the installed package's `source:Version`.
Its cached DSC bodies match Snapshot's archived-object SHA-1, the recorded
SHA-256, and their exact Source/Version headers.

The same immutable dpkg metadata declares **580** distinct exact `Built-Using`
or `Static-Built-Using` source identities. Only 12 appeared in the primary map;
**568 additional identities** required a separate inventory. All 568 exact
Snapshot source records and DSC bodies were retrieved and hash/header checked
privately, without substituting a newer version. There were zero unresolved
archival lookups in this pass. These are metadata and DSC checks; the full source
tarballs were not downloaded, and OpenPGP signatures were not independently
verified here.

Private files remain under the ignored
`out/private-source-candidate-20e24dd0-20260905/` directory. Its receipts bind
the two ISO hashes, source commit, package-manifest hashes, extracted dpkg-status
hashes, primary map and supplementary metadata. No live/public manifest changed.

### Recorded private checks

Run from the repository root. The commands below record the successful checks;
their output already exists. Select a new output filename for a new inventory
run, because the checker refuses to overwrite existing evidence.

```sh
python3 tools/check-generated-source-map.py \
  --map out/private-source-candidate-20e24dd0-20260905/exact-source-map.private.json \
  --index out/private-source-candidate-20e24dd0-20260905/source-index.private.json \
  --free-manifest out/private-source-candidate-20e24dd0-20260905/manifests/free.packages \
  --pro-manifest out/private-source-candidate-20e24dd0-20260905/manifests/pro.packages

python3 tools/check-embedded-sources.py \
  --free-status out/private-source-candidate-20e24dd0-20260905/manifests/free-dpkg-status \
  --pro-status out/private-source-candidate-20e24dd0-20260905/manifests/pro-dpkg-status \
  --map out/private-source-candidate-20e24dd0-20260905/exact-source-map.private.json \
  --supplement out/private-source-candidate-20e24dd0-20260905/embedded-source-supplement.private.json \
  --dagric-commit 20e24dd04ea3de802531be5139f9f36fe96a1490 \
  --free-iso-sha256 0bab5d46faba0245de54c327c8291d9a2ef581022f7eeb481fa353371c34dcfc \
  --pro-iso-sha256 69f0ea42ef9a98dc17857824e492b9a2a33e1a6eaec0c15478ef7686f51c9bfa \
  --output out/private-source-candidate-20e24dd0-20260905/embedded-source-check-complete.private.json
```

Results: primary check exit 0 (1,771 Free, 2,498 Pro, 1,294 sources); embedded
check without the supplement exit 1 (568 missing); embedded check with the
supplement exit 0 (580 declared identities, 12 primary plus 568 supplementary,
zero missing). The final inventory explicitly retains
`corresponding_source_complete: false` and `release_approved: false`.

`embedded-source-resolution.private.json` records all 568 successful exact
archival lookups in 142.12 seconds with six workers, two attempts per request
and 12-second request timeouts. Full source tarball retrieval/content checks,
OpenPGP verification and source-delivery obligations remain unverified.

## Why the extra inventory matters

Debian describes `Built-Using` as exact source versions incorporated into a
binary, including code that need not be represented by its runtime dependencies.
The field supports retention of sources required by applicable source-availability
conditions. `Static-Built-Using` also records static build inputs for purposes
such as security rebuild tracking; its presence alone does not decide legal
obligations. See [Debian Policy §7.8](https://www.debian.org/doc/debian-policy/ch-relationships.html#additional-source-packages-used-to-build-the-binary-built-using)
and [dpkg control-field documentation](https://manpages.debian.org/trixie/dpkg-dev/deb-control.5.en.html).

The old generator validates one primary source package for each binary. That
remains useful and tested, but it cannot by itself establish exhaustive
corresponding-source coverage. Undeclared vendored code and rights review also
remain outside the new declaration-based inventory.

## Safe tooling changes

- `check-generated-source-map.py` explicitly reports a **primary** map pass and
  names the separate embedded-source check. Its validation is not disabled.
- `check-embedded-sources.py` parses exact declarations from both supplied
  immutable-image status files, rejects ambiguous/malformed identities, validates
  source locator/digest metadata, and binds the supplied ISO receipt hashes plus
  computed input hashes. Missing exact metadata produces a failing exit and a
  private inventory. It explicitly states that it did not independently extract
  or hash the images, and never sets `corresponding_source_complete` or
  `release_approved` to true.
- `install-generated-source-map.py` no longer writes public source-complete
  records or clears hold reasons after only a primary pass. It runs the primary
  check and then returns a clear blocked result without changing any records.
- Both commercial gate modes retain their existing checks, then explicitly stop
  before success or upload-authorization writes. Detached completion flags,
  caller-supplied counts and old public `status: complete` records cannot bypass
  this hold. There is no force flag or environment bypass.

## Remaining promotion integration

The release schema and promotion integration are deliberately **not implemented**
by this bounded fix. Removing the hold requires reviewed code and fixtures that:

1. Persist the exact supplementary records and per-edition declared-source
   inventory with the source commit, both ISO hashes, primary-map/manifest hashes
   and immutable dpkg-status hashes.
2. Independently extract/recheck the actual images at promotion and recompute
   source coverage; do not trust a detached successful report, count or status.
3. Verify candidate-bound source availability/delivery and preserve truthful
   distinctions between metadata checks, archive content checks, signature
   verification and qualified package-rights approval.
4. Restore positive end-to-end promotion tests only when that real binding exists,
   retaining failure tests for omitted dependencies, stale/wrong-edition inputs,
   changed images/commits and zero writes on failure.

Firmware, package rights, Mozilla disposition, artwork, physical Secure Boot,
accessibility, hardware and multi-user approvals remain separate requirements.
