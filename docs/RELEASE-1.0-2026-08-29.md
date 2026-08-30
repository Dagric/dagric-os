# Dagric OS 1.0 “Foundation” — verified 29 August 2026 release

This release replaces the earlier Dagric OS 1.0 images with freshly built,
signed Free and Pro images. The public release record ties both files to source
revision `3f19b305464b82478ce83db8d970a2abbf326cf9`, exact byte counts, package
inventories, and SHA-256 hashes.

## Downloads

- [Download Dagric OS Free](https://dagric.com/download)
- [Buy and download Dagric OS Pro](https://dagric.com/pro)
- [Machine-readable release record](https://dagric.com/manifest/release.json)
- [Build and test record](https://dagric.com/testing)
- [Reviewer kit](https://dagric.com/review)

The ISO files are not attached to GitHub because each exceeds GitHub's release
asset limit. The Free image is hosted on Cloudflare R2; the Pro image is private
and is delivered through the Stripe-validated download gate.

## Signed artifacts

| Edition | Size | SHA-256 |
| --- | ---: | --- |
| Free — `dagric-os-1.0-amd64.iso` | 2,251,653,120 bytes | `68380d47e6eb6f98bb5c6de0fe93e4feaaed4e849317f7faefaa7a502ba117d0` |
| Pro — `dagric-os-pro-1.0-amd64.iso` | 4,152,623,104 bytes | `e373edfea1cba30cade6f3fe6ad13fb6f836e68edafcb300be2cb49fc9858c5e` |

This release attaches `SHA256SUMS`, its detached GPG signature, the signing
key, the release JSON, and both package inventories. The signing-key fingerprint
is `3A07 9F85 DE74 375D D655 5709 6CE3 7402 BA0A 0EF8`.

## Verification status

Passed in the release harness:

- Fresh, separate Free and Pro builds
- SHA-256 and detached-signature verification
- BIOS, UEFI, and virtual Secure Boot live boot
- Free-edition Calamares install and installed-system boot in a VM
- Snapshot rollback in a VM
- Public Free download re-download and hash verification
- Private Pro object/hash verification and unauthenticated-request rejection
- Live zero-total Stripe checkout, private Pro delivery, full-download hash, and
  resumed HTTP Range verification

Still open, and not represented as passed:

- Physical USB and broad retail-PC testing
- Secure Boot across varied physical firmware
- Broad Wi-Fi, GPU, suspend, camera, printer, and battery coverage
- A screen-reader review by someone who relies on one
- A non-zero Stripe test-mode checkout through the disposable staging gate (no live charge or refund)

See the [public matrix](https://dagric.com/testing) for the evidence and exact
scope behind each line.
