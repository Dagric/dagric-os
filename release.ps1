# Dagric OS - package a release: versioned ISO name + SHA256 checksums.
#   .\release.ps1                     # names the current ISO as free edition
#   .\release.ps1 -Edition pro        # names it as Pro
#   (Run right after the matching .\build.ps1 [-Edition pro].)
param(
    [string]$Version = "1.0",
    [ValidateSet("free","pro")][string]$Edition = "free"
)
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
if ($Edition -eq "pro") { $name = "dagric-os-pro-$Version-amd64.iso" }
else { $name = "dagric-os-$Version-amd64.iso" }

# The ISO already carries its edition's name, so there is normally nothing to
# copy. container-build.sh used to hand back live-build's own
# live-image-amd64.hybrid.iso for BOTH editions - which is why this script had
# to rename it, and why building free and then Pro overwrote the free image
# before anyone got the chance. Both build paths name their own output now.
# The legacy name is still accepted so an ISO left behind by an older container
# can be released without a 25-minute rebuild.
$iso = "$repo\out\$name"
$legacy = "$repo\out\live-image-amd64.hybrid.iso"
if (-not (Test-Path $iso)) {
    if (Test-Path $legacy) { Copy-Item $legacy $iso -Force }
    else { Write-Host "No ISO - run .\build.ps1 -Edition $Edition first" -ForegroundColor Red; exit 1 }
}
$sums = @()
Get-ChildItem "$repo\out\dagric-os-*-amd64.iso" | ForEach-Object {
    $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
    $sums += "$h  $($_.Name)"
}
$sums | Out-File "$repo\out\SHA256SUMS" -Encoding ascii
Write-Host "Release ready:" -ForegroundColor Green
Write-Host "  out\$name"
$sums | ForEach-Object { Write-Host "  $_" }
Write-Host "Publish the ISOs together with SHA256SUMS so buyers can verify."
