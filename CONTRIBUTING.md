# Contributing to Dagric OS

Thank you for helping make Dagric clearer, safer, and easier for ordinary
computer owners. Small, testable improvements are welcome.

## Good first contributions

- Correct a confusing sentence in the offline guide.
- Improve a translation without changing its meaning.
- Add a reproducible hardware result with exact device information.
- Fix an accessibility, keyboard-navigation, or contrast issue.
- Add a negative-path test for an existing feature.
- Report a package or integration problem with evidence.

Browse issues labeled `good first issue`, `help wanted`, or `documentation`, or
start a GitHub Discussion before investing in a large change.

## Before opening an issue

1. Search existing issues and Discussions.
2. Confirm the problem against the current release or current `main` source.
3. Remove passwords, API keys, email addresses, serial numbers, and unrelated
   logs.
4. Include exact reproduction steps, expected behavior, actual behavior, and
   the relevant edition/version.

Security vulnerabilities must follow [SECURITY.md](SECURITY.md) and must not be
filed publicly.

## Pull requests

Keep one logical change per pull request. Explain the user-visible problem,
the chosen fix, the risks, and the evidence used to verify it. Preserve existing
copyright and license notices. New Dagric-authored code is submitted under the
repository's GPL-3.0-or-later terms; identified branding contributions require
confirmation that the contributor has the rights to provide them under the
stated artwork license.

Run the fast checks that match your change. The broad local entry point is:

```sh
sh tools/audit-all.sh
```

Common focused checks are:

```sh
python3 tools/check-source.py
python3 tools/check-concepts.py
python3 tools/check-release-rights.py
python3 tools/audit-site.py
sh tools/check-site.sh
```

ISO, installation, firmware, and hardware claims require the separate test
gates documented under `docs/` and `test/`. A successful source check does not
prove physical-hardware compatibility.

By contributing, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
