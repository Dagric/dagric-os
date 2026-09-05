# Reproducible source audit — 5 September 2026

## New developer mode

`sh tools/audit-all.sh --source-only` selects the existing source, policy, regression, website, syntax, localization and dependency checks, and omits only the untracked generated candidate `out/exact-source-map-1.0.json`.

The output identifies that map as **NOT CHECKED**, and the final message explicitly says this is **not release approval**. Built images, boot/runtime evidence and physical tests are not examined. `--source-only --artifacts` is rejected before any checks; the optional `--package-names` query can still be selected.

The default command retains its generated-map gate. `--artifacts` still adds the immutable-image audit. No release, publication, provenance, source-map or artifact gate was weakened. The source-only mode still checks the tracked public source index and its relationship to the recorded historical candidate; that does not approve a newly built image.

This is not an offline mode: the normal JavaScript vulnerability query uses the registry, and `--package-names` uses Debian repositories. Missing tools and genuine source failures still fail the run.

## Clean candidate checkout evidence

The existing 38 selected source checks were run equivalently against the untouched clean clone at `/var/tmp/dagric-private-pro.vUYrFJ/source`, exact revision `34aafa1403a65762e2d6e08915a548cb8634cf9e`. The new mode script/test did not yet exist at that revision, so commands came from that clone's own `audit-all.sh`, omitting the one generated-map invocation. Python caches were redirected to a temporary location outside the candidate.

- **37 of 38 source checks passed.**
- Website safety failed because `site/security.html` linked to the absent, generated `/repo/dagric-repo.gpg.asc` file. Both the shell link gate and Python site audit caught it.
- After recording that failure, the remaining checks were run independently and passed. This does not override the failed aggregate result.
- `git status --porcelain` was empty before and after. The candidate source was not edited, and no generated map or public key was copied into it.

The website reference defect is fixed only in the later working-tree changes. A clean checkout containing that fix is required to report a clean-checkout pass. The source mode must not skip the website gate to conceal this kind of missing public input.

## Public-key reference correction

The generated public repository key and the already-tracked `site/dagric-signing-key.asc` are byte-for-byte identical:

- SHA-256: `b837a6612a715632842214814780322f14262b6c1cf3247fb8efd221974f3b3e`
- OpenPGP fingerprint, inspected with `gpg --show-keys --with-colons`: `3A079F85DE74375DD65557096CE37402BA0A0EF8`

`site/security.html` now links to that existing tracked key. The old generated repository path remains untouched for compatibility. No private key was opened or exported.

Website images/videos, icon sources/contact sheets, translations and the public release/package/source-index manifests are tracked assets; their checks remain enabled. They should not be skipped merely because they were generated at some earlier point. `out/exact-source-map-1.0.json` is ignored build output and has a separate explicit candidate gate.

## Regression checks

Six POSIX tests in `test/test-audit-all-modes.py` exercise the actual audit script's selection and stop-on-failure behavior with inert gate substitutes. They verify unchanged default map enforcement, exactly one omitted gate in source-only mode, propagation of source failures, rejection of conflicting flags, preservation of optional package/artifact checks, and rejection of unknown flags. All six passed under Debian/WSL; shell parsing and ShellCheck error-level analysis also passed.

After the public-key link fix, the complete working-tree `sh tools/audit-all.sh --source-only`
run exited 0: all 39 selected source gates passed, including the full 30-page site gate,
the new six-test mode suite, all 140 shell entry points, current dependency audit, and all five
translation catalogues. Its final output explicitly retained the NOT CHECKED artifact/runtime/
physical limitations and NOT-a-release-approval statement. The new mode test is also wired
into `.github/workflows/quality.yml`.

This successful working-tree result is separate from the failed historical clean-candidate
result above. A later clean checkout including the website link and QA changes still needs its
own run before a clean-checkout success can be claimed.

## Corrected clean candidate result

The actual `sh tools/audit-all.sh --source-only` command subsequently exited 0
against the untouched corrected clone at
`/var/tmp/dagric-private-pro.QoSTpV/source`, exact revision
`20e24dd04ea3de802531be5139f9f36fe96a1490`. **All 40 selected gates passed**,
including the seven semantic Calamares policy regressions added after the
earlier 39-gate run. Tracked and untracked Git status were empty before and
after the audit. This is the clean source used for both completed corrected
private images, not an audit of an altered failed-build checkout.

Generated exact-source evidence and image/runtime/physical acceptance remain
separate. Later website-only privacy clarification has its own website gate,
render checks and live deployment verification in `WEBSITE-FINISHING-2026-09-05.md`.

## Final audit-tooling and website integration run

At approximately 18:07 UTC the coordinating agent's complete current-working-tree
`sh tools/audit-all.sh --source-only` run exited 0 with all **42 selected gates**
passing. This includes the added embedded-source inventory and zero-write
completion guards, 17 embedded-source fixtures, 15 commercial-gate checks,
13 security-artifact/output fixtures, and the final deployed website wording.
A separate source/security check after staging the new files also exited 0,
covering 2,293 tracked paths, 79 Python sources and 730 secret-scanned text files.

This final integration run is a working-tree/staged-source result, not a claim
that the frozen images were rebuilt from later audit-only or website changes.
The earlier clean `20e24dd` candidate's 40-gate result and exact image/source
identities remain unchanged. The new deliberate embedded-source promotion
hold was tested as a hold; no commercial success or upload authorization was
issued, and generated/runtime/physical release approval remains excluded.
