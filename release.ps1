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
$iso = "$repo\out\live-image-amd64.hybrid.iso"
if (-not (Test-Path $iso)) { Write-Host "No ISO - run .\build.ps1 first" -ForegroundColor Red; exit 1 }

if ($Edition -eq "pro") { $name = "dagric-os-pro-$Version-amd64.iso" }
else { $name = "dagric-os-$Version-amd64.iso" }

Copy-Item $iso "$repo\out\$name" -Force
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
