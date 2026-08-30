# Dagric OS reviewer and accessibility outreach packet

Prepared August 30, 2026. This is a working packet, not a record of messages sent.

## Release gate before outreach

Do not send the first-wave review pitch until the current signed ISO has completed a physical-PC drill: write it to an erasable USB drive, boot the live desktop, run Check This PC, confirm display/audio/Ethernet/Wi-Fi, install to a blank test disk, reboot without the USB, apply updates, exercise migration against disposable Windows data, and test rollback. Record the machine, firmware mode, exact ISO hash, result and any limitations in `docs/` and on `/testing`.

The release already has useful virtual-machine, checksum, Secure Boot, install, public-download and private-gate evidence. The physical test is the remaining credibility gate; component inventory is not a substitute for boot evidence.

## Public review kit

- Review hub: https://dagric.com/review
- Current proof and limitations: https://dagric.com/testing
- Free download and signed checksums: https://dagric.com/download
- Source and issue tracker: https://github.com/Dagric/dagric-os
- Accessibility record: https://dagric.com/accessibility
- Privacy: https://dagric.com/privacy
- Security: https://dagric.com/security
- Contact route: https://dagric.com/contact (choose Business / press)

Offer a private Pro review link only after a named reviewer accepts. Treat it as an evaluation copy, not payment for favorable coverage. Never send a Stripe session link publicly.

## Suggested first wave

1. **ExplainingComputers** — practical Linux and hardware coverage; current Linux index: https://www.explainingcomputers.com/linux_videos.html and contact page: https://www.explainingcomputers.com/contact.html
2. **The Linux Experiment** — desktop Linux audience; published editorial contact route: https://thelinuxexperiment.com/privacy-policy/
3. **TechHut** — Linux and homelab coverage: https://techhut.tv/ and https://techhut.tv/team
4. **Learn Linux TV** — Linux education and hands-on coverage: https://www.learnlinux.tv/
5. **Phoronix** — technically demanding Linux publication: https://www.phoronix.com/

Start with two individualized messages, learn from the response, then approach the next three. Do not mass-mail.

## Base review email

**Subject:** Hands-on review offer: Dagric OS for Windows 10-era PCs

Hello [name],

[One sentence referring to a specific recent video/article and why Dagric fits that audience.]

I build Dagric OS, a Debian 13 and KDE desktop intended for Windows 10 PCs that still work. It has no required account or Dagric telemetry, and the Free edition includes a read-only Windows migration assistant, a hardware preflight and boot-menu rollback. I am looking for an honest hands-on test, including criticism—not sponsored coverage.

The reviewer page, current test evidence and known limitations are at https://dagric.com/review and https://dagric.com/testing. The Free ISO, signed checksum and source are public. If useful, I can provide a private Pro evaluation link and answer technical questions.

There is no embargo and no requirement for positive coverage. Please disclose the evaluation copy if you use it.

Thank you,

[Owner name]<br>
DGR Operations / Dagric OS<br>
[Reply email]

## Personalization prompts

- **ExplainingComputers:** connect the pitch to keeping capable Windows 10-era desktop hardware useful and ask for a real-hardware installation test.
- **The Linux Experiment:** emphasize the first-run desktop experience, privacy disclosures and whether the Windows-migration story survives skeptical testing.
- **TechHut:** ask for scrutiny of installation, firmware/hardware support and the reproducible public proof trail.
- **Learn Linux TV:** offer the source/config tree as teaching material and ask whether the setup is understandable to a Linux newcomer.
- **Phoronix:** lead with Debian 13/KDE, signed artifacts, manifests and test methodology; make no performance claim without benchmarks.

## Accessibility review brief

Fable provides paid testing by trained assistive-technology users: https://makeitfable.com/testers/.

Ask for an independent review of these customer-critical journeys:

1. Understand the homepage purpose and reach Free download.
2. Locate the SHA-256 checksum and verification instructions.
3. Compare Free and Pro without relying on color alone.
4. Complete and recover from errors in the contact form.
5. Read the proof, accessibility, privacy and refund terms.
6. Use keyboard-only navigation at 200% zoom and with reduced motion.
7. Test with NVDA/JAWS on Windows and VoiceOver on iOS or macOS, including headings, landmarks, focus order, skip link, form labels, status messages and checkout handoff.

Request a severity-ranked report with reproduction steps and assistive-technology/browser versions. Do not claim independent accessibility validation until the review is complete and published accurately.

## Before anything is sent

Fill in the owner's preferred public name, sender address, selected recipients and accessibility-review budget. Sending messages or purchasing a review requires separate approval because it speaks for the business or spends money.
