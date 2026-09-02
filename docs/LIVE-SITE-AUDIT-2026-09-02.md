# Dagric live-site audit — 2026-09-02

Scope: public `https://dagric.com` deployment, checked on 2026-09-02. This audit is read-only; it did not deploy, modify, or publish any site or release artifact.

## Result: pass, with one stated checksum limitation

| Check | Result | Evidence |
| --- | --- | --- |
| Primary public endpoints | PASS | `/`, `/download`, `/testers`, `/testing`, `/manifest/release.json`, `SHA256SUMS`, sitemap, and robots all returned HTTP 200. |
| Sitemap routes | PASS | 25 of 25 sitemap routes returned HTTP 200. |
| Public-site hygiene | PASS | No uppercase `PLACEHOLDER` tokens, no `trycloudflare`/`ngrok` links, and no localhost links in the fetched sitemap pages. |
| Internal root links | PASS | 31 unique internal root links were checked; none returned a 4xx/5xx response. |
| Release identity | PASS | Live manifest declares Dagric OS 1.0, source commit `3f19b305464b82478ce83db8d970a2abbf326cf9`. |
| Manifest and checksum file | PASS | Free and Pro filenames/hashes in `SHA256SUMS` match the live release manifest. |
| Release signature | PASS | `SHA256SUMS.sig` verified successfully against `dagric-signing-key.asc`; signer fingerprint: `3A079F85DE74375DD65557096CE37402BA0A0EF8`. |
| Free ISO availability | PASS | Download page links to `dagric-os-1.0-amd64.iso`; the CDN returned HTTP 206 to a byte-range request. Its advertised size, 2,251,653,120 bytes, matches the release manifest. |
| Tester flow | PASS | `/testers` is live and presents the tester entry page. |
| Limitations disclosure | PASS | `/testing` exposes a limitations section rather than claiming universal hardware proof. |

## Important release distinction

The public site is consistently presenting the signed Dagric 1.0 release. It is **not** presenting local `out/_testing.iso`; that file has a different hash and remains an unsigned test candidate.

## Remaining limitation

The audit verified the signed checksum file, its key fingerprint, the download link, CDN reachability, and ISO byte size. It did **not** download and hash the full 2.25 GB remote ISO during this live-site pass. A full end-to-end artifact audit should download the ISO from the public CDN and compare its computed SHA-256 with the signed `SHA256SUMS` entry before a release is promoted.
