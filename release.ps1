# Dagric OS - SUPERSEDED. This script must not run. Use tools/release.sh.
#
# Kept as a refusal rather than deleted, for the same reason repo.ps1 is: it was
# a documented entry point and it is the thing somebody types from habit.
#
# WHY IT HAD TO STOP. It regenerated out\SHA256SUMS and did not sign it, and it
# said nothing about signing - its closing line was "Publish the ISOs together
# with SHA256SUMS so buyers can verify", which omits the only step that makes
# verification mean anything. Run after `tools/release.sh sign`, from habit or
# by accident, it left out\SHA256SUMS NEWER than out\SHA256SUMS.sig: a manifest
# whose signature covers different bytes.
#
# tools/release.sh's own header is about exactly this failure reaching
# customers. On 2026-08-05 the published checksums did not describe the
# published ISO, so everyone following the download page's instructions was told
# their download had been tampered with. The stale-manifest guard in release.sh
# would now catch this particular version of it at publish time - but a tool
# that quietly creates the half-done state and invites you to publish it is not
# something to leave lying next to the tool that exists to prevent it.
#
# What to run instead, in order:
#
#     wsl sh tools/release.sh sign      hash out/*.iso and SIGN the manifest
#     (upload both ISOs to R2 by hand)
#     wsl sh tools/release.sh publish   verifies R2 first, then copies to site/
#     firebase deploy --only hosting
#     wsl sh packages/build-repo.sh     the update channel is half the release
#     wsl sh tools/verify-published.sh  proves the LIVE end state
param(
    [string]$Version = "1.0",
    [ValidateSet("free","pro")][string]$Edition = "free"
)

Write-Host ""
Write-Host "release.ps1 is superseded and will not run." -ForegroundColor Red
Write-Host ""
Write-Host "It wrote out\SHA256SUMS without signing it, which silently invalidates"
Write-Host "out\SHA256SUMS.sig and produces the exact half-published state that told"
Write-Host "customers their download had been tampered with on 2026-08-05."
Write-Host ""
Write-Host "Use instead:" -ForegroundColor Cyan
Write-Host "  wsl sh tools/release.sh sign"
Write-Host "  (upload both ISOs to R2)"
Write-Host "  wsl sh tools/release.sh publish"
Write-Host "  firebase deploy --only hosting"
Write-Host "  wsl sh packages/build-repo.sh"
Write-Host "  wsl sh tools/verify-published.sh"
Write-Host ""
exit 1
