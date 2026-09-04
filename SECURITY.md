# Security policy

## Supported versions

| Version | Security updates |
| --- | --- |
| Dagric OS 1.0 Foundation | Supported |
| Earlier development images and tags | Not supported; upgrade before reporting |

The current verified release and its signed hashes are listed at
https://dagric.com/download.

## Report a vulnerability privately

Do not open a public issue for a vulnerability that could expose users,
credentials, signing material, the paid-download gate, or update infrastructure.

Use GitHub's **Report a vulnerability** button on the repository Security page.
If that route is unavailable, email support@dagric.com with “Security report”
in the subject or use https://dagric.com/contact.

Include:

- affected Dagric version, edition, and component;
- impact and conditions required to reproduce it;
- minimal reproduction steps or proof of concept;
- whether the issue is already public or actively exploited; and
- a safe way to contact you.

Remove unrelated personal information and never send production credentials.
We will acknowledge the report, investigate it, and coordinate disclosure based
on severity and user risk. Please allow a reasonable remediation window before
public disclosure.

## Scope

In scope are Dagric-authored packages and scripts, update and signing
infrastructure, dagric.com delivery systems, and security-relevant integration
changes made by Dagric. Vulnerabilities solely in an upstream component should
also be reported to that upstream project's security team; tell Dagric when the
issue affects a shipped release so mitigations can be evaluated.
